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
