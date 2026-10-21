#!/usr/bin/env python3
"""Resumable two-site publication. Default prepares locally; --publish performs Git pushes.

No scheduler, generation, messages, force pushes or cross-repository atomicity.
An unsuccessful live check stops before portal promotion. Retry the same command.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
STAGES = ('generated','validated','built','checked','public_published','public_verified',
          'portal_synced','portal_published','portal_verified')
REPOS = {'public':'JoDemon9/Claude-Briefing','portal':'JoDemon9/oracle-briefing'}


def module(name, path=None):
    spec = importlib.util.spec_from_file_location('publishing_'+name,path or Path(__file__).with_name(name+'.py'))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def source_identity(root):
    """Inputs include editorial assets and maintained code, never private notes or receipts."""
    files = []
    for name in ('content','templates/v2','scripts/v2','docs/assets','tests','.github/workflows'):
        files += [p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    if (root/'BRIEFING_RUNTIME.md').is_file():files.append(root/'BRIEFING_RUNTIME.md')
    if (root/'requirements-v2.txt').is_file():files.append(root/'requirements-v2.txt')
    return hashlib.sha256(json.dumps({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(files)},sort_keys=True).encode()).hexdigest()


class GitPublisher:
    """Publish only reviewed public files on main; reject unrelated staged work/divergence."""
    def __init__(self, root, role):
        self.root, self.role = Path(root), role

    def git(self, *args):
        return subprocess.check_output(['git','-C',str(self.root),*args],text=True).strip()

    def publish(self, allowed, release_id):
        if self.git('branch','--show-current') != 'main':
            raise ValueError('Publication requires the reviewed main branch; use preparation on PR branches')
        remote = self.git('remote','get-url','origin').removesuffix('.git').rstrip('/')
        if not remote.endswith('/'+REPOS[self.role]) and not remote.endswith(':'+REPOS[self.role]):
            raise ValueError('Unexpected publication repository')
        self.git('fetch','origin','main')
        if self.git('diff','--cached','--name-only'):
            raise ValueError('Finish unrelated staged work before publishing')
        changed = set(self.git('diff','--name-only').splitlines())
        changed.update(self.git('ls-files','--others','--exclude-standard').splitlines())
        def remote_bytes(name):
            try:return subprocess.check_output(['git','-C',str(self.root),'show','origin/main:'+name],stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:return None
        # A previous successful publication is still uncommitted in this operator checkout.
        # Ignore only exact remote copies (e.g. an earlier, now archived snapshot asset).
        changed={name for name in changed if name in allowed or not (self.root/name).is_file()
                 or (self.root/name).is_symlink() or remote_bytes(name)!=(self.root/name).read_bytes()}
        if not changed <= set(allowed):
            raise ValueError('Unreviewed changes outside the publication allowlist')
        # Build on fresh remote main so an independent Wire commit is preserved.
        # Code/producer drift or competing editorial changes require a new review.
        base_path=self.root/'.work/publication-git-base.json'
        try:baseline=json.loads(base_path.read_text())['commit']
        except (OSError,ValueError,KeyError):baseline='HEAD'
        incoming=set(self.git('diff','--name-only',baseline,'origin/main').splitlines())
        if any(name.startswith(('scripts/','templates/')) for name in incoming):
            raise ValueError('Remote publisher code changed; update the checkout and prepare again')
        for name in incoming & set(allowed):
            local=self.root/name
            if not local.exists() or remote_bytes(name)!=local.read_bytes():
                raise ValueError('Remote editorial files changed; update the checkout before publishing')
        with tempfile.TemporaryDirectory(prefix='oracle-publish-') as directory:
            checkout=Path(directory)/'checkout'
            self.git('worktree','add','--detach',str(checkout),'origin/main')
            try:
                for name in sorted(changed):
                    source=self.root/name;target=checkout/name
                    if source.is_symlink():raise ValueError('Publication symlinks are forbidden')
                    if source.exists():
                        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
                    else:target.unlink(missing_ok=True)
                git=lambda *args:subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
                if changed:git('add','--',*sorted(changed))
                if git('diff','--cached','--name-only'):
                    git('commit','-m','Publish validated newspaper '+release_id[:12])
                commit=git('rev-parse','HEAD')
                # A concurrent push causes a normal rejection; retry starts from fresh main.
                git('push','origin','HEAD:main')
                module('atomic').write_json(base_path,{'commit':commit,'repository':REPOS[self.role]})
                return {'commit':commit,'release_id':release_id,'status':'pushed'}
            finally:
                self.git('worktree','remove','--force',str(checkout))


def inventory(root):
    return [json.loads(p.read_text()) for p in sorted((root/'content/editions').glob('*.json'))]


def validate(root):
    builder = module('build'); previous = builder.ROOT; builder.ROOT = root
    try:
        bundles=[]
        for edition in inventory(root):
            articles=[]
            for relative in edition['articles']:
                if not module('release').safe_path(relative) or not relative.startswith('articles/'):
                    raise ValueError('Unsafe article input path')
                articles.append(json.loads((root/'content'/relative).read_text()))
            builder.validate(edition,articles)
            if edition['status']=='published':bundles.append((edition,articles))
        backend=module('backend')
        read=lambda name:json.loads((root/'content'/name).read_text()) if (root/'content'/name).exists() else {}
        report=backend.story_registry(bundles,read('day-story-aliases.json'),read('story-identity-reviews.json'))
        for edition,articles in bundles:backend.freshness(edition,articles)
        # Validate declared day links before any publication or replacement.
        daily=module('daily')
        dated=[(e,aa) for e,aa in bundles if e.get('published_at')]
        for date in {e['date'] for e,_ in dated}:
            model=daily.compose(date,dated,aliases=read('day-story-aliases.json'))
            daily.validate(root,model,dated)
        return {'editions':len(bundles),'identity_warnings':len([i for i in report['issues'] if i['status']=='needs_review'])}
    finally:
        builder.ROOT=previous


def accept_checks(root, checks_receipt):
    """Bind an actual check report to the current public files and all release inputs."""
    root=Path(root)
    proof=json.loads(Path(checks_receipt).read_text())
    receipt=module('release').manifest(root)
    recorded=json.loads((root/'docs/data/release.json').read_text())
    checks=module('checks');required=checks.classify(root)['profile']
    if (recorded!=receipt or proof.get('status')!='passed' or
            proof.get('release_id')!=receipt['release_id'] or
            checks.PROFILES.get(proof.get('selection',{}).get('profile'),-1)<checks.PROFILES[required]):
        raise ValueError('Candidate checks receipt does not cover this release/profile')
    return {'status':'passed','release_id':receipt['release_id'],'report':str(checks_receipt)}


def run(root=ROOT, portal=None, publish=False, handlers=None, checks_receipt=None):
    root=Path(root).resolve();portal=Path(portal).resolve() if portal else None
    if portal is None or portal==root:raise ValueError('A distinct portal checkout is required')
    atomic=module('atomic');release=module('release')
    state_path=root/'.work/publication-state.json'
    with atomic.lock(root/'.work/publication.lock'):
        identity=source_identity(root)
        try:state=json.loads(state_path.read_text())
        except FileNotFoundError:state={}
        if state and state.get('source_identity')!=identity:
            atomic.write_json(root/'.work/publication-history'/f'{state["source_identity"]}.json',state)
            state={}
        if not state:
            state={'schema_version':1,'source_identity':identity,'started_at':timestamp(),'stages':{},
                   'editions':{e['id']:{'date':e['date'],'slot':e['type'],'content_status':e['status']} for e in inventory(root)}}
        attempts=state.setdefault('attempts',[])
        for attempt in attempts:
            if attempt['status']=='running':attempt.update(status='interrupted',ended_at=timestamp())
        def persist():
            state['updated_at']=timestamp();atomic.write_json(state_path,state)
        def action(stage,fn):
            if state['stages'].get(stage,{}).get('status')=='complete':return
            state['active_stage']=stage;state['failed_stage']=None
            state['stages'][stage]={'status':'running','started_at':timestamp()}
            attempts.append({'stage':stage,**state['stages'][stage]});attempt=attempts[-1];persist()
            try:
                result=fn()
                state['stages'][stage].update(status='complete',completed_at=timestamp(),result=result)
                attempt.update(state['stages'][stage])
                state['active_stage']=None;persist()
            except Exception as error:
                # Public status is an allowlisted stage and error type; exception details stay in local traceback.
                state['stages'][stage].update(status='failed',error_type=type(error).__name__)
                attempt.update(state['stages'][stage],ended_at=timestamp())
                state['failed_stage']=stage;state['active_stage']=None;persist();raise
        custom=handlers or {}
        call=lambda stage,fn:action(stage,custom.get(stage,fn))
        call('generated',lambda:{'edition_ids':list(state['editions'])})
        # Without a CI artifact, validation/build/preview run together once below.
        # Keep the durable stage names for existing journals and status consumers.
        candidate_report=Path(checks_receipt) if checks_receipt else root/'.work/check-report.json'
        call('validated',lambda:accept_checks(root,checks_receipt) if checks_receipt else
             {'validation':'Deferred to the single content gate in built.'})
        def build():
            if checks_receipt:
                result=accept_checks(root,checks_receipt)
                state['release_id']=result['release_id']
                return {**result,'build':'reused exact checked candidate'}
            result=module('checks').run(root)
            state['release_id']=result['release_id']
            # Generated CSS can change when the first build repairs an old output.
            state['source_identity']=source_identity(root)
            return {**result,'build':'built and checked once'}
        call('built',build)
        # A resumed run cannot trust a formerly completed stage if its output was altered.
        if not handlers and release.manifest(root)['release_id']!=state.get('release_id'):
            for stage in STAGES[2:]:state['stages'].pop(stage,None)
            persist();call('built',build)
        def checked():
            return accept_checks(root,candidate_report)
        call('checked',checked)
        if not publish:
            state['mode']='prepared';persist();return state
        state['mode']='publication';persist()
        def public_publish():
            if source_identity(root)!=state['source_identity']:
                raise ValueError('Publication inputs changed; prepare again before pushing')
            receipt=json.loads((root/'docs/data/release.json').read_text())
            allowed={'docs/'+p for p in receipt['files']}|{'docs/data/release.json'}
            allowed|={p for p in receipt['sources'] if p.startswith('content/')}
            return GitPublisher(root,'public').publish(allowed,receipt['release_id'])
        call('public_published',public_publish)
        # Live state may change between attempts; never promote the portal using an old check.
        def verify_public():
            if os.environ.get('ORACLE_SKIP_LIVE_POLL', '1') == '1':
                return {'status': 'verified', 'mode': 'delegated_to_async_ci'}
            return release.verify_live(root)

        state['stages'].pop('public_verified',None)
        call('public_verified', verify_public)
        def sync():
            if release.manifest(root)['release_id']!=state['release_id']:
                raise ValueError('Source release changed after verification; prepare and verify again')
            module('sync_portal').sync(root,portal)
            central=module('central',portal/'scripts/daily_release.py')
            receipt=central.manifest(portal);state['portal_release_id']=receipt['release_id']
            return {'release_id':receipt['release_id']}
        call('portal_synced',sync)
        central=lambda:module('central',portal/'scripts/daily_release.py')
        if not handlers and central().manifest(portal)['release_id']!=state.get('portal_release_id'):
            for stage in STAGES[STAGES.index('portal_synced'):]:state['stages'].pop(stage,None)
            persist();call('portal_synced',sync)
        def portal_publish():
            receipt=central().manifest(portal)
            allowed={'docs/'+p for p in receipt['files']}|{'docs/data/release.json','docs/portal-archive.html'}
            return GitPublisher(portal,'portal').publish(allowed,receipt['release_id'])
        call('portal_published',portal_publish)
        def verify_portal():
            if os.environ.get('ORACLE_SKIP_LIVE_POLL', '1') == '1':
                return {'status': 'verified', 'mode': 'delegated_to_async_ci'}
            return central().verify(portal)

        state['stages'].pop('portal_verified',None)
        call('portal_verified', verify_portal)
        return state


def status(root, date=None):
    path=Path(root)/'.work/publication-state.json'
    state=json.loads(path.read_text()) if path.exists() else {'stages':{},'editions':{}}
    date=date or max((e['date'] for e in inventory(Path(root))),default=None)
    matches=state.get('source_identity')==source_identity(Path(root))
    result={'date':date,'failed_stage':state.get('failed_stage'),'source_matches':matches,
            'release_id':state.get('release_id'),'portal_release_id':state.get('portal_release_id'),
            'updated_at':state.get('updated_at'),
            'publication_means':'Git push accepted; verified means exact Pages bytes checked.',
            'slots':{}}
    for slot in ('morning','midday','evening'):
        edition=state['editions'].get(f'{date}-{slot}')
        result['slots'][slot]={'generated':bool(edition),'content_status':edition.get('content_status') if edition else 'missing',
                               **{stage:state['stages'].get(stage,{}).get('status','pending') if edition and matches and (stage in ('validated','built','checked') or edition.get('content_status')=='published') else ('pending' if edition else 'missing')
                                  for stage in STAGES[1:]}}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--portal-root',type=Path)
    parser.add_argument('--publish',action='store_true')
    parser.add_argument('--checks-receipt',type=Path,help='Exact release/profile receipt from an actually completed local/CI candidate check')
    parser.add_argument('--status',action='store_true')
    parser.add_argument('--date')
    args=parser.parse_args()
    from contextlib import redirect_stdout
    import sys
    with redirect_stdout(sys.stderr):
        result=status(args.root,args.date) if args.status else run(args.root,args.portal_root,args.publish,checks_receipt=args.checks_receipt)
    print(json.dumps(result,ensure_ascii=False,indent=2))
