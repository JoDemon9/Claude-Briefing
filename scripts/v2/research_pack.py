"""Sealed private handoff and mechanical hydration of one small synthesis response."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def module(name):
    spec=importlib.util.spec_from_file_location('pack_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def seal(pack):
    pack=copy.deepcopy(pack)
    pack.pop('sha256',None)
    pack['sha256']=digest(pack)
    return pack


def load(path):
    pack=json.loads(Path(path).read_text(encoding='utf-8'))
    if pack.get('version')!=1 or seal(pack)!=pack:
        raise ValueError('Research pack integrity/version mismatch')
    return pack


def hydrate(payload,pack,root,at=None):
    """No web access, inferred source review, price lookup, or implicit story inheritance."""
    payload=copy.deepcopy(payload)
    at=at or datetime.now(timezone.utc).isoformat()
    moment=module('research').instant(at)
    prepared=module('research').instant(pack['prepared_at'])
    if seal(pack)!=pack or payload.get('research_pack_sha256')!=pack['sha256']:
        raise ValueError('Synthesis must name the exact prepared research pack')
    if payload['edition_id']!=pack['edition_id'] or not timedelta(0)<=moment-prepared<=timedelta(minutes=90):
        raise ValueError('Missing, stale, future or mismatched pre-run pack; never collect inside the AI task')
    slot=payload['edition_id'].rsplit('-',1)[1]
    if pack.get('selection_policy') == 'balanced-v1' or payload['edition_id'][:10] >= '2026-10-28':
        payload['selection_policy'] = 'balanced-v1'
    if payload.get('baseline')!=pack['baseline']:
        raise ValueError('Synthesis baseline differs from the pre-run baseline')
    if slot!='morning' and not pack['baseline']:
        raise ValueError('Delta editions require an explicit published baseline')
    old_records={}
    if pack['baseline']:
        _,records=module('baseline').load(root,pack['baseline'])
        old_records={a['story_id']:a for a in records}
    routine=('markets','sports','panels','freshness','opportunities')
    if any(k in payload for k in routine):
        raise ValueError('Routine data belongs to Python; do not re-emit it in a synthesis')
    for key in ('published_at','editorial_completed_at'):
        if payload.get(key)=='auto':
            payload[key]=at
    if payload.get('reading_review',{}).get('completed_at')=='auto':
        payload['reading_review']['completed_at']=at
    for key in routine:
        payload[key]=copy.deepcopy(pack['data'][key])
    module('market_briefing').hydrate(payload,pack,old_records)
    module('sports_briefing').hydrate(payload,pack)
    if module('sports_briefing').active(payload['sports']):
        payload['sports']['major_stories_reason']=payload.pop('sports_shortfall_reason','')
    # Structured UEFA facts are rendered by Python, without AI re-emission.
    module('sports_briefing').article_budget(payload['articles'],slot,payload['sports'])
    if slot=='morning' and payload.get('carry_story_ids'):
        raise ValueError('Morning selects at most ten stories; carries belong to delta editions')
    if slot!='morning':
        baseline_ids={s['story_id'] for s in pack['baseline_stories']}
        emitted={a['story_id'] for a in payload['articles']}
        omitted=payload.get('selection_review',{}).get('omitted_stories',{})
        carries=set(payload.get('carry_story_ids',[]))
        if not isinstance(omitted,dict) or any(not isinstance(v,str) or len(v.strip())<20 for v in omitted.values()):
            raise ValueError('Each omitted baseline story needs a specific reason')
        if set(omitted)-baseline_ids or set(omitted)&(emitted|carries):
            raise ValueError('Omitted stories must belong only to the unselected baseline')
        if baseline_ids - emitted - carries - set(omitted):
            raise ValueError('Each baseline story needs an update, @CarryOver id=... or @Omit id=... reason="..."')
    for article in payload['articles']:
        if article.get('change_status') not in ('NEW','UPDATED','REVERSAL','CORRECTION'):
            raise ValueError('Only new/materially changed articles may be emitted; use @CarryOver for unchanged')
        previous=old_records.get(article['story_id'])
        if article['change_status']!='NEW':
            if not previous or article['story_identity']!=previous['story_identity']:
                raise ValueError('Updated stories require the baseline story ID and identity')
            if article.get('published_at',previous['published_at'])!=previous['published_at']:
                raise ValueError('Updated story must preserve original publication time')
            article['published_at']=previous['published_at']
        elif previous:
            raise ValueError('A baseline story is an update, not a new identity')
    budget=payload.get('tool_usage')
    if not isinstance(budget,dict) or set(budget)!={'searches','reads'} or any(type(v)!=int or v<0 for v in budget.values()):
        raise ValueError('Declare search/read counts, including retries and each batched query')
    if budget['searches']>(5 if slot=='morning' else 3) or budget['reads']>(2 if slot=='morning' else 1):
        raise ValueError('Declared web tool budget exceeded')
    points=payload.pop('synthesis_points',[])
    if not 1<=len(points)<=3 or sum(len(p['text'].split()) for p in points)>160:
        raise ValueError('Executive synthesis needs 1–3 points, at most 160 words')
    known={a['story_id'] for a in payload['articles']} | set(payload.get('carry_story_ids',[]))
    if any(not p['stories'] or not set(p['stories'])<=known for p in points):
        raise ValueError('Executive synthesis must reference selected or explicitly carried stories')
    payload['daily']={'summary_60s':[p['text'] for p in points],'summary_story_ids':[p['stories'] for p in points], 'follow_ups':[]}
    scan={k:[] for k in ('geopolitics_macro','cyprus_institutions','markets_tech')}
    for p in points:
        if p['axis'] not in scan:
            raise ValueError('Unknown synthesis axis')
        scan[p['axis']].append(p['text'])
    payload['executive_scan']={k:' '.join(v) for k,v in scan.items()} | {'day_catalysts':[]}
    market_scan=payload.pop('_market_scan','')
    if not payload['executive_scan']['markets_tech'] and market_scan:
        payload['executive_scan']['markets_tech']=market_scan
    payload['delta_log']=[a.get('delta_update') or a['summary'] for a in payload['articles']] if slot!='morning' else []
    payload['synthesis_profile']='single-turn-v1'
    payload['prefetch_provenance']={'sha256':pack['sha256'],'prepared_at':pack['prepared_at']}
    module('source_photos').attach(payload,pack)
    return payload


def output_budget(text,slot):
    """Reference tokenizer, not a measurement of ChatGPT account consumption."""
    import tiktoken
    tokens=len(tiktoken.get_encoding('o200k_base').encode(text))
    limit=6500 if slot=='morning' else 4000
    if tokens>limit:
        raise ValueError(f'Synthesis exceeds {limit} o200k_base tokens ({tokens}); preserve input for correction')
    return tokens
