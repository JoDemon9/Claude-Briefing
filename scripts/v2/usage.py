#!/usr/bin/env python3
"""Private pilot/work ledger. Pro quota is an optional observation, never a work estimate."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def module(name):
    spec=importlib.util.spec_from_file_location('usage_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def record(root,packet_path,checks_path=None,private_root=None,manual_web_calls=None,before=None,after=None,same_window=False):
    root=Path(root).resolve();packet=json.loads(Path(packet_path).read_text())
    folder=module('research').private_folder(root,private_root) if private_root else root/'.work/research'
    run=folder/'runs'/packet['edition_id'];run.mkdir(parents=True,exist_ok=True)
    collection=json.loads((run/'collection.json').read_text()) if (run/'collection.json').exists() else {}
    checks=json.loads(Path(checks_path).read_text()) if checks_path and Path(checks_path).exists() else {}
    if manual_web_calls is not None and manual_web_calls<0:raise ValueError('Work counts cannot be negative')
    if any(value is not None and not 0<=value<=100 for value in (before,after)):raise ValueError('Quota observations must be percentages')
    observation={'before_percent':before,'after_percent':after,'same_window_confirmed':same_window,
        'window_delta_percent':after-before if same_window and before is not None and after is not None and after>=before else None,
        'attribution':'Observed account window only; other activity/rolling resets can prevent edition attribution.'}
    slot=packet['edition_id'].rsplit('-',1)[-1]
    prompt=root/'prompts'/(slot+'.md')
    if not prompt.exists():prompt=root/'templates/v2/task-prompts'/(slot+'.txt')
    edition_path=root/'content/editions'/(packet['edition_id']+'.json')
    articles=[]
    if edition_path.exists():
        edition=json.loads(edition_path.read_text())
        paths=[root/'content'/p for p in edition['articles']]
        if any(not p.resolve().is_relative_to((root/'content/articles').resolve()) for p in paths):raise ValueError('Unsafe metrics article')
        articles=[json.loads(p.read_text()) for p in paths]
    quality_status=checks.get('status','not_recorded')
    if quality_status=='passed':
        release=module('release').manifest(root)
        if checks.get('release_id')!=release['release_id'] or packet['edition_id'] not in release['edition_ids']:
            quality_status='stale_or_unrelated_receipt'
    value={'schema_version':1,'edition_id':packet['edition_id'],'recorded_at':datetime.now(timezone.utc).isoformat(),
        'packet_sha256':packet['input_sha256'],
        'work':{'context_stories':len(packet['stories']),'packet_bytes':Path(packet_path).stat().st_size,
            'runtime_policy_bytes':(root/'BRIEFING_RUNTIME.md').stat().st_size,
            'prompt_characters':len(prompt.read_text()) if prompt.exists() else None,
            'manual_web_calls':manual_web_calls,'collection':collection.get('metrics'),
            'article_count':len(articles),'reused_photos':sum(bool(a.get('image',{}).get('reuse_review')) for a in articles if a.get('image'))},
        'quality':{'status':quality_status,'release_id':checks.get('release_id'),
            'profile':checks.get('selection',{}).get('profile'),'failed_step':checks.get('failed_step')},
        'pro_usage_observation':observation,'actual_edition_quota_cost':None,
        'limitation':'Bytes/calls/runtime are work proxies. This record does not prove editorial quality or measured Pro savings.'}
    module('atomic').write_json(run/'metrics.json',value)
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--packet',type=Path,required=True);parser.add_argument('--checks',type=Path);parser.add_argument('--private-root',type=Path)
    parser.add_argument('--manual-web-calls',type=int);parser.add_argument('--usage-before',type=float);parser.add_argument('--usage-after',type=float)
    parser.add_argument('--same-window',action='store_true');args=parser.parse_args()
    print(json.dumps(record(args.root,args.packet,args.checks,args.private_root,args.manual_web_calls,args.usage_before,args.usage_after,args.same_window),ensure_ascii=False,indent=2))
