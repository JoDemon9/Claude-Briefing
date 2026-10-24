#!/usr/bin/env python3
"""Prepare a private editorial handoff for any ChatGPT model. No writing/review/release."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def module(name):
    spec=importlib.util.spec_from_file_location('handoff_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def prepare(root,day,slot,at,private_root,wire_root=None,client=None):
    """Run outside the model task. Persist one sealed pack and one bounded digest."""
    root=Path(root).resolve()
    research=module('research'); atomic=module('atomic'); transport=module('prefetch_http')
    folder=research.private_folder(root,private_root)
    packet,packet_path=research.prepare(root,day,slot,at,private_root,wire_root)
    feeds=json.loads((root/'templates/v2/prefetch-feeds.json').read_text(encoding='utf-8'))
    hosts=module('prefetch').HOSTS | module('sports_data').HOSTS | {h for f in feeds for h in f['hosts']}
    client=client or transport.Client(folder/'source-cache',hosts)
    cutoff=research.instant(at)
    routine=module('prefetch').collect(root,client,cutoff)
    sports=module('sports').prefetch(client,cutoff)
    news=research.ingest(root,packet,client,cutoff,folder)
    evidence={}; count=0
    for candidate in news['candidates']:
        for row in candidate['evidence']:
            count+=1; row['id']='e'+str(count); evidence[row['id']]=row
    opportunities=[{**o['record'],'review_due':True} for o in packet['opportunities']]
    baseline_records=module('baseline').load(root,packet['baseline'])[1] if packet.get('baseline') else []
    pack=module('research_pack').seal(dict(version=1,protocol='oracle-synthesis/1',edition_id=packet['edition_id'],
        submission_workflow_installed=(Path(private_root)/'.github/workflows/submit-synthesis.yml').is_file(),
        submission_ready=(Path(private_root)/'.github/workflows/submit-synthesis.yml').is_file() and os.environ.get('ORACLE_SUBMISSION_READY')=='true',
        prepared_at=transport.now(),baseline=packet.get('baseline'),
        baseline_stories=[dict(story_id=a['story_id'],identity=a['story_identity'],headline=a['headline'],finding=a['summary'],
                              section=a['daily']['section'],published_at=a['published_at']) for a in baseline_records],
        candidates=news['candidates'],evidence=evidence,
        data=dict(markets=routine['markets'],sports=sports,panels=routine['weather']['panels'],freshness=routine['weather']['freshness'],opportunities=opportunities),
        weather_status=routine['weather']['status'],
        metrics={**news['metrics'],'http_requests':len(client.records),'market_rows':len(routine['markets']),
            'market_available':sum(q['status']!='unavailable' for q in routine['markets']),'ai_collection_calls':0},
        failures=[r for r in client.records if r['status']=='unavailable']))
    run=packet_path.parent
    pack_path=run/'research_pack.json'; atomic.write_json(pack_path,pack)
    digest_path=run/'digest.md'
    digest_path.write_text(module('context_view').synthesis(pack),encoding='utf-8')
    handoff=dict(version=2,edition_id=pack['edition_id'],prepared_at=pack['prepared_at'],sha256=pack['sha256'],
        paths=dict(research_pack=str(pack_path),digest=str(digest_path)),inventory=pack['metrics'],
        scope='Pre-run collection only. Read the digest once; write one synthesis, not routine data. No publication or editorial source-review claim.')
    handoff_path=run/'handoff.json'; atomic.write_json(handoff_path,handoff)
    return dict(edition_id=pack['edition_id'],handoff=str(handoff_path),research_pack=str(pack_path),digest=str(digest_path),inventory=pack['metrics'],status='prepared; editorial evidence review required')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--date',required=True)
    parser.add_argument('--slot',choices=('morning','midday','evening'),required=True)
    parser.add_argument('--at',required=True,help='Actual research time with UTC offset')
    parser.add_argument('--private-root',type=Path,required=True);parser.add_argument('--wire-root',type=Path)
    args=parser.parse_args()
    print(json.dumps(prepare(args.root,args.date,args.slot,args.at,args.private_root,args.wire_root),ensure_ascii=False))
