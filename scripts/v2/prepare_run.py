#!/usr/bin/env python3
"""Prepare a private editorial handoff for any ChatGPT model. No writing/review/release."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def module(name):
    spec=importlib.util.spec_from_file_location('handoff_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def prepare(root,day,slot,at,private_root,wire_root=None):
    root=Path(root).resolve()
    research=module('research');atomic=module('atomic');context=module('context_view')
    # Require durable private storage outside the public checkout, including symlinks.
    folder=research.private_folder(root,private_root)
    packet,packet_path=research.prepare(root,day,slot,at,private_root,wire_root)
    run=packet_path.parent
    collected=module('collect').collect(root,packet_path,private_root)
    collection=json.loads(Path(collected['report']).read_text())
    sports=module('sports_news').collect(folder/'sports-cache')
    sports_path=run/'sports.json';atomic.write_json(sports_path,sports)
    capabilities=module('backend').capabilities(root)
    atomic.write_json(run/'capabilities.json',capabilities)
    header,rows=context.project(packet,collection,sports)
    header['paths']={'packet':str(packet_path),'collection':collected['report'],'sports':str(sports_path)}
    pages=[];number=0
    while True:
        view=context.page(header,rows,number)
        target=run/'views'/f'{number:03}.json'
        # The serialized file obeys the same UTF-8 budget as the CLI view.
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(context.encoded(view),encoding='utf-8')
        pages.append(str(target))
        if view['next_page'] is None:break
        number=view['next_page']
    handoff={'version':1,'edition_id':packet['edition_id'],'packet_sha256':packet['input_sha256'],
        'prepared_at':datetime.now(timezone.utc).isoformat(),
        'producer_contract':{k:capabilities[k] for k in ('producer_protocol','content_schema_sha256')},
        'paths':{**header['paths'],'capabilities':str(run/'capabilities.json'),'views':pages},
        'inventory':{'planning_records':len(rows),'planning_pages':len(pages),
            'source_statuses':{status:sum(r['status']==status for r in collection['records'])
                               for status in sorted({r['status'] for r in collection['records']})},
            'sports':{key:{'status':row['status'],'headlines':len(row['items'])} for key,row in sports['news_links'].items()}},
        'editorial_steps':[
            'Read every planning page; inspect exact private records for due, failed, disputed or unresolved evidence. These pages are not source evidence.',
            'Scan independent world/Cyprus desks beyond tracked topics; select five world/five Cyprus stories or document genuine researched shortfalls.',
            'Read supporting evidence; separate facts, comparisons, interpretation and material uncertainty. Draft each story once. Never invent a mechanism to add depth.',
            'Scaffold the matching draft and copy stable data. Apply sports metadata to that draft; review Greek headlines and refresh checks if older than 120 minutes at completion.',
            'Review dated market quotes, every-slot weather, due opportunities and relevant licensed photos. Approve only evidence actually reviewed.',
            'One editorial pass checks factual support, original times, omissions and clear Greek; optional analysis/reader must add specific supported knowledge.',
            'Submit one source candidate to existing GitHub checks. Use its exact passing artifact/receipt; verify source Pages, then full-day portal. Preserve blockers and last good releases.'
        ],
        'scope':'Preparation only. No article/edition writes, source-reading approval, verified_at changes, model/API selection, quality waiver or publication.'}
    handoff_path=run/'handoff.json';atomic.write_json(handoff_path,handoff)
    return {'edition_id':packet['edition_id'],'handoff':str(handoff_path),'views':pages,
        'inventory':handoff['inventory'],'status':'prepared; editorial evidence review required'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--date',required=True)
    parser.add_argument('--slot',choices=('morning','midday','evening'),required=True)
    parser.add_argument('--at',required=True,help='Actual research time with UTC offset')
    parser.add_argument('--private-root',type=Path,required=True);parser.add_argument('--wire-root',type=Path)
    args=parser.parse_args()
    print(json.dumps(prepare(args.root,args.date,args.slot,args.at,args.private_root,args.wire_root),ensure_ascii=False))
