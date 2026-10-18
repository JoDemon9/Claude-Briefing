#!/usr/bin/env python3
"""Compact public continuity index and private per-run research packets. No generation."""
import argparse
import copy
from datetime import datetime, timedelta, timezone, date
import hashlib
import importlib.util
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
SLOTS=('morning','midday','evening')


def module(name):
    spec=importlib.util.spec_from_file_location('research_'+name,Path(__file__).with_name(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def instant(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Research times require an explicit timezone')
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def bundles(root):
    result=[]
    for path in sorted((root/'content/editions').glob('*.json')):
        edition=read(path)
        if edition['status']!='published' or not edition.get('published_at'):continue
        articles=[]
        for relative in edition['articles']:
            path=root/'content'/relative
            if not path.resolve().is_relative_to((root/'content/articles').resolve()):raise ValueError('Unsafe research article path')
            articles.append(read(path))
        result.append((edition,articles))
    return result


def index(root=ROOT):
    root=Path(root)
    editions=[];stories=[]
    for edition,articles in bundles(root):
        editions.append({k:edition[k] for k in ('id','date','type','published_at','url')})
        for article in articles:
            sources=[s for s in article['sources'] if s.get('access')=='read' and s.get('used_for_claims')]
            dates=[edition['published_at'],article.get('updated_at'),edition.get('analysis_revision_at'),edition.get('image_revision_at')]
            dates += [s.get('retrieved_at') for s in sources]
            available=max((instant(t) for t in dates if t)).isoformat()
            stories.append({'story_id':article['story_id'],'identity':article.get('story_identity'),
                'edition_id':edition['id'],'date':edition['date'],'slot':edition['type'],
                'published_at':article['published_at'],'available_at':available,
                'headline':article['headline'],'finding':article['summary'],
                'section':article.get('daily',{}).get('section',article['category']),
                'priority':article.get('daily',{}).get('priority',1000),
                'article_path':f'articles/{edition["id"]}/{article["id"]}.json',
                'reader_url':article['url'],'sources':[{k:s.get(k) for k in ('url','publisher','reporting_group','published_at','retrieved_at','kind')} for s in sources],
                'freshness':article.get('freshness',[]),'image_asset':article.get('image',{}).get('url') if article.get('image') else None})
    return {'schema_version':1,'protocol':'oracle-editorial/1','editions':editions,'stories':stories,
            'scope':'Published context with original times; never a claim of fresh verification.'}


def opportunity_due(record,at,policy):
    checked=instant(record['verified_at']);rules=policy['opportunities']
    reasons=[]
    hours=rules['closed_hours'] if record['status'] in ('closed','proposed') else rules['legal_right_hours'] if record['kind']=='legal_right' else rules['standard_hours']
    if record['status']=='needs_verification':hours=rules['urgent_hours'];reasons.append('uncertain_status')
    if record['id'] in rules['budget_sensitive_ids'] and record['status']=='open':
        hours=min(hours,rules['urgent_hours']);reasons.append('budget_sensitive')
    for field in ('opens_at','deadline'):
        raw=record.get(field)
        if not raw:continue
        # A date-only deadline covers a local calendar day; do not invent 23:59.
        if len(raw)==10:
            distance=(date.fromisoformat(raw)-at.astimezone(ZoneInfo('Asia/Nicosia')).date()).days
            near=0<=distance<=rules['near_event_hours']/24
            passed=distance<0
        else:
            difference=instant(raw)-at
            near=timedelta(0)<=difference<=timedelta(hours=rules['near_event_hours'])
            passed=difference<timedelta(0)
        if near and record['status'] in ('open','upcoming'):
            hours=min(hours,rules['urgent_hours']);reasons.append('near_'+field)
        if passed and ((field=='deadline' and record['status'] in ('open','upcoming')) or (field=='opens_at' and record['status']=='upcoming')):
            hours=0;reasons.append('status_date_conflict')
    due_at=checked+timedelta(hours=hours)
    return {'due':at>=due_at,'due_at':due_at.isoformat(),'reasons':reasons or ['scheduled_review'],
            'verified_at':record['verified_at'],'action':'check_official_sources' if at>=due_at else 'carry_with_original_verification'}


def validate_opportunity_reviews(root,edition):
    if edition['status']!='published' or edition['date']<'2026-10-16':return
    at=instant(edition.get('editorial_completed_at') or edition['published_at'])
    policy=read(Path(root)/'templates/v2/research-policy.json')
    for record in edition.get('opportunities',[]):
        if instant(record['verified_at'])>at:raise ValueError('Opportunity review cannot follow edition completion')
        review=opportunity_due(record,at,policy)
        if review['due']:raise ValueError('Due opportunity requires actual source review or an honest unavailable/closed update: '+record['id'])


def private_folder(root,private_root):
    private_root=Path(private_root).resolve();root=Path(root).resolve()
    if private_root==root or private_root.is_relative_to(root) or root.is_relative_to(private_root):
        raise ValueError('Research state must be outside the public repository')
    private_root.mkdir(parents=True,exist_ok=True)
    return private_root/'research'


def remember(root,edition_id,at,private_root,notes=None):
    root=Path(root).resolve();moment=instant(at)
    if private_root is None:raise ValueError('A persistent checkpoint requires a private checkout')
    source=root/'content/editions'/(edition_id+'.json')
    if not source.resolve().is_relative_to((root/'content/editions').resolve()):raise ValueError('Unsafe checkpoint identity')
    edition=read(source)
    if edition['id']!=edition_id:raise ValueError('Checkpoint edition identity mismatch')
    articles=[]
    for relative in edition['articles']:
        path=root/'content'/relative
        if not path.resolve().is_relative_to((root/'content/articles').resolve()):raise ValueError('Unsafe checkpoint article')
        articles.append(read(path))
    if any(instant(s['retrieved_at'])>moment for a in articles for s in a['sources'] if s.get('retrieved_at') and s.get('used_for_claims')):
        raise ValueError('Checkpoint cannot include future source evidence')
    folder=private_folder(root,private_root);memory_path=folder/'editorial-memory.json'
    memory=read(memory_path) if memory_path.exists() else {'stories':{},'drafts':{}}
    memory.setdefault('stories',{});memory.setdefault('drafts',{})
    known={a['story_id'] for a in articles}
    for sid,note in (notes or {}).items():
        if sid not in known or not isinstance(note.get('unresolved',[]),list) or any(not isinstance(v,str) for v in note.get('unresolved',[])):
            raise ValueError('Editorial notes need known stable IDs and explicit unresolved questions')
        if note.get('next_check_at') and instant(note['next_check_at'])<moment:raise ValueError('Next review cannot precede this checkpoint')
        memory['stories'][sid]={'reviewed_at':at,'unresolved':note.get('unresolved',[]),'next_check_at':note.get('next_check_at')}
    snapshot={'edition':edition,'articles':articles,'snapshot_at':at,'source_sha256':digest([edition,articles]),
              'status':'research_checkpoint; publication/claim verification remains separate'}
    target=folder/'drafts'/(edition_id+'.json');module('atomic').write_json(target,snapshot)
    memory['drafts'][edition_id]={'snapshot_at':at,'source_sha256':snapshot['source_sha256']}
    module('atomic').write_json(memory_path,memory)
    return {'snapshot':str(target),'stories':len(articles),'source_sha256':snapshot['source_sha256']}


def scaffold(root,packet_path,title,article_paths):
    """Copy stable structured data mechanically; never invent text or approve an edition."""
    root=Path(root).resolve();packet=read(packet_path);eid=packet['edition_id']
    target=root/'content/editions'/(eid+'.json')
    if not target.resolve().is_relative_to((root/'content/editions').resolve()):raise ValueError('Unsafe scaffold identity')
    if target.exists():raise ValueError('Resume the existing edition instead of replacing it')
    previous=packet['market_reference']['edition_id']
    if not previous:raise ValueError('First edition requires a reviewed schema example')
    edition=copy.deepcopy(read(root/'content/editions'/(previous+'.json')))
    for key in ('preserve_legacy_html','aliases','reader_routes','image_review','reading_review','selection_review','producer_contract',
                'summary_60s','daily','panels','freshness','image_revision_at','analysis_revision_at','market_summary','market_movers','market_next_event','market_notes'):
        edition.pop(key,None)
    day,slot=eid.rsplit('-',1)
    if slot not in SLOTS or date.fromisoformat(day).isoformat()!=day:raise ValueError('Invalid scaffold date/slot')
    for relative in article_paths:
        path=root/'content'/relative
        if not path.resolve().is_relative_to((root/'content/articles'/eid).resolve()):raise ValueError('Scaffold readers must belong to the new edition')
        article=read(path)
        if article['edition_id']!=eid:raise ValueError('Scaffold article belongs to another edition')
    edition.update(id=eid,date=day,type=slot,status='draft',title=title,published_at=None,editorial_completed_at=None,
        scheduled_slot={'morning':'07:30','midday':'13:30','evening':'19:30'}[slot],url=f'{slot}/{day}.html',
        articles=article_paths,changes=[],opportunities=[copy.deepcopy(o['record']) for o in packet['opportunities']])
    edition['sports']['major_stories']=[]
    edition['sports']['major_stories_reason']='Δεν έχει ολοκληρωθεί η επιλογή άλλων αθλητικών ειδήσεων.'
    schema=read(root/'templates/v2/content.schema.json')
    from jsonschema import Draft202012Validator,FormatChecker
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(edition)
    module('atomic').write_json(target,edition)
    return {'edition_id':eid,'status':'draft; no review/publication granted','copied_quotes':len(edition['markets']),
            'carried_opportunities':len(edition['opportunities']),'path':str(target)}


def prepare(root,day,slot,at,private_root=None,wire_root=None):
    root=Path(root).resolve();at=instant(at)
    if slot not in SLOTS or date.fromisoformat(day)!=at.astimezone(ZoneInfo('Europe/Athens')).date():
        raise ValueError('Packet date/slot must match its explicit local research time')
    edition_id=day+'-'+slot;policy=read(root/'templates/v2/research-policy.json')
    public=index(root)
    eligible=[r for r in public['stories'] if r['edition_id']!=edition_id and r['date']<=day and instant(r['available_at'])<=at
              and (r['date']<day or SLOTS.index(r['slot'])<SLOTS.index(slot))]
    selected_day=max((r['date'] for r in eligible),default=None)
    selected={}
    aliases=read(root/'content/day-story-aliases.json') if (root/'content/day-story-aliases.json').exists() else {}
    for record in sorted(eligible,key=lambda r:(instant(r['available_at']),SLOTS.index(r['slot']))):
        if record['date']==selected_day:selected[aliases.get(record['story_id'],record['story_id'])]=record
    old_opportunities={};previous=None
    for edition,_ in sorted(bundles(root),key=lambda pair:instant(pair[0]['published_at'])):
        if edition['date']>day or (edition['date']==day and SLOTS.index(edition['type'])>=SLOTS.index(slot)) or instant(edition['published_at'])>at:continue
        previous=edition
        for record in edition.get('opportunities',[]):
            if instant(record['verified_at'])<=at and all(not s.get('retrieved_at') or instant(s['retrieved_at'])<=at for s in record['sources']):
                old=old_opportunities.get(record['id'])
                if not old or instant(record['verified_at'])>instant(old['verified_at']):old_opportunities[record['id']]=record
    memory={}
    folder=private_folder(root,private_root) if private_root else root/'.work/research'
    path=folder/'editorial-memory.json'
    if path.exists():memory=read(path)
    # Private editor notes must be explicit, dated and excluded when they come from the future.
    notes={sid:value for sid,value in memory.get('stories',{}).items() if value.get('reviewed_at') and instant(value['reviewed_at'])<=at}
    checkpoint=memory.get('drafts',{}).get(edition_id)
    resume=None
    if checkpoint and instant(checkpoint['snapshot_at'])<=at:
        snapshot=folder/'drafts'/(edition_id+'.json')
        if snapshot.is_file():
            data=read(snapshot)
            current=root/'content/editions'/(edition_id+'.json')
            if current.exists():
                e=read(current);paths=[root/'content'/p for p in e['articles']]
                if any(not p.resolve().is_relative_to((root/'content/articles').resolve()) for p in paths):raise ValueError('Unsafe checkpoint article')
                aa=[read(p) for p in paths]
                if digest([e,aa])==checkpoint['source_sha256']:resume={'snapshot':str(snapshot),'source_sha256':checkpoint['source_sha256'],'status':'reuse draft research; complete all due/evidence/publication gates'}
    opportunities=[{'record':copy.deepcopy(r),'review':opportunity_due(r,at,policy)} for r in old_opportunities.values()]
    packet={'schema_version':1,'protocol':policy['protocol'],'edition_id':edition_id,'as_of':at.isoformat(),
        'runtime_policy':'BRIEFING_RUNTIME.md','broad_news_scan_required':True,'context_date':selected_day,
        'section_targets':module('selection').TARGETS.copy(),
        'section_selection':{'lead_counts_in_actual_section':True,
            'review_version':2 if module('selection').coverage_required({'date':day,'type':slot}) else 1,
            'action':'Select world and Cyprus separately; investigate shortages before an evidence-backed exception. Later slots retain useful dated context without claiming new reporting.'},
        'resume_research':resume,
        'stories':[{**r,'editorial_notes':notes.get(sid), 'use':'historical_context; research material changes'} for sid,r in sorted(selected.items(),key=lambda p:(p[1]['priority'],p[0]))],
        'opportunities':opportunities,'market_reference':{'edition_id':previous['id'] if previous else None,
            'instruments':[q['instrument'] for q in previous.get('markets',[])] if previous else [],
            'action':'machine_refresh_then_analyse_core_and_material_movers; preserve quote timestamps'},
        'due_checks':[{'owner':previous['id'],**r} for r in previous.get('freshness',[]) if r.get('recheck_at') and instant(r['recheck_at'])<=at] if previous else [],
        'weather':{'check_every_edition':True,'sources':[s['url'] for p in previous.get('panels',[]) if p['id']=='weather' for s in p['sources']]} if previous else {'check_every_edition':True,'sources':[]},
        'discovery':{'status':'not_loaded','items':[]},
        'stop_rule':'Preserve unpublished drafts and report the exact gate; do not debug renderer/tests during generation.'}
    if wire_root:
        wire_root=Path(wire_root);health_path=wire_root/'docs/wire-health.json'
        health=read(health_path) if health_path.exists() else {}
        last=health.get('last_success_at')
        fresh=bool(last and timedelta(0)<=at-instant(last)<=timedelta(minutes=90))
        items=read(wire_root/'docs/live-wire.json') if (wire_root/'docs/live-wire.json').exists() else []
        if isinstance(items,dict):items=items.get('items',[])
        timely=sorted((r for r in items if r.get('published_at') and instant(r['published_at'])<=at),key=lambda r:instant(r['published_at']),reverse=True)
        packet['discovery']={'status':'recent' if fresh else 'stale_use_direct_scan','last_success_at':last,
            'evidence':'Discovery only; open sources before supporting any claim.',
            'items':[{k:r.get(k) for k in ('title','link','source','category','published_at')} for r in timely[:40]] if fresh else []}
    packet['input_sha256']=digest(packet)
    target=folder/'runs'/edition_id/'packet.json';module('atomic').write_json(target,packet)
    return packet,target


def replay(root,editions):
    """Work-volume comparison only. Historical quota accounting is unavailable."""
    root=Path(root);rows=[]
    import tempfile
    docs=['AGENTS.md','OPERATIONS.md','BRIEFING_SPEC.md','CHATGPT_TASK_INSTRUCTIONS.md','DAILY_HUB_HANDOFF.md','templates/v2/content.schema.json','templates/v2/day.schema.json']
    for edition_id in editions:
        edition=read(root/'content/editions'/f'{edition_id}.json')
        at=edition.get('editorial_completed_at') or edition['published_at']
        with tempfile.TemporaryDirectory() as directory:
            packet,_=prepare(root,edition['date'],edition['type'],at,private_root=directory)
        # Legacy instruction size is stored as an honest measured baseline, not Pro tokens.
        history=root/'maintenance/history/2026-10-15'
        instruction_bytes=sum((history/p).stat().st_size if (history/p).exists() else (root/p).stat().st_size for p in docs if (history/p).exists() or (root/p).exists())
        payload_bytes=len(json.dumps(packet,ensure_ascii=False).encode())+(root/'BRIEFING_RUNTIME.md').stat().st_size
        rows.append({'edition_id':edition_id,'prior_stories':len(packet['stories']), 'opportunities_due':sum(o['review']['due'] for o in packet['opportunities']),
            'opportunities_carried':sum(not o['review']['due'] for o in packet['opportunities']),
            'legacy_startup_instruction_bytes':instruction_bytes,'runtime_plus_packet_bytes':payload_bytes,
            'actual_pro_usage_percent':None})
    return {'protocol':'oracle-editorial/1','replays':rows,
            'limitation':'Input bytes/due checks are work proxies, not Pro quota or editorial evaluation. Stored history can include later maintenance; unavailable future evidence is conservatively withheld, not reconstructed.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--date');parser.add_argument('--slot',choices=SLOTS)
    parser.add_argument('--at');parser.add_argument('--private-root',type=Path);parser.add_argument('--wire-root',type=Path)
    parser.add_argument('--remember');parser.add_argument('--notes',type=Path)
    parser.add_argument('--scaffold',type=Path,help='Prepared packet; creates a new draft without retyping carried data')
    parser.add_argument('--title');parser.add_argument('--articles',nargs='+')
    parser.add_argument('--replay',nargs='+');args=parser.parse_args()
    if args.scaffold:result=scaffold(args.root,args.scaffold,args.title,args.articles or [])
    elif args.remember:result=remember(args.root,args.remember,args.at or datetime.now(timezone.utc).isoformat(),args.private_root,read(args.notes) if args.notes else None)
    elif args.replay:result=replay(args.root,args.replay)
    else:
        packet,path=prepare(args.root,args.date,args.slot,args.at or datetime.now(timezone.utc).isoformat(),args.private_root,args.wire_root)
        result={'packet':str(path),'edition_id':packet['edition_id'],'stories':len(packet['stories']),
                'due_opportunities':[o['record']['id'] for o in packet['opportunities'] if o['review']['due']],
                'input_sha256':packet['input_sha256']}
    print(json.dumps(result,ensure_ascii=False,indent=2))
