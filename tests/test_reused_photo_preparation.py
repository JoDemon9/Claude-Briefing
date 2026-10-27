"""Fresh CI checkouts must restore reviewed photo bytes without network or re-encoding."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reused_prepare_images', ROOT/'scripts/v2/prepare_images.py')
images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(images)


class ReusedPhotoPreparationTests(unittest.TestCase):
    def fixture(self, root):
        source = root/'docs/assets/editorial/library/photo.webp'
        source.parent.mkdir(parents=True)
        Image.new('RGB', (320, 240), '#123456').save(source, 'WEBP')
        raw = source.read_bytes()
        article = {'id': 'lead', 'image': {
            'url': 'assets/editorial/current/lead.webp',
            'original_url': 'https://upload.wikimedia.org/example.jpg',
            'reuse_review': {'source_asset': 'assets/editorial/library/photo.webp',
                             'sha256': hashlib.sha256(raw).hexdigest(),
                             'relevance_and_archive_date_checked': True}}}
        (root/'content/articles').mkdir(parents=True)
        (root/'content/editions').mkdir()
        (root/'content/articles/lead.json').write_text(json.dumps(article))
        (root/'content/editions/current.json').write_text(json.dumps({
            'articles': ['articles/lead.json'], 'photo_policy': 'real-photos-v1'}))
        return source, root/'docs'/article['image']['url'], raw

    def test_missing_target_copies_exact_reviewed_bytes_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, raw = self.fixture(root)
            with mock.patch.object(images.urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')) as network:
                images.prepare(root, 'current')
                images.prepare(root, 'current', verify_only=True)
            self.assertEqual(target.read_bytes(), raw)
            self.assertEqual(source.read_bytes(), raw)
            network.assert_not_called()

    def test_verify_only_keeps_missing_target_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, target, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'Missing image asset'):
                images.prepare(root, 'current', verify_only=True)
            self.assertFalse(target.exists())

    def test_changed_reviewed_source_is_rejected_before_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, _ = self.fixture(root)
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'source no longer matches'):
                images.prepare(root, 'current')
            self.assertFalse(target.exists())

    def test_existing_different_target_is_rejected_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, target, _ = self.fixture(root)
            target.parent.mkdir(parents=True)
            Image.new('RGB', (320, 240), '#abcdef').save(target, 'WEBP')
            changed = target.read_bytes()
            with self.assertRaisesRegex(ValueError, 'bytes do not match'):
                images.prepare(root, 'current')
            self.assertEqual(target.read_bytes(), changed)


if __name__ == '__main__':
    unittest.main()
