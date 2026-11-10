#!/usr/bin/env python3
"""Offline private-pack replay. Never fetch, reseal or overwrite production packets.

Only saved excerpts can be replayed; absent raw HTML and unfetched alternatives
remain unknown. Store the URL-level output privately, never in public artifacts.
"""
import argparse
import copy
from datetime import datetime
import importlib.util
import json
from pathlib import Path


def module(name):
    spec=importlib.util.spec_from_file_location('audit_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def replay(pack):
    news=module('news_digest');projected=copy.deepcopy(pack);items=[];excluded=[];routing=[]
    by_evidence={e['id']:c for c in pack['candidates'] for e in c['evidence']}
    for candidate in pack['candidates']:
        for original in candidate['evidence']:
            item=copy.deepcopy(original)
            section=news.geography(item.get('title',candidate['title']),item['url'],candidate['section'])
            if section!=candidate['section']:
                routing.append(dict(id=item['id'],url=item['url'],before=candidate['section'],after=section))
            item['section']=section
            if section=='sports':item['sports_lane']=news.sports_lane(item.get('title',''),item.get('sports_lane') or 'other')
            reason=item.get('rejection_reason') if item.get('access')!='article_excerpt' else news.body_rejection(item.get('excerpt',''))
            if not news.news_report(item.get('title',candidate['title'])):reason='not_reporting'
            published=item.get('published_at') or (item.get('source') or {}).get('published_at')
            if published and datetime.fromisoformat(published)>datetime.fromisoformat(pack['prepared_at']):reason='future_publication'
            if item.get('access')!='article_excerpt':reason=reason or 'feed_only'
            if reason:
                excluded.append(dict(id=item['id'],url=item['url'],section=section,reason=reason))
                item.update(access='feed_only',source=None,rejection_reason=reason)
            else:item['excerpt']=news.article_text(item['excerpt'])
            items.append(item)
    candidates=[]
    for group in news.cluster(items):
        original=by_evidence[group[0]['id']]
        candidate=copy.deepcopy(original)
        candidate.update(section=group[0]['section'],sports_lane=group[0].get('sports_lane'),evidence=group)
        # Combine hints, never assign a published story identity from similarity.
        for key in ('baseline_matches','known_story_matches'):
            candidate[key]=[]
            for item in group:
                for hint in by_evidence[item['id']].get(key,[]):
                    if hint not in candidate[key]:candidate[key].append(hint)
        candidates.append(candidate)
    projected['candidates']=candidates
    projected['evidence']={e['id']:e for e in items}
    for desk in ('cyprus','world','sports'):
        pipeline=projected.setdefault('metrics',{}).setdefault('pipeline',{}).setdefault(desk,{})
        pipeline.update(discovered=sum(e['section']==desk for e in items),fetched=sum(e['section']==desk for e in items),
            readable=sum(c['section']==desk and any(e['access']=='article_excerpt' for e in c['evidence']) for c in candidates),
            rejected=[e for e in excluded if e['section']==desk])
    return projected,dict(excluded=excluded,routing=routing,
        events=[dict(id=c['id'],section=c['section'],evidence=[e['id'] for e in c['evidence']]) for c in candidates])


def audit(root,runs,start,end):
    results=[]
    for path in sorted(Path(runs).glob('*/research_pack.json')):
        if not start<=path.parent.name[:10]<=end:continue
        pack=module('research_pack').load(path);original=copy.deepcopy(pack)
        projected,report=replay(pack)
        digest=module('context_view').synthesis(projected)
        assert pack==original,'Replay mutated a sealed packet'
        assert len(digest.encode('utf-8'))<=48000
        report.update(edition_id=pack['edition_id'],pack_sha256=pack['sha256'],digest_bytes=len(digest.encode('utf-8')),
            recorded_article_requests=pack.get('metrics',{}).get('article_requests'),
            readable_events={k:v['readable'] for k,v in projected['metrics']['pipeline'].items()},
            diagnostic_lines=[line for line in digest.splitlines() if line.startswith(('Excluded article-backed','Evidence shortfall','Visible article-backed'))])
        edition_path=Path(root)/'content/editions'/(pack['edition_id']+'.json')
        if edition_path.exists():
            edition=json.loads(edition_path.read_text(encoding='utf-8'))
            articles=[json.loads((Path(root)/'content'/p).read_text(encoding='utf-8')) for p in edition['articles']]
            report['published_selection']=module('selection').coverage(edition,articles)
            urls={module('news_digest').canonical(s['url']) for a in articles for s in a['sources']}
            report['unselected_evidence']=[dict(id=e['id'],url=e['url'],section=e['section'],
                reason=e.get('rejection_reason') or 'not_selected_in_published_snapshot') for e in projected['evidence'].values()
                if module('news_digest').canonical(e['url']) not in urls]
        results.append(report)
    if not results:raise ValueError('No sealed packs in the requested interval')
    return dict(scope='Offline saved-excerpt replay; no raw HTML or unfetched alternatives are inferred. Historical editorial omissions without recorded reasons remain unspecified.',
                packs=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--runs',type=Path,required=True)
    parser.add_argument('--start',required=True);parser.add_argument('--end',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=audit(args.root,args.runs,args.start,args.end)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'packs':len(result['packs']),'output':str(args.output)}))
