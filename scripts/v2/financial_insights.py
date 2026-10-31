"""News-led financial evidence, comparable session statistics and sourced insights.

No network/model calls. Chart observations are context, never evidence of causation.
"""
import copy
from datetime import datetime, timedelta, timezone
import json
import math
import re
from zoneinfo import ZoneInfo

POLICY = 'news-insights-v1'
TECH = {'AMZN', 'GOOGL', 'NVDA', 'MSFT', 'AAPL', 'META', 'MU', 'TSM'}
MACRO = (r'\b(?:inflation|interest rates?|central bank|federal reserve|fed|ecb|bond yields?|'
         r'payrolls|gdp|tariffs?|oil prices?|earnings|guidance|revenue|profits?|cash flow|'
         r'capital expenditure|capex|stock market|shares?|stocks?)\b|'
         r'πληθωρισ|επιτοκι|ομολογ|δασμ|εσοδ|κερδ|μετοχ|χρηματιστηρ')


def candidate(title, lane, markets):
    text = markets.normalized(title)
    return bool(lane == 'finance' or re.search(MACRO, text) or
                any(re.search(pattern, text) for pattern in markets.COMPANIES.values()) or
                re.search(r'\b(?:binance|coinbase|crypto exchange|defi)\b', text))


def completed_series(item, row, at):
    """Use dated daily bars from the already-fetched response; exclude open sessions."""
    try:
        if row.get('status') != 'available': return None
        retrieved = datetime.fromisoformat(row['retrieved_at'].replace('Z', '+00:00'))
        if not retrieved.tzinfo or retrieved > at: return None
        chart = json.loads(row['text'])['chart']['result'][0]
        meta = chart['meta']
        if meta['symbol'] != item['instrument'] or meta['currency'] != item['currency']: return None
        zone = ZoneInfo(item['market_timezone'])
        timestamps = chart['timestamp']
        close = chart['indicators']['quote'][0]['close']
        adjusted = chart['indicators'].get('adjclose', [{}])[0].get('adjclose')
        values = adjusted if adjusted is not None else close
        if len(timestamps) != len(values): return None
        # Without a consistently adjusted series, do not chart a split as a loss.
        if adjusted is None and chart.get('events', {}).get('splits'): return None
        today = at.astimezone(zone).date()
        end = meta.get('currentTradingPeriod', {}).get('regular', {}).get('end')
        points = {}
        for stamp, value in zip(timestamps, values):
            if type(stamp) not in (int, float) or not math.isfinite(stamp): continue
            instant = datetime.fromtimestamp(stamp, timezone.utc)
            if instant > min(at, retrieved): continue
            day = instant.astimezone(zone).date()
            if day == today and not (type(end) in (int, float) and math.isfinite(end) and
                                      stamp <= end < min(at, retrieved).timestamp() - 900): continue
            if day > today or type(value) not in (int, float) or not math.isfinite(value) or value <= 0: continue
            points[day.isoformat()] = value
        points = sorted(points.items())[-5:]
        if len(points) < 2 or today - datetime.fromisoformat(points[-1][0]).date() > timedelta(days=4): return None
        source = dict(publisher='Yahoo Finance', url=row['url'], published_at=None,
                      retrieved_at=row['retrieved_at'], reporting_group='Yahoo Finance', kind='primary',
                      access='read', used_for_claims=True)
        return {'points': dict(points), 'source': source,
                'basis': 'adjusted_close' if adjusted is not None else 'close'}
    except (ValueError, KeyError, IndexError, TypeError, OverflowError):
        return None


def context(inventory, rows, at, endpoint):
    """Intersect session dates; compare returns, never different-session quote deltas."""
    series = {q['instrument']: completed_series(q, rows.get(endpoint(q['instrument']), {}), at)
              for q in inventory if q['asset_class'] in ('equity', 'index')}
    result = []
    for item in inventory:
        key = item['instrument']
        if item['asset_class'] != 'equity' or not series.get(key): continue
        benchmark = '^IXIC' if key in TECH else '^GSPC'
        if not series.get(benchmark): continue
        own, reference = series[key], series[benchmark]
        dates = sorted(set(own['points']) & set(reference['points']))
        if len(dates) < 2: continue
        # Adjusted and unadjusted observations cannot share a return calculation.
        if own['basis'] != reference['basis']: continue
        first, last = dates[0], dates[-1]
        returns = lambda s: round((s['points'][last] / s['points'][first] - 1) * 100, 4)
        value, bench = returns(own), returns(reference)
        result.append(dict(id='m'+str(len(result)+1), instrument=key, benchmark=benchmark,
                           start=first, end=last, basis=own['basis'], return_pct=value,
                           benchmark_return_pct=bench, excess_pp=round(value-bench, 4),
                           points=[dict(date=d, value=own['points'][d], benchmark=reference['points'][d]) for d in dates],
                           sources=[own['source'], reference['source']]))
    return result


def hydrate(payload, pack, markets):
    """Resolve model aliases offline; keep full chart arrays out of the model digest."""
    if pack.get('financial_policy') != POLICY:
        if payload.get('financial_briefs') or payload.get('financial_shortfall_reason') or payload.get('carry_financial_insights'):
            raise ValueError('Financial insights require a current financial pack')
        return
    if payload.get('market_briefs'):
        raise ValueError('Use financial insights instead of duplicate @Market explanations')
    briefs = payload.pop('financial_briefs', [])
    carries = payload.pop('carry_financial_insights', [])
    reason = payload.pop('financial_shortfall_reason', '').strip()
    if len(briefs)+len(carries) > 3: raise ValueError('At most three financial insights')
    if len(briefs)+len(carries) < 2 and len(reason) < 20 and (briefs or carries or any(c.get('finance_candidate') for c in pack['candidates'])):
        raise ValueError('Fewer than two financial insights need @FinanceReason with a specific limitation')
    quotes = {q['instrument']: q for q in pack['data']['markets']}
    stats = {s['id']: s for s in pack.get('market_context', [])}
    insights, used = [], set()
    if carries and (not pack.get('baseline') or pack['baseline']['edition_id'][:10] != pack['edition_id'][:10]):
        raise ValueError('Financial carries require an exact same-day baseline')
    for index in carries:
        if type(index) != int or index < 1 or index > len(pack.get('baseline_financial', [])):
            raise ValueError('Unknown baseline financial insight')
        insight = copy.deepcopy(pack['baseline_financial'][index-1])
        urls = frozenset(s['url'] for s in insight['sources'] if '/finance/chart/' not in s['url'])
        if urls in used: raise ValueError('Duplicate carried financial insight')
        used.add(urls); insights.append(insight)
    for brief in briefs:
        if not 70 <= sum(len(brief[k].split()) for k in ('reported', 'meaning', 'watch')) <= 100:
            raise ValueError('Financial insight must contain 70–100 words across reported, meaning and watch')
        if not 3 <= len(brief['headline'].split()) <= 16 or any(not brief[k].strip() for k in ('reported', 'meaning', 'watch')):
            raise ValueError('Financial insight needs a short headline, reported explanation, meaning and next test')
        aliases = brief['evidence']
        evidence = [pack['evidence'].get(alias) for alias in aliases]
        if not evidence or any(not e or e.get('access') != 'article_excerpt' or not e.get('source') or
                               e['source'].get('access') != 'read' or not e['source'].get('used_for_claims') for e in evidence):
            raise ValueError('Financial insights require readable article evidence, never quote/feed-only evidence')
        urls = frozenset(e['source']['url'] for e in evidence)
        if urls in used: raise ValueError('Do not repeat the same reporting as another financial insight')
        used.add(urls)
        instruments = brief['instruments']
        if len(instruments) > 3 or len(set(instruments)) != len(instruments) or not set(instruments) <= quotes.keys():
            raise ValueError('Financial instruments must be unique inventory identifiers, at most three')
        # A company-linked insight needs company reporting, even when the quote is unavailable.
        for key in instruments:
            if key in markets.COMPANIES and not any(re.search(markets.COMPANIES[key], markets.normalized(
                    e.get('title', '')+' '+e.get('excerpt', ''))) for e in evidence):
                raise ValueError('Financial evidence must identify each explained company')
        selected_stats = []
        if len(brief['statistics'])>1: raise ValueError('Use one focused comparison chart per financial insight')
        for alias in brief['statistics']:
            stat = stats.get(alias)
            if not stat or stat['instrument'] not in instruments:
                raise ValueError('Financial statistics must resolve to the explained instrument')
            if stat not in selected_stats: selected_stats.append(copy.deepcopy(stat))
        sources = []
        for source in ([e['source'] for e in evidence] + [s for stat in selected_stats for s in stat['sources']] +
                       [s for key in instruments for s in quotes[key].get('sources',[])]):
            if source not in sources: sources.append(copy.deepcopy(source))
        insights.append({k: brief[k] for k in ('headline', 'reported', 'meaning', 'watch')} |
                        dict(instruments=instruments, statistics=selected_stats, sources=sources, as_of=pack['prepared_at']))
    payload['financial_policy'] = POLICY
    payload['financial_insights'] = insights
    payload['financial_review'] = reason or ('Δεν υπήρχε διαθέσιμη τεκμηρίωση οικονομικών άρθρων.' if not insights else '')
    # Evidence-first overview: no automatic percentage-only highlights under this policy.
    payload['market_summary'] = []
    payload['market_movers'] = []
    payload['_market_scan'] = ' '.join(i['reported'] for i in insights[:1])


def validate(edition):
    """Validate public insights too, including direct JSON submissions and chart math."""
    if edition.get('financial_policy') != POLICY: return
    insights=edition.get('financial_insights',[])
    if len(insights)>3: raise ValueError('At most three financial insights')
    if len(insights)<2 and len(edition.get('financial_review','').strip())<20:
        raise ValueError('Explain a financial insight shortfall')
    published=datetime.fromisoformat(edition['published_at'].replace('Z','+00:00'))
    known={q['instrument'] for q in edition['markets']}
    for insight in insights:
        if not 70<=sum(len(insight[k].split()) for k in ('reported','meaning','watch'))<=100:
            raise ValueError('Financial insight must contain 70–100 words')
        at=datetime.fromisoformat(insight['as_of'].replace('Z','+00:00'))
        if not at.tzinfo or at>published or not set(insight['instruments'])<=known:
            raise ValueError('Financial insight has future time or unknown instruments')
        for source in insight['sources']:
            if (source['access']!='read' or not source['used_for_claims'] or
                    datetime.fromisoformat(source['retrieved_at'].replace('Z','+00:00'))>at):
                raise ValueError('Financial insight needs dated readable sources')
        for stat in insight['statistics']:
            points=stat['points'];dates=[p['date'] for p in points]
            if (dates!=sorted(set(dates)) or stat['start']!=dates[0] or stat['end']!=dates[-1] or
                    dates[-1]>at.date().isoformat() or stat['instrument'] not in insight['instruments']):
                raise ValueError('Financial chart needs matching chronological sessions')
            value=(points[-1]['value']/points[0]['value']-1)*100
            benchmark=(points[-1]['benchmark']/points[0]['benchmark']-1)*100
            if any(abs(actual-stat[key])>.001 for key,actual in (
                    ('return_pct',value),('benchmark_return_pct',benchmark),('excess_pp',value-benchmark))):
                raise ValueError('Financial chart statistics disagree with observations')
            if any(s not in insight['sources'] for s in stat['sources']):
                raise ValueError('Financial chart sources must be disclosed with the insight')


def render(b, edition):
    """Accessible inline charts from sealed observations; no browser fetch or JS needed."""
    output = '<div class="financial-insights"><h3>Τι κινεί τις αγορές · και γιατί έχει σημασία</h3>'
    for index, insight in enumerate(edition.get('financial_insights', []), 1):
        output += '<article class="financial-insight" id="financial-insight-'+str(index)+'"><h4>'+b.esc(insight['headline'])+'</h4>'
        output += '<p class="financial-as-of">Ανάλυση με στοιχεία έως '+b.stamp(insight['as_of'])+'</p>'
        for label, key in (('Τι συνέβη και γιατί', 'reported'), ('Σημασία · συντακτική εκτίμηση', 'meaning'), ('Τι παρακολουθούμε', 'watch')):
            output += '<p><strong>'+label+':</strong> '+b.esc(insight[key])+'</p>'
        for stat in insight['statistics']:
            rows = stat['points']; base, bench = rows[0]['value'], rows[0]['benchmark']
            own = [(r['value']/base-1)*100 for r in rows]
            comparison = [(r['benchmark']/bench-1)*100 for r in rows]
            low, high = min(own+comparison+[0]), max(own+comparison+[0])
            span = max(high-low, 1); high=low+span
            points = lambda values: ' '.join(f'{45+i*270/(len(values)-1):.1f},{120-(v-low)*90/span:.1f}' for i,v in enumerate(values))
            number = lambda value: f'{value:+.2f}'.replace('.', ',')
            title = stat['instrument']+' έναντι '+stat['benchmark']+' · '+stat['start']+' έως '+stat['end']
            caption = (title+' · '+number(stat['return_pct'])+'% έναντι '+number(stat['benchmark_return_pct'])+
                       '% · διαφορά '+number(stat['excess_pp'])+' ποσοστιαίες μονάδες.')
            output += '<figure class="financial-chart"><svg viewBox="0 0 360 155" role="img" aria-label="'+b.esc(caption)+'">'
            output += '<title>'+b.esc(title)+'</title><desc>Μεταβολή από την πρώτη κοινή ολοκληρωμένη συνεδρίαση. Η διακεκομμένη γραμμή είναι ο δείκτης αναφοράς.</desc>'
            output += '<text x="2" y="25" fill="currentColor" font-size="11">'+b.esc(number(high))+'%</text><text x="2" y="123" fill="currentColor" font-size="11">'+b.esc(number(low))+'%</text>'
            output += '<polyline points="'+points(own)+'" fill="none" stroke="currentColor" stroke-width="2.5"/>'
            output += '<polyline points="'+points(comparison)+'" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="5 4"/>'
            output += '<text x="45" y="148" fill="currentColor" font-size="11">'+b.esc(stat['start'])+'</text><text x="250" y="148" fill="currentColor" font-size="11">'+b.esc(stat['end'])+'</text></svg>'
            output += '<figcaption>'+b.esc(caption)+' Συνεχής γραμμή: '+b.esc(stat['instrument'])+' · διακεκομμένη: '+b.esc(stat['benchmark'])+'.</figcaption>'
            output += '<details><summary>Συνεδριάσεις και τιμές γραφήματος</summary><table><caption>'+b.esc(stat['basis'])+'</caption><thead><tr><th>Ημερομηνία</th><th>'+b.esc(stat['instrument'])+'</th><th>'+b.esc(stat['benchmark'])+'</th></tr></thead><tbody>'
            output += ''.join('<tr><th>'+b.esc(r['date'])+'</th><td>'+b.esc(str(round(r['value'], 4)))+'</td><td>'+b.esc(str(round(r['benchmark'], 4)))+'</td></tr>' for r in rows)+'</tbody></table></details></figure>'
        output += b.source_disclosure(insight['sources'], 'Άρθρα και τεκμηρίωση')+'</article>'
    if len(edition.get('financial_insights', [])) < 2 and edition.get('financial_review'):
        output += '<p class="financial-limitation">'+b.esc(edition['financial_review'])+'</p>'
    return output+'</div>'
