import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import shutil
import urllib.error

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts/v2'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load('release')
builder = load('build')


class ReleaseTests(unittest.TestCase):
    def fixture(self, root):
        (root/'docs/data').mkdir(parents=True)
        (root/'docs/morning').mkdir()
        (root/'content').mkdir()
        (root/'templates/v2').mkdir(parents=True)
        (root/'docs/morning/2026-10-12.html').write_text('real edition', encoding='utf-8')
        (root/'docs/data/editions.json').write_text(json.dumps([{'id': '2026-10-12-morning', 'status': 'published', 'url': 'morning/2026-10-12.html'}]), encoding='utf-8')
        (root/'content/source.json').write_text('{}', encoding='utf-8')
        (root/'private-notes.md').write_text('PRIVATE', encoding='utf-8')

    def test_release_is_reproducible_and_private_files_are_not_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'project'; self.fixture(root)
            first = release.record(root)
            self.assertEqual(first, release.record(root))
            output = Path(directory)/'package'
            release.stage(root, output)
            self.assertFalse((output/'private-notes.md').exists())
            self.assertFalse((output/'content').exists())
            self.assertTrue((output/'morning/2026-10-12.html').is_file())

    def test_changed_data_produces_a_different_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            first = release.record(root)['release_id']
            (root/'docs/morning/2026-10-12.html').write_text('changed', encoding='utf-8')
            self.assertNotEqual(first, release.record(root)['release_id'])

    def test_private_markdown_symlinks_and_path_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            (root/'docs/source.md').write_text('private', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Non-public'):
                release.record(root)
            self.assertFalse(release.safe_path('../private.json'))
            self.assertFalse(release.safe_path('.env'))

    def test_failed_render_keeps_existing_website(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['content', 'templates', 'docs']:
                shutil.copytree(ROOT/name, root/name)
            marker = root/'docs/index.html'
            original = marker.read_bytes()
            with mock.patch.object(builder, 'write', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    builder.build(root)
            self.assertEqual(original, marker.read_bytes())

    def test_failed_promotion_restores_existing_website(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['content', 'templates', 'docs']:
                shutil.copytree(ROOT/name, root/name)
            original = (root/'docs/index.html').read_bytes()
            real_replace = builder.os.replace
            def replace(source, target):
                if Path(source).name == 'docs' and Path(source).parent.name == 'candidate':
                    raise OSError('promotion failure')
                return real_replace(source, target)
            with mock.patch.object(builder.os, 'replace', side_effect=replace):
                with self.assertRaises(OSError):
                    builder.build(root)
            self.assertEqual(original, (root/'docs/index.html').read_bytes())

    def test_http_success_with_wrong_content_does_not_verify_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root); release.record(root)
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.status = 200
            response.geturl.return_value = release.BASE+'data/release.json'
            response.read.return_value = b'previous release'
            with self.assertRaisesRegex(ValueError, 'does not serve'):
                release.verify_live(root, opener=lambda *a, **k: response)

    def test_unreachable_release_fails_after_a_bounded_retry_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root); release.record(root)
            opener = mock.Mock(side_effect=urllib.error.URLError('connection reset'))
            with mock.patch.object(release.time, 'sleep'):
                with self.assertRaisesRegex(ValueError, 'could not be reached'):
                    release.verify_live(root, opener=opener)
            self.assertEqual(opener.call_count, 3)
            self.assertFalse((root/'.work/publication-check.json').exists())


if __name__ == '__main__':
    unittest.main()
