"""Article photo provenance, bounded offline handoff, and mandatory fallback."""
import base64
import copy
from datetime import datetime, timezone
from email.message import Message
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('source_test_'+name, ROOT/'scripts/v2'/f'{name}.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


photos = load('source_photos')
PAGE = 'https://www.philenews.com/news/story'
URL = 'https://www.philenews.com/photos/event.jpg'
CAPTION = 'Photo: the opening of the public building in Nicosia'
LICENCE = 'https://creativecommons.org/licenses/by/4.0/'


def html(**overrides):
    obj = dict(contentUrl=URL, caption=CAPTION, creditText='Fixture Photographer', license=LICENCE)
    obj.update(overrides)
    return '<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','url':PAGE,'image':obj})+'</script>'


class Response(io.BytesIO):
    status = 200
    def __init__(self, data, url=URL, mime='image/jpeg'):
        super().__init__(data); self.url = url; self.headers = Message(); self.headers['Content-Type'] = mime
    def geturl(self): return self.url


def fixture_bytes():
    # A synthetic transport fixture, never a published editorial photo.
    im = Image.new('RGB', (500, 300), 'blue')
    out = io.BytesIO(); im.save(out, 'JPEG'); return out.getvalue()


def candidate():
    row = photos.extract(BeautifulSoup(html(), 'html.parser'), PAGE)[0]
    return photos.eligible(row, PAGE, photos.policy(ROOT))


def record():
    with tempfile.TemporaryDirectory() as cache:
        return photos.fetch(candidate(), photos.policy(ROOT), cache, lambda *a, **k: Response(fixture_bytes()))


class SourcePhotoTests(unittest.TestCase):
    def test_article_metadata_and_figure_are_merged_without_network(self):
        markup = html()+'<article><figure><img src="/photos/event.jpg"><figcaption>'+CAPTION+'</figcaption></figure></article><meta property="og:image" content="'+URL+'">'
        with mock.patch('urllib.request.urlopen', side_effect=AssertionError('network')):
            rows = photos.extract(BeautifulSoup(markup, 'html.parser'), PAGE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['license_url'], LICENCE)
        self.assertEqual(rows[0]['attribution'], 'Fixture Photographer')

    def test_footer_article_licence_social_image_and_credit_are_not_image_permission(self):
        markup = html(license='').replace('"url":', '"license":"'+LICENCE+'", "url":', 1)
        markup += '<footer><a rel="license" href="'+LICENCE+'">licence</a></footer>'
        row = photos.extract(BeautifulSoup(markup, 'html.parser'), PAGE)[0]
        self.assertIsNone(photos.eligible(row, PAGE, photos.policy(ROOT)))
        for licence in ('https://creativecommons.org/licenses/by-nc/4.0/', 'https://creativecommons.org/licenses/by-nd/4.0/', LICENCE+'?fake=1'):
            self.assertIsNone(photos.eligible(dict(row, license_url=licence), PAGE, photos.policy(ROOT)))

    def test_unrelated_jsonld_and_logos_are_rejected(self):
        markup = html().replace(PAGE, PAGE+'-other')
        self.assertEqual(photos.extract(BeautifulSoup(markup, 'html.parser'), PAGE), [])
        for values in ({'contentUrl':'/logo.png'}, {'caption':'AI generated illustration of a building'}):
            self.assertEqual(photos.extract(BeautifulSoup(html(**values), 'html.parser'), PAGE), [])
        row = photos.extract(BeautifulSoup(html(caption='A chart of the economy'), 'html.parser'), PAGE)[0]
        self.assertIsNone(photos.eligible(row, PAGE, photos.policy(ROOT)))

    def test_image_rights_do_not_enable_arbitrary_hosts_or_redirects(self):
        rules = photos.policy(ROOT)
        self.assertIsNone(photos.eligible(dict(candidate(), url='https://127.0.0.1/image.jpg'), PAGE, rules))
        with tempfile.TemporaryDirectory() as cache:
            for url in ('https://evil.example/image.jpg', 'http://www.philenews.com/image.jpg'):
                with self.assertRaises(ValueError):
                    photos.fetch(candidate(), rules, cache, lambda *a, **k: Response(fixture_bytes(), url))

    def test_decode_bounds_and_cache_keep_exact_original_retrieval(self):
        with tempfile.TemporaryDirectory() as cache:
            opener = mock.Mock(side_effect=lambda *a, **k: Response(fixture_bytes()))
            first = photos.fetch(candidate(), photos.policy(ROOT), cache, opener)
            second = photos.fetch(candidate(), photos.policy(ROOT), cache, opener)
            self.assertEqual(first, second); self.assertEqual(opener.call_count, 1)
            image, raw = photos.validate(first)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), image['source_review']['sha256'])
            self.assertNotIn('relevance_and_archive_date_checked', image['source_review'])
        with self.assertRaises((ValueError, OSError)): photos.image_bytes(b'not an image')
        im = Image.new('RGB', (100,100)); data = io.BytesIO(); im.save(data,'PNG')
        with self.assertRaises(ValueError): photos.image_bytes(data.getvalue())

    def test_sealed_bytes_and_visual_hash_tampering_fail(self):
        photo = record()
        bad = copy.deepcopy(photo); bad['data'] = base64.b64encode(b'corrupted').decode()
        with self.assertRaises(ValueError): photos.validate(bad)
        bad = copy.deepcopy(photo); bad['image']['source_review']['perceptual_hash'] = 'f'*16
        with self.assertRaises(ValueError): photos.validate(bad)

    def test_download_failures_and_unknown_rights_leave_fallback_available(self):
        row = dict(access='article_excerpt', source={'url':PAGE}, image_candidates=[candidate()])
        with tempfile.TemporaryDirectory() as cache:
            result = photos.prepare({'e1':row}, ROOT, cache, mock.Mock(side_effect=TimeoutError))
            self.assertEqual(result['photos'], {}); self.assertEqual(result['metrics']['failed'], 1)
            row['image_candidates'][0]['license_url'] = ''
            opener = mock.Mock(side_effect=AssertionError('must not fetch'))
            result = photos.prepare({'e1':row}, ROOT, cache, opener)
            self.assertEqual(result['metrics']['no_eligible_image'], 1); opener.assert_not_called()

    def test_download_attempts_are_bounded_separately_from_article_requests(self):
        row = dict(access='article_excerpt', source={'url':PAGE}, image_candidates=[candidate()])
        with tempfile.TemporaryDirectory() as cache, mock.patch.object(photos, 'fetch', side_effect=TimeoutError) as fetch:
            result = photos.prepare({f'e{i}':row for i in range(30)}, ROOT, cache)
        self.assertEqual(fetch.call_count, 24); self.assertEqual(result['metrics']['failed'], 24)

    def test_only_cited_evidence_gets_source_photo_and_duplicates_try_alternatives(self):
        photo = record()
        source = dict(url=PAGE, access='read', used_for_claims=True)
        payload = {'articles':[{'sources':[source]}, {'sources':[dict(source,url=PAGE+'-other')]}]}
        pack = {'evidence':{'e1':dict(access='article_excerpt',source=source)}, 'source_photos':{'photos':{'e1':photo}}}
        photos.attach(payload,pack)
        self.assertIn('_source_photos',payload['articles'][0]); self.assertNotIn('_source_photos',payload['articles'][1])
        article = payload['articles'][0]
        self.assertIsNotNone(photos.select(article,set()))
        self.assertIsNone(photos.select(article,{photo['image']['source_review']['perceptual_hash']}))
        tampered = copy.deepcopy(article); tampered['sources'][0]['url'] = PAGE+'-other'
        with self.assertRaises(ValueError): photos.select(tampered,set())

    def test_compiler_uses_source_bytes_offline_then_mandatory_licensed_fallback(self):
        compose = load('compose'); policy = load('photo_policy')
        original = json.loads((ROOT/'content/articles/2026-10-28-morning/kherson-humanitarian-truce.json').read_text())
        raw = dict(original,slug=original['id'],section='world',sources=[dict(original['sources'][0],url=PAGE)],_source_photos=[record()])
        catalog = policy.extend_catalog({'photos':[]},ROOT)
        with mock.patch('urllib.request.urlopen', side_effect=AssertionError('offline compiler')):
            doc, data = compose.article(raw,'2026-10-29-morning',0,ROOT,catalog,require_photo=True)
            self.assertIn('source_review',doc['image'])
            self.assertEqual(data,base64.b64decode(raw['_source_photos'][0]['data']))
            used = {doc['image']['source_review']['sha256']}
            fallback, _ = compose.article(raw,'2026-10-29-morning',0,ROOT,catalog,require_photo=True,used_photos=used)
        self.assertIn('reuse_review', fallback['image']); self.assertNotIn('source_review', fallback['image'])
        raw['image_selection'] = {'photo_id':'0'*64}
        with self.assertRaisesRegex(ValueError,'Required real photograph'):
            compose.article(raw,'2026-10-29-morning',0,ROOT,catalog,require_photo=True)

    def test_photo_payload_does_not_expand_model_digest(self):
        compose = load('compose'); view = load('context_view')
        draft = compose.scaffold('2026-10-29-morning',ROOT)
        pack = dict(prepared_at=datetime.now(timezone.utc).isoformat(),edition_id=draft['edition_id'],sha256='a'*64,
                    baseline=None,baseline_stories=[],weather_status='unavailable',candidates=[],evidence={},
                    data={k:draft[k] for k in ('markets','sports','panels','freshness','opportunities')})
        before = view.synthesis(pack)
        pack['source_photos'] = {'photos':{'e1':record()}}
        self.assertEqual(before,view.synthesis(pack))

    def test_archive_fallback_variety_never_selects_an_unrelated_photo(self):
        policy = load('photo_policy'); rules = policy.load(ROOT)
        article = {'section':'world','headline':'Ukraine and France discuss talks'}
        first = policy.selection(article, ROOT)
        second = policy.selection(article, ROOT, {first['photo_id']})
        self.assertNotEqual(first['photo_id'], second['photo_id'])
        self.assertEqual(second['photo_id'],rules['photos']['france']['id'])
        self.assertEqual(policy.selection({'section':'world','headline':'Unknown topic'},ROOT)['photo_id'],rules['photos']['earth']['id'])


if __name__ == '__main__': unittest.main()
