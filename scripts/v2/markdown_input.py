"""Strict Markdown authoring adapter into compose.py's existing payload contract.

No general Markdown rendering, HTML, executable expressions or inferred provenance.
"""
import json
from pathlib import Path
import re

BLOCKS = {'sports', 'panels', 'freshness', 'opportunities', 'daily', 'executive_scan', 'markets',
          'market_summary', 'market_movers', 'market_next_event', 'market_core', 'market_notes',
          'fast_wire', 'selection_review', 'image_review', 'changes', 'delta_log', 'calculator'}
ARTICLE_BLOCK = {'paragraphs','sections','newspaper_analysis','reader_mode','reader_value',
                 'related_story_ids','daily','freshness','revision_note','evidence_note','published_at','updated_at','why_it_matters',
                 'mechanics_and_incentives','second_order_effects'}


def attributes(text):
    result = {}
    position = 0
    decoder = json.JSONDecoder()
    while position < len(text):
        if text[position].isspace() or text[position] == '|':
            position += 1
            continue
        match = re.match(r'([a-z][a-z0-9_]*)=',text[position:])
        if not match or match[1] in result:
            raise ValueError('Expected unique key=value attributes')
        key = match[1]
        position += match.end()
        if position < len(text) and text[position] == '"':
            value, used = decoder.raw_decode(text[position:])
            position += used
        else:
            match = re.match(r'[^\s|]+',text[position:])
            if not match:
                raise ValueError('Attribute value is missing')
            value = match[0]
            position += match.end()
        if position < len(text) and not (text[position].isspace() or text[position] == '|'):
            raise ValueError('Attributes need a separator')
        result[key] = value
    return result


def fields(values, allowed, required=()):
    if set(values) - set(allowed) or not set(required) <= set(values):
        raise ValueError('Unknown or missing attributes: '+', '.join(sorted(set(values)-set(allowed) | set(required)-set(values))))


def boolean(value):
    if value not in ('true', 'false'):
        raise ValueError('Boolean must be true or false')
    return value == 'true'


def parse(text, root, pack=None):
    if len(text.encode('utf-8')) > 2_000_000 or re.search(r'<\s*(?:/?[A-Za-z]|!)', text):
        raise ValueError('Raw HTML and oversized Markdown are not supported')
    payload = {'articles':[]}
    inventory = {q['instrument']:q for q in json.loads((Path(root)/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))}
    article = None
    section = None
    sources = {}
    analysis_ids = []
    seen = set()
    lines = text.splitlines()

    def finish():
        nonlocal article, sources, analysis_ids
        if article is None:
            return
        for key in ('headline', 'summary'):
            if not article.get(key):
                raise ValueError('Every article needs @Headline and @Fact')
        referenced = set(re.findall(r'\[([a-z][a-z0-9-]*)\]', '\n'.join(str(v) for v in article.values())))
        if not referenced | set(analysis_ids) <= set(sources):
            raise ValueError('Unresolved source reference')
        article['sources'] = list(sources.values())
        article['analysis_sources'] = [sources[key]['url'] for key in analysis_ids]
        for key in ('summary', 'mechanics_and_incentives', 'second_order_effects', 'delta_update', 'newspaper_analysis'):
            if key in article:
                clean = lambda value:re.sub(r'\[[a-z][a-z0-9-]*\]\s*', '', value)
                article[key] = [clean(value) for value in article[key]] if isinstance(article[key],list) else clean(article[key])
        for key in article.get('scenarios', {}):
            article['scenarios'][key] = re.sub(r'\[[a-z][a-z0-9-]*\]\s*', '', article['scenarios'][key])
        if article['change_status'] in ('NEW', 'UPDATED', 'REVERSAL', 'CORRECTION'):
            article.setdefault('delta_update', article['summary'])
        if any(article.get(k) for k in ('mechanics_and_incentives','second_order_effects','scenarios')) and not analysis_ids:
            raise ValueError('Analytical directives need @AnalysisSources')
        payload['articles'].append(article)
        article, sources, analysis_ids = None, {}, []

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        try:
            if line.startswith('## '):
                finish()
                section = line[3:]
                if section not in ('world', 'cyprus', 'sports'):
                    raise ValueError('Unknown section')
                continue
            if line.startswith('### '):
                finish()
                if section is None:
                    raise ValueError('Article needs a section')
                slug, separator, rest = line[4:].partition(' | ')
                meta = attributes(rest)
                fields(meta, ('story','identity','status','lead','interest'), ('story','identity','status','lead'))
                if not separator:
                    raise ValueError('Article header needs metadata')
                article = {'slug':slug, 'story_id':meta['story'], 'story_identity':meta['identity'],
                           'change_status':meta['status'], 'is_lead':boolean(meta['lead']), 'section':section}
                if 'interest' in meta:
                    article['sports_interest'] = meta['interest']
                seen = set()
                continue
            name, separator, value = line.partition(' ')
            if not name.startswith('@') or not separator:
                raise ValueError('Expected a declared directive')
            if name == '@Edition':
                if 'edition_id' in payload:
                    raise ValueError('Duplicate edition')
                meta = attributes(value)
                fields(meta, ('v','id','published','completed','baseline','title'), ('v','id','published','completed','baseline'))
                if meta['v'] != '1':
                    raise ValueError('Unsupported Markdown version')
                payload.update(edition_id=meta['id'], published_at=meta['published'], editorial_completed_at=meta['completed'])
                if 'title' in meta:
                    payload['title'] = meta['title']
                if meta['baseline'] != 'none':
                    eid, split, fingerprint = meta['baseline'].partition('@')
                    if not split:
                        raise ValueError('Baseline uses edition-id@fingerprint')
                    payload['baseline'] = {'edition_id':eid, 'fingerprint':fingerprint}
            elif name == '@Review':
                if 'reading_review' in payload:
                    raise ValueError('Duplicate review')
                meta = attributes(value)
                fields(meta, ('version','completed'), ('version','completed'))
                if meta['version'] != '2':
                    raise ValueError('Reading review version must be 2')
                payload['reading_review'] = {'version':2, 'completed_at':meta['completed']}
            elif name == '@Carry':
                payload.setdefault('carry_story_ids', []).extend(value.split(','))
            elif name == '@CarryOver':
                finish()
                meta = attributes(value)
                fields(meta, ('id',), ('id',))
                payload.setdefault('carry_story_ids', []).append(meta['id'])
            elif name in ('@Coverage', '@Omit', '@WorldException'):
                finish()
                meta = attributes(value)
                key = 'section' if name == '@Coverage' else 'id'
                required = ('reason',) if name == '@WorldException' else (key, 'reason')
                fields(meta, required, required)
                if len(meta['reason'].strip()) < 20:
                    raise ValueError('Selection decisions require a specific reason of at least 20 characters')
                review = payload.setdefault('selection_review', {'version':2, 'completed_at':None,
                    'global_exception_reason':None, 'section_shortfalls':{}})
                if name == '@WorldException':
                    if review['global_exception_reason']:
                        raise ValueError('Duplicate world exception')
                    review['global_exception_reason'] = meta['reason']
                else:
                    if name == '@Coverage' and meta[key] not in ('world', 'cyprus'):
                        raise ValueError('Coverage reason needs a news desk')
                    mapping = review.setdefault('coverage_notes' if name == '@Coverage' else 'omitted_stories', {})
                    if meta[key] in mapping:
                        raise ValueError('Duplicate selection decision')
                    mapping[meta[key]] = meta['reason']
            elif name == '@Pack':
                if 'research_pack_sha256' in payload:
                    raise ValueError('Duplicate pack')
                meta = attributes(value)
                fields(meta, ('sha256',), ('sha256',))
                payload['research_pack_sha256'] = meta['sha256']
            elif name == '@Tools':
                if 'tool_usage' in payload:
                    raise ValueError('Duplicate tool budget')
                meta = attributes(value)
                fields(meta, ('searches','reads'), ('searches','reads'))
                payload['tool_usage'] = {k:int(v) for k,v in meta.items()}
            elif name == '@Executive':
                finish()
                head, sep, body = value.partition(' | ')
                meta = attributes(head)
                fields(meta, ('axis','stories'), ('axis','stories'))
                if not sep or not body.strip():
                    raise ValueError('Executive needs text and story references')
                payload.setdefault('synthesis_points', []).append({'axis':meta['axis'],'stories':meta['stories'].split(','),'text':body})
            elif name == '@SportBrief':
                finish()
                meta = attributes(value)
                fields(meta, ('interest','evidence','changed','meaning','watch'), ('interest','evidence','changed','meaning','watch'))
                notes = payload.setdefault('sport_briefs', {})
                key = meta.pop('interest')
                if key in notes:
                    raise ValueError('Duplicate favourite briefing')
                meta['evidence'] = meta['evidence'].split(',')
                notes[key] = meta
            elif name == '@Insight':
                finish()
                head, sep, body = value.partition(' | ')
                meta = attributes(head)
                fields(meta, ('instruments','evidence','stats','reported','meaning','watch'), ('instruments','evidence','reported','meaning','watch'))
                if not sep or not body.strip(): raise ValueError('Financial insight needs a headline')
                meta['headline'] = body
                meta['instruments'] = [] if meta['instruments']=='none' else meta['instruments'].split(',')
                meta['evidence'] = meta['evidence'].split(',')
                meta['statistics'] = [] if meta.get('stats','none')=='none' else meta['stats'].split(',')
                meta.pop('stats',None)
                payload.setdefault('financial_briefs',[]).append(meta)
            elif name == '@FinanceReason':
                finish()
                if 'financial_shortfall_reason' in payload or len(value.strip())<20:
                    raise ValueError('Supply one specific financial evidence limitation')
                payload['financial_shortfall_reason']=value
            elif name == '@CarryInsight':
                finish()
                meta=attributes(value);fields(meta,('index',),('index',))
                payload.setdefault('carry_financial_insights',[]).append(int(meta['index']))
            elif name == '@Market':
                finish()
                head, sep, body = value.partition(' | ')
                meta = attributes(head)
                fields(meta, ('instrument','evidence'), ('instrument','evidence'))
                if not sep or not body.strip():
                    raise ValueError('Market explanation requires text')
                payload.setdefault('market_briefs', []).append({'instrument':meta['instrument'],
                    'evidence':meta['evidence'].split(','),'text':body})
            elif name == '@SkipPriority':
                finish()
                meta = attributes(value)
                fields(meta, ('candidate','reason'), ('candidate','reason'))
                skips = payload.setdefault('priority_skips', {})
                if meta['candidate'] in skips or len(meta['reason'].strip()) < 20:
                    raise ValueError('Priority omission needs one specific reason')
                skips[meta['candidate']] = meta['reason']
            elif name == '@SportsReason':
                finish()
                if 'sports_shortfall_reason' in payload or len(value.strip()) < 20:
                    raise ValueError('Supply one specific sports shortfall reason')
                payload['sports_shortfall_reason'] = value
            elif name == '@Block':
                if value != 'article':
                    finish()
                elif article is None:
                    raise ValueError('Article block needs an article')
                if value != 'article' and (value not in BLOCKS or value in payload):
                    raise ValueError('Unknown or duplicate typed block')
                if index >= len(lines) or lines[index].strip() != '```json':
                    raise ValueError('Typed block needs a fenced JSON value')
                index += 1
                body = []
                while index < len(lines) and lines[index].strip() != '```':
                    body.append(lines[index]); index += 1
                if index == len(lines):
                    raise ValueError('Unclosed typed block')
                index += 1
                data = json.loads('\n'.join(body))
                if value == 'article':
                    if not isinstance(data, dict) or set(data)-ARTICLE_BLOCK or set(data)&set(article):
                        raise ValueError('Unknown or duplicate article block fields')
                    article.update(data)
                else:
                    payload[value] = data
            else:
                if article is None:
                    raise ValueError('Article directive outside an article')
                if name not in ('@Source', '@Data') and name in seen:
                    raise ValueError('Duplicate article directive')
                seen.add(name)
                names = {'@Headline':'headline','@Fact':'summary','@Delta':'delta_update',
                         '@Mechanism':'mechanics_and_incentives','@Effects':'second_order_effects'}
                if name in names:
                    article[names[name]] = value
                elif name == '@Meaning':
                    article['newspaper_analysis'] = [value]
                elif name == '@Scenarios':
                    meta = attributes(value)
                    fields(meta, ('base','alternative','tail','label'))
                    article.setdefault('scenarios', {}).update({{'base':'base_case','alternative':'alternative_case','tail':'tail_risk','label':'alternative_label'}[key]:val for key,val in meta.items()})
                elif name == '@Watch':
                    article.setdefault('scenarios', {})['watch_next'] = value
                elif name == '@Tags':
                    article['driver_tags'] = value.split(',')
                elif name == '@AnalysisSources':
                    analysis_ids = value.split(',')
                    if len(set(analysis_ids)) != len(analysis_ids):
                        raise ValueError('Duplicate analysis source')
                elif name == '@Evidence':
                    if pack is None:
                        raise ValueError('@Evidence requires --research-pack')
                    for alias in value.split(','):
                        evidence = pack['evidence'].get(alias)
                        if alias in sources or not evidence or evidence.get('access') != 'article_excerpt' or not evidence.get('source'):
                            raise ValueError('Unknown, duplicate or discovery-only pack evidence')
                        sources[alias] = dict(evidence['source'])
                    article['evidence_note'] = 'Βάση: προανακτημένα αποσπάσματα πηγών· όχι ισχυρισμός ανάγνωσης ολόκληρου άρθρου.'
                elif name == '@Source':
                    alias, sep, rest = value.partition(' | ')
                    if not sep or not re.fullmatch(r'[a-z][a-z0-9-]*', alias) or alias in sources:
                        raise ValueError('Source alias must be unique')
                    meta = attributes(rest)
                    fields(meta, ('publisher','url','published','retrieved','group','kind','access','claims'), ('publisher','url','published','retrieved','group','kind','access','claims'))
                    sources[alias] = {'publisher':meta['publisher'],'url':meta['url'], 'published_at':None if meta['published']=='null' else meta['published'],
                                      'retrieved_at':None if meta['retrieved']=='null' else meta['retrieved'], 'reporting_group':None if meta['group']=='null' else meta['group'], 'kind':meta['kind'],
                                      'access':meta['access'], 'used_for_claims':boolean(meta['claims'])}
                elif name == '@Image':
                    if value.startswith('unavailable | '):
                        continue
                    meta = attributes(value)
                    fields(meta, ('photo','reviewed','relevance_checked','caption','alt'), ('photo','reviewed','relevance_checked','caption','alt'))
                    article['image_selection'] = {'photo_id':meta['photo'], 'reviewed_at':meta['reviewed'],
                        'relevance_and_archive_date_checked':boolean(meta['relevance_checked']), 'caption':meta['caption'], 'alt':meta['alt']}
                elif name == '@Data':
                    meta = attributes(value)
                    fields(meta, ('instrument','value','status','quoted_at','change_pct','sources'), ('instrument','value','status','quoted_at'))
                    if meta['instrument'] not in inventory:
                        raise ValueError('Unknown market instrument')
                    quote = dict(inventory[meta['instrument']])
                    quote.update(value=json.loads(meta['value']), status=meta['status'],
                                 quoted_at=None if meta['quoted_at']=='null' else meta['quoted_at'], change_pct=json.loads(meta.get('change_pct','null')))
                    ids = meta.get('sources','').split(',') if meta.get('sources') else []
                    if not set(ids) <= set(sources):
                        raise ValueError('Declare quote sources before @Data')
                    quote['sources'] = [sources[key] for key in ids]
                    if any(q['instrument']==quote['instrument'] for q in payload.get('markets',[])):
                        raise ValueError('Duplicate market instrument')
                    payload.setdefault('markets', []).append(quote)
                else:
                    raise ValueError('Unknown directive '+name)
        except (ValueError, KeyError) as error:
            raise ValueError('Markdown line '+str(index)+': '+str(error)) from None
    finish()
    if 'edition_id' not in payload or 'reading_review' not in payload:
        raise ValueError('Markdown needs @Edition and @Review')
    return payload


def export(payload):
    """Lossless replay helper for measured format comparison; never claim new review."""
    quote = lambda value:json.dumps(str(value), ensure_ascii=False)
    attrs = lambda values:' '.join(key+'='+quote(value) for key,value in values.items())
    ref = payload.get('baseline')
    head = {'v':1,'id':payload['edition_id'],'published':payload['published_at'],
            'completed':payload['editorial_completed_at'],'baseline':ref['edition_id']+'@'+ref['fingerprint'] if ref else 'none'}
    if payload.get('title'):
        head['title'] = payload['title']
    lines = ['@Edition '+attrs(head), '@Review '+attrs({'version':payload['reading_review']['version'],'completed':payload['reading_review']['completed_at']})]
    if payload.get('carry_story_ids'):
        lines.append('@Carry '+','.join(payload['carry_story_ids']))
    def block(name, value):
        lines.extend(['@Block '+name,'```json',json.dumps(value,ensure_ascii=False,separators=(',',':')),'```'])
    for raw in payload['articles']:
        lines.extend(['## '+raw['section'],'### '+raw['slug']+' | '+attrs({'story':raw['story_id'],'identity':raw['story_identity'],
            'status':raw.get('change_status','UNKNOWN'),'lead':str(raw.get('is_lead',False)).lower(),**({'interest':raw['sports_interest']} if raw.get('sports_interest') else {})}),
            '@Headline '+raw['headline'],'@Fact '+raw['summary']])
        for field, directive in [('delta_update','Delta'),('mechanics_and_incentives','Mechanism'),('second_order_effects','Effects')]:
            if raw.get(field) and not isinstance(raw[field],list):
                value = raw[field]
                lines.append('@'+directive+' '+(' '.join(value) if isinstance(value,list) else value))
        cases = dict(raw.get('scenarios',{}))
        if 'what_to_watch' in cases:
            cases.setdefault('watch_next',cases.pop('what_to_watch'))
        if any(key in cases for key in ('base_case','alternative_case','tail_risk')):
            lines.append('@Scenarios '+attrs({{'base_case':'base','alternative_case':'alternative','tail_risk':'tail','alternative_label':'label'}[key]:value for key,value in cases.items() if key!='watch_next'}))
        if cases.get('watch_next'):
            lines.append('@Watch '+cases['watch_next'])
        if raw.get('driver_tags'):
            lines.append('@Tags '+','.join(raw['driver_tags']))
        aliases = {}
        for n, source in enumerate(raw['sources'],1):
            alias = 's'+str(n);aliases[source['url']] = alias
            lines.append('@Source '+alias+' | '+attrs({'publisher':source['publisher'],'url':source['url'],
                'published':source['published_at'] or 'null','retrieved':source['retrieved_at'] or 'null','group':source['reporting_group'] or 'null',
                'kind':source['kind'],'access':source['access'],'claims':str(source['used_for_claims']).lower()}))
        if raw.get('analysis_sources'):
            lines.append('@AnalysisSources '+','.join(aliases[url] for url in raw['analysis_sources']))
        image = raw.get('image_selection')
        lines.append('@Image '+(attrs({'photo':image['photo_id'],'reviewed':image['reviewed_at'],
            'relevance_checked':str(image['relevance_and_archive_date_checked']).lower(),'caption':image['caption'],'alt':image['alt']}) if image else 'unavailable | No reviewed relevant photograph.'))
        extra = {key:raw[key] for key in sorted(ARTICLE_BLOCK) if key in raw and (key not in ('mechanics_and_incentives','second_order_effects') or isinstance(raw[key],list))}
        if extra:
            block('article',extra)
    for field in sorted(BLOCKS):
        if field in payload:
            block(field,payload[field])
    return '\n'.join(lines)+'\n'
