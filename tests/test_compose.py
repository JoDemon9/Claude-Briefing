"""Regression coverage for the audited single-payload and public rendering contracts."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('audit_' + name, ROOT/'scripts/v2'/(name+'.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


compose, build, publish = load('compose'), load('build'), load('publish')


def payload_fixture():
    # Existing public content is fixture data, not a new editorial verification.
    edition = json.loads((ROOT/'content/editions/2026-10-21-evening.json').read_text(encoding='utf-8'))
    payload = {key:copy.deepcopy(edition[key]) for key in (*compose.REQUIRED, *compose.OPTIONAL) if key in edition}
    payload.update(edition_id=edition['id'], edition_mode='evening_synthesis')
    payload['executive_scan'] = {key:'Δοκιμαστικό κείμενο για έλεγχο της δομής, χωρίς νέα δημοσίευση.' for key in ('geopolitics_macro','cyprus_institutions','markets_tech')}
    payload['executive_scan']['day_catalysts'] = ['Επόμενος έλεγχος αποκλειστικά στο δοκιμαστικό σενάριο.']
    catalog = json.loads((ROOT/'docs/data/photo-library.json').read_text(encoding='utf-8'))
    payload['articles'] = []
    for relative in edition['articles']:
        art = json.loads((ROOT/'content'/relative).read_text(encoding='utf-8'))
        raw = copy.deepcopy(art)
        raw.update(slug=art['id'], section=art['daily']['section'], is_lead=art['story_id']==edition['daily']['lead_story_id'])
        image = art['image']
        photo = next(p for p in catalog['photos'] if p['id']==load('photo_library').sha(ROOT/'docs'/image['url']))
        raw['image_selection'] = {'photo_id':photo['id'], 'reviewed_at':edition['editorial_completed_at'],
                                 'relevance_and_archive_date_checked':True, 'caption':image['caption'], 'alt':image['alt']}
        raw['analysis_sources'] = [s['url'] for s in art['sources'] if s['access']=='read' and s['used_for_claims']]
        payload['articles'].append(raw)
    for wire in payload.get('fast_wire', []):
        wire['source_url'] = payload['articles'][0]['sources'][0]['url']
    return payload


def current_slot(payload):
    payload.update(edition_id='2026-10-22-evening',published_at='2026-10-22T20:15:00+03:00',
                   editorial_completed_at='2026-10-22T20:15:00+03:00')
    return payload


class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.payload = payload_fixture()

    def test_explicit_blocks_times_and_rights_survive_without_mutating_input(self):
        original = copy.deepcopy(self.payload)
        edition, docs, files = compose.compile_payload(self.payload, ROOT)
        for key in ('markets','market_summary','opportunities','panels','sports','freshness'):
            self.assertEqual(edition.get(key), original.get(key))
        self.assertEqual(docs[0]['story_id'], original['articles'][0]['story_id'])
        self.assertEqual(docs[0]['daily']['events'], original['articles'][0]['daily']['events'])
        self.assertEqual(self.payload, original)
        catalog = json.loads((ROOT/'docs/data/photo-library.json').read_text(encoding='utf-8'))
        photo = next(p for p in catalog['photos'] if p['id']==docs[0]['image']['reuse_review']['sha256'])
        for key in ('license','attribution','source_url','original_url','retrieved_at'):
            self.assertEqual(docs[0]['image'][key], photo['image'][key])
        self.assertEqual(len(edition['markets']), 38)
        self.assertIn('docs/'+docs[0]['image']['url'], files)

    def test_missing_core_review_fails_but_optional_gaps_and_bad_articles_do_not(self):
        for key in ('published_at','editorial_completed_at','reading_review'):
            with self.subTest(key=key):
                value=copy.deepcopy(self.payload);del value[key]
                with self.assertRaisesRegex(ValueError,'Missing reviewed'):compose.compile_payload(value, ROOT)
        self.payload['articles'][0]['sources']=[]
        current_slot(self.payload)
        edition, docs, _=compose.compile_payload(self.payload, ROOT)
        self.assertNotIn(self.payload['articles'][0]['slug'],[a['id'] for a in docs])
        self.assertTrue(edition['availability_notes'])
        self.payload=payload_fixture();self.payload['markets']=[]
        edition, _, _=compose.compile_payload(self.payload, ROOT)
        self.assertEqual(len(edition['markets']),38)
        self.assertTrue(all(q['status']=='unavailable' for q in edition['markets']))

    def test_wrong_photo_or_missing_editorial_approval_cannot_fallback(self):
        for change in ({'photo_id':'0'*64}, {'relevance_and_archive_date_checked':False}):
            value=copy.deepcopy(self.payload);value['articles'][0]['image_selection'].update(change)
            edition, docs, _=compose.compile_payload(value, ROOT)
            self.assertIsNone(docs[0]['image'])
            self.assertTrue(docs[0]['image_unavailable_reason'])

    def test_no_guessed_summary_links_and_no_relabelled_sources(self):
        self.payload['daily']['summary_story_ids'][0]=['invented-story']
        edition, _, _=compose.compile_payload(self.payload, ROOT)
        self.assertNotIn('invented-story',str(edition['daily']['summary_story_ids']))
        self.payload=payload_fixture();del self.payload['articles'][0]['sources'][0]['access']
        current_slot(self.payload)
        _, docs, _=compose.compile_payload(self.payload, ROOT)
        self.assertNotIn(self.payload['articles'][0]['slug'],[a['id'] for a in docs])

    def test_world_lead_keeps_its_real_section_and_slot_and_slug_are_explicit(self):
        self.payload['articles'][0]['section']='world'
        # A source-only section exception must be supplied explicitly, never synthesized.
        self.payload['selection_review']['global_exception_reason']='Δοκιμαστική πρόσθετη διεθνής κάλυψη με τεκμηριωμένη εξαίρεση.'
        self.payload['selection_review']['section_shortfalls']['cyprus']={
            'reason':'Δοκιμαστική τεκμηριωμένη έλλειψη μετά από έρευνα ανεξάρτητων πηγών.',
            'checked_sources':['https://example.org/news','https://example.net/news']}
        _, docs, _=compose.compile_payload(self.payload, ROOT)
        self.assertEqual(docs[0]['daily']['section'],'world')
        self.payload['articles'][0]['slug']='../unsafe'
        with self.assertRaisesRegex(ValueError,'safe ASCII'):compose.compile_payload(self.payload, ROOT)

    def test_future_evidence_and_bare_fixtures_are_rejected(self):
        self.payload['articles'][0]['sources'][0]['retrieved_at']='2099-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'editorial completion'):compose.compile_payload(self.payload, ROOT)
        self.payload=payload_fixture();self.payload['sports']['coverage']['manutd']['next_fixture']='Invented new fixture'
        edition, _, _=compose.compile_payload(self.payload, ROOT)
        self.assertIsNone(edition['sports']['coverage']['manutd']['next_fixture'])

    def test_failure_rolls_back_all_written_candidate_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'payload.json';path.write_text('{}')
            target=root/'content/editions/test.json';target.parent.mkdir(parents=True);target.write_bytes(b'old')
            builder=mock.Mock();builder.validate.side_effect=ValueError('semantic failure')
            real_module=compose.module
            with mock.patch.object(compose,'compile_payload',return_value=({'id':'test'},[],{'content/editions/test.json':b'new','content/articles/test/new.json':b'new'})), \
                 mock.patch.object(compose,'module',side_effect=lambda name:builder if name=='build' else real_module(name)):
                with self.assertRaisesRegex(ValueError,'semantic failure'):compose.compose_edition(path,root=root)
            self.assertEqual(target.read_bytes(),b'old')
            self.assertFalse((root/'content/articles/test/new.json').exists())

    def test_publish_requires_explicit_portal_before_writing(self):
        with self.assertRaisesRegex(ValueError,'portal-root'):compose.compose_edition(Path('absent.json'),publish=True)

    def test_scaffold_contains_only_unknown_quotes_and_no_invented_reviews(self):
        draft=compose.scaffold('2026-10-22-morning',ROOT)
        self.assertEqual(len(draft['markets']),38)
        self.assertTrue(all(q['value'] is None and q['status']=='unavailable' for q in draft['markets']))
        self.assertIsNone(draft['image_review']['completed_at'])
        self.assertEqual(draft['freshness'],[])

    def test_major_sports_metadata_can_be_derived_without_padding_or_misclassification(self):
        del self.payload['sports']['major_stories']
        sport=next(a for a in self.payload['articles'] if a['section']=='sports')
        sport['sports_interest']='manutd'
        sport['why_it_matters']='Αυτό είναι ρητό δοκιμαστικό συντακτικό κείμενο για τη σημασία του θέματος.'
        edition, docs, _=compose.compile_payload(self.payload,ROOT)
        self.assertEqual(edition['sports']['major_stories'][0]['article_id'],sport['slug'])
        self.assertEqual(next(a for a in docs if a['id']==sport['slug'])['sports_interest'],'manutd')

    def test_one_sourced_article_without_optional_desks_or_photos_is_publishable(self):
        source=current_slot(payload_fixture())
        payload={key:source[key] for key in compose.REQUIRED}
        payload['edition_id']=source['edition_id']
        payload['articles']=[copy.deepcopy(source['articles'][0])]
        payload['articles'][0].pop('image_selection')
        edition, docs, _=compose.compile_payload(payload,ROOT)
        self.assertIsNone(docs[0]['image'])
        self.assertEqual(len(edition['markets']),38)
        self.assertEqual(edition['panels'],[])
        self.assertEqual(len(edition['sports']['coverage']),4)
        build.ROOT=ROOT
        build.validate(edition,docs)
        self.assertTrue(edition['availability_notes'])
        daily=load('daily');model=daily.compose(edition['date'],[(edition,docs)])
        doc=BeautifulSoup(daily.render(build,model,[(edition,docs)]),'html.parser')
        self.assertIsNotNone(doc.select_one('#cyprus'))
        self.assertIsNotNone(doc.select_one('#world'))

    def test_zero_sourced_articles_is_a_real_blocker(self):
        self.payload=current_slot(self.payload)
        for row in self.payload['articles']:row['sources']=[]
        with self.assertRaisesRegex(ValueError,'No supported article'):compose.compile_payload(self.payload,ROOT)

    def test_f1_payload_alias_is_normalized_before_schema_validation(self):
        raw=next(a for a in self.payload['articles'] if a['section']=='sports')
        raw['sports_interest']='f1'
        _, docs, _=compose.compile_payload(self.payload,ROOT)
        self.assertEqual(next(a for a in docs if a['id']==raw['slug'])['sports_interest'],'formula1')

    def test_due_opportunities_are_archival_without_refreshing_verified_time(self):
        edition, articles, _=compose.compile_payload(current_slot(self.payload),ROOT)
        original=self.payload['opportunities'][0]
        record=edition['opportunities'][0]
        self.assertEqual(record['verified_at'],original['verified_at'])
        self.assertTrue(record['review_due'])
        daily=load('daily')
        model=daily.compose(edition['date'],[(edition,articles)])
        schema=json.loads((ROOT/'templates/v2/day.schema.json').read_text(encoding='utf-8'))
        validator=Draft202012Validator(schema,format_checker=FormatChecker())
        validator.validate(model)
        self.assertEqual(model['opportunities'][0],record)
        doc=BeautifulSoup(load('opportunities').render(build,model['opportunities']),'html.parser')
        self.assertFalse(doc.select('.opportunity-apply'))
        self.assertIn('Παλιότερη ενημέρωση',doc.text)
        model['opportunities'][0]['review_due']='true'
        with self.assertRaises(ValidationError):validator.validate(model)

    def test_edition_and_day_share_the_complete_opportunity_contract(self):
        schemas=[json.loads((ROOT/'templates/v2'/name).read_text(encoding='utf-8'))
                 for name in ('content.schema.json','day.schema.json')]
        self.assertEqual(schemas[0]['$defs']['opportunity'],schemas[1]['$defs']['opportunity'])


class RenderingAndPublicationTests(unittest.TestCase):
    def test_unavailable_sports_attempt_preserves_last_successful_check(self):
        news=load('sports_news');at='2026-10-22T07:00:00Z';old='2026-10-20T07:00:00Z'
        row={'source_url':news.LISTINGS['omonoia'],'checked_at':old,'attempted_at':at,
             'status':'unavailable','items':[],'note':'source_unavailable'}
        edition={'date':'2026-10-22','status':'published','published_at':at,
                 'sports':{'news_links':{key:dict(row,source_url=url) for key,url in news.LISTINGS.items()}}}
        news.validate(edition)
        self.assertEqual(edition['sports']['news_links']['omonoia']['checked_at'],old)
        self.assertFalse(news.not_future('invalid-date',at))

    def test_rss_skips_betting_and_youth_before_selecting_headlines(self):
        news=load('sports_news')
        raw=b'<rss><channel><item><title>Real Madrid Youth League lineup</title><link>https://example.org/youth</link></item><item><title>Real Madrid first team preparation</title><link>https://example.org/first</link></item></channel></rss>'
        response=mock.MagicMock();response.__enter__.return_value=response;response.read.return_value=raw
        rows=news.fetch_rss_feed('https://example.org/feed',opener=mock.Mock(return_value=response),limit=1)
        self.assertEqual([r['headline'] for r in rows],['Real Madrid first team preparation'])

    def test_analysis_and_delta_are_escaped_and_available_inside_cards(self):
        payload=payload_fixture();edition, docs, _=compose.compile_payload(payload, ROOT)
        docs[0]['delta_update']='<script>delta</script>'
        doc=BeautifulSoup(build.card(edition,docs[0]),'html.parser')
        self.assertIsNotNone(doc.select_one('.card-analysis .article-layer'))
        self.assertIn('Τι παρακολουθούμε',doc.text)
        self.assertIn('<script>delta</script>',doc.text)
        self.assertFalse(doc.select('script'))

    def test_day_and_edition_share_scan_and_favourite_story_cards(self):
        payload=payload_fixture();edition, docs, _=compose.compile_payload(payload, ROOT)
        sport=next(a for a in docs if a['daily']['section']=='sports');sport['sports_interest']='omonoia'
        edition['delta_log']=['Ρητή νέα εξέλιξη δοκιμής.']
        daily=load('daily');model=daily.compose(edition['date'],[(edition,docs)])
        doc=BeautifulSoup(daily.render(build,model,[(edition,docs)]),'html.parser')
        self.assertEqual(len(doc.select('.executive-scan')),1)
        self.assertTrue(doc.select('.fast-wire-ticker .wire-item'))
        self.assertIn('Ρητή νέα εξέλιξη δοκιμής.',doc.select_one('.midday-delta-callout').text)
        self.assertIn(sport['headline'],doc.select_one('#other-sports').text)
        self.assertTrue(doc.select('.card-analysis .article-layer'))

    def test_legacy_scan_and_watch_alias_remain_visible(self):
        edition=json.loads((ROOT/'content/editions/2026-10-21-evening.json').read_text(encoding='utf-8'))
        doc=BeautifulSoup(build.edition_scan(edition),'html.parser')
        self.assertEqual(len(doc.select('.scan-col')),3)
        self.assertIn('Διπλωματική κινητικότητα',doc.text)
        self.assertIn('legacy trigger',build.article_layers({'scenarios':{'what_to_watch':'legacy trigger'}}))

    def test_three_favourite_sports_are_allowed_only_after_cutoff(self):
        edition, docs, _=compose.compile_payload(payload_fixture(), ROOT)
        sport=next(a for a in docs if a['daily']['section']=='sports')
        sports=[];records=[]
        for i,key in enumerate(('omonoia','realmadrid','f1')):
            item=copy.deepcopy(sport);item.update(id='sport-'+str(i),story_id='sport-'+str(i),sports_interest=key);sports.append(item)
            records.append({'article_id':item['id']})
        edition['sports']['major_stories']=records
        load('selection').validate(edition,[a for a in docs if a['daily']['section']!='sports']+sports)
        edition.update(date='2026-10-20',edition_mode='evening_synthesis')
        with self.assertRaisesRegex(ValueError,'two other'):load('selection').validate(edition,docs)

    def test_live_verification_cannot_be_skipped_and_transient_propagation_is_bounded(self):
        attempt=mock.Mock(side_effect=[ValueError('Pages does not serve this release'),{'status':'verified'}]);pause=mock.Mock()
        self.assertEqual(publish.await_live(attempt,pause=pause),{'status':'verified'})
        pause.assert_called_once_with(10)
        with self.assertRaisesRegex(ValueError,'does not serve'):
            publish.await_live(mock.Mock(side_effect=ValueError('Pages does not serve this release')),attempts=2,pause=mock.Mock())
        self.assertNotIn('ORACLE_SKIP_LIVE_POLL',(ROOT/'scripts/v2/publish.py').read_text())

    def test_ci_requests_pages_build_without_exposing_token_and_local_push_uses_its_normal_trigger(self):
        opener=mock.Mock();response=mock.MagicMock();response.__enter__.return_value=response;response.status=201
        opener.return_value=response
        with mock.patch.dict(publish.os.environ,{'ORACLE_PAGES_BUILD_TOKEN':'test-secret'}):
            result=publish.request_public_pages_build(opener)
        request=opener.call_args.args[0]
        self.assertEqual(request.get_method(),'POST')
        self.assertEqual(request.full_url,'https://api.github.com/repos/JoDemon9/Claude-Briefing/pages/builds')
        self.assertNotIn('test-secret',str(result))
        with mock.patch.dict(publish.os.environ,{},clear=True):
            self.assertEqual(publish.request_public_pages_build()['status'],'normal_git_push_trigger')

    def test_download_failure_never_creates_a_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);edition_id='2026-10-22-morning'
            ep=root/'content/editions'/(edition_id+'.json');ep.parent.mkdir(parents=True)
            ep.write_text(json.dumps({'articles':['articles/test.json'],'image_review':{'version':2}}))
            ap=root/'content/articles/test.json';ap.parent.mkdir();ap.write_text(json.dumps({'image':{
                'url':'assets/editorial/test/missing.webp','original_url':'https://upload.wikimedia.org/missing.jpg'}}))
            images=load('prepare_images')
            with mock.patch.object(images.urllib.request,'urlopen',side_effect=OSError('offline')),mock.patch.object(images.time,'sleep'):
                with self.assertRaisesRegex(ValueError,'could not be prepared'):images.prepare(root,edition_id)
            self.assertFalse((root/'docs/assets/editorial/test/missing.webp').exists())


if __name__ == '__main__':
    unittest.main()
