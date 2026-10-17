import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import subprocess
import unittest
from unittest import mock
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('test_backend_'+name,ROOT/'scripts/v2'/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


backend=load('backend');build=load('build');publish=load('publish');release=load('release');sync=load('sync_portal')


class BackendTests(unittest.TestCase):
    def edition(self, slot='morning'):
        return {'id':'2026-10-16-'+slot,'date':'2026-10-16','type':slot,'status':'published',
                'published_at':'2026-10-16T08:00:00+03:00','editorial_completed_at':'2026-10-16T08:00:00+03:00'}

    def article(self, sid='story-one', headline='A sufficiently specific headline',url='https://example.org/report'):
        return {'id':sid,'story_id':sid,'headline':headline,'url':sid+'.html',
                'sources':[{'url':url,'used_for_claims':True,'access':'read'}]}

    def root_copy(self,root):
        for name in ('content','templates','docs','scripts'):
            shutil.copytree(ROOT/name,root/name)

    def test_contract_is_exact_and_historical_acceptance_requires_unchanged_sources(self):
        edition=self.edition()
        with self.assertRaisesRegex(ValueError,'producer_contract'):backend.check_contract(ROOT,edition)
        caps=backend.capabilities(ROOT)
        edition['producer_contract']={k:caps[k] for k in ('producer_protocol','content_schema_sha256')}
        backend.check_contract(ROOT,edition)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT/'templates',root/'templates')
            (root/'docs/data').mkdir(parents=True)
            record={edition['id']:{'contract':copy.deepcopy(edition['producer_contract']),'source_sha256':backend.edition_fingerprint(edition,[])}}
            (root/'docs/data/edition-contracts.json').write_text(json.dumps(record))
            (root/'templates/v2/content.schema.json').write_text((root/'templates/v2/content.schema.json').read_text()+'\n')
            backend.check_contract(root,edition,[])
            edition['title']='new change'
            with self.assertRaisesRegex(ValueError,'mismatch'):backend.check_contract(root,edition,[])

    def test_duplicate_candidates_require_review_and_aliases_are_explicit(self):
        first,second=self.article(),self.article('story-two','A different headline')
        e=self.edition();e['date']='2026-10-15'
        report=backend.story_registry([(e,[first,second])],{})
        self.assertEqual(report['issues'][0]['kind'],'shared_reporting_url')
        e['date']='2026-10-16'
        with self.assertRaisesRegex(ValueError,'review required'):backend.story_registry([(e,[first,second])],{})
        reviews={i['id']:{'decision':'distinct_stories','reason':'Two separately researched angles of the same official report.'} for i in report['issues']}
        self.assertEqual(backend.story_registry([(e,[first,second])],{},reviews)['issues'][0]['status'],'reviewed')
        with self.assertRaisesRegex(ValueError,'Conflicting story IDs'):
            backend.story_registry([(e,[first,second])],{'story-two':'story-one'})

    def test_alias_cycles_missing_targets_and_future_followups_fail(self):
        with self.assertRaisesRegex(ValueError,'cycle'):backend.story_registry([],{"a":"b","b":"a"})
        with self.assertRaisesRegex(ValueError,'absent'):backend.story_registry([],{"a":"b"})
        e=self.edition();later=self.edition('midday');later['published_at']='2026-10-16T14:00:00+03:00'
        e['daily']={'follow_ups':[{'from_story_id':'story-one','to_story_id':'story-two'}]}
        with self.assertRaisesRegex(ValueError,'unavailable'):
            backend.story_registry([(e,[self.article()]),(later,[self.article('story-two','Later event','https://example.org/later')])],{})

    def test_reused_story_id_with_a_different_editorial_identity_fails(self):
        first=self.article();first['story_identity']='subject/event/2026-10-16'
        second=copy.deepcopy(first);second['story_identity']='other/event/2026-10-16'
        with self.assertRaisesRegex(ValueError,'Conflicting identity'):
            backend.story_registry([(self.edition(),[first]),(self.edition('midday'),[second])],{})

    def record(self,kind='weather'):
        return {'id':'forecast','kind':kind,'label':'Official forecast','checked_at':'2026-10-16T07:00:00+03:00',
                'valid_from':'2026-10-16T06:00:00+03:00','valid_until':'2026-10-16T12:00:00+03:00',
                'recheck_at':'2026-10-16T10:00:00+03:00','sources':['https://example.org/weather']}

    def test_freshness_is_as_of_publication_and_current_audits_do_not_rewrite_history(self):
        e=self.edition();e['freshness']=[self.record()]
        self.assertEqual(backend.freshness(e,[])['records'][0]['state'],'current')
        self.assertEqual(backend.freshness(e,[],now='2026-10-16T13:00:00+03:00')['records'][0]['state'],'expired')
        self.assertEqual(backend.freshness(e,[])['records'][0]['state'],'current')
        e['freshness'][0]['valid_until']='2026-10-16T07:30:00+03:00'
        with self.assertRaisesRegex(ValueError,'Refresh'):backend.freshness(e,[])
        e['freshness'][0]['historical_context']=True
        self.assertEqual(backend.freshness(e,[])['records'][0]['state'],'expired')

    def test_weather_event_and_interval_failures_are_explicit(self):
        e=self.edition();e['panels']=[{'id':'weather'}]
        with self.assertRaisesRegex(ValueError,'structured'):backend.freshness(e,[])
        e['panels']=[]
        e['freshness']=[self.record('event')];e['freshness'][0]['starts_at']='2026-10-16T07:30:00+03:00'
        with self.assertRaisesRegex(ValueError,'Refresh'):backend.freshness(e,[])
        e['freshness'][0]['starts_at']='2026-10-16T09:00:00+03:00';e['freshness'][0]['valid_from']='2026-10-16T13:00:00+03:00'
        with self.assertRaisesRegex(ValueError,'reversed'):backend.freshness(e,[])
        e['freshness'][0]['checked_at']='2026-10-16T14:00:00+03:00'
        with self.assertRaisesRegex(ValueError,'later'):backend.freshness(e,[])

    def test_publication_retry_preserves_completed_stages_and_rechecks_live_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'content/editions').mkdir(parents=True)
            (root/'content/editions/edition.json').write_text(json.dumps(self.edition()))
            calls=[];fail=[True]
            def stage(name):
                def run():
                    calls.append(name)
                    if name=='public_verified' and fail[0]:raise TimeoutError('Pages pending')
                    return {'status':'okay'}
                return run
            handlers={name:stage(name) for name in publish.STAGES}
            with self.assertRaises(TimeoutError):publish.run(root,root/'portal',True,handlers)
            state=json.loads((root/'.work/publication-state.json').read_text())
            self.assertEqual(state['failed_stage'],'public_verified')
            self.assertNotIn('portal_synced',calls)
            fail[0]=False
            state=publish.run(root,root/'portal',True,handlers)
            self.assertEqual(calls.count('public_published'),1)
            self.assertEqual(calls.count('validated'),1)
            self.assertEqual(state['stages']['portal_verified']['status'],'complete')
            self.assertTrue(any(a['stage']=='public_verified' and a['status']=='failed' for a in state['attempts']))
            publish.run(root,root/'portal',True,handlers)
            self.assertEqual(calls.count('portal_published'),1)
            self.assertEqual(calls.count('portal_verified'),2)
            self.assertEqual(publish.status(root)['slots']['evening']['content_status'],'missing')

    def test_changed_inputs_start_a_new_run_and_archive_prior_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'content/editions').mkdir(parents=True)
            edition=self.edition();path=root/'content/editions/edition.json';path.write_text(json.dumps(edition))
            handlers={name:mock.Mock(return_value={}) for name in publish.STAGES}
            publish.run(root,root/'portal',False,handlers)
            self.assertFalse(handlers['public_published'].called)
            edition['title']='New editorial input';path.write_text(json.dumps(edition))
            self.assertFalse(publish.status(root)['source_matches'])
            publish.run(root,root/'portal',False,handlers)
            self.assertEqual(handlers['validated'].call_count,2)
            self.assertEqual(len(list((root/'.work/publication-history').glob('*.json'))),1)

    def test_second_publication_process_cannot_enter_same_checkout(self):
        atomic=load('atomic')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'lock'
            with atomic.lock(path):
                with self.assertRaisesRegex(ValueError,'Another publication'):
                    with atomic.lock(path):pass

    def test_git_publication_preserves_concurrent_wire_and_retry_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);remote=root/'JoDemon9/oracle-briefing.git'
            remote.parent.mkdir()
            def git(path,*args):
                return subprocess.check_output(['git','-C',str(path),*args],text=True,stderr=subprocess.DEVNULL).strip()
            subprocess.run(['git','init','--bare','--initial-branch=main',str(remote)],check=True,capture_output=True)
            local=root/'local';subprocess.run(['git','clone',str(remote),str(local)],check=True,capture_output=True)
            git(local,'config','user.name','Test');git(local,'config','user.email','test@example.org')
            (local/'docs').mkdir();(local/'docs/index.html').write_text('previous')
            (local/'.gitignore').write_text('.work/\n')
            git(local,'add','.');git(local,'commit','-m','Initial');git(local,'push','origin','main')
            other=root/'wire';subprocess.run(['git','clone',str(remote),str(other)],check=True,capture_output=True)
            git(other,'config','user.name','Test');git(other,'config','user.email','test@example.org')
            (other/'docs/wire-health.json').write_text('independent update')
            git(other,'add','.');git(other,'commit','-m','Wire update');git(other,'push','origin','main')
            (local/'docs/index.html').write_text('reviewed newspaper')
            (local/'docs/old.svg').write_text('previously published snapshot asset')
            publisher=publish.GitPublisher(local,'portal')
            result=publisher.publish({'docs/index.html','docs/old.svg'},'abc')
            self.assertEqual(git(remote,'show','main:docs/wire-health.json'),'independent update')
            self.assertEqual(git(remote,'show','main:docs/index.html'),'reviewed newspaper')
            self.assertEqual(publisher.publish({'docs/index.html'},'abc')['commit'],result['commit'])
            (local/'docs/index.html').write_text('next reviewed newspaper')
            publisher.publish({'docs/index.html'},'def')
            self.assertEqual(git(remote,'show','main:docs/index.html'),'next reviewed newspaper')
            (local/'unreviewed.txt').write_text('unrelated')
            with self.assertRaisesRegex(ValueError,'allowlist'):publisher.publish({'docs/index.html'},'ghi')

    def test_failed_portal_candidate_does_not_change_any_live_files(self):
        with tempfile.TemporaryDirectory() as directory:
            portal=Path(directory)/'portal';(portal/'docs/data').mkdir(parents=True)
            (portal/'docs/index.html').write_text('previous good edition')
            (portal/'docs/data/wire.json').write_text('independent Wire')
            def broken(public,candidate):
                (candidate/'docs/index.html').write_text('half built edition');raise OSError('disk failure')
            with mock.patch.object(sync,'_sync',side_effect=broken):
                with self.assertRaises(OSError):sync.sync(ROOT,portal)
            self.assertEqual((portal/'docs/index.html').read_text(),'previous good edition')
            self.assertEqual((portal/'docs/data/wire.json').read_text(),'independent Wire')

    def test_changed_inputs_during_render_keep_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.root_copy(root)
            original=(root/'docs/index.html').read_bytes();render=build._render
            def changed(*args,**kwargs):
                render(*args,**kwargs)
                path=root/'content/legacy-editions.json';path.write_text(path.read_text()+'\n')
            with mock.patch.object(build,'_render',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'inputs changed'):build.build(root)
            self.assertEqual((root/'docs/index.html').read_bytes(),original)
            self.assertFalse((root/'.work/build-cache.json').exists())

    def test_build_stages_outside_synced_checkout_on_same_filesystem(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)/'synced-workspace'
            root=workspace/'checkout';root.mkdir(parents=True);self.root_copy(root)
            render=build._render
            def isolated(candidate,*args,**kwargs):
                self.assertFalse(candidate.is_relative_to(workspace),
                                 'Background sync must not recreate build staging files')
                self.assertEqual(candidate.stat().st_dev,root.stat().st_dev,
                                 'Promotion must remain an atomic same-filesystem rename')
                return render(candidate,*args,**kwargs)
            with mock.patch.object(build,'_render',side_effect=isolated):
                build.build(root)
            self.assertTrue((root/'docs/data/day-latest.json').is_file())
            self.assertEqual(list(workspace.iterdir()),[root])

    def test_failed_build_promotion_restores_previous_docs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'checkout';root.mkdir();self.root_copy(root)
            original=(root/'docs/index.html').read_bytes();replace=build.os.replace
            def promote(source,target):
                if Path(source).name=='docs' and Path(source).parent.name=='candidate':
                    raise OSError('promotion failed')
                return replace(source,target)
            with mock.patch.object(build.os,'replace',side_effect=promote):
                with self.assertRaisesRegex(OSError,'promotion failed'):build.build(root)
            self.assertEqual((root/'docs/index.html').read_bytes(),original)
            self.assertFalse((root/'.work/build-cache.json').exists())

    def test_failed_portal_promotion_restores_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            portal=Path(directory)/'portal';(portal/'docs').mkdir(parents=True)
            (portal/'docs/index.html').write_text('previous good snapshot')
            replace=sync.os.replace
            def promote(source,target):
                if Path(source).name=='docs' and Path(source).parent.name=='candidate':raise OSError('promotion failed')
                return replace(source,target)
            def candidate(public,staged):(staged/'docs/index.html').write_text('new candidate')
            with mock.patch.object(sync,'_sync',side_effect=candidate),mock.patch.object(sync.os,'replace',side_effect=promote):
                with self.assertRaises(OSError):sync.sync(ROOT,portal)
            self.assertEqual((portal/'docs/index.html').read_text(),'previous good snapshot')

    def test_portal_stages_outside_synced_checkout_on_same_filesystem(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)/'synced-workspace'
            portal=workspace/'portal';(portal/'docs').mkdir(parents=True)
            (portal/'docs/index.html').write_text('previous snapshot')
            (portal/'docs/wire.json').write_text('independent Wire')
            def candidate(public,staged):
                self.assertFalse(staged.is_relative_to(workspace))
                self.assertEqual(staged.stat().st_dev,portal.stat().st_dev)
                (staged/'docs/index.html').write_text('complete new snapshot')
            with mock.patch.object(sync,'_sync',side_effect=candidate):sync.sync(ROOT,portal)
            self.assertEqual((portal/'docs/index.html').read_text(),'complete new snapshot')
            self.assertEqual((portal/'docs/wire.json').read_text(),'independent Wire')
            self.assertEqual(list(workspace.iterdir()),[portal])

    def test_incremental_matches_full_build_and_repairs_modified_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.root_copy(root)
            build.build(root)
            with mock.patch.object(build,'card',wraps=build.card) as render:
                result=build.build(root,incremental=True)
                self.assertEqual(result['rendered_editions'],[])
                render.assert_not_called()
            path=root/'content/articles/2026-10-15-midday/world-tsmc.json'
            article=json.loads(path.read_text());article['evidence_note']+=' Verified editorial note.';path.write_text(json.dumps(article,ensure_ascii=False))
            result=build.build(root,incremental=True)
            expected={json.loads(p.read_text())['id'] for p in (root/'content/editions').glob('2026-10-15-*.json')}
            self.assertEqual(set(result['rendered_editions']),expected)
            incremental=load('incremental');expected=incremental.hashes(root/'docs')
            build.build(root)
            self.assertEqual(expected,incremental.hashes(root/'docs'))
            (root/'docs/index.html').write_text('corrupted output')
            self.assertEqual(build.build(root,incremental=True)['mode'],'full')

    def test_incremental_verification_checks_changes_and_retains_last_good_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'docs/data').mkdir(parents=True);(root/'docs/archive').mkdir()
            (root/'docs/archive/old.html').write_text('old')
            (root/'docs/morning.html').write_text('new')
            (root/'docs/data/editions.json').write_text(json.dumps([{'id':'current','url':'morning.html','status':'published','date':'2026-10-15'}]))
            release.record(root);calls=[];bad=set()
            def opener(request,**kwargs):
                name=urlsplit(request.full_url).path.removeprefix('/Claude-Briefing/');calls.append(name)
                response=mock.MagicMock();response.__enter__.return_value=response
                response.status=200;response.geturl.return_value=request.full_url
                response.read.return_value=b'wrong' if name in bad else (root/'docs'/name).read_bytes()
                return response
            first=release.verify_live(root,opener=opener)
            self.assertEqual(first['mode'],'full');calls.clear()
            release.verify_live(root,opener=opener)
            self.assertNotIn('archive/old.html',calls)
            (root/'docs/archive/old.html').write_text('corrected archive');release.record(root);calls.clear()
            bad.add('archive/old.html')
            before=(root/'.work/publication-check.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'does not serve'):release.verify_live(root,opener=opener)
            self.assertIn('archive/old.html',calls)
            self.assertEqual(before,(root/'.work/publication-check.json').read_bytes())
            bad.clear();calls.clear();release.verify_live(root,opener=opener,full=True)
            self.assertIn('archive/old.html',calls)


if __name__=='__main__':unittest.main()
