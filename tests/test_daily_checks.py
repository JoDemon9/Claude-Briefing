"""Keep daily gates small without accepting bad evidence or changed releases."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


checks=load('minimal_checks',ROOT/'scripts/v2/checks.py')
smoke=load('minimal_preview',ROOT/'tests/edition_browser_checks.py')
fixture=load('minimal_fixture',ROOT/'tests/test_structured_content.py')


class DailyChecksTests(unittest.TestCase):
    def setUp(self):
        self.helper=fixture.StructuredContentTests();self.helper.setUp()

    def candidate(self,directory):
        return self.helper.fixture_root(directory,self.helper.edition,self.helper.articles)

    def classification(self,profile='content'):
        return {'profile':profile,'edition_ids':[self.helper.edition['id']],'changed_files':[]}

    def test_daily_has_only_three_gates_and_no_unit_or_archive_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.candidate(tmp);seen=[]
            def execute(name,command,fn):
                seen.append((name,command))
                if fn:fn()
            with mock.patch.object(checks,'classify',return_value=self.classification()):
                result=checks.run(root,execute=execute)
            self.assertEqual([name for name,_ in seen],['content','preview','integrity'])
            self.assertIn('edition_browser_checks.py',str(seen[1][1]))
            self.assertNotIn('unittest',str(seen))
            self.assertEqual(result['status'],'passed')

    def test_invalid_claim_source_stops_at_content_before_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.candidate(tmp);path=root/'content'/self.helper.edition['articles'][0]
            article=json.loads(path.read_text());article['sources'][0].update(access='inaccessible',used_for_claims=True)
            path.write_text(json.dumps(article))
            def execute(name,command,fn):
                if fn:fn()
                elif command:raise AssertionError('Bad evidence must not reach preview')
            with mock.patch.object(checks,'classify',return_value=self.classification()):
                with self.assertRaises(ValueError):checks.run(root,execute=execute)
            report=json.loads((root/'.work/check-report.json').read_text())
            self.assertEqual(report['failed_step'],'content')
            self.assertTrue(report['steps'][0]['detail'])

    def test_changed_preview_bytes_cannot_receive_a_passing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.candidate(tmp)
            def execute(name,command,fn):
                if fn:fn()
                if name=='preview':
                    path=root/'docs'/self.helper.edition['url'];path.write_text(path.read_text()+'corrupted')
            with mock.patch.object(checks,'classify',return_value=self.classification()):
                with self.assertRaisesRegex(ValueError,'changed during'):checks.run(root,execute=execute)
            self.assertEqual(json.loads((root/'.work/check-report.json').read_text())['failed_step'],'integrity')
            self.assertFalse((root/'docs/data/release.json').exists())

    def test_maintenance_adds_units_and_archive_checks_require_explicit_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.candidate(tmp)
            for profile,expected in [('maintenance',['content','unit','preview','integrity']),
                    ('full',['content','unit','preview','browser_checks','frontend_polish_browser_checks','editorial_browser_checks','integrity'])]:
                seen=[]
                def execute(name,command,fn):
                    seen.append(name)
                    if fn:fn()
                with mock.patch.object(checks,'classify',return_value=self.classification('maintenance')):
                    checks.run(root,profile=profile,execute=execute)
                self.assertEqual(seen,expected)

    def test_selected_candidate_cannot_silently_fall_back_to_another_edition(self):
        with self.assertRaisesRegex(ValueError,'missing or unpublished'):
            checks.selected_editions(ROOT,['2099-01-01-morning'])

    def test_preview_uses_two_pages_and_two_configurations_without_reader_sweep(self):
        editions,pages=smoke.preview_plan(ROOT,['2026-10-20-midday'])
        self.assertEqual(set(pages),{'midday/2026-10-20.html','daily/2026-10-20.html'})
        self.assertEqual(smoke.CASES,((390,True),(1440,False)))
        self.assertEqual(len(editions),1)

    def test_broken_local_article_link_blocks_the_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'docs').mkdir()
            (root/'docs/index.html').write_text('<main><a href="missing-reader.html">Read</a></main>')
            with self.assertRaisesRegex(ValueError,'Missing/unsafe local preview link'):
                smoke.check_local_links(root,'index.html')


if __name__=='__main__':unittest.main()
