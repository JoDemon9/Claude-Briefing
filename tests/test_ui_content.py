"""Presentation must keep the reviewed text, source evidence and dated reader."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ui_content_builder',ROOT/'scripts/v2/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class UIContentTests(unittest.TestCase):
    def test_frontend_reapplication_preserves_identity_and_never_duplicates_evidence_or_navigation(self):
        edition=json.loads((ROOT/'content/editions/2026-10-14-morning.json').read_text())
        original=(ROOT/'docs/daily/2026-10-14.html').read_text()
        day=json.loads((ROOT/'docs/data/days/2026-10-14.json').read_text())
        frontend=build.load_module('newspaper_ui')
        first=frontend.decorate(build,original,edition,day)
        self.assertEqual(frontend.decorate(build,first,edition,day),first)
        doc=BeautifulSoup(first,'html.parser')
        self.assertEqual(len(doc.select('.publication-bar')),1)
        ids=[x['data-story-id'] for x in doc.select('[data-story-id]')]
        self.assertEqual(ids,[x['data-story-id'] for x in BeautifulSoup(original,'html.parser').select('[data-story-id]')])
        self.assertCountEqual(ids,[s['story_id'] for s in day['stories']])
        self.assertEqual(len(doc.select('.edition-desk a')),len(day['editions']))
        self.assertFalse(doc.select('.edition-desk [aria-current]'))

    def test_native_article_and_photo_disclosures_keep_every_reviewed_paragraph_and_credit(self):
        edition=json.loads((ROOT/'content/editions/2026-10-14-morning.json').read_text())
        for path in edition['articles']:
            article=json.loads((ROOT/'content'/path).read_text())
            for hero in [False,True]:
                with self.subTest(article=article['id'],hero=hero):
                    doc=BeautifulSoup(build.card(edition,article,hero),'html.parser')
                    self.assertEqual(doc.select_one('.abstract').get_text(),article['summary'])
                    if hero:
                        self.assertEqual(doc.select_one('.lead-analysis').name,'section')
                        self.assertFalse(doc.select('.lead-analysis summary'))
                    else:
                        self.assertFalse(doc.select_one('.card-analysis').has_attr('open'))
                    self.assertEqual([p.get_text() for p in doc.select('.card-context>p')],article['newspaper_analysis'])
                    im=article['image']
                    self.assertIn(im['caption'],doc.select_one('.photo-details').get_text())
                    self.assertIn(im['attribution'],doc.select_one('.photo-details').get_text())
                    self.assertTrue(doc.select_one('.photo-details').find('a',href=im['license_url']))
                    self.assertTrue(doc.find('a',href='../'+article['url']))

    def test_shared_overview_changes_and_sports_keep_all_editorial_text(self):
        edition=json.loads((ROOT/'content/editions/2026-10-14-morning.json').read_text())
        original=copy.deepcopy(edition)
        ui=build.load_module('newspaper_ui')
        summary=BeautifulSoup(ui.summary(build,edition['summary_60s'],'Η έκδοση σε 60 δευτερόλεπτα'),'html.parser')
        self.assertEqual(len(summary.select('.summary-point')),len(edition['summary_60s']))
        for paragraph,item in zip(edition['summary_60s'],summary.select('.summary-point')):
            # Decorative icons do not replace a word of the reviewed overview.
            for marker in item.select('[aria-hidden]'):marker.decompose()
            self.assertEqual(' '.join(item.get_text(' ',strip=True).split()),' '.join(paragraph.split()))
        changes=BeautifulSoup(ui.changes(build,edition['changes']),'html.parser')
        self.assertEqual([p.get_text() for p in changes.select('.edition-change p')],[c['text'] for c in edition['changes']])
        sports=BeautifulSoup(build.sports(edition),'html.parser')
        for key,team in edition['sports']['coverage'].items():
            card=sports.select_one('.team-'+key)
            self.assertEqual(card.select_one('.teamicon')['aria-hidden'],'true')
            self.assertIn(team['summary'],card.get_text())
            self.assertIn(build.stamp(team['updated_at']),card.get_text())
        self.assertEqual(edition,original)

    def test_published_day_and_snapshot_use_explicit_editorial_lead_without_duplicates(self):
        edition=json.loads((ROOT/'content/editions/2026-10-14-morning.json').read_text())
        articles=[json.loads((ROOT/'content'/path).read_text()) for path in edition['articles']]
        lead=next(a for a in articles if a['story_id']==edition['daily']['lead_story_id'])
        day=BeautifulSoup((ROOT/'docs/daily/2026-10-14.html').read_text(),'html.parser')
        independent=BeautifulSoup((ROOT/'docs'/edition['url']).read_text(),'html.parser')
        for doc in [day,independent]:
            self.assertEqual(doc.select_one('.hero h2').get_text(),lead['headline'])
            self.assertEqual(len(doc.select('.hero,.newscard')),len(articles))
            self.assertFalse(doc.select('.lead-analysis summary'))
            self.assertTrue(doc.select_one('.hub-home'))
        self.assertFalse(day.select('.edition-desk [aria-current]'))
        self.assertEqual(len(independent.select('.edition-desk [aria-current]')),1)

    def test_panels_preserve_editorial_paragraphs_sources_and_reference_times(self):
        records=json.loads((ROOT/'docs/data/editions.json').read_text())
        edition=json.loads((ROOT/'content/editions'/f'{records[0]["id"]}.json').read_text())
        before=copy.deepcopy(edition)
        doc=BeautifulSoup(build.edition_panels(edition),'html.parser')
        for panel in edition.get('panels',[]):
            section=doc.find(id=panel['id'])
            text=' '.join(section.get_text(' ',strip=True).split())
            for paragraph in panel['paragraphs']:
                self.assertIn(' '.join(paragraph.split()),text)
            for source in panel['sources']:
                self.assertTrue(section.find('a',href=source['url']))
                self.assertIn(build.stamp(source.get('published_at')),text)
                self.assertIn(build.stamp(source.get('retrieved_at')),text)
        self.assertEqual(edition,before)

    def test_calendar_unknown_format_keeps_full_text_and_never_invents_a_time(self):
        paragraph='Η ώρα δεν έχει επαληθευτεί · Αναμένουμε την επίσημη ανακοίνωση.'
        edition={'panels':[{'id':'risk-radar','heading':'Ημερολόγιο','paragraphs':[paragraph],'sources':[]}]}
        doc=BeautifulSoup(build.edition_panels(edition),'html.parser')
        self.assertIn(paragraph,doc.get_text(' ',strip=True))
        self.assertFalse(doc.select('.event-when'))
        self.assertFalse(doc.select('time'))

if __name__=='__main__':unittest.main()
