"""DEC-007: evidence-backed opportunities, with explicit application stages/dates."""
from datetime import datetime,date
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ZONE=ZoneInfo('Asia/Nicosia')
STATUS={'open':'Δέχεται αιτήσεις','upcoming':'Ανοίγει σύντομα','closed':'Έκλεισε','proposed':'Πρόταση · δεν ισχύει ακόμη','needs_verification':'Χρειάζεται επιβεβαίωση'}
KIND={'grant':'Χρηματοδότηση','benefit':'Παροχή','legal_right':'Δικαίωμα / φορολογικό όφελος'}

def instant(value):
    moment=datetime.fromisoformat(value.replace('Z','+00:00'))
    if moment.tzinfo is None:raise ValueError('Opportunity times require an explicit UTC offset')
    return moment

def validate(records):
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate opportunity ID')
    for r in records:
        checked=instant(r['verified_at'])
        if not any(s['kind']=='primary' and s['access']=='read' and s.get('used_for_claims') and s.get('retrieved_at') for s in r['sources']):
            raise ValueError('Opportunity requires a read primary source with retrieval time')
        for source in r['sources']:
            if source.get('retrieved_at') and instant(source['retrieved_at'])>checked:raise ValueError('Verification cannot predate source retrieval')
        deadline=r['deadline']
        if (r['deadline_type']=='fixed')!=bool(deadline):raise ValueError('Fixed deadlines require a date; rolling/unknown must not invent one')
        if deadline:
            expired=(instant(deadline)<checked) if len(deadline)>10 else (date.fromisoformat(deadline)<checked.astimezone(ZONE).date())
            if expired and r['status'] in ('open','upcoming'):raise ValueError('Expired call cannot be open at verification')
        opens=r['opens_at']
        if opens:
            future=(instant(opens)>checked) if len(opens)>10 else (date.fromisoformat(opens)>checked.astimezone(ZONE).date())
            if future and r['status']=='open':raise ValueError('Future call is not yet open')
            if not future and r['status']=='upcoming':raise ValueError('Opening date has passed; verify status')
            if deadline:
                if len(opens)==len(deadline)==10:
                    if opens>deadline:raise ValueError('Opening is after deadline')
                elif len(opens)>10 and len(deadline)>10 and instant(opens)>instant(deadline):raise ValueError('Opening is after deadline')
        url=r['application_url']
        if url and (urlsplit(url).scheme!='https' or not urlsplit(url).hostname or urlsplit(url).username):raise ValueError('Unsafe application URL')
        if bool(url)!=(r['application_kind']!='none'):raise ValueError('Application link kind mismatch')
        if r['status'] in ('open','upcoming') and not url:raise ValueError('Actionable calls need an official form or instructions')

def collect(bundles):
    records={}
    for e,_ in bundles:
        for r in e.get('opportunities',[]):
            previous=records.get(r['id'])
            if previous is None or instant(r['verified_at'])>=instant(previous['verified_at']):records[r['id']]=r
    return sorted(records.values(),key=lambda r:(r['deadline'] or '9999',r['id']))

def render(b, records):
    if not records:return ''
    validate(records)
    def card(r):
        def timing(value):
            if len(value)==10:return date.fromisoformat(value).strftime('%d/%m/%Y')+' · ώρα μη δημοσιευμένη'
            return instant(value).astimezone(ZONE).strftime('%d/%m/%Y · %H:%M')+' Κύπρου'
        due=timing(r['deadline']) if r['deadline'] else 'Συνεχής υποβολή' if r['deadline_type']=='rolling' else 'Δεν έχει επιβεβαιωθεί ημερομηνία'
        link=('<a class="opportunity-apply" href="'+b.esc(r['application_url'])+'" rel="noopener noreferrer">'+('Επίσημη αίτηση ↗' if r['application_kind']=='form' else 'Επίσημη διαδικασία ↗')+'</a>') if r['application_url'] else ''
        rows=[('Ποιον αφορά',r['eligibility']),('Τι προσφέρει',r['support'])]
        if r['opens_at']:rows.append(('Έναρξη',timing(r['opens_at'])))
        rows.extend([('Προθεσμία αίτησης',due),('Όροι προθεσμίας',r['deadline_note']),('Επόμενο βήμα',r['action'])])
        return '<article class="opportunity-card" id="opportunity-'+b.esc(r['id'])+'"><p class="opportunity-type">'+b.esc(KIND[r['kind']])+' · '+b.esc(r['jurisdiction'])+'</p><h3>'+b.esc(r['title'])+'</h3><p class="opportunity-status">'+b.esc(STATUS[r['status']])+' <small>κατά τον έλεγχο '+b.stamp(r['verified_at'],'Asia/Nicosia')+'</small></p><p>'+b.esc(r['summary'])+'</p><dl>'+''.join('<div><dt>'+label+'</dt><dd>'+b.esc(value)+'</dd></div>' for label,value in rows)+'</dl>'+link+b.source_disclosure(r['sources'],'Επίσημες πηγές')+'</article>'
    active=[r for r in records if r['status'] in ('open','upcoming')]
    watch=[r for r in records if r not in active]
    html='<section class="edition-panel opportunities" id="opportunities"><div class="sectionhead"><h2>Πραγματική Οικονομία, Ακίνητα &amp; Θεσμικό Ραντάρ</h2></div><p>Χρηματοδότηση για επιχειρήσεις, παροχές για νοικοκυριά, ακίνητα και δικαιώματα από Κύπρο και ΕΕ. Δες κριτήρια, επίσημη διαδικασία και προθεσμίες· η επιλεξιμότητά σου δεν έχει αξιολογηθεί.</p><div class="opportunities-grid">'+''.join(card(r) for r in active[:3])+'</div>'
    if len(active)>3:html+='<details class="more-opportunities"><summary>Περισσότερες ενεργές δυνατότητες ('+str(len(active)-3)+')</summary><div class="opportunities-grid">'+''.join(card(r) for r in active[3:])+'</div></details>'
    if watch:html+='<details class="opportunity-watch"><summary>Παρακολούθηση: κλειστές προσκλήσεις και προτάσεις ('+str(len(watch))+')</summary><div class="opportunities-grid">'+''.join(card(r) for r in watch)+'</div></details>'
    return html+'</section>'
