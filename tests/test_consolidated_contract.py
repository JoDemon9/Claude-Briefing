"""Coverage accountability, deliberate retirement, and shared-photo regressions."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('contract_'+name, ROOT/'scripts/v2'/f'{name}.py')
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


selection, continuity, baseline, md, compose, checks = [load(n) for n in
    ('selection', 'continuity', 'baseline', 'markdown_input', 'compose', 'checks')]


def article(n, section='world'):
    return dict(id=f'event-{n}', story_id=f'event-{n}', story_identity=f'event-{n}',
                summary=f'Unique supported reporting number {n}.', daily={'section':section,'events':[]},
                published_at='2026-10-28T07:30:00+02:00', updated_at='2026-10-28T07:30:00+02:00',
                category='Διεθνή' if section=='world' else 'Κύπρος', change_status='NEW')


def edition():
    return dict(id='2026-10-28-morning', date='2026-10-28', type='morning', status='published',
                published_at='2026-10-28T07:30:00+02:00', selection_policy='balanced-v1',
                daily={'lead_story_id':'event-0'}, selection_review={'version':2,'coverage_notes':{}})


class CoverageTests(unittest.TestCase):
    def test_five_article_morning_needs_explanation_per_news_desk(self):
        e=edition(); aa=[article(n,'cyprus' if n<2 else 'world') for n in range(4)]+[article(4,'sports')]
        with self.assertRaisesRegex(ValueError,'coverage below four'): selection.validate_balanced(e,aa)
        e['selection_review']['coverage_notes']={'cyprus':'Only two distinct supported Cyprus events in the reviewed evidence.',
                                               'world':'Remaining world candidates lack accessible supporting excerpts.'}
        selection.validate_balanced(e,aa)
        report=selection.coverage(e,aa)
        self.assertEqual(report['shortfalls'],{'world':2,'cyprus':2})
        self.assertEqual(report['coverage_notes'],e['selection_review']['coverage_notes'])

    def test_four_per_desk_is_valid_without_a_blanket_ten_article_floor(self):
        e=edition(); aa=[article(n,'cyprus' if n<4 else 'world') for n in range(8)]
        selection.validate_balanced(e,aa)
        self.assertEqual(selection.coverage(e,aa)['shortfalls'],{})
        e['selection_review']['coverage_notes']['world']='Stale reason after meeting coverage'
        with self.assertRaisesRegex(ValueError,'stale world'): selection.validate_balanced(e,aa)

    def test_semantic_slugs_resolve_lead_and_cannot_hide_a_missing_lead(self):
        e=edition(); aa=[article(n,'cyprus' if n<4 else 'world') for n in range(8)]
        selection.validate_balanced(e,aa)
        e['daily']['lead_story_id']='absent-story'
        with self.assertRaisesRegex(ValueError,'lead'): selection.validate_balanced(e,aa)

    def test_historical_contract_is_not_retroactively_rejected(self):
        e=edition(); e.update(date='2026-10-27'); e.pop('selection_policy')
        selection.validate_balanced(e,[article(0)])
        e['date']='2026-10-28'
        selection.validate_balanced(e,[article(0)])  # Contract gate decides historical acceptance.

    def test_current_contract_requires_policy_but_a_delayed_merge_preserves_accepted_history(self):
        backend=load('backend');e=edition();aa=[article(0)];e.pop('selection_policy')
        caps=backend.capabilities(ROOT)
        e['producer_contract']={k:caps[k] for k in ('producer_protocol','content_schema_sha256')}
        with self.assertRaisesRegex(ValueError,'selection_policy'):backend.check_contract(ROOT,e,aa)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'templates/v2').mkdir(parents=True);(root/'docs/data').mkdir(parents=True)
            (root/'templates/v2/content.schema.json').write_bytes((ROOT/'templates/v2/content.schema.json').read_bytes())
            e['producer_contract']['content_schema_sha256']='0'*64
            receipt={e['id']:{'contract':e['producer_contract'],'source_sha256':backend.edition_fingerprint(e,aa)}}
            (root/'docs/data/edition-contracts.json').write_text(json.dumps(receipt),encoding='utf-8')
            backend.check_contract(root,e,aa)
            continuity.validate(e,aa,root)
            aa[0]['summary']+=' Unreviewed change.'
            with self.assertRaisesRegex(ValueError,'mismatch'):backend.check_contract(root,e,aa)

    def test_prompt_and_policy_changes_select_maintenance(self):
        for path in ('AGENTS.md','CLAUDE.md','BRIEFING_SPEC.md','CHATGPT_TASK_INSTRUCTIONS.md','prompts/morning.md'):
            with self.subTest(path=path), mock.patch.object(checks.subprocess,'check_output',side_effect=['ok',path+'\n','']):
                self.assertEqual(checks.classify(ROOT,'HEAD')['profile'],'maintenance')

    def test_generated_prompts_cannot_drift_from_execution_contract(self):
        load('task_prompts').generate(ROOT,check=True)


class ContinuityTests(unittest.TestCase):
    def fixture(self,root):
        aa=[article(0),article(1,'cyprus')]; e=edition()
        e['articles']=[f'articles/{e["id"]}/{a["id"]}.json' for a in aa]
        for relative,a in zip(e['articles'],aa):
            path=root/'content'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(a),encoding='utf-8')
        path=root/'content/editions'/f'{e["id"]}.json';path.parent.mkdir(parents=True);path.write_text(json.dumps(e),encoding='utf-8')
        ref={'edition_id':e['id'],'fingerprint':baseline.fingerprint(e,aa)}
        later=copy.deepcopy(e);later.update(id='2026-10-28-midday',type='midday',published_at='2026-10-28T13:30:00+02:00',baseline=ref)
        return later,aa,ref

    def test_exact_same_day_carry_and_retirement_are_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e,aa,ref=self.fixture(root)
            aa[0].update(change_status='UNCHANGED',baseline_origin=ref)
            e['selection_review']['omitted_stories']={'event-1':'This routine notice is no longer useful in this snapshot.'}
            continuity.validate(e,aa[:1],root)
            self.assertTrue((root/'content/articles/2026-10-28-morning/event-1.json').exists())

    def test_unaccounted_and_conflicting_omissions_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e,aa,ref=self.fixture(root)
            aa[0].update(change_status='UNCHANGED',baseline_origin=ref)
            with self.assertRaisesRegex(ValueError,'Account for'):continuity.validate(e,aa[:1],root)
            e['selection_review']['omitted_stories']={'event-0':'Cannot both select and retire this same story.'}
            with self.assertRaisesRegex(ValueError,'unselected baseline'):continuity.validate(e,aa,root)

    def test_cross_day_carry_and_timestamp_only_updates_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e,aa,ref=self.fixture(root)
            for a in aa:a.update(change_status='UNCHANGED',baseline_origin=ref)
            e.update(date='2026-10-29',id='2026-10-29-midday',published_at='2026-10-29T13:30:00+02:00')
            with self.assertRaisesRegex(ValueError,'same-day'):continuity.validate(e,aa,root)
            for a in aa:a.update(change_status='UPDATED',updated_at=e['published_at'],delta_update='New label only')
            with self.assertRaisesRegex(ValueError,'Identical reporting'):continuity.validate(e,aa,root)

    def test_new_slug_and_missing_baseline_cannot_disguise_exact_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e,aa,ref=self.fixture(root);e.pop('baseline')
            for a in aa:a.update(story_id=a['story_id']+'-new',headline='Changed title')
            with self.assertRaisesRegex(ValueError,'Identical reporting'):continuity.validate(e,aa,root)

    def test_supported_material_update_preserves_original_identity_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e,aa,ref=self.fixture(root)
            aa[0].update(change_status='UPDATED',summary='A genuinely different reported event development.',delta_update='New decision approved.')
            aa[1].update(change_status='UNCHANGED',baseline_origin=ref)
            continuity.validate(e,aa,root)
            aa[0]['published_at']=e['published_at']
            with self.assertRaisesRegex(ValueError,'original publication'):continuity.validate(e,aa,root)

    def test_compact_selection_directives_and_duplicate_rejection(self):
        header='@Edition v=1 id=2026-10-28-midday published=auto completed=auto baseline=none\n@Review version=2 completed=auto\n'
        text=header+'@Coverage section=cyprus reason="Only two distinct supported local developments."\n@Omit id=old-event reason="Superseded by the confirmed outcome story."\n'
        payload=md.parse(text,ROOT)
        self.assertIn('cyprus',payload['selection_review']['coverage_notes'])
        self.assertIn('old-event',payload['selection_review']['omitted_stories'])
        with self.assertRaisesRegex(ValueError,'Duplicate'):md.parse(text+'@Omit id=old-event reason="Another reason for the same retired story."\n',ROOT)


class SharedPhotoTests(unittest.TestCase):
    def test_catalog_decodes_identical_assets_once_and_retains_references(self):
        library=load('photo_library')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'content/editions').mkdir(parents=True)
            (root/'content/articles').mkdir();(root/'docs/assets/editorial').mkdir(parents=True)
            real=next(iter(load('photo_policy').load(ROOT)['photos'].values()))
            data=(ROOT/'docs'/real['asset']).read_bytes()
            for n in range(2):
                (root/f'docs/assets/editorial/copy-{n}.webp').write_bytes(data)
                row={'story_id':f'test-{n}','image':dict(real['image'],url=f'assets/editorial/copy-{n}.webp')}
                (root/f'content/articles/test-{n}.json').write_text(json.dumps(row),encoding='utf-8')
            (root/'content/editions/test.json').write_text(json.dumps({'id':'test','status':'published',
                'image_review':{'version':2},'articles':['articles/test-0.json','articles/test-1.json']}),encoding='utf-8')
            with mock.patch.object(library.Image,'open',wraps=library.Image.open) as opened:
                result=library.catalog(root)
            self.assertEqual(opened.call_count,1)
            self.assertEqual(len(result['photos']),1)
            self.assertEqual(len(result['photos'][0]['references']),2)

    def test_two_new_slugs_reference_one_existing_reviewed_binary(self):
        policy=load('photo_policy');catalog=policy.extend_catalog({'photos':[]},ROOT)
        raw={'story_id':'unmatched-test','section':'world'}
        raw['image_selection']=policy.selection(raw,ROOT)
        first,bytes1=compose.reviewed_image(raw,'2026-10-28-morning','first-story',ROOT,catalog)
        second,bytes2=compose.reviewed_image(raw,'2026-10-28-morning','second-story',ROOT,catalog)
        self.assertEqual(first['url'],second['url'])
        self.assertEqual(first['url'],first['reuse_review']['source_asset'])
        self.assertEqual(bytes1,bytes2)
        self.assertEqual(bytes1,(ROOT/'docs'/first['url']).read_bytes())


class CompilerIntegrationTests(unittest.TestCase):
    def test_new_sealed_pack_requires_and_preserves_honest_shortfall(self):
        from test_synthesis import fixture, AT
        from test_compose import payload_fixture
        pack,payload,_=fixture('morning');pack['selection_policy']='balanced-v1'
        pack=load('research_pack').seal(pack);payload['research_pack_sha256']=pack['sha256']
        raw=payload_fixture()['articles'][0]
        raw.update(slug='integration-new-event',story_id='integration-new-event',story_identity='integration-new-event',
                   section='world',change_status='NEW',summary='Δοκιμαστική νέα εξέλιξη με υποστηριζόμενη τεκμηρίωση για τον έλεγχο του compiler.',is_lead=True)
        raw['delta_update']=raw['summary']
        payload['articles']=[raw];payload['carry_story_ids']=[]
        payload['synthesis_points'][0]['stories']=[raw['story_id']]
        hydrated=load('research_pack').hydrate(payload,pack,ROOT,AT.isoformat())
        with self.assertRaisesRegex(ValueError,'coverage below four'):compose.compile_payload(hydrated,ROOT)
        hydrated['selection_review']={'version':2,'completed_at':AT.isoformat(),'global_exception_reason':None,
            'section_shortfalls':{},'coverage_notes':{'world':'Only one distinct supported development remains after review.',
                'cyprus':'No accessible Cyprus article evidence in this test fixture.'}}
        e,aa,files=compose.compile_payload(hydrated,ROOT)
        self.assertEqual(e['selection_policy'],'balanced-v1')
        self.assertEqual(e['daily']['lead_story_id'],'integration-new-event')
        self.assertIn('Only one distinct',str(e['availability_notes']))
        self.assertEqual(aa[0]['image']['url'],aa[0]['image']['reuse_review']['source_asset'])
        self.assertFalse(any('2026-10-26-morning/integration-new-event.webp' in key for key in files))


if __name__=='__main__':unittest.main()
