import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    return loaded
latest=module('latest_tests',ROOT/'scripts/v2/latest.py')
build=module('latest_builder_tests',ROOT/'scripts/v2/build.py')
sync=module('latest_sync_tests',ROOT/'scripts/v2/sync_portal.py')

class LatestTests(unittest.TestCase):
    def test_latest_ignores_drafts_and_compares_publication_instants(self):
        records=[{'id':'old','date':'2026-10-13','status':'published','published_at':'2026-10-13T08:00:00+03:00'},
                 {'id':'new','date':'2026-10-13','status':'published','published_at':'2026-10-13T06:00:00+00:00'},
                 {'id':'draft','date':'2026-10-14','status':'draft','published_at':'2026-10-14T12:00:00+00:00'}]
        self.assertEqual(latest.newest(records)['id'],'new')
        self.assertIsNone(latest.newest([records[-1]]))

    def test_css_only_update_refreshes_the_publication_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'docs/morning').mkdir(parents=True)
            (root/'docs/assets').mkdir()
            (root/'docs/data').mkdir()
            (root/'docs/assets/test.css').write_text('body{color:black}')
            (root/'docs/morning/test.html').write_text('<html><head><link rel="stylesheet" href="../assets/test.css"></head><body><main id="main">News</main></body></html>')
            record={'id':'2026-10-13-morning','date':'2026-10-13','status':'published','published_at':'2026-10-13T08:00:00+03:00','url':'morning/test.html'}
            first=latest.publish(root,[record])
            (root/'docs/assets/test.css').write_text('body{color:green}')
            second=latest.publish(root,[record])
            self.assertNotEqual(first['html_sha256'],second['html_sha256'])
            self.assertNotEqual(first['version'],second['version'])

    def test_compact_preserved_lead_keeps_analysis_and_photo_credits(self):
        original='<html><head></head><body><div class="hero-grid"><article class="hero"><figure class="photo"><img src="x.webp"><figcaption>Φωτογράφος · CC BY</figcaption></figure><div class="story-content"><h2>Τίτλος</h2><div class="abstract"><p>Βασική είδηση</p></div></div></article><section class="analysis-grid"><article><p>Ουσιαστική ανάλυση</p></article></section><aside class="hero-side">Άλλες ειδήσεις</aside></div></body></html>'
        result=latest.compact_document(original)
        doc=BeautifulSoup(result,'html.parser')
        self.assertIsNone(doc.select_one('.hero-grid > .analysis-grid'))
        self.assertIn('Ουσιαστική ανάλυση',doc.select_one('.hero details').text)
        self.assertIn('CC BY',doc.select_one('.lead-overview').text)
        self.assertLess(result.index('<h2>'),result.index('<figure'))
        self.assertEqual(latest.compact_document(result),result)

    def test_missing_edition_label_remains_accessible_after_rebuilding(self):
        first=latest.compact_document('<nav class="edition-desk"><span>Μεσημεριανή · Δεν έχει δημοσιευτεί</span></nav>')
        second=latest.compact_document(first)
        self.assertEqual(first,second)
        self.assertIn('Δεν έχει δημοσιευτεί',BeautifulSoup(second,'html.parser').span['aria-label'])

    def test_card_has_context_and_full_reporting_without_navigation(self):
        edition=json.loads((ROOT/'content/editions/2026-10-12-morning.json').read_text(encoding='utf-8'))
        article=json.loads((ROOT/'content'/edition['articles'][1]).read_text(encoding='utf-8'))
        rendered=BeautifulSoup(build.card(edition,article),'html.parser')
        self.assertIn(article['summary'],rendered.text)
        self.assertTrue(rendered.select_one('.card-context'))
        for section in article['sections']:
            for paragraph in section['paragraphs']:
                self.assertIn(paragraph,rendered.text)
        self.assertTrue(rendered.select_one('.story-more > summary'))

    def test_portal_snapshot_preserves_full_html_and_rejects_mismatched_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            portal=Path(directory)/'portal';(portal/'docs').mkdir(parents=True)
            (portal/'docs/index.html').write_text('original portal')
            sync.sync(ROOT,portal)
            doc=BeautifulSoup((portal/'docs/index.html').read_text(encoding='utf-8'),'html.parser')
            self.assertTrue(doc.select_one('#cyprus'))
            self.assertTrue(doc.select_one('#world'))
            self.assertFalse(doc.select('iframe'))
            self.assertEqual((portal/'docs/portal-archive.html').read_text(),'original portal')
            for img in doc.select('img[src]'):
                if img['src'].startswith('assets/latest-snapshot/'):
                    self.assertTrue((portal/'docs'/img['src']).is_file())
            descriptor=json.loads((ROOT/'docs/data/latest.json').read_text(encoding='utf-8'))
            descriptor['html_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'do not match'):
                latest.portal_snapshot(ROOT,descriptor)

    def test_portable_latest_keeps_hash_anchors_and_resolves_article_links(self):
        doc=BeautifulSoup((ROOT/'docs/latest.html').read_text(encoding='utf-8'),'html.parser')
        self.assertEqual(doc.select_one('.navs a[href="#cyprus"]')['href'],'#cyprus')
        self.assertTrue(doc.select_one('link[rel="stylesheet"]')['href'].startswith(latest.BASE+'assets/'))
        self.assertTrue(doc.select_one('.read-link')['href'].startswith(latest.BASE))
        self.assertTrue(doc.find('meta',attrs={'name':'oracle-edition-id'}))

if __name__=='__main__':unittest.main()
