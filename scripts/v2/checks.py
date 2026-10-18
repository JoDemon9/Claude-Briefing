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
CONTENT_TESTS=('test_reading_policy.py','test_editorial_images.py','test_selection.py','test_opportunities.py','test_follow_ups.py')


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
        return {'profile':'full','changed_files':[],'edition_ids':[],'reason':'Unknown baseline; full checks required.'}
    profile='full' if any(path.startswith(CODE) for path in files) else 'content'
    editions=set()
    for path in files:
        parts=Path(path).parts
        if len(parts)==3 and parts[:2]==('content','editions'):editions.add(Path(path).stem)
        if len(parts)>=4 and parts[:2]==('content','articles'):editions.add(parts[2])
        if len(parts)>=5 and parts[:3]==('docs','assets','editorial'):editions.add(parts[3])
    return {'profile':profile,'changed_files':sorted(set(files)),'edition_ids':sorted(editions),
            'reason':'Publisher/schema/template/test/workflow change.' if profile=='full' else 'Content only; current/changed gates remain blocking.'}


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
    if profile=='full':selection['profile']='full'
    if profile=='content' and selection['profile']=='full':raise ValueError('Code changes cannot use content-only gates')
    output=root/'.work/check-report.json';folder=root/'.work/check-logs';folder.mkdir(parents=True,exist_ok=True)
    result={'schema_version':1,'status':'running','selection':selection,'steps':[],
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
                with log.open('w') as stream:subprocess.run(command,cwd=root,stdout=stream,stderr=subprocess.STDOUT,check=True)
            elif fn:
                with log.open('w') as stream,redirect_stdout(stream):
                    value=fn()
                    if value is not None:print(json.dumps(value,ensure_ascii=False))
            record.update(status='passed',seconds=round(time.perf_counter()-start,3),log=str(log.relative_to(root)))
        except Exception as error:
            record.update(status='failed',error_type=type(error).__name__,seconds=round(time.perf_counter()-start,3))
            result.update(status='failed',failed_step=name);atomic.write_json(output,result);raise
        atomic.write_json(output,result)
    def sections():
        inventory=module('selection');rows=[]
        paths=sorted((root/'content/editions').glob('*.json'))
        for path in paths:
            edition=json.loads(path.read_text())
            if edition['status']!='published':continue
            if selection['edition_ids'] and edition['id'] not in selection['edition_ids']:continue
            articles=[json.loads((root/'content'/p).read_text()) for p in edition['articles']]
            rows.append(inventory.coverage(edition,articles))
        result['section_coverage']=rows
        return rows
    step('prepare_images',fn=lambda:prepare_candidate_images(root,selection['edition_ids'],verify_only=prebuilt))
    step('section_coverage',fn=sections)
    if not prebuilt:
        # The builder validates source inputs before rendering. The complete
        # publication validator also requires generated edition/reader files.
        step('build',fn=lambda:module('build').build(root,incremental=True))
    step('validate',fn=lambda:module('publish').validate(root))
    if not prebuilt:
        step('release_record',fn=lambda:{'release_id':module('release').record(root)['release_id']})
    def integrity():
        if module('release').manifest(root)!=json.loads((root/'docs/data/release.json').read_text()):raise ValueError('Candidate release receipt is stale')
    step('release_integrity',fn=integrity)
    receipt=module('release').manifest(root)
    if selection['profile']=='full':
        step('unit',command=[sys.executable,'-m','unittest','discover','-s','tests','-q'])
        for name in ('browser_checks','frontend_polish_browser_checks','editorial_browser_checks'):
            step(name,command=[sys.executable,'tests/'+name+'.py','--screenshots',str(folder/name)])
    else:
        for test in CONTENT_TESTS:step(Path(test).stem,command=[sys.executable,'-m','unittest','discover','-s','tests','-p',test,'-q'])
        command=[sys.executable,'tests/edition_browser_checks.py','--root',str(root),'--screenshots',str(folder/'changed-preview')]
        for eid in selection['edition_ids']:command.extend(['--edition',eid])
        step('edition_browser',command=command)
    def unchanged():
        if module('release').manifest(root)!=receipt:raise ValueError('Candidate changed during quality checks')
    step('candidate_unchanged',fn=unchanged)
    result.update(status='passed',release_id=receipt['release_id'],completed_at=datetime.now(timezone.utc).isoformat())
    atomic.write_json(output,result)
    return {'status':'passed','profile':selection['profile'],'release_id':receipt['release_id'],
            'steps':len(result['steps']),'report':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--base');parser.add_argument('--prebuilt',action='store_true');parser.add_argument('--profile',choices=('full','content'))
    parser.add_argument('--classify',action='store_true');args=parser.parse_args()
    print(json.dumps(classify(args.root,args.base) if args.classify else run(args.root,args.base,args.prebuilt,args.profile),ensure_ascii=False))
