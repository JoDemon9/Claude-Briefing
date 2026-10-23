#!/usr/bin/env python3
"""Private, bounded model-facing projections; full evidence remains on disk."""
import argparse
import hashlib
import json
from pathlib import Path

MAX_BYTES=12000


def encoded(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def project(packet=None,collection=None,sports=None):
    rows=[];header={'scope':'Planning metadata only. Read actual supporting evidence for new/material claims; hashes and this view grant no review.',
                    'broad_discovery_required':True}
    if packet:
        header.update(edition_id=packet['edition_id'],as_of=packet['as_of'],section_targets=packet.get('section_targets'),
                      resume=packet.get('resume_research'),weather=packet.get('weather'),baseline=packet.get('baseline'))
        for index,story in enumerate(packet.get('stories',[])):
            notes=story.get('editorial_notes') or {}
            rows.append({'kind':'story','index':index,**{k:story.get(k) for k in ('story_id','headline','finding','section','published_at','article_path')},
                         'evidence_dates':sorted({s.get('retrieved_at') for s in story.get('sources',[]) if s.get('retrieved_at')}),
                         'unresolved':notes.get('unresolved',[]),'next_check_at':notes.get('next_check_at')})
            rows[-1]['status'] = 'historical_context; review changes or explicitly carry'
        for index,item in enumerate(packet.get('opportunities',[])):
            record=item['record'];review=item['review']
            rows.append({'kind':'opportunity','index':index,'id':record['id'],'status':record['status'],
                         'verified_at':record['verified_at'],'due':review['due'],'due_at':review['due_at'],'reasons':review['reasons']})
        rows.extend({**r,'record_kind':r.get('kind'),'kind':'due'} for r in packet.get('due_checks',[]))
        rows.extend({**r,'kind':'discovery'} for r in packet.get('discovery',{}).get('items',[]))
        header['discovery_status']=packet.get('discovery',{}).get('status')
    if collection:
        if header.get('edition_id') and header['edition_id']!=collection['edition_id']:raise ValueError('Collection belongs to another packet')
        header.update(collection_metrics=collection.get('metrics'),manual_quote_instruments=[q['instrument'] for q in collection.get('manual_quotes',[])])
        for index,source in enumerate(collection['records']):
            candidate=source.get('quote_candidate')
            if candidate:
                q=candidate['quote']
                rows.append({'kind':'quote','index':index,'url':source['url'],'status':source['status'],
                             **{k:q.get(k) for k in ('instrument','value','currency','unit','quoted_at','change_pct')},
                             'requires_close_review':candidate.get('requires_close_review')})
            else:
                rows.append({'kind':'source','index':index,**{k:source.get(k) for k in ('url','status','owners','retrieved_at','checked_at','text_truncated')},
                             'evidence_on_disk':bool(source.get('text'))})
    if sports:
        header['sports_http_attempts']=sports['http_attempts']
        for key,record in sports['news_links'].items():rows.append({'kind':'sports','interest':key,**record})
    return header,rows


def page(header,rows,number=0,max_bytes=MAX_BYTES,kind=None):
    if not 2000<=max_bytes<=MAX_BYTES or number<0:raise ValueError('Invalid context page budget/index')
    if kind:rows=[r for r in rows if r['kind']==kind]
    fingerprint=hashlib.sha256(encoded([header,rows]).encode()).hexdigest()
    chunks=[];chunk=[]
    def envelope(items,index,more=True):
        return {'view_sha256':fingerprint,'page':index,'next_page':index+1 if more else None,
                'total_records':len(rows),'header':header,'rows':items}
    for row in rows:
        trial=chunk+[row]
        if len(encoded(envelope(trial,len(chunks))).encode())>max_bytes:
            if not chunk:raise ValueError('One record exceeds the context budget; inspect its exact fields on disk')
            chunks.append(chunk);chunk=[row]
            if len(encoded(envelope(chunk,len(chunks))).encode())>max_bytes:raise ValueError('One record exceeds context budget; inspect exact fields on disk')
        else:chunk=trial
    if chunk or not chunks:chunks.append(chunk)
    if number>=len(chunks):raise ValueError('Context page out of range')
    result=envelope(chunks[number],number,number+1<len(chunks))
    if len(encoded(result).encode())>max_bytes:raise ValueError('Context header exceeds budget')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('packet','collection','sports'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--page',type=int,default=0);parser.add_argument('--max-bytes',type=int,default=MAX_BYTES)
    parser.add_argument('--kind',choices=('story','opportunity','due','discovery','source','quote','sports'))
    args=parser.parse_args()
    if not any((args.packet,args.collection,args.sports)):parser.error('At least one private report is required')
    loaded=[json.loads(path.read_text()) if path else None for path in (args.packet,args.collection,args.sports)]
    header,rows=project(*loaded)
    header['paths']={name:str(getattr(args,name)) for name in ('packet','collection','sports') if getattr(args,name)}
    print(encoded(page(header,rows,args.page,args.max_bytes,args.kind)))
