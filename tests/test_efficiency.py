import copy
from email.message import Message
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import urllib.error

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('efficiency_'+name,ROOT/'scripts/v2'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


research=load('research');collector=load('collect');photos=load('photo_library');checks=load('checks');usage=load('usage')


class EfficiencyTests(unittest.TestCase):
    def policy(self):return json.loads((ROOT/'templates/v2/research-policy.json').read_text())

    def opportunity(self):
        return {'id':'ordinary','kind':'grant','status':'open','verified_at':'2026-10-15T08:00:00+03:00','deadline':'2026-11-20','opens_at':None}

    def test_due_policy_carries_records_without_advancing_verification(self):
        record=self.opportunity();original=copy.deepcopy(record)
        result=research.opportunity_due(record,research.instant('2026-10-15T19:30:00+03:00'),self.policy())
        self.assertFalse(result['due']);self.assertEqual(record,original)
        record['deadline']='2026-10-16'
        self.assertTrue(research.opportunity_due(record,research.instant('2026-10-15T19:30:00+03:00'),self.policy())['due'])
        record.update(deadline='2026-11-20',id='cy-home-energy-2026')
        self.assertIn('budget_sensitive',research.opportunity_due(record,research.instant('2026-10-15T19:30:00+03:00'),self.policy())['reasons'])

    def test_closed_and_legal_records_are_not_researched_every_slot(self):
        record=self.opportunity();record.update(status='closed',deadline='2024-07-31')
        self.assertFalse(research.opportunity_due(record,research.instant('2026-10-16T07:30:00+03:00'),self.policy())['due'])
        record.update(status='open',kind='legal_right',deadline=None)
        self.assertFalse(research.opportunity_due(record,research.instant('2026-10-16T07:30:00+03:00'),self.policy())['due'])
        record.update(kind='grant',deadline='2026-10-14')
        self.assertIn('status_date_conflict',research.opportunity_due(record,research.instant('2026-10-16T07:30:00+03:00'),self.policy())['reasons'])

    def test_packet_excludes_target_future_slots_and_keeps_original_opportunity_times(self):
        with tempfile.TemporaryDirectory() as directory:
            packet,path=research.prepare(ROOT,'2026-10-15','midday','2026-10-15T22:00:00+03:00',directory)
            self.assertTrue(path.is_file());self.assertTrue(packet['broad_news_scan_required'])
            self.assertEqual(packet['section_targets'],{'world':5,'cyprus':5})
            self.assertEqual(packet['market_reference']['edition_id'],'2026-10-15-morning')
            self.assertTrue(all(r['slot']=='morning' for r in packet['stories']))
            self.assertTrue(all(r['record']['verified_at']==r['review']['verified_at'] for r in packet['opportunities']))
            self.assertNotIn('us-ppi-september-2026-release',[s['story_id'] for s in packet['stories']])

    def test_packet_filters_future_private_notes_and_never_exports_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            private=Path(directory);(private/'research').mkdir()
            sid='tsmc-q3-2026-results-preview'
            (private/'research/editorial-memory.json').write_text(json.dumps({'stories':{sid:{'reviewed_at':'2026-10-16T12:00:00+03:00','unresolved':['PRIVATE-NOTE-MARKER']}}}))
            packet,_=research.prepare(ROOT,'2026-10-15','evening','2026-10-15T19:30:00+03:00',private)
            self.assertNotIn('PRIVATE-NOTE-MARKER',json.dumps(packet))
            self.assertNotIn('PRIVATE-NOTE-MARKER',json.dumps(research.index(ROOT)))
        with self.assertRaisesRegex(ValueError,'outside'):research.private_folder(ROOT,ROOT/'docs/private-state')

    def test_checkpoint_resume_requires_matching_inputs_and_excludes_future_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            private=Path(directory)/'private'
            result=research.remember(ROOT,'2026-10-15-evening','2026-10-15T22:00:00+03:00',private,
                {'us-ppi-september-2026-release':{'unresolved':['A specifically dated follow-up question.'],'next_check_at':'2026-10-16T07:30:00+03:00'}})
            packet,_=research.prepare(ROOT,'2026-10-15','evening','2026-10-15T22:05:00+03:00',private)
            self.assertEqual(packet['resume_research']['source_sha256'],result['source_sha256'])
            with self.assertRaisesRegex(ValueError,'future source'):research.remember(ROOT,'2026-10-15-evening','2026-10-15T07:00:00+03:00',private)

    def test_new_publication_cannot_carry_due_active_terms_as_current(self):
        record=self.opportunity();record['verified_at']='2026-10-14T08:00:00+03:00'
        edition={'status':'published','date':'2026-10-16','published_at':'2026-10-16T08:00:00+03:00','opportunities':[record]}
        with self.assertRaisesRegex(ValueError,'Due opportunity'):research.validate_opportunity_reviews(ROOT,edition)
        record.update(verified_at='2026-10-16T07:45:00+03:00',status='needs_verification')
        research.validate_opportunity_reviews(ROOT,edition)
        edition['date']='2026-10-15';research.validate_opportunity_reviews(ROOT,edition)

    def test_draft_scaffold_copies_stable_data_without_fabricating_reviews(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'public';private=Path(directory)/'private'
            for name in ('content','templates'):shutil.copytree(ROOT/name,root/name)
            # This fixture models a new slot even after the real dated edition exists.
            (root/'content/editions/2026-10-16-morning.json').unlink(missing_ok=True)
            shutil.rmtree(root/'content/articles/2026-10-16-morning',ignore_errors=True)
            packet,path=research.prepare(root,'2026-10-16','morning','2026-10-16T07:30:00+03:00',private)
            eid=packet['edition_id'];article_path=f'articles/{eid}/lead.json'
            local=root/'content'/article_path;local.parent.mkdir(parents=True)
            article=json.loads((ROOT/'content/articles/2026-10-15-evening/lead.json').read_text())
            article.update(edition_id=eid,id='lead',url=f'articles/{eid}/lead.html');local.write_text(json.dumps(article))
            result=research.scaffold(root,path,'Πρωινή ελεγχόμενη υποψήφια έκδοση',[article_path])
            edition=json.loads((root/'content/editions'/f'{eid}.json').read_text())
            self.assertEqual(result['copied_quotes'],38);self.assertEqual(edition['status'],'draft');self.assertIsNone(edition['published_at'])
            self.assertNotIn('reading_review',edition);self.assertNotIn('image_review',edition);self.assertNotIn('panels',edition)
            self.assertEqual(edition['opportunities'],[o['record'] for o in packet['opportunities']])
            with self.assertRaisesRegex(ValueError,'Resume'):research.scaffold(root,path,'Do not replace',[article_path])

    def test_wire_discovery_uses_newest_items_and_requires_fresh_health(self):
        with tempfile.TemporaryDirectory() as directory:
            private=Path(directory)/'private';wire=Path(directory)/'wire';(wire/'docs').mkdir(parents=True)
            (wire/'docs/wire-health.json').write_text(json.dumps({'last_success_at':'2026-10-15T21:30:00+03:00'}))
            items=[{'title':str(i),'published_at':f'2026-10-15T20:{i:02}:00+03:00','link':'https://example.org/'+str(i)} for i in range(60)]
            (wire/'docs/live-wire.json').write_text(json.dumps(items))
            packet,_=research.prepare(ROOT,'2026-10-15','evening','2026-10-15T22:00:00+03:00',private,wire)
            self.assertEqual(packet['discovery']['items'][0]['title'],'59');self.assertEqual(len(packet['discovery']['items']),40)
            (wire/'docs/wire-health.json').write_text(json.dumps({'last_success_at':'2026-10-15T18:00:00+03:00'}))
            packet,_=research.prepare(ROOT,'2026-10-15','evening','2026-10-15T22:00:00+03:00',private,wire)
            self.assertEqual(packet['discovery']['items'],[]);self.assertEqual(packet['discovery']['status'],'stale_use_direct_scan')

    def response(self,raw=b'<main>Verified source terms</main>',kind='text/html',url='https://www.industry.gov.cy/call'):
        response=mock.MagicMock();response.__enter__.return_value=response
        response.status=200;response.geturl.return_value=url;response.read.return_value=raw
        headers=Message();headers['Content-Type']=kind;headers['ETag']='"first"';response.headers=headers
        return response

    def test_conditional_source_cache_preserves_retrieval_and_never_creates_verified_at(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory);url='https://www.industry.gov.cy/call';settings=self.policy()['network']
            first=collector.fetch(url,cache,'2026-10-15T08:00:00+03:00',settings,lambda *a,**k:self.response())
            self.assertEqual(first['status'],'baseline_requires_review')
            seen=[]
            def unchanged(request,**kwargs):
                seen.append(request.get_header('If-none-match'));raise urllib.error.HTTPError(url,304,'Not modified',{},None)
            second=collector.fetch(url,cache,'2026-10-15T14:00:00+03:00',settings,unchanged)
            self.assertEqual(second['status'],'unchanged');self.assertEqual(second['retrieved_at'],first['retrieved_at'])
            self.assertEqual(second['checked_at'],'2026-10-15T14:00:00+03:00');self.assertEqual(seen,['"first"'])
            self.assertNotIn('verified_at',second)
            third=collector.fetch(url,cache,'2026-10-15T19:00:00+03:00',settings,lambda *a,**k:self.response(b'<main>Applications closed</main>'))
            self.assertEqual(third['status'],'changed')

    def test_collector_bounds_failures_and_rejects_unapproved_destinations(self):
        for url in ('http://www.industry.gov.cy','https://localhost/a','https://gov.cy.evil.example/a','https://www.industry.gov.cy:bad/a'):
            self.assertFalse(collector.permitted(url))
        with tempfile.TemporaryDirectory() as directory:
            opener=mock.Mock(side_effect=urllib.error.URLError('offline'))
            with mock.patch.object(collector.time,'sleep'):
                result=collector.fetch('https://www.industry.gov.cy/a',Path(directory),'2026-10-15T14:00:00+03:00',self.policy()['network'],opener)
            self.assertEqual(result['status'],'unavailable');self.assertEqual(opener.call_count,2)

    def quote(self):return json.loads((ROOT/'content/editions/2026-10-15-evening.json').read_text())['markets'][0]

    def yahoo(self):
        return {'status':'changed','url':'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=5d',
            'retrieved_at':'2026-10-15T20:40:00+03:00','parsed_json':{'chart':{'result':[{'meta':{'symbol':'^GSPC','regularMarketPrice':7800.0,'regularMarketTime':1792086000,'currency':'USD','chartPreviousClose':7700}}]}}}

    def test_market_candidates_reject_identity_currency_future_and_ambiguous_daily_baselines(self):
        raw=self.yahoo();raw['parsed_json']['chart']['result'][0]['meta']['regularMarketTime']=int(research.instant('2026-10-15T20:39:00+03:00').timestamp())
        candidate=collector.yahoo_candidate(self.quote(),raw,'2026-10-15T20:40:00+03:00')
        self.assertIsNotNone(candidate);self.assertEqual(candidate['quote']['status'],'delayed');self.assertIsNone(candidate['quote']['change_pct'])
        self.assertTrue(candidate['requires_close_review'])
        raw['parsed_json']['chart']['result'][0]['meta']['currency']='EUR'
        self.assertIsNone(collector.yahoo_candidate(self.quote(),raw,'2026-10-15T20:40:00+03:00'))
        raw['parsed_json']['chart']['result'][0]['meta']['currency']='USD'
        self.assertIsNone(collector.yahoo_candidate(self.quote(),raw,'2026-10-15T20:00:00+03:00'))

    def test_only_explicit_matching_draft_quote_application_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'content/editions').mkdir(parents=True);shutil.copytree(ROOT/'templates',root/'templates')
            edition=json.loads((ROOT/'content/editions/2026-10-15-evening.json').read_text());edition['status']='draft'
            target=root/'content/editions'/f'{edition["id"]}.json';target.write_text(json.dumps(edition))
            q=copy.deepcopy(edition['markets'][0]);q.update(value=7800.0,quoted_at='2026-10-15T20:39:00+03:00',status='delayed')
            for source in q['sources']:source['retrieved_at']='2026-10-15T20:40:00+03:00'
            report=root/'report.json';report.write_text(json.dumps({'edition_id':edition['id'],'records':[{'quote_candidate':{'quote':q}}]}))
            result=collector.apply_quotes(root,edition['id'],report,['^GSPC'],'2026-10-15T20:40:00+03:00')
            self.assertEqual(result['updated_quotes'],['^GSPC']);self.assertEqual(json.loads(target.read_text())['markets'][0]['value'],7800)
            edition['status']='published';target.write_text(json.dumps(edition))
            with self.assertRaisesRegex(ValueError,'matching draft'):collector.apply_quotes(root,edition['id'],report,['^GSPC'],'2026-10-15T20:40:00+03:00')

    def test_photo_reuse_requires_explicit_editorial_review_and_keeps_rights(self):
        candidates=photos.find(ROOT,'tsmc-q3-2026-results-preview');self.assertTrue(candidates)
        candidate=candidates[0]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('content','docs'):shutil.copytree(ROOT/name,root/name)
            eid='2026-10-16-midday';article_id='reused-photo'
            old=json.loads((ROOT/'content/editions/2026-10-15-midday.json').read_text())
            edition={**old,'id':eid,'date':'2026-10-16','status':'draft','articles':[f'articles/{eid}/{article_id}.json']}
            path=root/'content/articles'/eid/(article_id+'.json');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({'id':article_id,'edition_id':eid}))
            (root/'content/editions'/f'{eid}.json').write_text(json.dumps(edition))
            args=(root,eid,article_id,candidate['id'],'A truthful archival photograph and its original date.','An accessible archival description.','2026-10-16T13:00:00+03:00')
            with self.assertRaisesRegex(ValueError,'Explicit'):photos.reuse(*args)
            result=photos.reuse(*args,confirmed=True);stored=json.loads(path.read_text())['image']
            self.assertEqual(stored['retrieved_at'],candidate['image']['retrieved_at'])
            self.assertEqual(stored['license'],candidate['image']['license']);self.assertEqual(photos.sha(root/'docs'/result['asset']),candidate['id'])
            self.assertFalse(stored['url'].startswith('assets/brands/'))

    def test_cached_photos_do_not_repeat_network_pacing(self):
        prepare=load('prepare_images')
        with mock.patch.object(prepare.time,'sleep') as pause,mock.patch.object(prepare.urllib.request,'urlopen') as network:
            prepare.prepare(ROOT,'2026-10-15-evening')
            pause.assert_not_called();network.assert_not_called()

    def test_ci_prepares_missing_selected_images_and_prebuilt_checks_do_not_download(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'content/editions').mkdir(parents=True)
            (root/'content/articles/current').mkdir(parents=True)
            edition={'id':'current','status':'published','image_review':{'version':2},'articles':['articles/current/story.json']}
            (root/'content/editions/current.json').write_text(json.dumps(edition))
            (root/'content/editions/legacy.json').write_text(json.dumps({
                'id':'legacy','status':'published','articles':['legacy-illustration.json']}))
            url='https://upload.wikimedia.org/wikipedia/commons/example.jpg'
            asset=root/'docs/assets/editorial/current/story.webp'
            (root/'content/articles/current/story.json').write_text(json.dumps({'image':{
                'url':'assets/editorial/current/story.webp','original_url':url}}))
            payload=io.BytesIO();Image.new('RGB',(400,300),'blue').save(payload,'JPEG')
            response=mock.MagicMock();response.__enter__.return_value=response
            response.headers.get_content_type.return_value='image/jpeg'
            response.geturl.return_value=url;response.read.return_value=payload.getvalue()
            with mock.patch('urllib.request.urlopen',return_value=response) as network,mock.patch('time.sleep'):
                with self.assertRaisesRegex(ValueError,'Missing image asset'):
                    checks.prepare_candidate_images(root,['current'],verify_only=True)
                network.assert_not_called()
                result=checks.prepare_candidate_images(root,['current'])
                self.assertEqual(result['edition_ids'],['current']);self.assertTrue(asset.is_file())
                network.assert_called_once()
                with Image.open(asset) as decoded:self.assertEqual(decoded.format,'WEBP')
                original=asset.read_bytes();network.reset_mock()
                result=checks.prepare_candidate_images(root,verify_only=True)
                self.assertEqual(result['edition_ids'],['current'])
                network.assert_not_called();self.assertEqual(asset.read_bytes(),original)

    def test_code_changes_cannot_downgrade_to_content_checks(self):
        with mock.patch.object(checks,'classify',return_value={'profile':'full','changed_files':['templates/v2/x.css'],'edition_ids':[]}):
            with self.assertRaisesRegex(ValueError,'cannot use'):checks.run(ROOT,profile='content',execute=mock.Mock())

    def test_source_only_ci_builds_before_file_validation_and_still_rejects_missing_readers(self):
        fixture_spec=importlib.util.spec_from_file_location('source_only_fixture',ROOT/'tests/test_structured_content.py')
        fixture=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(fixture)
        helper=fixture.StructuredContentTests();helper.setUp()
        with tempfile.TemporaryDirectory() as directory:
            edition,articles=helper.edition,helper.articles
            root=helper.fixture_root(directory,edition,articles)
            self.assertFalse((root/'docs'/edition['url']).exists())
            with self.assertRaisesRegex(ValueError,'unavailable edition'):
                load('publish').validate(root)
            executed=[]
            def execute(name,command,fn):
                executed.append(name)
                if fn:fn()
            with mock.patch.object(checks,'classify',return_value={
                    'profile':'content','changed_files':['content/editions/'+edition['id']+'.json'],
                    'edition_ids':[edition['id']]}):
                result=checks.run(root,execute=execute)
                self.assertEqual(result['status'],'passed')
                self.assertEqual(executed,['content','preview','integrity'])
                reader=root/'docs'/articles[0]['url']
                self.assertTrue(reader.is_file());reader.unlink()
                with self.assertRaisesRegex(ValueError,'unavailable reader'):
                    checks.run(root,prebuilt=True,execute=execute)
                report=json.loads((root/'.work/check-report.json').read_text())
                self.assertEqual(report['failed_step'],'content')

    def test_routine_and_code_change_profiles_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);subprocess.run(['git','init','--initial-branch=main',str(root)],check=True,capture_output=True)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL)
            git('config','user.name','Test');git('config','user.email','test@example.org')
            (root/'content/editions').mkdir(parents=True);path=root/'content/editions/2026-10-16-evening.json';path.write_text('{}')
            git('add','.');git('commit','-m','Initial');path.write_text('{"status":"draft"}')
            self.assertEqual(checks.classify(root,'HEAD')['profile'],'content')
            self.assertEqual(checks.classify(root,'HEAD')['edition_ids'],['2026-10-16-evening'])
            (root/'scripts').mkdir();(root/'scripts/helper.py').write_text('pass')
            self.assertEqual(checks.classify(root,'HEAD')['profile'],'maintenance')

    def test_usage_does_not_translate_work_into_quota_and_handles_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            packet,path=research.prepare(ROOT,'2026-10-15','evening','2026-10-15T19:30:00+03:00',directory)
            result=usage.record(ROOT,path,private_root=directory,before=60,after=10,same_window=True)
            self.assertIsNone(result['pro_usage_observation']['window_delta_percent']);self.assertIsNone(result['actual_edition_quota_cost'])
            self.assertEqual(result['quality']['status'],'not_recorded')
            result=usage.record(ROOT,path,private_root=directory,before=10,after=20,same_window=True)
            self.assertEqual(result['pro_usage_observation']['window_delta_percent'],10)

    def test_compact_runtime_keeps_critical_contracts_and_avoids_old_startup(self):
        runtime=(ROOT/'BRIEFING_RUNTIME.md').read_text()
        for phrase in ('private Pages','source/quote times','morning','image_review.version=2','No fuzzy automatic','No arbitrary quota/time limit','unchanged historical','No PR merge'):
            self.assertIn(phrase,runtime)
        for path in (ROOT/'templates/v2/task-prompts').glob('*.txt'):
            text=path.read_text();self.assertLess(len(text),5500)
            self.assertIn('BRIEFING_RUNTIME.md',text);self.assertIn('never emit unsupported fields',text)


if __name__=='__main__':unittest.main()
