#!/usr/bin/env python3
"""Deterministic static publishing. No network, scheduler, AI generation or delivery."""
import argparse
import html
import hashlib
import json
import re
import os
import shutil
import tempfile
import importlib.util
from types import SimpleNamespace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://jodemon9.github.io/Claude-Briefing/'
TYPES = {'morning': 'Πρωινή', 'midday': 'Μεσημεριανή', 'evening': 'Βραδινή'}
TEAMS = {'omonoia': 'Ομόνοια', 'manutd': 'Manchester United', 'realmadrid': 'Real Madrid', 'formula1': 'Formula 1'}
UNKNOWN = 'Δεν έχει επαληθευτεί.'

def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)

def stamp(value, timezone='Europe/Athens'):
    if not value:
        return 'Χρόνος μη διαθέσιμος'
    if len(value) == 10:
        return datetime.fromisoformat(value).strftime('%d/%m/%Y')+' · ώρα μη διαθέσιμη'
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(ZoneInfo(timezone)).strftime('%d/%m/%Y · %H:%M %Z')

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')

def sources_label(sources):
    publishers = {s['publisher'].casefold().strip() for s in sources}
    groups = {s['reporting_group'] for s in sources if s.get('reporting_group') and s.get('access') != 'inaccessible'}
    label = f'{len(publishers)} εκδοτικές πηγές' if len(publishers) != 1 else '1 εκδοτική πηγή'
    chains=f'{len(groups)} γνωστές αλυσίδες αναφοράς' if len(groups)!=1 else '1 γνωστή αλυσίδα αναφοράς'
    return label + ' · ' + chains

def source_links(sources):
    kinds={'primary':'Πρωτογενής πηγή','reporting':'Ρεπορτάζ','wire':'Πρακτορείο','context':'Πλαίσιο'}
    return '<div class="source-links sourcelinks">' + ''.join(
        f'<div class="source-item"><a href="{esc(s["url"])}" rel="noopener noreferrer">{esc(s["publisher"])} ↗</a>'
        f'<span class="source-kind">{kinds[s["kind"]]}</span><dl class="source-times">'
        f'<div><dt>Δημοσίευση</dt><dd>{stamp(s.get("published_at"))}</dd></div>'
        f'<div><dt>Ανάκτηση</dt><dd>{stamp(s.get("retrieved_at"))}</dd></div></dl>'
        + ('<p class="source-access">Μη προσβάσιμη · δεν διαβάστηκε</p>' if s.get('access') == 'inaccessible' else '') + '</div>' for s in sources) + '</div>'

def source_disclosure(sources, label='Πηγές και χρόνοι αναφοράς', extra=''):
    return '<details class="sources-disclosure"><summary>'+icon('book')+esc(label)+'<span class="disclosure-count">'+str(len(sources))+'</span></summary><div class="disclosure-body">'+extra+source_links(sources)+'</div></details>'

def blocks(article, excluded=()):
    out = []
    for index,section in enumerate(article['sections'],1):
        paragraphs=[p for p in section['paragraphs'] if p.strip()!=article['summary'].strip() and p not in excluded]
        if not paragraphs:
            continue
        label = 'Δημοσιευμένες πληροφορίες' if section['kind'] == 'reported' else 'Συντακτική ανάλυση'
        out.append(f'<section class="section {esc(section["kind"])}" id="section-{index}"><div class="eyebrow">{label}</div><h2>{esc(section["heading"])}</h2>')
        out.extend(f'<p>{esc(p)}</p>' for p in paragraphs)
        out.append('</section>')
    return ''.join(out)

def words(article):
    return len(' '.join([article['summary']] + [p for s in article['sections'] for p in s['paragraphs'] if p.strip()!=article['summary'].strip()]).split())

def icon(name):
    paths={'news':'M4 4h16v16H4z M8 8h8 M8 12h8 M8 16h5','globe':'M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20 M2 12h20 M12 2c-5 5-5 15 0 20 M12 2c5 5 5 15 0 20','sport':'M5 3h14v5a7 7 0 0 1-14 0z M5 5H2v3c0 3 3 4 5 4 M19 5h3v3c0 3-3 4-5 4 M12 15v6 M8 21h8','chart':'M3 3v18h18 M6 15l5-5 4 3 5-8','search':'M10 3a7 7 0 1 0 0 14 7 7 0 1 0 0-14 M15 15l6 6','book':'M3 4h7l2 2 2-2h7v16h-7l-2 2-2-2H3z M12 6v16','clock':'M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20 M12 6v6l4 2','sun':'M12 7a5 5 0 1 0 0 10 5 5 0 1 0 0-10 M12 1v3 M12 20v3 M1 12h3 M20 12h3 M4 4l2 2 M18 18l2 2 M4 20l2-2 M18 6l2-2','moon':'M20 15A9 9 0 1 1 9 3a7 7 0 0 0 11 12','archive':'M3 3h18v5H3z M5 8v13h14V8 M9 12h6','up':'M5 14l7-7 7 7','check':'M4 12l5 5L20 6','arrow':'M4 12h16 M14 6l6 6-6 6','photo':'M3 4h18v16H3z M3 17l6-7 5 5 3-3 4 5 M15 7h1','print':'M6 8V2h12v6 M6 18H3V8h18v10h-3 M6 14h12v8H6z'}
    paths.update({'calendar':'M4 5h16v16H4z M4 10h16 M8 3v4 M16 3v4 M8 14h2 M14 14h2 M8 18h2', 'weather':'M8 17h11a4 4 0 0 0 0-8 6 6 0 0 0-11 1 4 4 0 0 0 0 7 M4 3v2 M1 8h2 M7 3l-1 2 M11 19l-1 3 M16 19l-1 3', 'tech':'M6 6h12v12H6z M9 9h6v6H9z M9 2v4 M15 2v4 M9 18v4 M15 18v4 M2 9h4 M2 15h4 M18 9h4 M18 15h4', 'info':'M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20 M12 11v6 M12 7h.01'})
    return '<svg class="ui-icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="'+paths.get(name,paths['news'])+'"/></svg>'

def emblem(name):
    symbols={'cyprus':'🇨🇾','world':'🌍','sports':'🏆','markets':'📈','weather':'🌦️','tech':'💻','calendar':'📅','info':'📰','summary':'⚡','changes':'🕒','lead':'🗞️','rates':'🏦'}
    return '<span class="section-emblem emblem-'+esc(name)+'" aria-hidden="true">'+symbols.get(name,'📰')+'</span>'

def image(a,depth=''):
    im = a.get('image')
    if not im:
        return '<p class="image-unavailable">'+esc(a['image_unavailable_reason'])+'</p>' if a.get('image_unavailable_reason') else ''
    url=im['url'] if im['url'].startswith(('https://','data:')) else depth+im['url']
    archive = '<span class="photo-archive" title="'+esc(im.get('caption',''))+'">Φωτογραφία αρχείου</span>' if im.get('caption','').startswith('Φωτογραφία αρχείου ·') else ''
    return f'<figure class="photo" data-editorial-image><img src="{esc(url)}" alt="{esc(im["alt"])}" loading="lazy" decoding="async">{archive}<p class="image-fallback" data-image-fallback hidden>Η φωτογραφία δεν φορτώθηκε.</p></figure>'

def photo_credits(bundles):
    """One public attribution record, without repeated article captions/panels."""
    entries=[]
    for e,articles in bundles:
        for a in articles:
            im=a.get('image')
            if not im:continue
            entries.append('<section id="'+esc(e['id']+'-'+a['id'])+'"><h2><a href="'+esc(article_url(e,a))+'">'+esc(a['headline'])+'</a></h2><p>'+esc(im.get('caption',''))+'</p><p><a href="'+esc(im.get('source_url',''))+'">'+esc(im['attribution'])+'</a> · <a href="'+esc(im.get('license_url',''))+'">'+esc(im.get('license','Στοιχεία στην αρχική πηγή'))+'</a></p><p>'+esc(im.get('original_url',''))+' · Ανάκτηση: '+esc(im.get('retrieved_at',''))+'</p></section>')
    entries.append(load_module('sports').credits(SimpleNamespace(**globals())))
    return head('Συντελεστές εικόνων','photo-credits.html','article','')+'<main class="shell"><a href="today.html">← Εφημερίδα</a><h1>Συντελεστές εικόνων</h1>'+''.join(entries)+'</main></body></html>'

def article_url(e, a):
    return f'articles/{e["id"]}/{a["id"]}.html'

def validate(e, articles):
    """Semantic gates complement the reusable JSON Schema."""
    from jsonschema import Draft202012Validator, FormatChecker
    schema = read(ROOT/'templates/v2/content.schema.json')
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(e)
    load_module('opportunities').validate(e.get('opportunities',[]))
    load_module('research').validate_opportunity_reviews(ROOT,e)
    load_module('backend').check_contract(ROOT,e,articles)
    load_module('intelligence').validate(e, articles, ROOT)
    if e['id'] != f'{e["date"]}-{e["type"]}':
        raise ValueError('Edition ID/date/type mismatch')
    if e['published_at'] and datetime.fromisoformat(e['published_at']).astimezone(ZoneInfo(e['timezone'])).date().isoformat() != e['date']:
        raise ValueError('Publication must fall on the local edition date')
    if e['status']=='published' and not e['published_at'] and not e.get('preserve_legacy_html'):
        raise ValueError('New published editions need a publication timestamp')
    if len({a['id'] for a in articles}) != len(articles):
        raise ValueError('Duplicate article IDs')
    if set(TEAMS) != set(e['sports']['coverage']):
        raise ValueError('Permanent sports coverage required')
    load_module('sports_news').validate(e,ROOT)
    load_module('selection').validate(e, articles)
    ids = {a['id'] for a in articles}
    policy_start=datetime.fromisoformat('2026-10-13T15:40:17+03:00')
    new_publication=e['status']=='published' and e.get('published_at') and datetime.fromisoformat(e['published_at'])>=policy_start
    review=e.get('reading_review',{}).get('version')
    strict=review in (1,2)
    partial = e.get('availability_policy') == 'partial-v1' and e['date'] >= '2026-10-22'
    if e.get('photo_policy') == 'real-photos-v1' and any(not a.get('image') for a in articles):
        raise ValueError('Every article requires a licensed real photograph')
    if new_publication and (not strict or not partial and e.get('image_review',{}).get('version')!=2):
        raise ValueError('New publications require image_review.version=2 and reading_review.version=1 or 2')
    if e['status']=='published' and e.get('published_at') and datetime.fromisoformat(e['published_at'])>=datetime.fromisoformat('2026-10-15T00:00:00+03:00') and review!=2:
        raise ValueError('New publications require reading_review.version=2 (DEC-005)')
    if strict:
        if not partial and e.get('image_review',{}).get('version')!=2:
            raise ValueError('Full reading review requires mandatory photographs')
        for a in articles:
            if not a.get('image'):
                if not partial or not a.get('image_unavailable_reason'):
                    raise ValueError('Every article requires a licensed photograph: '+a['id'])
            if review==2:
                load_module('editorial').validate_reading(a)
            else:
                count=len(' '.join(a.get('newspaper_analysis',[])).split())
                if not 110<=count<=220:
                    raise ValueError('Newspaper analysis must contain 110–220 useful words: '+a['id'])
                if words(a)<450:
                    raise ValueError('Full reader requires at least 450 useful words: '+a['id'])
    if e.get('image_review'):
        if not partial and not any(a.get('image') for a in articles):
            raise ValueError('Reviewed edition contains no images; finish image research before publishing')
        for a in articles:
            im=a.get('image')
            if not im:
                if e['image_review']['version']==2 and not partial:
                    raise ValueError('Every article requires a licensed photograph: '+a['id'])
                if not a.get('image_unavailable_reason'):
                    raise ValueError('Missing image research outcome: '+a['id'])
                continue
            for field in ['source_url','original_url','caption','alt','attribution','license','license_url','retrieved_at']:
                if not im.get(field):
                    raise ValueError('Image evidence missing '+field+': '+a['id'])
            for field in ['source_url','license_url']:
                if not im[field].startswith('https://'):
                    raise ValueError('Image credit URL must be HTTPS')
            path=Path(im['url'])
            if path.is_absolute() or '..' in path.parts or not im['url'].startswith('assets/editorial/'):
                raise ValueError('Reviewed images must be local editorial assets')
            if not (ROOT/'docs'/path).is_file():
                raise ValueError('Image asset missing; run prepare_images.py: '+im['url'])
            if im.get('reuse_review'):
                library=load_module('photo_library');reuse=im['reuse_review']
                source=library.asset(ROOT,reuse['source_asset'])
                if not reuse.get('relevance_and_archive_date_checked') or library.sha(source)!=reuse['sha256'] or library.sha(ROOT/'docs'/path)!=reuse['sha256']:
                    raise ValueError('Reused photograph no longer matches its reviewed source')
                reviewed=load_module('backend').instant(reuse['reviewed_at'])
                review_limit = e.get('image_revision_at') or e.get('editorial_completed_at')
                if review_limit and reviewed>load_module('backend').instant(review_limit):
                    raise ValueError('Reuse review cannot follow edition completion')
            from PIL import Image
            with Image.open(ROOT/'docs'/path) as decoded:
                decoded.load()
                if decoded.width<200 or decoded.height<200:
                    raise ValueError('Editorial photograph too small: '+im['url'])
    for a in articles:
        Draft202012Validator({'$ref':'#/$defs/article','$defs':schema['$defs']}, format_checker=FormatChecker()).validate(a)
        if a['edition_id'] != e['id']:
            raise ValueError('Historical article belongs to another edition')
        if a['url'] != article_url(e,a):
            raise ValueError('Article URL must be stable and dated')
        if not a['sections'] or (review!=2 and not any(s['kind'] == 'analysis' for s in a['sections'])):
            raise ValueError('Separate original analysis required')
        if not (review==2 and a.get('reader_mode')=='source') and all(p.strip() in a['summary'] for s in a['sections'] for p in s['paragraphs']):
            raise ValueError('Article repeats the summary')
        if any(s['access'] == 'inaccessible' and s.get('used_for_claims') for s in a['sources']):
            raise ValueError('Inaccessible material cannot substantiate claims')
    for sport in e['sports']['major_stories']:
        if sport['article_id'] not in ids:
            raise ValueError('Sports explainer missing')
    for team in e['sports']['coverage'].values():
        for record in [team.get('last_match'), team.get('next_fixture'), team.get('latest_session')]:
            if isinstance(record, dict) and (not record.get('sources') or not record.get('verified_at')):
                raise ValueError('Sports results/fixtures require evidence and verification time')
        for u in team['updates']:
            if not u.get('published_at') or not u.get('sources'):
                raise ValueError('Sports updates require timestamps and sources')
        if len(team['updates']) > 5:
            raise ValueError('Too many sports updates')
    for q in e['markets']:
        if q.get('quoted_at'):
            stamp(q['quoted_at'])
        if q['status'] != 'unavailable' and (q['value'] is None or not q.get('quoted_at') or not q.get('sources') or not q['unit'] or not q['currency']):
            raise ValueError('Market quote missing evidence, unit or timestamp')
        if q['status'] == 'previous_close' and q.get('market_timezone') == 'America/New_York':
            quote=datetime.fromisoformat(q['quoted_at'])
            t=quote.astimezone(ZoneInfo('America/New_York')) if len(q['quoted_at'])>10 else quote
            published=datetime.fromisoformat(e['published_at']).astimezone(ZoneInfo('America/New_York')) if e['published_at'] else None
            if t.weekday()<5 and ((len(q['quoted_at'])>10 and t.hour<16) or (published and t.date()==published.date() and published.hour<16)):
                raise ValueError('Ongoing US session cannot be labelled daily close')

def fixture(record):
    if not record:
        return f'<p>{UNKNOWN}</p>'
    lines = []
    labels = {'opponent':'Αντίπαλος','competition':'Διοργάνωση','venue':'Γήπεδο','date':'Ημερομηνία','result':'Αποτέλεσμα','scorers':'Σκόρερ'}
    for key, label in labels.items():
        if key in record:
            val = record[key]
            lines.append(f'<dt>{label}</dt><dd>{esc(", ".join(val) if isinstance(val,list) else val) or UNKNOWN}</dd>')
    if 'kickoff_at' in record:
        lines.append(f'<dt>Σέντρα · ώρα Κύπρου</dt><dd>{stamp(record["kickoff_at"]) if record["kickoff_at"] else UNKNOWN}</dd>')
    return '<dl class="fixture">'+''.join(lines)+'</dl>'+f'<p class="muted">Έλεγχος: {stamp(record["verified_at"])}</p>'+source_links(record['sources'])

def sports(e, articles=(), anchors=None, include_major=True):
    return load_module('sports').render(SimpleNamespace(**globals()), e, articles, anchors, include_major)


def load_module(name):
    spec=importlib.util.spec_from_file_location('oracle_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def quote_key(q):
    return load_module('compact_markets').quote_key(q)

def markets(e):
    return load_module('compact_markets').markets(SimpleNamespace(**globals()),e)


def calculator(e):
    c=e.get('calculator')
    if not c:
        return ''
    return f'<section class="section" id="rates"><div class="sectionhead"><h2>Υπολογιστής δόσης.</h2></div><div class="calc" data-calculator><h3>Υποθετική σταθερή μηνιαία δόση</h3><p>Μαθηματικό παράδειγμα χωρίς έξοδα και ασφάλιση· δεν είναι τραπεζική προσφορά.</p><div class="field"><label for="principal">Κεφάλαιο · EUR</label><input id="principal" type="number" min="1" max="10000000" value="{c["principal"]}"></div><div class="field"><label for="years">Διάρκεια · έτη</label><input id="years" type="number" min="1" max="40" value="{c["years"]}"></div><div class="field"><label for="interest">Ετήσιο επιτόκιο · %</label><input id="interest" type="number" min="0" max="30" step="0.01" value="{c["annual_rate"]}"></div><output id="payment" aria-live="polite"></output></div></section>'

def article_layers(a):
    """Shared Greek analytical content for cards, independent readers and the day."""
    out = []
    for key, title in [('mechanics_and_incentives', 'Μηχανισμοί και κίνητρα'),
                       ('second_order_effects', 'Δευτερογενείς συνέπειες')]:
        value = a.get(key)
        if value:
            paragraphs = value if isinstance(value, list) else [value]
            out.append('<section class="article-layer"><h3>'+title+'</h3>'+''.join('<p>'+esc(p)+'</p>' for p in paragraphs)+'</section>')
    scenarios = a.get('scenarios', {})
    if scenarios:
        out.append('<section class="article-layer scenarios-layer"><h3>Σενάρια · συντακτική εκτίμηση</h3>')
        if 'change_status' not in a:
            # Keep the accepted historical presentation; new records get tabs.
            for key, label in [('base_case','Βασικό σενάριο'), ('tail_risk','Ακραίος κίνδυνος'), ('watch_next','Τι παρακολουθούμε')]:
                value=scenarios.get(key) or (scenarios.get('what_to_watch') if key=='watch_next' else None)
                if value:
                    out.append('<div class="scenario-card"><strong>'+label+'</strong><p>'+esc(value)+'</p></div>')
            out.append('</section>')
            return ''.join(out)
        prefix = 'scenario-' + hashlib.sha256((a.get('edition_id','')+'/'+a.get('id','')+'/'+a.get('story_id','')).encode()).hexdigest()[:12]
        cases = [(key, label, scenarios[key]) for key, label in [('base_case','Βάση'), ('alternative_case', scenarios.get('alternative_label') or 'Εναλλακτικό'), ('tail_risk','Ακραίος κίνδυνος')] if scenarios.get(key)]
        if cases:
            out.append('<div class="scenario-switcher" data-scenarios><div class="scenario-buttons" data-scenario-buttons hidden role="tablist" aria-label="Σενάρια">')
            for key, label, value in cases:
                out.append('<button type="button" id="'+prefix+'-tab-'+key+'" data-scenario="'+key+'" aria-controls="'+prefix+'-'+key+'">'+esc(label)+'</button>')
            out.append('</div>')
            for key, label, value in cases:
                out.append('<section class="scenario-panel" data-scenario-panel="'+key+'" id="'+prefix+'-'+key+'"><h4>'+esc(label)+'</h4><p>'+esc(value)+'</p></section>')
            out.append('</div>')
        for key, label in [('watch_next','Τι παρακολουθούμε')]:
            value = scenarios.get(key) or (scenarios.get('what_to_watch') if key == 'watch_next' else None)
            if value:
                out.append('<div class="scenario-card"><strong>'+label+'</strong><p>'+esc(value)+'</p></div>')
        out.append('</section>')
    return ''.join(out)


def edition_scan(e):
    """The same executive scan, delta and wire on the edition and central day."""
    out = []
    scan = e.get('executive_scan', {})
    if scan:
        out.append('<section class="executive-scan" aria-label="Επισκόπηση έκδοσης"><div class="scan-grid">')
        axes = [('geopolitics_macro','Γεωπολιτική και μακροοικονομία'), ('cyprus_institutions','Κύπρος και θεσμοί'), ('markets_tech','Αγορές και τεχνολογία')]
        # Render the published legacy names honestly, without inventing a mapping.
        if not any(scan.get(key) for key, _ in axes):
            axes = [('geopolitics_and_defense','Γεωπολιτική και άμυνα'), ('macro_and_markets','Μακροοικονομία και αγορές'), ('tech_and_energy','Τεχνολογία και ενέργεια')]
        for key, title in axes:
            value = scan.get(key)
            if not value:
                continue
            text = '<p>'+esc(value)+'</p>' if isinstance(value, str) else '<p>'+esc(value.get('headline',''))+'</p><ul>'+''.join('<li>'+esc(p)+'</li>' for p in value.get('bullets', []))+'</ul>'
            out.append('<div class="scan-col"><h3>'+title+'</h3>'+text+'</div>')
        out.append('</div>')
        if scan.get('day_catalysts'):
            out.append('<div class="catalysts-box"><h3>Καταλύτες και επόμενοι έλεγχοι</h3><ul>'+''.join('<li>'+esc(p)+'</li>' for p in scan['day_catalysts'])+'</ul></div>')
        out.append('</section>')
    if e.get('delta_log'):
        out.append('<section class="midday-delta-callout"><h3>Τι άλλαξε από την πρωινή έκδοση</h3><ul>'+''.join('<li>'+esc(p)+'</li>' for p in e['delta_log'])+'</ul></section>')
    if e.get('fast_wire'):
        out.append('<section class="fast-wire-ticker"><h3>Τηλεγραφικές εξελίξεις</h3><div class="ticker-content">')
        for row in e['fast_wire']:
            link = ' <a href="'+esc(row['source_url'])+'" rel="noopener noreferrer">'+esc(row.get('source_name') or 'Πηγή')+'</a>' if row.get('source_url') else ''
            out.append('<div class="wire-item"><strong class="wire-badge">'+esc(row['category'])+'</strong> <span>'+esc(row['summary'])+'</span>'+link+'</div>')
        out.append('</div></section>')
    if e.get('availability_notes'):
        out.append('<details class="availability-notes"><summary>Διαθεσιμότητα ενημέρωσης</summary><ul>'+''.join('<li>'+esc(note)+'</li>' for note in e['availability_notes'])+'</ul></details>')
    return ''.join(out)


def card(e, a, hero=False):
    cl = 'hero' if hero else 'newscard'
    layered=e.get('reading_review',{}).get('version')==2
    abstract='<details class="story-findings"><summary>'+icon('news')+'Ευρήματα</summary>'+f'<div class="abstract"><p>{esc(a["summary"])}</p></div></details>'
    shown=[]
    context=''
    if a.get('newspaper_analysis'):
        context='<div class="card-context">'+''.join('<p>'+esc(p)+'</p>' for p in a['newspaper_analysis'])+'</div>'
    elif not hero and not layered:
        reported=[p for s in a['sections'] if s['kind']=='reported' for p in s['paragraphs'] if not p.strip().startswith(a['summary'].strip())][:2]
        analysis=next((s for s in a['sections'] if s['kind']=='analysis'),None)
        shown=reported+(analysis['paragraphs'][:1] if analysis else [])
        context=''.join(f'<p>{esc(p)}</p>' for p in reported)
        if analysis:
            context+=f'<div class="card-context"><b>Συντακτική ανάλυση · {esc(analysis["heading"])}</b><p>{esc(analysis["paragraphs"][0])}</p></div>'
    more='' if a.get('newspaper_analysis') or layered else '<details class="story-more"><summary>Περισσότερα μέσα στην έκδοση</summary>'+blocks(a,shown)+'</details>'
    context += article_layers(a)
    if context:
        if layered:
            context='<details class="card-analysis'+(' lead-analysis' if hero else '')+'"><summary>'+icon('book')+'Τι σημαίνει · ανάλυση</summary>'+context+'</details>'
        else:
            context=('<section class="lead-analysis"><h3>'+icon('book')+'Γιατί έχει σημασία</h3>'+context+'</section>') if hero else '<details class="card-analysis"><summary>'+icon('book')+'Η ουσία</summary>'+context+'</details>'
    sources=source_disclosure(a['sources'], 'Πηγές και στοιχεία', '<p class="muted">'+sources_label(a['sources'])+'</p>')
    reader=f'<a class="read-link" href="../{article_url(e,a)}">{icon("book")} Πλήρης ανάλυση{icon("arrow")}</a>'
    if layered and a.get('reader_mode')=='source':
        source=next(s for s in a['sources'] if s.get('access')=='read' and s.get('used_for_claims'))
        reader='<a class="read-link original-report" href="'+esc(source['url'])+'" rel="noopener noreferrer">'+icon('book')+'Πλήρες ρεπορτάζ · '+esc(source['publisher'])+' ↗</a>'
    delta = '<p class="article-delta-callout"><strong>Τι άλλαξε:</strong> '+esc(a['delta_update'])+'</p>' if a.get('delta_update') and a['delta_update']!=a['summary'] else ''
    copy=delta+abstract+context+more+'<div class="story-actions">'+reader+'</div>'+sources
    label='Πρώτο θέμα' if hero else 'Κύπρος' if a['category']=='Πρώτο θέμα' else a['category']
    heading=f'<div class="eyebrow">'+(emblem('lead') if hero else '')+f'{esc(label)}</div><h{2 if hero else 3}>{esc(a["headline"])}</h{2 if hero else 3}>'
    overview='<div class="lead-overview"><div class="lead-copy">'+heading+copy+'</div>'+image(a,'../')+'</div>' if hero else heading+copy
    attributes = ''
    if e.get('intelligence_contract') == 1:
        status = a.get('change_status', 'UNKNOWN')
        times = [event['at'] for event in a.get('daily',{}).get('events',[]) if event['kind'] in ('new','substantive_update','correction')]
        if status in ('NEW','UPDATED','REVERSAL','CORRECTION'):
            times.append(e['published_at'])
        attributes = ' data-intelligence-story data-change-status="'+esc(status)+'" data-driver-tags="'+esc(' '.join(a.get('driver_tags',[])))+'" data-change-times="'+esc(json.dumps(times))+'"'
    return f'<article class="{cl}" id="{esc(a["id"])}"'+attributes+'>'+('' if hero else image(a,'../'))+'<div class="story-content">'+overview+'</div></article>'

def edition_desk(e, registry):
    out = ['<nav class="edition-desk" aria-label="Εκδόσεις της ημέρας"><b>Γραφείο εκδόσεων</b>']
    for t, label in TYPES.items():
        match = next((x for x in registry if x['date'] == e['date'] and x['type'] == t and x['status'] == 'published'), None)
        if match:
            state='Τρέχουσα έκδοση' if match['id']==e['id'] else 'Δημοσιευμένη'
            out.append(f'<a href="../{match["url"]}" title="{label} · {state}" aria-label="{label} · {state}"'+(' aria-current="page"' if match['id'] == e['id'] else '')+f'>{icon({"morning":"sun","midday":"clock","evening":"moon"}[t])}{label}</a>')
        else:
            out.append(f'<span title="{label} · Δεν έχει δημοσιευτεί" aria-label="{label} · Δεν έχει δημοσιευτεί">{label} · —</span>')
    return ''.join(out)+'</nav>'

def head(title, canonical, css, depth='', edition=None):
    indicator = f' data-edition="{esc(edition)}"' if edition else ''
    meta = f'<meta name="oracle-edition" content="{esc(edition)}">' if edition else ''
    components=f'<link rel="stylesheet" href="{depth}assets/newspaper-ui.css">' if css=='newspaper' else ''
    return f'<!doctype html><html lang="el" data-theme="light"{indicator}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{meta}<title>{esc(title)} · The Oracle Sovereign</title><link rel="canonical" href="{BASE}{canonical}"><link rel="stylesheet" href="{depth}assets/{css}.css"><link rel="stylesheet" href="{depth}assets/accessibility.css">{components}<script defer src="{depth}assets/reading.js"></script></head><body><a class="back-top" href="#main" aria-label="Επιστροφή στην αρχή">{icon("up")}<span>Αρχή</span></a><a class="skip-link" href="#main">Μετάβαση στο περιεχόμενο</a>'

def edition_panels(e):
    out=[]
    for panel in e.get('panels', []):
        kind='weather' if panel['id']=='weather' else 'calendar' if panel['id'] in ('watch','risk-radar') else 'tech' if panel['id']=='tech-watch' else 'info'
        out.append('<section class="section edition-panel panel-'+kind+'" id="'+esc(panel['id'])+'"><div class="sectionhead"><h2>'+emblem(kind)+esc(panel['heading'])+'</h2></div>')
        if kind=='calendar':
            out.append('<ol class="calendar-list">')
            for paragraph in panel['paragraphs']:
                when, separator, text=paragraph.partition(' · ')
                # Only separate the date/time already explicitly written by the editor.
                dated=bool(separator and re.match(r'^\d{1,2}/\d{1,2}',when))
                out.append('<li class="calendar-event">'+('<div class="event-when">'+icon('clock')+esc(when)+'</div><span class="event-separator"> · </span><p>'+esc(text)+'</p>' if dated else '<p>'+esc(paragraph)+'</p>')+'</li>')
            out.append('</ol>')
        else:
            out.append('<div class="panel-items">')
            for index,paragraph in enumerate(panel['paragraphs']):
                warning=kind=='weather' and paragraph.startswith('Πορτοκαλί προειδοποίηση')
                title='Προειδοποίηση' if warning else 'Πρόγνωση' if kind=='weather' else paragraph.partition(':')[0] if ':' in paragraph and len(paragraph.partition(':')[0])<=40 else ''
                out.append('<article class="panel-item'+(' panel-advisory' if warning else '')+'">'+('<h3>'+('<span aria-hidden="true">⚠️</span> ' if warning else '')+esc(title)+'</h3>' if title else '')+'<p>'+esc(paragraph)+'</p></article>')
            out.append('</div>')
        out.append(source_disclosure(panel['sources'], 'Πηγές της ενότητας')+'</section>')
    return ''.join(out)

def _render(root=ROOT, affected=None):
    global ROOT
    ROOT = Path(root)
    import importlib.util
    latest_spec=importlib.util.spec_from_file_location('latest_publishing',Path(__file__).with_name('latest.py'))
    latest=importlib.util.module_from_spec(latest_spec);latest_spec.loader.exec_module(latest)
    editions = [read(f) for f in sorted((ROOT/'content/editions').glob('*.json'))]
    registry = read(ROOT/'content/legacy-editions.json')
    bundles = []
    for e in editions:
        for p in e['articles']:
            if not re.fullmatch(r'articles/[a-z0-9-]+/[a-z0-9-]+\.json',p):
                raise ValueError('Unsafe article path')
        articles = [read(ROOT/'content'/p) for p in e['articles']]
        validate(e, articles)
        if e['status'] == 'published':
            registry.append({k:e[k] for k in ['id','date','type','status','published_at','title','url']})
            bundles.append((e,articles))
    if len({x['id'] for x in registry}) != len(registry) or len({(x['date'],x['type']) for x in registry}) != len(registry):
        raise ValueError('Duplicate archive edition')
    for x in registry:
        if x['status'] != 'published':
            raise ValueError('Only published records belong in archive')
        if x['id'] not in {e['id'] for e,_ in bundles} and not (ROOT/'docs'/x['url']).is_file():
            raise ValueError('Archive points at missing HTML')
    previous_registry=read(ROOT/'docs/data/editions.json') if (ROOT/'docs/data/editions.json').exists() else []
    prior={r['id']:r for r in previous_registry}
    for e,aa in bundles:
        if e['id'] in prior and prior[e['id']].get('published_at') != e['published_at']:
            raise ValueError('Keep the original edition published_at on correction')
        for a in aa:
            previous_article=ROOT/'docs/data/articles'/e['id']/(a['id']+'.json')
            if previous_article.exists() and read(previous_article)['published_at'] != a['published_at']:
                raise ValueError('Keep the original article published_at on correction')
    backend = load_module('backend')
    aliases_path = ROOT/'content/day-story-aliases.json'
    reviews_path = ROOT/'content/story-identity-reviews.json'
    identity = backend.story_registry(bundles,read(aliases_path) if aliases_path.exists() else {},read(reviews_path) if reviews_path.exists() else {})
    write(ROOT/'docs/data/capabilities.json',json.dumps(backend.capabilities(ROOT),ensure_ascii=False,indent=2)+'\n')
    write(ROOT/'docs/data/edition-contracts.json',json.dumps({e['id']:{'contract':e['producer_contract'],'source_sha256':backend.edition_fingerprint(e,aa),'reporting_sha256':backend.reporting_fingerprint(e,aa)} for e,aa in bundles if e.get('producer_contract')},ensure_ascii=False,indent=2)+'\n')
    write(ROOT/'docs/data/story-registry.json',json.dumps(identity,ensure_ascii=False,indent=2)+'\n')
    write(ROOT/'docs/data/freshness.json',json.dumps({'schema_version':1,'editions':[backend.freshness(e,aa) for e,aa in bundles]},ensure_ascii=False,indent=2)+'\n')
    write(ROOT/'docs/data/research-index.json',json.dumps(load_module('research').index(ROOT),ensure_ascii=False,indent=2)+'\n')
    write(ROOT/'docs/data/photo-library.json',json.dumps(load_module('photo_library').catalog(ROOT),ensure_ascii=False,indent=2)+'\n')
    search = []
    for e, aa in bundles:
        search.extend({'id':a['story_id'],'edition_id':e['id'],'date':e['date'],'headline':a['headline'],'summary':a['summary'],'driver_tags':a.get('driver_tags',[]),'body':' '.join(p for section in a['sections'] for p in section['paragraphs'])+' '+re.sub('<[^>]+>', ' ', article_layers(a)),'url':article_url(e,a)} for a in aa)
        if affected is not None and e['id'] not in affected:
            continue
        date = stamp(e['published_at'],e['timezone'])
        body = head(f'{TYPES[e["type"]]} έκδοση · {e["date"]} · {e["title"]}',e['url'],'newspaper','../',e['type'])
        slot = ' · '+esc(e['scheduled_slot']) if e.get('scheduled_slot') else ''
        body += f'<div class="line-top"></div><header class="masthead wrap"><div class="m-left">Ανεξάρτητο ημερήσιο briefing<br>Λεμεσός · Κύπρος</div><div class="brand"><h1>THE ORACLE <em>SOVEREIGN.</em></h1><p>Καθαρή ματιά πίσω από τους τίτλους</p></div><div class="m-right"><b>{e["date"]}</b>{TYPES[e["type"]]} έκδοση{slot}<br>Δημοσίευση: {date}</div></header>'
        body += f'<div class="stickybar"><div class="wrap"><nav class="navs" aria-label="Ενότητες εφημερίδας"><a href="#main">{icon('news')} Κύρια νέα</a><a href="#cyprus">{icon('news')} Κύπρος</a><a href="#world">{icon('globe')} Διεθνή</a><a href="#sports">{icon('sport')} Αθλητικά</a><a href="#markets">{icon('chart')} Αγορές</a><a href="#rates">Δόση</a><a href="../index.html">{icon('archive')} Αρχείο</a></nav><div class="tools"><button data-theme-toggle aria-label="Εναλλαγή θέματος">◐</button><a href="../search.html">{icon('search')} Αναζήτηση</a><button data-print>Εκτύπωση</button></div></div></div><main class="wrap" id="main">'
        body += edition_desk(e,registry)+f'<div class="introbar"><b>{TYPES[e["type"]]} έκδοση{slot} · {e["date"]}</b><span>Δημοσίευση: {date}</span></div>'
        if e.get('analysis_revision_at'):
            body += '<p class="revision-note">'+icon('photo')+' Εμπλουτισμός εικόνων και ανάλυσης: '+stamp(e['analysis_revision_at'])+' · Οι αρχικοί χρόνοι ειδήσεων και τιμών διατηρούνται.</p>'
        body += edition_scan(e)
        requested_lead=e.get('daily',{}).get('lead_story_id')
        lead=next((a for a in aa if a['story_id']==requested_lead),None) if requested_lead else aa[0] if aa and aa[0]['category']=='Πρώτο θέμα' else None
        ordered=sorted(aa,key=lambda a:a.get('daily',{}).get('priority',1000+aa.index(a)))
        if lead:
            selected=[a for a in ordered if a!=lead and a['category'] in ['Πρώτο θέμα','Κύπρος','Διεθνή']][:5]
            picks=''.join(f'<div class="brief-line"><b>{i+1:02}</b><p><a href="#{a["id"]}">{esc(a["headline"])}</a></p></div>' for i,a in enumerate(selected))
            body += '<div class="hero-grid">'+card(e,lead,True)+'<aside class="hero-side"><div class="brief-panel"><div class="heading">Η επιλογή της έκδοσης</div><h3>Όσα αξίζουν<br><em>την προσοχή σου.</em></h3>'+picks+'</div></aside></div>'
        if e.get('summary_60s'):
            body += load_module('newspaper_ui').summary(SimpleNamespace(**globals()),e['summary_60s'],'Η έκδοση σε 60 δευτερόλεπτα')
        for category, anchor in [('Κύπρος','cyprus'),('Διεθνή','world')]:
            body += f'<section class="section" id="{anchor}"><div class="sectionhead"><h2>'+emblem(anchor)+f'{category}.</h2></div><div class="g3">'+''.join(card(e,a) for a in ordered if a!=lead and (a['category']==category or category=='Κύπρος' and a['category']=='Πρώτο θέμα'))+'</div></section>'
        body += load_module('newspaper_ui').changes(SimpleNamespace(**globals()),e['changes'])
        if not e.get('calculator'):
            body = body.replace('<a href="#rates">Δόση</a>', '<a href="#watch">Στη συνέχεια</a>' if any(p['id']=='watch' for p in e.get('panels',[])) else '')
        body += load_module('opportunities').render(SimpleNamespace(**globals()),e.get('opportunities',[]))+sports(e,aa)+markets(e)+calculator(e)+edition_panels(e)
        body += '<p class="warning">Η προσβασιμότητα συνδέσμων και η πραγματολογική διασταύρωση είναι διαφορετικοί έλεγχοι. Οι σελίδες διατηρούν την εικόνα της δικής τους έκδοσης.</p></main><footer class="footer"><div class="wrap">THE ORACLE SOVEREIGN · '+date+'</div></footer></body></html>'
        body=load_module('newspaper_ui').decorate(SimpleNamespace(**globals()),body,e)
        if not e.get('preserve_legacy_html') or e.get('photo_policy')=='real-photos-v1' or not (ROOT/'docs'/e['url']).is_file():
            write(ROOT/'docs'/e['url'],body)
        elif e.get('image_review'):
            write(ROOT/'docs'/e['url'],latest.compact_document((ROOT/'docs'/e['url']).read_text(encoding='utf-8'),edition_desk(e,registry)))
        for alias in e.get('aliases',[]) if not e.get('preserve_legacy_html') else []:
            # Preserve existing URLs as full edition pages; canonical stays on the primary path.
            write(ROOT/'docs'/alias,body)
        for a in aa:
            url=article_url(e,a)
            related=''.join(f'<a href="{esc(b["id"])}.html">{esc(b["headline"])}</a>' for b in aa if b['id']!=a['id'] and (b['story_id'] in a.get('related_story_ids',[]) or b['category']==a['category']))
            p=head(a['headline'],url,'article','../../')
            p+=f'<header class="top"><div class="shell"><a class="logo" href="../../{e["url"]}">THE ORACLE SOVEREIGN.</a><nav class="navlinks"><a href="../../{e["url"]}">← Εφημερίδα</a><a href="../../search.html">{icon('search')} Αναζήτηση</a><button data-theme-toggle aria-label="Εναλλαγή θέματος">◐</button></nav></div></header><main class="shell" id="main" data-article-key="{e["id"]}/{a["id"]}"><div class="kicker">{esc(a["category"])} · {TYPES[e["type"]]} έκδοση</div><h1>{esc(a["headline"])}</h1><div class="eyebrow">Συνοπτική καταγραφή της έκδοσης</div><p class="lede">{esc(a["summary"])}</p><div class="meta"><span>Δημοσίευση: {stamp(a["published_at"])}</span><span>Ενημέρωση: {stamp(a["updated_at"])}</span><span>{words(a)} λέξεις</span><span>{sources_label(a["sources"])}</span></div>'+image(a,'../../')
            if a.get('delta_update'):
                p+=f'<div class="article-delta-callout"><strong>Εξέλιξη / Τι άλλαξε:</strong> {esc(a["delta_update"])}</div>'
            if e.get('reading_review',{}).get('version')==2 and a.get('reader_mode')=='source':
                source=next(s for s in a['sources'] if s.get('access')=='read' and s.get('used_for_claims'))
                p+='<p><a class="read-link original-report" href="'+esc(source['url'])+'" rel="noopener noreferrer">'+icon('book')+'Πλήρες δημοσίευμα · '+esc(source['publisher'])+' ↗</a></p>'
            if e.get('published_at'):
                p+=f'<a class="read-link" href="../../daily/{e["date"]}.html">← Εφημερίδα της ημέρας · {e["date"]}</a>'
            p+='<div class="actions"><button data-font-step="-1" aria-label="Μικρότερο μέγεθος κειμένου">A−</button><button data-font-step="1" aria-label="Μεγαλύτερο μέγεθος κειμένου">A+</button><button data-bookmark aria-pressed="false">Αποθήκευση άρθρου</button><button data-resume hidden>Συνέχεια ανάγνωσης</button><span data-storage-status role="status"></span></div><progress id="reading-progress" max="100" value="0" aria-label="Πρόοδος ανάγνωσης"></progress>'
            if a.get('revision_note'):
                p+='<p class="revision-note">'+esc(a['revision_note'])+'</p>'
            toc='<div class="sidebox reader-toc"><h3>Σε αυτό το άρθρο</h3>'+''.join(f'<a href="#section-{i}">{esc(s["heading"])}</a>' for i,s in enumerate(a['sections'],1) if any(p.strip()!=a['summary'].strip() for p in s['paragraphs']))+'</div>'
            p+='<div class="layout"><article class="prose">'+blocks(a)+article_layers(a)+'<section class="section"><h2>Πηγές και χρόνοι αναφοράς</h2>'+source_links(a['sources'])+f'<p>{esc(a.get("evidence_note",""))}</p>'+'<p class="warning">Οι αλυσίδες αναφοράς δείχνουν την προέλευση των πληροφοριών. Αναδημοσιεύσεις του ίδιου πρακτορείου δεν αποτελούν ανεξάρτητη διασταύρωση.</p></section>'+f'<a class="read-link" href="../../{e["url"]}">← Επιστροφή στη συγκεκριμένη έκδοση</a></article><aside class="side">'+toc+f'<div class="sidebox"><h3>Σχετικές ιστορίες</h3><div class="sourcelinks">{related or "Δεν υπάρχουν επιπλέον σχετικές ιστορίες."}</div></div></aside></div></main></body></html>'
            p=p.replace('</main></body>', '<footer class="shell"><a href="'+BASE+'photo-credits.html">Συντελεστές εικόνων</a></footer></main></body>')
            write(ROOT/'docs'/url,p)
            write(ROOT/'docs/data/articles'/e['id']/(a['id']+'.json'),json.dumps(a,ensure_ascii=False,indent=2)+'\n')
    write(ROOT/'docs/photo-credits.html',photo_credits(bundles))
    registry.sort(key=lambda x:x['published_at'] or x['date'],reverse=True)
    write(ROOT/'docs/data/editions.json',json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    write(ROOT/'docs/search-index.json',json.dumps(search,ensure_ascii=False,indent=2)+'\n')
    routes={e['id']:{a['id']:article_url(e,a) for a in aa} for e,aa in bundles}
    route_registry={'articles':routes}
    for e,_ in bundles:
        for route in e.get('reader_routes',[]):
            route_registry[route]={'edition_id':e['id']}
            depth='../' if '/' in route else ''
            compat=head('Άνοιγμα ιστορικού άρθρου',route,'article',depth)
            compat+=f'<meta name="briefing-root" content="{depth or "./"}"><main class="shell" id="main"><h1>Άνοιγμα άρθρου</h1><p id="reader-status" role="status">Φόρτωση της συγκεκριμένης έκδοσης…</p><a class="read-link" href="{depth}index.html">← Αρχείο εκδόσεων</a><noscript>Χρειάζεται JavaScript για αυτόν τον παλιό σύνδεσμο. Τα άρθρα της έκδοσης είναι διαθέσιμα από το αρχείο.</noscript></main><script src="{depth}assets/reader-route.js"></script></body></html>'
            write(ROOT/'docs'/route,compat)
    write(ROOT/'docs/data/reader-routes.json',json.dumps(route_registry,ensure_ascii=False,indent=2)+'\n')
    for name in ['newspaper','article','newspaper-ui']:
        write(ROOT/'docs/assets'/(name+'.css'),(ROOT/'templates/v2'/(name+'.css')).read_text(encoding='utf-8'))
    archive=head('Αρχείο εκδόσεων','index.html','newspaper')+f'<header class="masthead wrap"><div class="brand"><h1>THE ORACLE <em>SOVEREIGN.</em></h1><p>Αρχείο δημοσιευμένων εκδόσεων</p></div></header><main class="wrap" id="main"><div class="tools"><button data-theme-toggle aria-label="Εναλλαγή θέματος">◐</button><a href="search.html">Αναζήτηση άρθρων</a><a href="https://jodemon9.github.io/oracle-briefing/">🗞️ Κύρια εφημερίδα ημέρας ↗</a><a href="daily/index.html">Αρχείο ημερών</a></div>'
    current_id=registry[0]['id'] if registry else None
    for edition_type, label in TYPES.items():
        archive+=f'<section class="section" id="{edition_type}"><div class="sectionhead"><h2>{label}.</h2></div><div class="g3">'
        for x in (item for item in registry if item['type']==edition_type):
            current=x['id']==current_id
            archive+=f'<article class="newscard{" current" if current else ""}"><div class="story-content"><p>{x["date"]} · {TYPES[x["type"]]} έκδοση{" · Τρέχουσα" if current else ""}</p><h3>{esc(x["title"])}</h3><p>{stamp(x["published_at"])}</p><a class="read-link" href="{esc(x["url"])}"'+(' aria-current="page"' if current else '')+'>Ανάγνωση έκδοσης ↗</a></div></article>'
        archive+='</div></section>'
    write(ROOT/'docs/index.html',archive+'</main></body></html>')
    pages={e['url'] for e,_ in bundles if not e.get('preserve_legacy_html') or e.get('image_review')}
    pages.update(article_url(e,a) for e,aa in bundles for a in aa)
    pages.update(alias for e,_ in bundles for alias in e.get('aliases',[]))
    if affected is not None:
        pages = {page for page in pages if any(page == e['url'] or page in e.get('aliases',[]) or page.startswith('articles/'+e['id']+'/') for e,_ in bundles if e['id'] in affected)}
    for page_url in sorted(pages):
        path=ROOT/'docs'/page_url
        write(path,latest.version_resources(path.read_text(encoding='utf-8'),ROOT,page_url))
    latest.publish(ROOT,registry)
    load_module('daily').publish(SimpleNamespace(**globals()),latest,bundles,affected_dates=None if affected is None else {e['date'] for e,_ in bundles if e['id'] in affected})
    write(ROOT/'docs/assets/latest-briefing.js',(ROOT/'templates/v2/latest-briefing.js').read_text(encoding='utf-8'))
    print(f'Built {len(bundles)} editions, {len(search)} separate articles, {len(registry)} archive entries')


def build(root=ROOT, incremental=False):
    """Publish a fully validated local candidate, with rollback; no remote writes."""
    global ROOT
    actual = Path(root).resolve()
    previous = ROOT
    cache = load_module('incremental')
    affected = cache.affected(actual,Path(__file__).parent,incremental)
    input_state = cache.inputs(actual,Path(__file__).parent)
    # Keep disposable candidates out of workspace synchronisation, which can
    # recreate moved/deleted files during cleanup. Promotion still requires the
    # same filesystem; fall back to a sibling when system temp is another mount.
    staging_parent = Path(tempfile.gettempdir()).resolve()
    if staging_parent.stat().st_dev != actual.stat().st_dev:
        staging_parent = actual.parent
    try:
        with tempfile.TemporaryDirectory(prefix='oracle-build-', dir=staging_parent) as directory:
            candidate = Path(directory)/'candidate'
            candidate.mkdir()
            for name in ['content', 'templates', 'docs']:
                if (actual/name).exists():
                    shutil.copytree(actual/name, candidate/name)
            if (actual/'BRIEFING_RUNTIME.md').is_file():
                shutil.copyfile(actual/'BRIEFING_RUNTIME.md',candidate/'BRIEFING_RUNTIME.md')
            _render(candidate,affected)
            if cache.inputs(actual,Path(__file__).parent) != input_state:
                raise ValueError('Publication inputs changed during build; retry from validation')
            live = actual/'docs'
            backup = Path(directory)/'previous-docs'
            had_live = live.exists()
            if had_live:
                os.replace(live, backup)
            try:
                os.replace(candidate/'docs', live)
            except BaseException:
                if had_live:
                    os.replace(backup, live)
                raise
            cache.save(actual,Path(__file__).parent,load_module('atomic'))
    finally:
        ROOT = previous
    return {'mode':'full' if affected is None else 'incremental','rendered_editions':None if affected is None else sorted(affected)}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--incremental',action='store_true')
    args=parser.parse_args()
    print(json.dumps(build(args.root,args.incremental)))
