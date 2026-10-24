"""Model-neutral preparation keeps evidence private and never grants editorial review."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_test',ROOT/'scripts/v2/prepare_run.py')
handoff=importlib.util.module_from_spec(spec);spec.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def test_private_pack_has_one_bounded_digest_and_does_not_approve_or_publish(self):
        class Offline:
            def __init__(self):self.records=[]
            def get(self,url):
                row={'url':url,'status':'unavailable','reason':'offline fixture'}
                self.records.append(row);return row
            def many(self,urls):return {u:self.get(u) for u in sorted(set(urls))}
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'content').rglob('*.json')}
        with tempfile.TemporaryDirectory() as private:
            result=handoff.prepare(ROOT,'2026-10-20','evening','2026-10-20T18:00:00+03:00',private,client=Offline())
            record=json.loads(Path(result['handoff']).read_text(encoding='utf-8'))
            pack=json.loads(Path(result['research_pack']).read_text(encoding='utf-8'))
            self.assertEqual(record['version'],2)
            self.assertFalse(pack['submission_ready'])
            self.assertEqual(pack['metrics']['ai_collection_calls'],0)
            records=handoff.module('baseline').load(ROOT,pack['baseline'])[1]
            self.assertEqual({a['story_id'] for a in records},{a['story_id'] for a in pack['baseline_stories']})
            self.assertEqual(len(pack['data']['markets']),38)
            self.assertEqual(len(pack['data']['sports']['coverage']),4)
            self.assertLessEqual(Path(result['digest']).stat().st_size,48000)
            self.assertTrue(Path(result['digest']).resolve().is_relative_to(Path(private).resolve()))
            self.assertNotIn('reading_review',record)
        after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'content').rglob('*.json')}
        self.assertEqual(before,after)

    def test_public_or_symlinked_private_storage_is_rejected_before_collection(self):
        for path in [ROOT,ROOT/'docs',ROOT/'content']:
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'outside the public'):
                handoff.prepare(ROOT,'2026-10-20','evening','2026-10-20T18:00:00+03:00',path)
        with tempfile.TemporaryDirectory() as tmp:
            link=Path(tmp)/'private';link.symlink_to(ROOT/'docs',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'outside the public'):
                handoff.prepare(ROOT,'2026-10-20','evening','2026-10-20T18:00:00+03:00',link)


if __name__=='__main__':unittest.main()
