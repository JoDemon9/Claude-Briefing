"""DEC-004/005: daily coverage and evidence-backed depth instead of word quotas."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location('value_'+name,ROOT/'scripts/v2'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
build=module('build');daily=module('daily');editorial=module('editorial')

class EditorialValueTests(unittest.TestCase):
    def setUp(self):
        build.ROOT=ROOT
        self.bundles=[]
        for slot in daily.SLOTS:
            e=json.loads((ROOT/'content/editions'/f'2026-10-14-{slot}.json').read_text())
            self.bundles.append((e,[json.loads((ROOT/'content'/p).read_text()) for p in e['articles']]))
        self.e,self.articles=self.bundles[-1]

    def test_current_daily_overview_retains_important_earlier_stories_and_has_working_links(self):
        model=daily.compose('2026-10-14',self.bundles)
        ids={sid for p in model['overview']['points'] for sid in p['story_ids']}
        morning={a['story_id'] for a in self.bundles[0][1]}
        midday={a['story_id'] for a in self.bundles[1][1]}
        self.assertTrue(ids&morning);self.assertTrue(ids&midday)
        self.assertIn('black-sea-bulgaria-shipping-drone-attacks-2026',ids)
        self.assertNotEqual([p['text'] for p in model['overview']['points']],self.e['summary_60s'])
        doc=BeautifulSoup(daily.render(build,model,self.bundles),'html.parser')
        for link in doc.select('.summary-story-links a'):
            self.assertIsNotNone(doc.find(id=link['href'][1:]))
        self.assertEqual(len(doc.select('.summary-point')),6)

    def test_legacy_fallback_uses_selected_day_stories_not_the_latest_slot_summary(self):
        bundles=copy.deepcopy(self.bundles)
        for e,_ in bundles:
            e.pop('reading_review');e['daily'].pop('summary_60s');e['daily'].pop('summary_story_ids')
        model=daily.compose('2026-10-14',bundles)
        self.assertEqual(model['overview']['kind'],'selected_summaries')
        ids={sid for p in model['overview']['points'] for sid in p['story_ids']}
        latest={a['story_id'] for a in bundles[-1][1]}
        self.assertTrue(ids-latest)

    def test_missing_unknown_or_mismatched_day_references_are_rejected(self):
        for case in ['missing','unknown','mismatch']:
            with self.subTest(case=case):
                bundles=copy.deepcopy(self.bundles);e=bundles[-1][0]
                if case=='missing':e['daily'].pop('summary_story_ids')
                if case=='unknown':e['daily']['summary_story_ids'][0]=['not-a-published-story']
                if case=='mismatch':e['daily']['summary_story_ids'].pop()
                with self.assertRaisesRegex(ValueError,'overview|references|unavailable'):daily.compose('2026-10-14',bundles)

    def test_short_relevant_analysis_and_source_only_articles_do_not_need_padding(self):
        for a in self.articles:editorial.validate_reading(a)
        source=copy.deepcopy(next(a for a in self.articles if a['reader_mode']=='source'))
        source['newspaper_analysis']=[];source['sections']=[{'kind':'reported','heading':'Είδηση','paragraphs':[source['summary']]}]
        editorial.validate_reading(source)
        card=BeautifulSoup(build.card(self.e,source,True),'html.parser')
        self.assertFalse(card.select('.card-analysis'))
        self.assertTrue(card.select_one('.original-report')['href'].startswith('https:'))
        self.assertFalse(card.select('a[href^="../articles/"]'))

    def test_copied_preview_or_unreviewed_sources_fail(self):
        for case in ['duplicate','unreviewed','missing']:
            with self.subTest(case=case):
                a=copy.deepcopy(self.articles[0])
                if case=='duplicate':a['newspaper_analysis']=[a['summary']]
                if case=='unreviewed':a['analysis_sources']=['https://example.com/unread']
                if case=='missing':a['analysis_sources']=[]
                with self.assertRaises(ValueError):editorial.validate_reading(a)

    def test_a_separate_full_reader_must_have_actual_extra_material(self):
        a=copy.deepcopy(next(a for a in self.articles if a['reader_mode']=='full'))
        self.assertLess(build.words(a),450)
        editorial.validate_reading(a)
        a['sections']=[{'kind':'analysis','heading':'Πάλι τα ίδια','paragraphs':a['newspaper_analysis']}]
        with self.assertRaisesRegex(ValueError,'add material'):editorial.validate_reading(a)

    def test_lead_and_secondary_analysis_are_optional_native_disclosures(self):
        for hero in [False,True]:
            a=self.articles[0];doc=BeautifulSoup(build.card(self.e,a,hero),'html.parser')
            self.assertEqual(doc.select_one('.abstract').get_text(),a['summary'])
            self.assertFalse(doc.select_one('.card-analysis').has_attr('open'))
            self.assertIn('30 δευτερόλεπτα',doc.get_text())

if __name__=='__main__':unittest.main()
