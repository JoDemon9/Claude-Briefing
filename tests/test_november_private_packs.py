"""Opt-in offline regressions; NOVEMBER_PACK_ROOT points to private research/runs.

Public CI runs the synthetic failure-shape tests. It never downloads private
research, prints excerpts or publishes them as fixtures/artifacts.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('november_audit',ROOT/'scripts/v2/audit_news_packs.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


@unittest.skipUnless(os.environ.get('NOVEMBER_PACK_ROOT'),'private pack root not supplied')
class PrivateNovemberPacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs=Path(os.environ['NOVEMBER_PACK_ROOT'])
        cls.paths=sorted(cls.runs.glob('2026-11-0[789]-*/research_pack.json'))

    def test_all_eight_sealed_packs_replay_with_unchanged_caps_and_provenance(self):
        self.assertEqual(len(self.paths),8)
        for path in self.paths:
            with self.subTest(edition=path.parent.name):
                pack=audit.module('research_pack').load(path);before=copy.deepcopy(pack)
                projected,report=audit.replay(pack)
                projected['coverage_policy']='auditable-v1'
                digest=audit.module('context_view').synthesis(projected)
                self.assertLessEqual(len(digest.encode('utf-8')),48000)
                self.assertEqual(pack['metrics']['article_requests'],24)
                self.assertEqual(pack,before)
                self.assertEqual(set(projected['evidence']),set(pack['evidence']))
                for eid,evidence in projected['evidence'].items():
                    if evidence['access']=='article_excerpt':
                        self.assertFalse(audit.module('news_digest').body_rejection(evidence['excerpt']))
                        self.assertEqual(evidence['source'],pack['evidence'][eid]['source'])
                self.assertTrue(any(e['reason']=='promotional_body_without_article' for e in report['excluded']))

    def test_critical_saved_passages_survive_full_digest_projection(self):
        checks={'2026-11-07-morning':{'e1':['80','2027','δεν καθορίζει']},
                '2026-11-08-morning':{'e4':['τρία άτομα','δύο ή και τρία σχολεία']},
                '2026-11-09-morning':{'e9':['5.7%','5.3%','0.7%','0.8%'],
                                      'e10':['no reason to believe','remains unclear']}}
        for edition,aliases in checks.items():
            pack=audit.module('research_pack').load(self.runs/edition/'research_pack.json')
            projected,_=audit.replay(pack);projected['coverage_policy']='auditable-v1'
            digest=audit.module('context_view').synthesis(projected)
            visible={row['id']:row for line in digest.splitlines() if line.startswith('{"id":')
                     and '"access":' in line for row in [json.loads(line)]}
            for alias,terms in aliases.items():
                for term in terms:
                    with self.subTest(edition=edition,alias=alias,term=term):
                        self.assertIn(term,visible[alias]['excerpt'])

    def test_9_geography_event_grouping_and_real_grouped_citations(self):
        pack=audit.module('research_pack').load(self.runs/'2026-11-09-morning/research_pack.json')
        projected,_=audit.replay(pack)
        self.assertEqual(projected['evidence']['e3']['section'],'sports')
        self.assertEqual(projected['evidence']['e5']['section'],'world')
        self.assertEqual(projected['evidence']['e21']['section'],'world')
        self.assertTrue(any({'e10','e11'}<={e['id'] for e in c['evidence']} for c in projected['candidates']))
        for path in self.paths:
            source=self.runs.parent.parent/'sources/synthesis'/(path.parent.name+'.md')
            self.assertTrue(source.is_file())
            p=audit.module('research_pack').load(path)
            payload=audit.module('markdown_input').parse(source.read_text(encoding='utf-8'),ROOT,p)
            for article in payload['articles']:
                self.assertNotRegex(json.dumps(article,ensure_ascii=False),r'\[\s*[es]\d+(?:\s*[,;]\s*[es]\d+)*\s*\]')


if __name__=='__main__':unittest.main()
