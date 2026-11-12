"""Model-neutral preparation keeps evidence private and never grants editorial review."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_test',ROOT/'scripts/v2/prepare_run.py')
handoff=importlib.util.module_from_spec(spec);spec.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def test_private_pack_has_one_bounded_digest_and_does_not_approve_or_publish(self):
        class Offline:
            def __init__(self):self.records=[]
            def get(self,url):
                row={'url':url,'status':'unavailable','reason':'offline fixture'}
                self.records.append(row);return row
            def many(self,urls):return {u:self.get(u) for u in sorted(set(urls))}
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'content').rglob('*.json')}
        with tempfile.TemporaryDirectory() as private:
            result=handoff.prepare(ROOT,'2026-10-20','evening','2026-10-20T18:00:00+03:00',private,client=Offline())
            record=json.loads(Path(result['handoff']).read_text(encoding='utf-8'))
            pack=json.loads(Path(result['research_pack']).read_text(encoding='utf-8'))
            self.assertEqual(record['version'],2)
            self.assertFalse(pack['submission_ready'])
            self.assertEqual(pack['metrics']['ai_collection_calls'],0)
            records=handoff.module('baseline').load(ROOT,pack['baseline'])[1]
            self.assertEqual({a['story_id'] for a in records},{a['story_id'] for a in pack['baseline_stories']})
            self.assertEqual(len(pack['data']['markets']),39)
            self.assertEqual(len(pack['data']['sports']['coverage']),4)
            self.assertLessEqual(Path(result['digest']).stat().st_size,48000)
            self.assertTrue(Path(result['digest']).resolve().is_relative_to(Path(private).resolve()))
            self.assertNotIn('reading_review',record)
        after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'content').rglob('*.json')}
        self.assertEqual(before,after)

    def test_large_routine_projection_keeps_reserved_article_evidence(self):
        view=handoff.module('context_view')
        report='Η ανακοίνωση αφορά τη νέα διαδικασία και περιλαμβάνει συγκεκριμένα στοιχεία για την εφαρμογή της. '
        lanes=('omonoia','manutd','realmadrid','formula1','padel','football','other')
        candidates=[]
        for section,entries in [('cyprus',[None]*5),('world',[None]*5),('sports',lanes)]:
            for lane in entries:
                i=len(candidates)+1
                candidates.append(dict(id=f'c{i}',section=section,title='Νέα ανακοίνωση',sports_lane=lane,
                    # Distinct facts force genuine projection pressure even when
                    # repeated source paragraphs are correctly deduplicated.
                    evidence=[dict(id=f'e{i}',access='article_excerpt',sports_lane=lane,
                                   excerpt='\n'.join(f'Μέτρο {n}: '+report for n in range(20)),
                                   source=dict(url=f'https://example.org/{i}',publisher='Fixture'))]))
        original=dict(edition_id='2026-11-04-evening',prepared_at='2026-11-04T17:00:00+00:00',
            sha256='fixture',weather_status='available',candidates=candidates,
            baseline_stories=[dict(story_id='prior-news',headline='Προηγούμενη είδηση',finding=report)],
            data=dict(markets=[],panels=[dict(paragraphs=[report*130])],
                      sports=dict(briefing_policy='intelligence-v1',
                                  coverage={'manutd':{'just_played':True}})))
        digest=view.synthesis(original)
        self.assertLessEqual(len(digest.encode('utf-8')),48000)
        self.assertIn('## Compact routine context',digest)
        self.assertIn('Sports just_played: {"manutd":true}',digest)
        self.assertIn('"story_id":"prior-news"',digest)
        self.assertIn('Visible article-backed candidates by desk: {"cyprus":5,"world":5,"sports":7}',digest)
        self.assertTrue(all(f'"id":"e{i}"' in digest for i in range(1,18)))
        self.assertEqual(original['data']['panels'][0]['paragraphs'],[report*130])
        original['data']['panels']=[]
        self.assertIn('## Python market table',view.synthesis(original))
        with self.assertRaisesRegex(ValueError,'Reserved news/sports evidence'):
            view.synthesis(original,max_bytes=3000)

    def test_preflight_guidance_is_versioned_without_changing_old_digests(self):
        view=handoff.module('context_view')
        pack=dict(edition_id='2026-11-12-evening',prepared_at='2026-11-12T16:21:23+00:00',
                  sha256='fixture',weather_status='available',candidates=[],
                  briefing_policy='depth-markets-v1',financial_policy='news-insights-v1',
                  data=dict(markets=[],panels=[],sports=dict(briefing_policy='intelligence-v1',coverage={})))
        old=view.synthesis(pack)
        self.assertIn('A new web source uses @Source',old)
        self.assertIn('70–100 Greek words TOTAL',old)
        self.assertEqual(view.synthesis({**pack,'authoring_preflight':'unknown'}),old)
        new=view.synthesis({**pack,'authoring_preflight':'scope-and-length-v1'})
        self.assertIn('inside its ### article, never in the header or @Evidence',new)
        self.assertIn('70–100 whitespace-separated words',new)
        self.assertLessEqual(len(new.encode('utf-8')),48000)

    def test_public_or_symlinked_private_storage_is_rejected_before_collection(self):
        for path in [ROOT,ROOT/'docs',ROOT/'content']:
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'outside the public'):
                handoff.prepare(ROOT,'2026-10-20','evening','2026-10-20T18:00:00+03:00',path)
        with tempfile.TemporaryDirectory() as tmp:
            link=Path(tmp)/'private';link.symlink_to(ROOT/'docs',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'outside the public'):
                handoff.prepare(ROOT,'2026-10-20','evening','2026-10-20T18:00:00+03:00',link)


if __name__=='__main__':unittest.main()
