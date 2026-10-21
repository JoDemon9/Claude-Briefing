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
    def test_full_private_packet_is_paged_without_losing_attention_or_approving_content(self):
        original=handoff.module
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'content').rglob('*.json')}
        raw='PRIVATE ACTUAL SOURCE BODY '*1000
        def collected(root,packet_path,private_root):
            packet=json.loads(packet_path.read_text())
            report={'edition_id':packet['edition_id'],'records':[
                {'url':'https://example.org/evidence/'+str(i),'status':'unavailable' if i==0 else 'changed',
                 'text':raw,'owners':[{'kind':'weather','id':'weather'}]} for i in range(55)],'manual_quotes':[]}
            target=packet_path.parent/'collection.json';original('atomic').write_json(target,report)
            return {'report':str(target)}
        sports={'http_attempts':4,'news_links':{key:{'source_url':url,'checked_at':'2026-10-20T18:00:00+03:00',
            'status':'unavailable','items':[],'note':'source_unavailable'} for key,url in original('sports_news').LISTINGS.items()}}
        def modules(name):
            if name=='collect':return SimpleNamespace(collect=collected)
            if name=='sports_news':return SimpleNamespace(collect=lambda cache:sports)
            return original(name)
        with tempfile.TemporaryDirectory() as private, mock.patch.object(handoff,'module',side_effect=modules):
            result=handoff.prepare(ROOT,'2026-10-20','evening','2026-10-20T18:00:00+03:00',private)
            record=json.loads(Path(result['handoff']).read_text())
            self.assertIn('editorial evidence review required',result['status'])
            self.assertGreater(len(result['views']),1)
            rows=[]
            for index,path in enumerate(result['views']):
                path=Path(path)
                self.assertTrue(path.resolve().is_relative_to(Path(private).resolve()))
                self.assertLessEqual(path.stat().st_size,12000)
                text=path.read_text();view=json.loads(text)
                self.assertNotIn(raw,text);rows.extend(view['rows'])
                self.assertEqual(view['page'],index)
                self.assertEqual(view['next_page'],index+1 if index+1<len(result['views']) else None)
            sources=[r for r in rows if r['kind']=='source']
            self.assertEqual(len(sources),55)
            self.assertEqual(sources[0]['status'],'unavailable')
            self.assertEqual(sum(r['kind']=='sports' for r in rows),4)
            self.assertEqual(len(rows),record['inventory']['planning_records'])
            self.assertIn(raw,Path(record['paths']['collection']).read_text())
            self.assertEqual(record['producer_contract']['content_schema_sha256'],hashlib.sha256((ROOT/'templates/v2/content.schema.json').read_bytes()).hexdigest())
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
