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
    if pack.get('financial_policy')=='news-insights-v1' and payload.get('market_briefs'):
        raise ValueError('Use financial insights instead of duplicate @Market explanations')
    review_candidates(payload,pack,old_records)
    module('market_briefing').hydrate(payload,pack,old_records)
    module('financial_insights').hydrate(payload,pack,module('market_briefing'))
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


def review_candidates(payload,pack,old_records):
    """Account for every visible alternative at a shortage, without new research."""
    reasons=payload.pop('candidate_exclusions',{})
    if pack.get('coverage_policy')!='auditable-v1':
        if reasons:raise ValueError('@Exclude requires an auditable-v1 pack')
        return
    news=module('news_digest')
    candidates={c['id']:c for c in pack['candidates']}
    if set(reasons)-set(candidates) or any(not isinstance(v,str) or len(v.strip())<20 for v in reasons.values()):
        raise ValueError('Candidate exclusions need known IDs and specific reasons')
    selected=payload['articles']+[old_records[sid] for sid in payload.get('carry_story_ids',[]) if sid in old_records]
    counts={desk:sum((a.get('section') or module('selection').section(a))==desk for a in selected) for desk in ('world','cyprus')}
    urls={a['story_id']:{news.canonical(s['url']) for s in a.get('sources',[])} for a in selected}
    digest=module('context_view').synthesis(pack)
    visible={json.loads(line)['id'] for line in digest.splitlines() if line.startswith('{"id":') and '"section":' in line}
    audit={}
    for cid,candidate in candidates.items():
        if candidate['section'] not in counts:continue
        ev=candidate['evidence'];readable=[e for e in ev if e.get('access')=='article_excerpt' and e.get('source') and e.get('excerpt')]
        evidence_urls={news.canonical(e['source']['url']) for e in readable}
        owners={sid for sid,links in urls.items() if links & evidence_urls}
        if len(owners)>1 and news.event_hint(candidate['title']):
            raise ValueError('Distinct story slots reuse one explicit event: '+cid+'; review identity, never auto-merge')
        if owners:
            if cid in reasons:raise ValueError('Selected candidate cannot also be excluded: '+cid)
            continue
        if not readable:
            audit[cid]='evidence: '+', '.join(sorted({e.get('rejection_reason','feed_only') for e in ev}))
        elif cid not in visible:audit[cid]='input_byte_cap: not visible to synthesis'
        elif cid in reasons:audit[cid]=reasons[cid]
        elif counts[candidate['section']]<4:
            raise ValueError('Coverage below four needs @Exclude candidate='+cid+' reason="..."')
    payload.setdefault('selection_review',dict(version=2,completed_at=None,global_exception_reason=None,section_shortfalls={}))['candidate_exclusions']=audit


def output_budget(text,slot):
    """Reference tokenizer, not a measurement of ChatGPT account consumption."""
    import tiktoken
    tokens=len(tiktoken.get_encoding('o200k_base').encode(text))
    limit=6500 if slot=='morning' else 4000
    if tokens>limit:
        raise ValueError(f'Synthesis exceeds {limit} o200k_base tokens ({tokens}); preserve input for correction')
    return tokens
