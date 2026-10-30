"""Bounded market alerts and reviewed explanations. No inferred price causality."""
import copy
from datetime import datetime, timedelta
import math
import re
import unicodedata
from zoneinfo import ZoneInfo

POLICY = 'depth-markets-v1'
COMPANIES = {
    'GOOGL': r'\balphabet\b|\bgoogle\b|\bgoogl?\b|αλφαμπετ',
    'AMZN': r'\bamazon\b|\bamzn\b|αμαζον',
    'NVDA': r'\bnvidia\b|\bnvda\b', 'MSFT': r'\bmicrosoft\b|\bmsft\b',
    'AAPL': r'\bapple\b|\baapl\b', 'META': r'\bmeta\b|\bfacebook\b',
    'TSM': r'\btsmc\b|\btsm\b', 'MU': r'\bmicron\b',
    'GS': r'\bgoldman sachs\b|\bgs\b', 'BAC': r'\bbank of america\b|\bbac\b',
    'BLK': r'\bblackrock\b|\bblk\b', 'STT': r'\bstate street\b|\bstt\b',
    'JNJ': r'\bjohnson\s*(?:&|and)\s*johnson\b|\bjnj\b',
    'BTC-USD': r'\bbitcoin\b|\bbtc\b', 'ETH-USD': r'\bethereum\b|\beth\b',
}
SECURITY = r'\b(?:hack\w*|breach\w*|ransomware|cyberattack\w*|exploit\w*|stolen|theft)\b|κυβερνοεπιθεσ|παραβιασ|κλοπη'
BUSINESS = r'\b(?:earnings|guidance|revenue|profit\w*|shares?|stocks?|antitrust|chips?|semiconductors?|outage\w*|cloud|artificial intelligence)\b|κερδ|μετοχ|εσοδ|τεχνητη νοημοσυνη'


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold()) if not unicodedata.combining(c))


def topic(title, lane=None):
    text = normalized(title)
    if re.search(SECURITY, text): return 'security'
    if re.search(BUSINESS, text) or any(re.search(p, text) for p in COMPANIES.values()): return 'markets-tech'
    return lane if lane in ('finance', 'technology', 'security') else None


def threshold(quote):
    return {'equity':3, 'index':1.5, 'futures_index':1.5, 'crypto':5}.get(quote.get('asset_class'))


def alerts(quotes, at):
    """Use dated provider observations; rank by threshold multiples, with no cause claim."""
    moment = datetime.fromisoformat(at.replace('Z', '+00:00'))
    result = []
    for q in quotes:
        limit = threshold(q)
        change, value = q.get('change_pct'), q.get('value')
        if not limit or any(type(v) not in (int, float) or not math.isfinite(v) for v in (change, value)):
            continue
        if value <= 0 or abs(change) < limit or q.get('status') not in ('live', 'delayed', 'previous_close'):
            continue
        try:
            observed = datetime.fromisoformat(q['quoted_at'].replace('Z', '+00:00'))
            if not observed.tzinfo or not moment.tzinfo: continue
            max_age = timedelta(hours=2 if q.get('asset_class') == 'crypto' else 96)
            if not timedelta(0) <= moment-observed <= max_age: continue
        except (ValueError, TypeError, KeyError):
            continue
        sources = [s for s in q.get('sources', []) if s.get('access') == 'read' and s.get('used_for_claims')]
        if not sources: continue
        result.append(dict(instrument=q['instrument'], name=q['name'], change_pct=change, quoted_at=q['quoted_at'],
                           status=q['status'], priority=q.get('asset_class') == 'equity' and abs(change) >= 5,
                           session=q.get('session'),score=abs(change)/limit, sources=copy.deepcopy(sources)))
    return sorted(result, key=lambda a:(not a['priority'], -a['score'], a['instrument']))


def discovery_score(title, lane=None, market_alerts=()):
    text = normalized(title)
    category = topic(title, lane)
    score = 6 if category == 'security' else 3 if category else 0
    if any(a['instrument'] in COMPANIES and re.search(COMPANIES[a['instrument']], text) for a in market_alerts):
        score += 5
    return score


def reserve(groups, count=2):
    """Reserve within an existing queue, never add article requests or assign identity."""
    picked = sorted([g for g in groups if g[0].get('topic')],
                    key=lambda g:g[0].get('market_priority', 0), reverse=True)[:count]
    return picked + [g for g in groups if g not in picked]


def quote_note(alert):
    delta = f'{alert["change_pct"]:+.2f}'.replace('.', ',')
    # A delayed observation is not automatically an exchange close.
    status = {'live':'ενδοσυνεδριακή', 'delayed':'με καθυστέρηση', 'previous_close':'κλείσιμο'}[alert['status']]
    session={'regular':'κανονική συνεδρίαση','pre':'πριν από το άνοιγμα','post':'μετά το κλείσιμο'}.get(alert.get('session'))
    if session:status+=' · '+session
    reference='το κλείσιμο της κανονικής συνεδρίασης' if alert.get('session') in ('pre','post') else 'την προηγούμενη τιμή αναφοράς του παρόχου'
    display_time=datetime.fromisoformat(alert['quoted_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Nicosia')).strftime('%d/%m/%Y %H:%M %Z')
    return {'text':f'{alert["name"]} ({alert["instrument"]}): {delta}% · {status}, χρόνος τιμής {display_time}. '
                   f'Μεταβολή έναντι {reference}· η αιτία δεν έχει επιβεβαιωθεί.',
            'sources':copy.deepcopy(alert['sources'])}


def hydrate(payload, pack, old_records):
    """Resolve short model directives against the sealed evidence and exact carries."""
    if pack.get('briefing_policy') != POLICY:
        if payload.get('market_briefs') or payload.get('priority_skips'):
            raise ValueError('Market directives require a current briefing pack')
        return
    payload['briefing_policy'] = POLICY
    quotes = {q['instrument']:q for q in pack['data']['markets']}
    current_alerts = alerts(pack['data']['markets'], pack['prepared_at'])
    lookup = {a['instrument']:a for a in current_alerts}
    records = payload['articles'] + [old_records[sid] for sid in payload.get('carry_story_ids', []) if sid in old_records]
    required = [c for c in pack['candidates'] if c.get('priority_required')]
    skips = payload.pop('priority_skips', {})
    if set(skips) - {c['id'] for c in required}:
        raise ValueError('Priority omission must refer to a required visible candidate')
    review = {}
    for candidate in required:
        urls = {e['source']['url'] for e in candidate['evidence'] if e.get('source') and e.get('access') == 'article_excerpt'}
        covered = next((a['story_id'] for a in records if any(s.get('url') in urls and s.get('access') == 'read'
                       and s.get('used_for_claims') for s in a.get('sources', []))), None)
        if covered and candidate['id'] in skips:
            raise ValueError('A covered priority candidate cannot also be omitted')
        if not covered and len(skips.get(candidate['id'], '').strip()) < 20:
            raise ValueError('Cover priority candidate '+candidate['id']+' or supply @SkipPriority with a specific reason')
        review[candidate['id']] = 'covered:'+covered if covered else skips[candidate['id']]
    payload.setdefault('selection_review', {'version':2,'completed_at':payload['editorial_completed_at'],
        'global_exception_reason':None,'section_shortfalls':{}})['priority_candidates'] = review
    technology=[]
    for article in records:
        if not any(s.get('access')=='read' and s.get('used_for_claims') for s in article.get('sources',[])):
            continue
        tags=set(article.get('driver_tags',[]))
        if tags & {'technology','cybersecurity','ai','cloud','chips','earnings','markets-tech'} or topic(article.get('headline','')):
            slug=article.get('slug') or article.get('id')
            technology.append({'story_id':article['story_id'],'headline':article['headline'],
                               'url':article.get('url') or f'articles/{payload["edition_id"]}/{slug}.html'})
    payload['technology_briefing']=technology[:3]
    notes, explained, observations = [], set(), {}
    briefs = payload.pop('market_briefs', [])
    if len(briefs) > 3: raise ValueError('At most three market explanations')
    for brief in briefs:
        instrument = brief['instrument']
        if instrument not in quotes or instrument in explained:
            raise ValueError('Market explanation needs one unique inventory instrument')
        if not 10 <= len(brief['text'].split()) <= 65:
            raise ValueError('Market explanation must contain 10–65 words')
        evidence = [pack['evidence'].get(alias) for alias in brief['evidence']]
        if not evidence or any(not e or e.get('access') != 'article_excerpt' or not e.get('source')
                               or e['source'].get('access')!='read' or not e['source'].get('used_for_claims') for e in evidence):
            raise ValueError('Market explanations require article evidence, never feed-only or quote evidence')
        # Relate the explanation to its instrument without asserting that a keyword proves causation.
        if not any(re.search(COMPANIES.get(instrument, r'(?<!\w)'+re.escape(instrument.casefold())+r'(?!\w)'),
                             normalized(e.get('title', '')+' '+e.get('excerpt', ''))) for e in evidence):
            raise ValueError('Market evidence must identify the explained instrument')
        quote = quotes[instrument]
        if not quote.get('sources') or quote.get('value') is None:
            raise ValueError('Market explanation needs an available quote')
        observation = quote_note(lookup[instrument])['text'] if instrument in lookup else (
            f'{quote["name"]} ({instrument}) · χρόνος τιμής {quote["quoted_at"]}. Η αιτία δεν έχει επιβεβαιωθεί.')
        observation=observation.replace('η αιτία δεν έχει επιβεβαιωθεί.','η τεκμηριωμένη εξήγηση ακολουθεί.')
        observation=observation.replace('Η αιτία δεν έχει επιβεβαιωθεί.','Η τεκμηριωμένη εξήγηση ακολουθεί.')
        sources = copy.deepcopy(quote['sources'])
        for e in evidence:
            if e['source'] not in sources: sources.append(copy.deepcopy(e['source']))
        notes.append({'text':f'{quote["name"]} ({instrument}): '+brief['text'], 'sources':sources})
        observations[instrument]={'text':observation, 'sources':copy.deepcopy(quote['sources'])}
        explained.add(instrument)
    # The three highest-ranked moves stay visible without an invented catalyst.
    payload['market_movers'] = notes
    priority_notes = [observations.get(a['instrument'], quote_note(a)) for a in current_alerts]
    payload['market_summary'] = (priority_notes + [n for key,n in observations.items() if key not in lookup])[:3]
    payload['_market_scan'] = ' '.join(n['text'] for n in payload['market_summary'][:2])
