#!/usr/bin/env python3
"""Choose and run blocking candidate gates; return one compact report, keep detailed logs."""
import argparse
from contextlib import redirect_stdout
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
CODE=('scripts/','templates/','tests/','.github/','requirements','BRIEFING_RUNTIME.md')
PROFILES={'content':0,'maintenance':1,'full':2}
DAILY_GATES=('content','preview','integrity')


def module(name):
    spec=importlib.util.spec_from_file_location('checks_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def classify(root,base=None):
    root=Path(root)
    try:
        if not base:base='origin/main'
        subprocess.check_output(['git','-C',str(root),'rev-parse','--verify',base],stderr=subprocess.DEVNULL)
        files=subprocess.check_output(['git','-C',str(root),'diff','--name-only',base,'--'],text=True).splitlines()
        files+=subprocess.check_output(['git','-C',str(root),'ls-files','--others','--exclude-standard'],text=True).splitlines()
    except subprocess.CalledProcessError:
        return {'profile':'maintenance','changed_files':[],'edition_ids':[],'reason':'Unknown baseline; include maintenance unit checks.'}
    profile='maintenance' if any(path.startswith(CODE) for path in files) else 'content'
    editions=set()
    for path in files:
        parts=Path(path).parts
        if len(parts)==3 and parts[:2]==('content','editions'):editions.add(Path(path).stem)
        if len(parts)>=4 and parts[:2]==('content','articles'):editions.add(parts[2])
        if len(parts)>=5 and parts[:3]==('docs','assets','editorial'):editions.add(parts[3])
    return {'profile':profile,'changed_files':sorted(set(files)),'edition_ids':sorted(editions),
            'reason':'Code/policy change: daily gates plus unit regressions.' if profile=='maintenance' else 'Daily content: three quality gates only.'}


def selected_editions(root,edition_ids=()):
    editions=[json.loads(path.read_text()) for path in (Path(root)/'content/editions').glob('*.json')]
    published=[e for e in editions if e['status']=='published' and e.get('published_at')]
    if not published:raise ValueError('No published candidate to check')
    if edition_ids:
        missing=set(edition_ids)-{e['id'] for e in published}
        if missing:raise ValueError('Requested candidate is missing or unpublished: '+', '.join(sorted(missing)))
        return [e for e in published if e['id'] in edition_ids]
    return [max(published,key=lambda e:datetime.fromisoformat(e['published_at'].replace('Z','+00:00')))]


def prepare_candidate_images(root, edition_ids=(), verify_only=False):
    """Prepare selected public assets before validation; never select or approve images."""
    root=Path(root);images=module('prepare_images');prepared=[]
    for path in sorted((root/'content/editions').glob('*.json')):
        edition=json.loads(path.read_text())
        if edition['status']!='published' or (edition_ids and edition['id'] not in edition_ids):continue
        # Historical snapshots can contain legacy illustrations. New publications
        # without image review are rejected by validation, never upgraded here.
        if not edition.get('image_review'):continue
        images.prepare(root,edition['id'],verify_only=verify_only)
        prepared.append(edition['id'])
    return {'edition_ids':prepared,'mode':'verify_only' if verify_only else 'prepare_selected_assets'}


def run(root=ROOT,base=None,prebuilt=False,profile=None,execute=None):
    root=Path(root).resolve();selection=classify(root,base)
    if profile:
        if profile not in PROFILES or PROFILES[profile]<PROFILES[selection['profile']]:
            raise ValueError('Code changes cannot use a weaker check profile')
        selection['profile']=profile
    output=root/'.work/check-report.json';folder=root/'.work/check-logs';folder.mkdir(parents=True,exist_ok=True)
    result={'schema_version':1,'quality_policy_version':2,'daily_gates':list(DAILY_GATES),'status':'running','selection':selection,'steps':[],
            'started_at':datetime.now(timezone.utc).isoformat()}
    try:
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        commit=None
    result['candidate']={'checked_commit_sha':commit,
        'source_commit_sha':os.environ.get('CANDIDATE_SOURCE_SHA') or commit,
        'workflow_run_id':os.environ.get('GITHUB_RUN_ID')}
    atomic=module('atomic')
    def step(name,command=None,fn=None):
        start=time.perf_counter();record={'name':name,'status':'running'};result['steps'].append(record);atomic.write_json(output,result)
        log=folder/(name+'.log')
        try:
            if execute:execute(name,command,fn)
            elif command:
                with log.open('w', encoding='utf-8') as stream:subprocess.run(command,cwd=root,stdout=stream,stderr=subprocess.STDOUT,check=True,env=dict(os.environ, PYTHONUTF8='1'))
            elif fn:
                with log.open('w', encoding='utf-8') as stream,redirect_stdout(stream):
                    value=fn()
                    if value is not None:print(json.dumps(value,ensure_ascii=False))
            record.update(status='passed',seconds=round(time.perf_counter()-start,3),log=str(log.relative_to(root)))
        except Exception as error:
            record.update(status='failed',error_type=type(error).__name__,detail=str(error)[:400],log=str(log.relative_to(root)),seconds=round(time.perf_counter()-start,3))
            result.update(status='failed',failed_step=name);atomic.write_json(output,result);raise
        atomic.write_json(output,result)
    def content():
        inventory=module('selection');rows=[]
        selected=selected_editions(root,selection['edition_ids'])
        selection['edition_ids']=[e['id'] for e in selected]
        for edition in selected:
            articles=[json.loads((root/'content'/p).read_text(encoding='utf-8')) for p in edition['articles']]
            rows.append(inventory.coverage(edition,articles))
        result['section_coverage']=rows
        prepare_candidate_images(root,selection['edition_ids'],verify_only=prebuilt)
        if prebuilt:
            module('publish').validate(root)
        else:
            # The builder already checks source/schema/reading/rights/coverage/
            # dates/identity and generated reader references. Do that once.
            module('build').build(root,incremental=True)
        return {'editions':selection['edition_ids'],'source_review_required':True,'section_coverage':rows}
    step('content',fn=content)
    receipt=module('release').manifest(root)
    if prebuilt and receipt!=json.loads((root/'docs/data/release.json').read_text(encoding='utf-8')):
        result.update(status='failed',failed_step='content');atomic.write_json(output,result)
        raise ValueError('Candidate release receipt is stale')
    if PROFILES[selection['profile']]>=PROFILES['maintenance']:
        step('unit',command=[sys.executable,'-X','utf8','-m','unittest','discover','-s','tests','-q'])
    command=[sys.executable,'-X','utf8','tests/edition_browser_checks.py','--root',str(root),'--screenshots',str(folder/'current-preview')]
    for eid in selection['edition_ids']:command.extend(['--edition',eid])
    step('preview',command=command)
    if selection['profile']=='full':
        for name in ('browser_checks','frontend_polish_browser_checks','editorial_browser_checks'):
            step(name,command=[sys.executable,'tests/'+name+'.py','--screenshots',str(folder/name)])
    def integrity():
        if module('release').manifest(root)!=receipt:raise ValueError('Candidate changed during quality checks')
        if not prebuilt:atomic.write_json(root/'docs/data/release.json',receipt)
        return {'release_id':receipt['release_id'],'immutable_candidate':True}
    step('integrity',fn=integrity)
    result.update(status='passed',release_id=receipt['release_id'],completed_at=datetime.now(timezone.utc).isoformat())
    atomic.write_json(output,result)
    return {'status':'passed','profile':selection['profile'],'release_id':receipt['release_id'],
            'steps':len(result['steps']),'report':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--base');parser.add_argument('--prebuilt',action='store_true');parser.add_argument('--profile',choices=tuple(PROFILES))
    parser.add_argument('--classify',action='store_true');args=parser.parse_args()
    print(json.dumps(classify(args.root,args.base) if args.classify else run(args.root,args.base,args.prebuilt,args.profile),ensure_ascii=False))
