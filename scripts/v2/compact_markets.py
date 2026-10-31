"""Compact quote presentation; keep every original quote and source available."""
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

CORE = [('S&P 500', ('^GSPC', 'sp500')), ('Nasdaq', ('^IXIC', 'nasdaq')), ('STOXX Europe 600', ('^STOXX', 'stoxx')), ('ΧΑΚ', ('cse',)), ('EUR/USD', ('eurusd',)), ('Brent', ('brent',))]
TECH = [('TSMC ADR','TSM'), ('Nvidia','NVDA'), ('Alphabet','GOOGL'), ('Microsoft','MSFT'), ('Apple','AAPL'), ('Micron','MU'), ('Meta','META'), ('Amazon','AMZN')]

def quote_key(q):
    if q.get('instrument'):
        return q['instrument']
    name = q['name'].casefold()
    if q.get('asset_class') == 'equity':
        for label, symbol in TECH:
            if name == label.casefold() or (label == 'Alphabet' and name.startswith('alphabet')):
                return symbol
    if q.get('asset_class') == 'index':
        if 'stoxx' in name: return '^STOXX'
        if 'χак' in name or 'χακ' in name: return 'cse'
        if 's&p 500' in name: return '^GSPC'
        if 'nasdaq' in name: return '^IXIC'
        if name.startswith('dow'): return '^DJI'
        if name.startswith('ftse 100'): return '^FTSE'
        if name == 'dax': return '^GDAXI'
    if 'eur/usd' in name: return 'eurusd'
    if 'brent' in name: return 'brent'
    return re.sub(r'\s+', ' ', name).strip()

def markets(b, e):
    enriched=e.get('briefing_policy')=='depth-markets-v1'
    financial=e.get('financial_policy')=='news-insights-v1'
    companies=TECH if enriched else [item for item in TECH if item[1]!='AMZN']
    labels = {'live':'Ενδοσυνεδριακή', 'delayed':'Με καθυστέρηση · ενδοσυνεδριακή', 'previous_close':'Κλείσιμο', 'unavailable':'Μη διαθέσιμη'}
    if enriched:labels['delayed']='Με καθυστέρηση'
    quotes = e['markets']
    used = set()
    def details(q):
        metadata = '<dl class="quote-metadata">' + ''.join('<dt>'+b.esc(k)+'</dt><dd>'+b.esc(v)+'</dd>' for k,v in q.items() if k != 'sources') + '</dl>'
        return '<details class="quote-sources"><summary>Πηγές και στοιχεία</summary><div class="disclosure-body">'+b.source_links(q['sources'])+'<details class="raw-quote"><summary>Πλήρη δεδομένα τιμής</summary>'+metadata+'</details></div></details>'
    def quote(q):
        value = q['value']
        if isinstance(value, (int,float)):
            value = f'{value:,.{q.get("precision",2)}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        change = q.get('change_pct')
        delta = ('↑ ' if change > 0 else '↓ ' if change < 0 else '→ ') + format(Decimal(str(change)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), '+.2f').replace('.', ',') + '%' if change is not None else 'Μεταβολή μη διαθέσιμη'
        unit = q['unit'] if q.get('asset_class') == 'rate' else q['unit'] + ' · ' + q['currency'] if q.get('asset_class') in ('index','futures_index') else q['currency'] + ' / ' + q['unit']
        direction='unknown' if change is None else 'positive' if change>0 else 'negative' if change<0 else 'neutral'
        transmission = f'<div class="quote-transmission"><span>Μετάδοση:</span> {b.esc(q["transmission_mechanism"])}</div>' if q.get('transmission_mechanism') else ''
        session={'regular':' · Κανονική συνεδρίαση','pre':' · Πριν από το άνοιγμα','post':' · Μετά το κλείσιμο'}.get(q.get('session'),'') if enriched else ''
        return '<article class="quote-card" data-quote-key="'+b.esc(quote_key(q))+'"><h4>'+b.esc(q['name'])+'</h4><strong class="quote-value">'+b.esc(value if value is not None else '—')+'</strong><span class="quote-unit">'+b.esc(unit)+'</span><b class="quote-change change-'+direction+'">'+b.esc(delta)+'</b><span class="quote-status">'+labels[q['status']]+session+'</span><time>'+b.stamp(q.get('quoted_at'))+'</time>'+transmission+details(q)+'</article>'
    core = []
    configured = e.get('market_core')
    targets = [(key,(key,)) for key in configured] if configured else CORE
    for _, keys in targets[:6]:
        candidates = [(i,q) for i,q in enumerate(quotes) if quote_key(q) in keys and q['status'] != 'unavailable' and q['value'] is not None]
        if candidates:
            i,q = max(candidates, key=lambda pair: datetime.fromisoformat(pair[1]['quoted_at']).timestamp())
            if i not in used: core.append(q); used.add(i)
    overview = e.get('market_summary', [])
    if not overview and not financial:
        if enriched:
            market_briefing=b.load_module('market_briefing')
            overview=[market_briefing.quote_note(a) for a in market_briefing.alerts(quotes,e['published_at'])[:3]]
        if not overview:
            overview = [{'text':q['name']+' · '+f'{q["change_pct"]:+.2f}%'.replace('.',',')+' ('+labels[q['status']]+'). Χρόνος τιμής: '+b.stamp(q['quoted_at'])+'. Δεν έχει τεκμηριωθεί μοναδική αιτία.', 'sources':q['sources']} for q in core if q.get('change_pct') is not None][:2]
        if e.get('market_next_event'): overview.append(e['market_next_event'])
    def note(n):
        return '<article class="market-note"><p>'+b.esc(n['text'])+'</p>'+b.source_disclosure(n['sources'],'Τεκμηρίωση')+'</article>'
    overview=overview[:3]
    summary='<ol class="market-summary">'+''.join('<li><p>'+b.esc(n['text'])+'</p></li>' for n in overview)+'</ol>' if overview else '<p>Δεν υπάρχουν επαληθευμένες τιμές σε αυτή την έκδοση.</p>'
    evidence=''.join('<h4>Σημείο '+str(i)+'</h4>'+b.source_links(n['sources']) for i,n in enumerate(overview,1))
    if evidence:summary+='<details class="sources-disclosure overview-sources"><summary>Πηγές σύνοψης</summary><div class="disclosure-body">'+evidence+'</div></details>'
    intro=b.load_module('financial_insights').render(b,e) if financial else '<div class="market-overview"><h3>Η εικόνα των αγορών σε 30 δευτερόλεπτα</h3>'+summary+'</div>'
    html = '<section class="section compact-markets" id="markets"><div class="sectionhead"><h2>'+b.emblem('markets')+'Αγορές.</h2><a class="read-link" href="../markets.html">Ιστορικά γραφήματα ↗</a></div>'+intro+'<div class="core-quotes">'+''.join(quote(q) for q in core)+'</div>'
    tech_keys = {key for _,key in companies}
    rates = []
    groups = {}
    tech = {}
    for i,q in enumerate(quotes):
        if i in used: continue
        key = quote_key(q)
        if key in tech_keys:
            tech.setdefault(key,[]).append(q)
        elif q.get('asset_class') in ('rate','interest_rate') or any(x in q['name'].casefold() for x in ('euribor','ecb','εκτ')):
            rates.append(q)
        else:
            category = {'index':'Δείκτες','futures_index':'Παράγωγα · futures','fx':'Συνάλλαγμα','commodity':'Εμπορεύματα','crypto':'Crypto','equity':'Μετοχές'}.get(q.get('asset_class'),'Λοιπά στοιχεία')
            groups.setdefault(category,[]).append(q)
    html += '<details class="all-quotes"><summary>'+b.icon('chart')+'Όλες οι τιμές · πρόσθετα στοιχεία</summary>'
    for category, items in groups.items():
        html += '<h3>'+category+'</h3><div class="quote-grid">'+''.join(quote(q) for q in items)+'</div>'
    if not groups: html += '<p>Οι διαθέσιμες τιμές βρίσκονται στις βασικές κάρτες, στο Tech watch ή στα επιτόκια.</p>'
    html += '</details>'
    if enriched and e.get('technology_briefing'):
        html+='<div class="technology-briefing"><h3>Τεχνολογία και κυβερνοασφάλεια</h3><ul>'+''.join(
            '<li><a href="../'+b.esc(item['url'])+'">'+b.esc(item['headline'])+'</a></li>' for item in e['technology_briefing'])+'</ul></div>'
    html += '<details class="tech-quotes"><summary>'+b.emblem('tech')+'Tech watch · '+('οκτώ' if enriched else 'επτά')+' εταιρείες</summary><table class="tech-table"><caption>Ελεγμένα στιγμιότυπα τεχνολογικών εταιρειών</caption><thead><tr><th scope="col">Εταιρεία</th><th scope="col">Τιμή · μονάδα · μεταβολή</th><th scope="col">Κατάσταση · χρόνος · πηγή</th></tr></thead><tbody>'
    from bs4 import BeautifulSoup
    for name,key in companies:
        if key not in tech:
            html += '<tr><th scope="row">'+name+'</th><td colspan="2">Τιμή μη διαθέσιμη</td></tr>'
            continue
        for q in tech[key]:
            row=BeautifulSoup(quote(q),'html.parser')
            html += '<tr data-quote-key="'+b.esc(key)+'"><th scope="row">'+b.esc(q['name'])+'</th><td>'+''.join(str(row.select_one(selector)) for selector in ('.quote-value','.quote-unit','.quote-change'))+'</td><td>'+str(row.select_one('.quote-status'))+str(row.time)+details(q)+'</td></tr>'
    html += '</tbody></table></details>'
    if rates:
        def rate(q):
            row=BeautifulSoup(quote(q),'html.parser')
            row.article['class']=['quote-card','rate-card']
            row.select_one('.quote-change').decompose()
            row.select_one('.quote-status').string='Μη διαθέσιμη' if q['status']=='unavailable' else 'Fixing' if 'euribor' in q['name'].casefold() else 'Ημερομηνία παρατήρησης' if e.get('synthesis_profile')=='single-turn-v1' else 'Ημερομηνία ισχύος'
            return str(row.article)
        html += '<div class="rate-summary"><div class="support-heading"><h3>'+b.emblem('rates')+'Επιτόκια · ΕΚΤ & Euribor</h3><p>Κάθε διάρκεια και ημερομηνία αναφοράς διαβάζονται χωριστά.</p></div><details class="rate-disclosure"><summary>Επιτόκια ανά διάρκεια και πηγές <span class="disclosure-count">'+str(len(rates))+'</span></summary><div class="quote-grid">'+''.join(rate(q) for q in rates)+'</div></details></div>'
    movers = e.get('market_movers', [])
    if not movers:
        movers = [n for n in e.get('market_notes',[]) if n.get('kind') != 'Τεκμηρίωση τιμών']
    if movers:
        html += '<div class="market-movers"><h3>Κινήσεις και τεκμηριωμένη εξήγηση</h3>'+''.join(note(n) for n in movers[:3])
        if len(movers)>3: html += '<details class="more-movers"><summary>Περισσότερες κινήσεις</summary>'+''.join(note(n) for n in movers[3:])+'</details>'
        html += '</div>'
    documentation = e.get('market_notes',[]) if e.get('market_movers') else [n for n in e.get('market_notes',[]) if n.get('kind') == 'Τεκμηρίωση τιμών']
    if documentation: html += '<details class="market-documentation"><summary>Κοινή τεκμηρίωση τιμών και μεθοδολογία</summary>'+''.join(note(n) for n in documentation)+'</details>'
    html += '<p class="market-method">Σταθερά στιγμιότυπα με τους αρχικούς χρόνους αναφοράς. Το χρώμα δεν είναι το μοναδικό σήμα μεταβολής. Οι αποδιδόμενες εξηγήσεις διακρίνονται από συντακτικές εκτιμήσεις.</p></section>'
    return html
