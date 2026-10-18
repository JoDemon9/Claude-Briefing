import hashlib
import copy
import importlib.util
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('selection_builder', ROOT/'scripts/v2/build.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
selection = build.load_module('selection')


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.edition = json.loads((ROOT/'content/editions/2026-10-15-midday.json').read_text())
        self.articles = [json.loads((ROOT/'content'/p).read_text()) for p in self.edition['articles']]

    def test_favourites_show_dated_headlines_and_extra_f1_is_excluded(self):
        original = copy.deepcopy(self.edition)
        doc = BeautifulSoup(build.sports(self.edition, self.articles), 'html.parser')
        self.assertEqual(len(doc.select('.sports-links .sport-news-link')), 4)
        for key,team in self.edition['sports']['coverage'].items():
            card=doc.select_one('.team-'+key)
            links=card.select('.sport-headline-link')
            self.assertLessEqual(len(links),2)
            if team['updates']:self.assertTrue(links)
            for link in links:
                self.assertIn(link['href'],[s['url'] for u in team['updates'] for s in u['sources']])
                self.assertIsNotNone(link.find_next_sibling('time'))
            self.assertIn('Από το αρχείο',card.text)
        self.assertEqual(len(doc.select('.sports-links img.sport-logo')),4)
        self.assertTrue(all(img['alt']=='' for img in doc.select('.sport-logo')))
        for record in json.loads((ROOT/'templates/v2/sports-logos.json').read_text()):
            self.assertEqual(hashlib.sha256((ROOT/'docs'/record['asset']).read_bytes()).hexdigest(),record['sha256'])
        self.assertFalse(doc.select('.sports-links details,.sports-links p'))
        self.assertIn('Six Kings Slam', doc.select_one('.sports-other').text)
        self.assertNotIn('Mekies', doc.select_one('.sports-other').text)
        self.assertEqual(self.edition, original)

    def test_day_has_one_story_version_balanced_opening_and_quiet_history(self):
        daily = build.load_module('daily')
        bundles = []
        for slot in ('morning', 'midday'):
            e = json.loads((ROOT/'content/editions'/f'2026-10-15-{slot}.json').read_text())
            bundles.append((e, [json.loads((ROOT/'content'/p).read_text()) for p in e['articles']]))
        model = daily.compose('2026-10-15', bundles)
        doc = BeautifulSoup(daily.render(build, model, bundles), 'html.parser')
        ids = [node['data-story-id'] for node in doc.select('[data-story-id]')]
        self.assertCountEqual(ids, [story['story_id'] for story in model['stories']])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(doc.select_one('#changes').has_attr('open'))
        sections = [node.get('id') for node in doc.select('main > section, main > details')]
        self.assertLess(sections.index('world'), sections.index('cyprus'))
        self.assertLess(sections.index('cyprus'), sections.index('changes'))
        for link in doc.select('.day-lead .brief-line a,.summary-story-links a'):
            self.assertIsNotNone(doc.select_one(link['href']))
        sports = doc.select_one('#other-sports')
        self.assertIn('Six Kings Slam', sports.text)
        self.assertNotIn('Mekies', sports.text)
        for story in model['stories']:
            self.assertTrue((ROOT/'docs'/story['selected']['url']).is_file())

    def test_other_sports_without_optional_analysis_keeps_its_photo_and_source_link(self):
        article = copy.deepcopy(next(a for a in self.articles if a.get('sports_interest') == 'other' and a['category'] == 'Αθλητικά'))
        article.update(newspaper_analysis=[], reader_mode='source')
        edition = copy.deepcopy(self.edition)
        edition['sports']['major_stories'] = [next(r for r in edition['sports']['major_stories'] if r['article_id'] == article['id'])]
        doc = BeautifulSoup(build.sports(edition, [article]), 'html.parser')
        card = doc.select_one('.sports-other article')
        self.assertEqual(card.select_one('[data-editorial-image] img')['src'], '../' + article['image']['url'])
        self.assertEqual(card.select_one('.abstract').get_text(strip=True), article['summary'])
        self.assertFalse(card.select('.card-analysis'))
        self.assertIn(card.select_one('.original-report')['href'], [s['url'] for s in article['sources'] if s.get('access') == 'read' and s.get('used_for_claims')])

    def morning(self, local=5, world=5, reason=None):
        edition = copy.deepcopy(self.edition)
        edition.update(type='morning', date='2026-10-16', selection_review={'version':1, 'completed_at':'2026-10-16T07:30:00+03:00','global_exception_reason':reason})
        edition['sports']['major_stories'] = []
        articles = [{'category':'Κύπρος'} for _ in range(local)] + [{'category':'Διεθνή'} for _ in range(world)]
        return edition, articles

    def test_morning_caps_count_the_lead_by_its_actual_section(self):
        e, articles = self.morning()
        articles[-1] = {'category':'Πρώτο θέμα','daily':{'section':'world'}}
        selection.validate(e, articles)
        with self.assertRaisesRegex(ValueError,'at most five'):
            selection.validate(e, articles+[{'category':'Κύπρος'}])
        e, articles = self.morning(world=8,reason='Eight stories are still above the absolute ceiling.')
        with self.assertRaisesRegex(ValueError,'seven global'):
            selection.validate(e,articles)

    def test_six_or_seven_global_stories_need_a_reason_and_fewer_are_allowed(self):
        for count in (6,7):
            e, articles = self.morning(world=count)
            with self.assertRaisesRegex(ValueError,'editorial reason'):
                selection.validate(e,articles)
            e['selection_review']['global_exception_reason']='Additional major verified developments warrant coverage.'
            selection.validate(e,articles)
        selection.validate(*self.morning(local=2,world=3))

    def test_new_morning_requires_review_and_old_snapshots_keep_their_inventory(self):
        e, articles = self.morning()
        e.pop('selection_review')
        with self.assertRaisesRegex(ValueError,'selection_review'):
            selection.validate(e,articles)
        e['date']='2026-10-15'
        selection.validate(e,articles+[{'category':'Κύπρος'}])

    def test_new_extra_sports_must_be_explicit_and_outside_the_favourites(self):
        e = copy.deepcopy(self.edition); e['date']='2026-10-16'
        with self.assertRaisesRegex(ValueError,'four favourites'):
            selection.validate(e,self.articles)
        e['sports']['major_stories'] = [r for r in e['sports']['major_stories'] if r['article_id']=='sport-slam']
        selection.validate(e,self.articles)
        articles=copy.deepcopy(self.articles);articles[-1].pop('sports_interest')
        with self.assertRaisesRegex(ValueError,'explicit sports_interest'):
            selection.validate(e,articles)

    def coverage_edition(self, slot='morning', local=5, world=5):
        edition, articles = self.morning(local, world)
        edition.update(id='2026-10-19-'+slot, date='2026-10-19', type=slot)
        edition['selection_review'].update(version=2, section_shortfalls={})
        for index, article in enumerate(articles):
            article['story_id'] = 'distinct-story-'+str(index)
        return edition, articles

    def test_every_slot_requires_separate_five_story_sections(self):
        for slot in ('morning', 'midday', 'evening'):
            with self.subTest(slot=slot):
                edition, articles = self.coverage_edition(slot)
                articles[-1].update(category='Πρώτο θέμα', daily={'section':'world'})
                selection.validate(edition, articles)
                for local, world, name in ((5,4,'world'),(4,5,'cyprus'),(0,5,'cyprus')):
                    with self.assertRaisesRegex(ValueError,name+' section needs five'):
                        selection.validate(*self.coverage_edition(slot,local,world))

    def test_shortfalls_require_section_specific_evidence_and_cannot_be_stale(self):
        edition, articles = self.coverage_edition(local=3)
        exception={'reason':'A broad Cyprus scan found only three distinct supported material stories.',
                   'checked_sources':['https://www.example.org/news','https://example.org/other']}
        edition['selection_review']['section_shortfalls']['cyprus']=exception
        with self.assertRaisesRegex(ValueError,'two independent'):
            selection.validate(edition,articles)
        exception['checked_sources'][1]='https://independent.example/news'
        selection.validate(edition,articles)
        self.assertEqual(selection.coverage(edition,articles)['shortfalls'],{'cyprus':2})
        edition, articles = self.coverage_edition()
        edition['selection_review']['section_shortfalls']['cyprus']=exception
        with self.assertRaisesRegex(ValueError,'stale cyprus'):
            selection.validate(edition,articles)

    def test_duplicate_stories_cannot_fill_sections_and_v1_cannot_bypass_policy(self):
        edition, articles = self.coverage_edition()
        articles[1]['story_id']=articles[0]['story_id']
        with self.assertRaisesRegex(ValueError,'distinct story IDs'):
            selection.validate(edition,articles)
        edition, articles = self.coverage_edition('midday')
        edition['selection_review']['version']=1
        with self.assertRaisesRegex(ValueError,'version=2'):
            selection.validate(edition,articles)

    def test_policy_begins_next_slot_and_preserves_completed_editions(self):
        edition, articles = self.morning(local=1,world=4)
        edition.update(date='2026-10-18',type='midday')
        selection.validate(edition,articles)
        edition['type']='evening'
        with self.assertRaisesRegex(ValueError,'version=2'):
            selection.validate(edition,articles)
        edition['status']='draft'
        selection.validate(edition,articles)


if __name__ == '__main__':
    unittest.main()
