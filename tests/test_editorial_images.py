import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('image_build',ROOT/'scripts/v2/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)


class EditorialImageTests(unittest.TestCase):
    def test_local_photo_keeps_source_license_and_failure_message(self):
        photo={'url':'assets/editorial/example/lead.webp','alt':'Ονομασία <εικόνας>',
               'attribution':'Ο φωτογράφος','caption':'Φωτογραφία αρχείου, 2025.',
               'source_url':'https://commons.wikimedia.org/wiki/File:example.jpg',
               'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/'}
        rendered=build.image({'image':photo},'../../')
        self.assertIn('../../assets/editorial/example/lead.webp',rendered)
        self.assertIn('Ονομασία &lt;εικόνας&gt;',rendered)
        self.assertNotIn('figcaption',rendered)
        credits=build.photo_credits([({'id':'2026-10-15-morning'},[{'id':'lead','headline':'Δοκιμή','image':photo}])])
        self.assertIn(photo['caption'],credits)
        self.assertIn(photo['source_url'],credits)
        self.assertIn(photo['license_url'],credits)
        self.assertIn('data-image-fallback hidden',rendered)

    def test_missing_photo_does_not_invent_an_image_url(self):
        self.assertEqual(build.image({'image':None}),'')


if __name__=='__main__':unittest.main()
