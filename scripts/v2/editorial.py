"""Reviewed daily overview and reading-depth validation (DEC-004/005)."""
import re

def normalized(text):
    return re.sub(r'\W+', ' ', text.casefold()).strip()

def validate_reading(article):
    """Check structural evidence; editorial judgment is still a human/model review."""
    summary=article['summary']
    preview=article.get('newspaper_analysis',[])
    if len(summary.split())>110:
        raise ValueError('30-second summary must be at most 110 words: '+article['id'])
    if len(' '.join(preview).split())>180:
        raise ValueError('Expanded analysis must be concise (at most 180 words): '+article['id'])
    if any(normalized(p)==normalized(summary) for p in preview):
        raise ValueError('Expanded analysis must add to the factual summary: '+article['id'])
    allowed={s['url'] for s in article['sources'] if s.get('access')=='read' and s.get('used_for_claims')}
    if not allowed:
        raise ValueError('Layered articles require a readable supporting source: '+article['id'])
    evidence=article.get('analysis_sources',[])
    if preview and not evidence:
        raise ValueError('Expanded analysis requires reviewed supporting sources: '+article['id'])
    if any(url not in allowed for url in evidence):
        raise ValueError('Analysis evidence must reference accessible reviewed sources: '+article['id'])
    mode=article.get('reader_mode')
    if mode not in ('full','source'):
        raise ValueError('Reading review v2 requires an explicit reader_mode: '+article['id'])
    if mode=='full':
        if not article.get('reader_value','').strip() or not evidence:
            raise ValueError('Full reader requires a reviewed account of added value and sources: '+article['id'])
        shown={normalized(summary),*(normalized(p) for p in preview)}
        extra=[p for s in article['sections'] for p in s['paragraphs'] if normalized(p) not in shown]
        if not extra:
            raise ValueError('Full reader must add material beyond summary and expansion: '+article['id'])

def overview(stories, bundles, canonical=lambda sid:sid):
    """Never mistake the latest slot's summary for a whole-day overview."""
    latest=bundles[-1][0]
    editorial=latest.get('daily',{})
    paragraphs=editorial.get('summary_60s')
    groups=editorial.get('summary_story_ids')
    known={s['story_id'] for s in stories}
    if latest.get('reading_review',{}).get('version')==2 and (not paragraphs or not groups):
        raise ValueError('Reading review v2 requires a reviewed whole-day overview with story references')
    if paragraphs and groups:
        if len(paragraphs)!=len(groups):
            raise ValueError('Daily summary points need matching story references')
        if sum(len(p.split()) for p in paragraphs)>220:
            raise ValueError('Whole-day 60-second overview must be at most 220 words')
        points=[]
        for text,ids in zip(paragraphs,groups):
            ids=[canonical(sid) for sid in ids]
            if not ids or any(sid not in known for sid in ids):
                raise ValueError('Daily summary references an unavailable participating story')
            points.append({'text':text,'story_ids':ids})
        return {'kind':'reviewed','points':points}
    # Backward compatibility: choose actual selected stories across the day,
    # preserving editorial priority, rather than inventing a cumulative narrative.
    lookup={(e['id'],a['id']):a for e,aa in bundles for a in aa}
    lead=editorial.get('lead_story_id')
    ranked=sorted(stories,key=lambda s:(s['story_id']!=canonical(lead) if lead else False,s['priority'],s['story_id']))
    picked=ranked[:6]
    if len(ranked)>6:
        for section in ('cyprus','world','sports'):
            if not any(s['section']==section for s in picked):
                candidate=next((s for s in ranked if s['section']==section),None)
                if candidate:
                    replace=next((i for i in range(len(picked)-1,0,-1) if sum(s['section']==picked[i]['section'] for s in picked)>1),None)
                    if replace is not None:picked[replace]=candidate
    points=[{'text':lookup[(s['selected']['edition_id'],s['selected']['article_id'])]['summary'],'story_ids':[s['story_id']]} for s in picked]
    return {'kind':'selected_summaries','points':points}
