import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reading_policy_builder',ROOT/'scripts/v2/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class ReadingPolicyTests(unittest.TestCase):
    def setUp(self):
        build.ROOT=ROOT
        self.edition=json.loads((ROOT/'content/editions/2026-10-13-midday.json').read_text())
        self.articles=[json.loads((ROOT/'content'/p).read_text()) for p in self.edition['articles']]

    def test_one_missing_photo_blocks_even_when_the_other_articles_have_images(self):
        self.articles[-1]['image']=None
        self.articles[-1]['image_unavailable_reason']='Research was done, but this must remain a draft.'
        with self.assertRaisesRegex(ValueError,'Every article requires'):
            build.validate(self.edition,self.articles)

    def test_short_preview_and_short_reader_are_distinct_publication_failures(self):
        for field in ['preview','reader']:
            with self.subTest(field=field):
                articles=copy.deepcopy(self.articles)
                if field=='preview':articles[0]['newspaper_analysis']=['Μόνο ένας τίτλος δεν αποτελεί αναλυτική ανάγνωση.']
                else:articles[0]['sections']=[{'kind':'analysis','heading':'Σύντομο','paragraphs':['Λείπει το αναλυτικό πλαίσιο.']}]
                with self.assertRaisesRegex(ValueError,'Newspaper analysis|Full reader'):
                    build.validate(self.edition,articles)

    def test_new_publication_cannot_silently_reuse_the_old_optional_image_policy(self):
        self.edition['published_at']='2026-10-13T18:00:00+03:00'
        self.edition.pop('reading_review')
        self.edition['image_review']['version']=1
        with self.assertRaisesRegex(ValueError,'New publications require'):
            build.validate(self.edition,self.articles)

    def test_preview_is_visible_and_full_reader_has_its_own_link(self):
        rendered=build.card(self.edition,self.articles[0],True)
        self.assertIn(self.articles[0]['newspaper_analysis'][0],rendered)
        self.assertIn('../'+self.articles[0]['url'],rendered)
        self.assertNotIn('story-more',rendered)
        self.assertIn('ui-icon',rendered)

if __name__=='__main__':unittest.main()
