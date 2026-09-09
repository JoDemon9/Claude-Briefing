#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Automated HTML Generator
Converts any `oracle-briefing-YYYY-MM-DD.md` into the executive web edition.
Features:
  - News-First Layout: Breaking News, Cyprus (6 items), World (5 items), Movers lead the page
  - Tools (Euribor rates, loan calculator, dashboard) placed logically after news
  - High-resolution editorial images for every news card with fallback
  - Expandable full text / antilogos details for maximum readability
  - Class-based Tailwind Dark Mode (zero FOUC) & reduced-motion support
  - Dynamic Open-Meteo live weather client fetch
  - Weekly House Search (Real Estate Radar) integration
  - Instant Archive Search across all past editions
"""

import os
import sys
import re
import json
import glob
import shutil
import string
import urllib.request
import ssl
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRIEFINGS_DIR = os.path.join(BASE_DIR, 'briefings')
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
DOCS_BRIEFINGS_DIR = os.path.join(DOCS_DIR, 'briefings')
HOUSE_SEARCH_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'House Search'))
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'image_cache.json')
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'edition.html')

# SSL context for image fetching
SSL_CTX = ssl._create_unverified_context()

# Values that could not be parsed out of the briefing markdown. Rendered as
# "—" on the page and shouted about at the end of the build; a stale hardcoded
# number must never reach the published edition dressed up as live data.
BUILD_WARNINGS = []


def warn(message):
    """Record a build warning and print it immediately."""
    BUILD_WARNINGS.append(message)
    print(f"!! BUILD WARNING: {message}")


def dash(value):
    """Render a missing value as an em dash rather than a stale default."""
    return value if value not in (None, '') else '—'


def parse_greek_number(raw):
    """'3,78%' / '€200.000' / '25' -> float. None when unparseable."""
    if not raw:
        return None
    txt = re.sub(r'[^\d.,]', '', str(raw))
    if not txt:
        return None
    if '.' in txt and ',' in txt:
        txt = txt.replace('.', '').replace(',', '.')      # 1.234,56
    elif ',' in txt:
        txt = txt.replace(',', '.')                       # 3,78
    elif txt.count('.') == 1 and len(txt.split('.')[1]) == 3:
        txt = txt.replace('.', '')                        # 200.000
    else:
        txt = txt.replace('.', '')
    try:
        return float(txt)
    except ValueError:
        return None


def format_euro(value):
    """1031.5 -> '€1.032' (Greek thousands separator)."""
    return '€' + f"{round(value):,}".replace(',', '.')


def annuity_payment(principal, years, annual_rate_pct):
    """Fixed monthly instalment of a level-payment loan. None on bad input."""
    if not principal or not years or annual_rate_pct is None:
        return None
    n = int(round(years * 12))
    if n <= 0:
        return None
    r = (annual_rate_pct / 100.0) / 12.0
    if r <= 0:
        return principal / n
    return (principal * r) / (1 - (1 + r) ** -n)


TOPIC_FALLBACKS = {
    'school': 'https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=800&q=80',
    'employment': 'https://images.unsplash.com/photo-1521791136064-7986c2920216?w=800&q=80',
    'economy': 'https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&q=80',
    'shipwreck': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80',
    'politics': 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&q=80',
    'housing': 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800&q=80',
    'diplomacy': 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&q=80',
    'germany': 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&q=80',
    'volcano': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80',
    'aviation': 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800&q=80',
    'justice': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&q=80',
    'general': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80'
}


def md_to_inline_html(text):
    if not text:
        return ""
    # Convert markdown links [name](url)
    text = re.sub(r'\[(.*?)\]\((https?://[^\s)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-semibold">\1</a>', text)
    # Convert bold **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Convert italic *text*
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    return text


def render_depth_html(depth, is_world=False):
    if not depth or len(depth) < 2:
        return ""

    rows = []
    if depth.get('background'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Το υπόβαθρο:</strong> {md_to_inline_html(depth["background"])}</div>')
    if depth.get('practical'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Τι σημαίνει πρακτικά:</strong> {md_to_inline_html(depth["practical"])}</div>')

    if not is_world and depth.get('next_watch'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Τι να παρακολουθήσω:</strong> {md_to_inline_html(depth["next_watch"])}</div>')
    elif is_world and depth.get('antilogos'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Αντίλογος:</strong> {md_to_inline_html(depth["antilogos"])}</div>')
    elif depth.get('next_watch'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Τι να παρακολουθήσω:</strong> {md_to_inline_html(depth["next_watch"])}</div>')
    elif depth.get('antilogos'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Αντίλογος:</strong> {md_to_inline_html(depth["antilogos"])}</div>')

    if len(rows) < 2:
        return ""

    content = '\n'.join(rows)
    return f'''
    <details class="depth mt-3 border-t border-[var(--rule)] pt-2.5">
      <summary class="cursor-pointer t-meta font-semibold text-[var(--accent)] hover:underline flex items-center justify-between py-1">
        <span>Περισσότερα: Υπόβαθρο & Πρακτική Σημασία</span>
        <span class="expand-icon text-[10px] transition-transform">▼</span>
      </summary>
      <div class="mt-2.5 t-meta text-[var(--ink-body)] bg-[var(--paper)] p-3 rounded space-y-2 border border-[var(--rule)] leading-relaxed">
        {content}
      </div>
    </details>
    '''


def load_image_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_image_cache(cache):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolve_image(url, title, default_category='ΕΠΙΚΑΙΡΟΤΗΤΑ'):
    cache = load_image_cache()
    if url in cache and cache[url].get('image'):
        return cache[url]['image'], cache[url].get('category', default_category)

    # Keyword fallback selection
    t_lower = (title + ' ' + url).lower()
    fallback = TOPIC_FALLBACKS['general']
    category = default_category

    if any(k in t_lower for k in ['σχολ', 'μαθητ', 'υποδομ', 'ύψωνα', 'παιδεία']):
        fallback = TOPIC_FALLBACKS['school']
        category = 'ΠΑΙΔΕΙΑ & ΥΠΟΔΟΜΕΣ'
    elif any(k in t_lower for k in ['απασχόληση', 'εργασί', 'cystat', 'μισθ']):
        fallback = TOPIC_FALLBACKS['employment']
        category = 'ΟΙΚΟΝΟΜΙΑ'
    elif any(k in t_lower for k in ['ναυάγ', 'νεκροί', 'σκάφος', 'κερύνει']):
        fallback = TOPIC_FALLBACKS['shipwreck']
        category = 'ΕΚΤΑΚΤΟ'
    elif any(k in t_lower for k in ['λιμουζίν', 'βουλ', 'χριστοδουλίδ', 'πολιτικ']):
        fallback = TOPIC_FALLBACKS['politics']
        category = 'ΠΟΛΙΤΙΚΗ'
    elif any(k in t_lower for k in ['ενοίκι', 'στέγη', 'τεπακ', 'ακίνητ', 'λεμεσ']):
        fallback = TOPIC_FALLBACKS['housing']
        category = 'Ο ΦΑΚΕΛΟΣ ΜΟΥ'
    elif any(k in t_lower for k in ['zelenskyy', 'putin', 'ουκραν', 'κίεβο', 'διπλωματ']):
        fallback = TOPIC_FALLBACKS['diplomacy']
        category = 'ΔΙΠΛΩΜΑΤΙΑ'
    elif any(k in t_lower for k in ['afd', 'γερμανί', 'merz', 'σαξονία']):
        fallback = TOPIC_FALLBACKS['germany']
        category = 'ΓΕΡΜΑΝΙΑ'
    elif any(k in t_lower for k in ['krakatau', 'ηφαίστει', 'ινδονησία']):
        fallback = TOPIC_FALLBACKS['volcano']
        category = 'ΑΣΙΑ'
    elif any(k in t_lower for k in ['amazon', 'boeing', 'μαϊάμι', 'αεροπορικ']):
        fallback = TOPIC_FALLBACKS['aviation']
        category = 'ΗΠΑ'
    elif any(k in t_lower for k in ['icj', 'χάγη', 'δικαστήρι', 'ισραήλ', 'γενοκτον']):
        fallback = TOPIC_FALLBACKS['justice']
        category = 'ΔΙΚΑΙΟΣΥΝΗ'
    elif any(k in t_lower for k in ['dbrs', 'αξιολόγηση', 'οίκος', 'δημοσιονομ']):
        fallback = TOPIC_FALLBACKS['economy']
        category = 'ΟΙΚΟΝΟΜΙΑ & ΑΞΙΟΧΡΕΟ'

    # Try fetching og:image live with short timeout
    og_img = None
    if url.startswith('http'):
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=3.0, context=SSL_CTX) as resp:
                html_txt = resp.read().decode('utf-8', errors='ignore')
                m = re.search(r'<meta[^>]+(?:property|name)=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', html_txt, re.I)
                if not m:
                    m = re.search(r'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+(?:property|name)=[\'"]og:image[\'"]', html_txt, re.I)
                if m:
                    candidate = m.group(1).strip()
                    if candidate.startswith('http'):
                        og_img = candidate
        except Exception:
            pass

    final_img = og_img if og_img else fallback
    cache[url] = {'image': final_img, 'category': category}
    save_image_cache(cache)
    return final_img, category


LINK_CLAIM_RE = re.compile(
    r'(Έλεγχος και Επαλήθευση Συνδέσμων|σύνδεσμοι ελέγχθηκαν|200\s*OK|broken/404)',
    re.IGNORECASE)


def link_check_footnote(date_slug):
    """The link-verification footnote, built from scripts/check-links.py's
    report — never from prose in the markdown. Editions used to assert
    «όλοι οι σύνδεσμοι ελέγχθηκαν (200 OK)» with nothing having checked."""
    path = os.path.join(BRIEFINGS_DIR, f'.link-check-{date_slug}.json')
    if not os.path.exists(path):
        warn(f"Δεν βρέθηκε αναφορά ελέγχου συνδέσμων ({os.path.basename(path)}). "
             f"Τρέξτε: python scripts/check-links.py <briefing.md>")
        return ('**Έλεγχος συνδέσμων:** δεν εκτελέστηκε αυτόματος έλεγχος για '
                'αυτή την έκδοση.')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            rep = json.load(f)
    except Exception as e:
        warn(f"Μη αναγνώσιμη αναφορά ελέγχου συνδέσμων: {e}")
        return ('**Έλεγχος συνδέσμων:** η αναφορά ελέγχου δεν ήταν αναγνώσιμη.')

    when = rep.get('checked_at', '')
    total, ok = rep.get('total', 0), rep.get('ok', 0)
    blocked, dead = rep.get('blocked', []), rep.get('dead', [])
    parts = [f"**Έλεγχος συνδέσμων:** {total} σύνδεσμοι ελέγχθηκαν αυτόματα με "
             f"αιτήματα HTTP στις {when}: {ok} απάντησαν κανονικά"]
    if blocked:
        parts.append(f"{len(blocked)} επέστρεψαν φραγή αυτοματοποιημένης "
                     f"πρόσβασης (403/429) και δεν επαληθεύτηκαν")
    if dead:
        parts.append(f"{len(dead)} ήταν νεκροί")
    return ' · '.join(parts) + '.'


def find_latest_briefing():
    pattern = os.path.join(BRIEFINGS_DIR, 'oracle-briefing-*.md')
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No briefing files found in {BRIEFINGS_DIR}")
    return files[-1]


def parse_markdown(md_content):
    data = {
        'title': 'THE ORACLE SOVEREIGN',
        'date_str': '',
        'time_str': '',
        'read_time': "7'",
        'top_story': {},
        'dashboard': [],
        'number_of_day': {},
        'rates': {
            'euribor': [],
            'ecb_rate': None,
            'next_ecb': None,
            'cbc_mortgage_rate': None,
            'loan_amount': None,
            'loan_years': None,
            'loan_rate': None,
            'example_payment': None,
            'example_total_interest': None,
            'example_change': None,
            'sources': []
        },
        'cyprus': [],
        'world': [],
        'markets': [],
        'sports': {
            'omonoia': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []},
            'manutd': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []},
            'realmadrid': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []},
            'formula1': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []}
        },
        'weather': {},
        'developments': [],
        'portfolio': [],
        'deadlines': [],
        'tomorrow': [],
        'footnotes': []
    }

    lines = md_content.splitlines()
    for line in lines[:6]:
        line_clean = line.strip()
        m_title = re.search(r'#\s+🏛️\s+THE ORACLE SOVEREIGN\s*[—–-]\s*(.+)', line_clean)
        if m_title:
            data['date_str'] = m_title.group(1).strip()
        m_time = re.search(r'\*\*(\d{1,2}:\d{2})\s*ώρα Κύπρου', line_clean)
        if m_time:
            data['time_str'] = m_time.group(1).strip()
        m_read = re.search(r'χρόνος ανάγνωσης\s*~?(\d+)', line_clean)
        if m_read:
            data['read_time'] = f"{m_read.group(1)}'"

    sections = re.split(r'\n##\s+', md_content)
    for sec in sections[1:]:
        sec_lines = sec.strip().splitlines()
        if not sec_lines:
            continue
        sec_header = sec_lines[0].strip()

        # TOP STORY
        if 'ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ' in sec_header:
            top_data = {'title': '', 'body': '', 'antilogos': '', 'sources': []}
            h3_match = re.search(r'###\s+(.+)', sec)
            if h3_match:
                top_data['title'] = h3_match.group(1).strip()

            anti_match = re.search(r'\*\*Αντίλογος:\*\*\s*(.+?)(?=\n\n|\n\*\*Πηγές:|\Z)', sec, re.DOTALL)
            if anti_match:
                top_data['antilogos'] = anti_match.group(1).strip()

            src_match = re.search(r'\*\*Πηγές:\*\*\s*(.+)', sec)
            if src_match:
                sources_raw = re.findall(r'\[(.*?)\]\((.*?)\)', src_match.group(1))
                top_data['sources'] = [{'name': name, 'url': url} for name, url in sources_raw]

            body_parts = []
            capture = False
            for sl in sec_lines[1:]:
                sl_clean = sl.strip()
                if sl_clean.startswith('### '):
                    capture = True
                    continue
                if sl_clean.startswith('**Αντίλογος:') or sl_clean.startswith('**Πηγές:'):
                    capture = False
                    break
                if capture and sl_clean and not sl_clean.startswith('---'):
                    body_parts.append(sl_clean)
            top_data['body'] = ' '.join(body_parts)
            data['top_story'] = top_data

        # DASHBOARD
        elif 'DASHBOARD' in sec_header:
            table_lines = [l.strip() for l in sec_lines if l.strip().startswith('|') and not '---' in l]
            for row in table_lines:
                cols = [c.strip() for c in row.split('|')[1:-1]]
                if len(cols) >= 4 and not cols[0].startswith('Δείκτης') and not ':---' in cols[0]:
                    asset_name = re.sub(r'\*\*', '', cols[0]).strip()
                    price = cols[1].strip()
                    change = cols[2].strip()
                    date_ref = cols[3].strip()
                    data['dashboard'].append({
                        'asset': asset_name,
                        'price': price,
                        'change': change,
                        'date_ref': date_ref
                    })
            nod_match = re.search(r'\*\*Ο αριθμός της ημέρας:\*\*\s*\*\*([^*]+)\*\*\s*[—–-]\s*(.+)', sec)
            if nod_match:
                data['number_of_day'] = {
                    'number': nod_match.group(1).strip(),
                    'text': nod_match.group(2).strip()
                }

        # RATES & MORTGAGE
        elif 'ΕΠΙΤΟΚΙΑ' in sec_header:
            table_lines = [l.strip() for l in sec_lines if l.strip().startswith('|') and not '---' in l]
            for row in table_lines:
                cols = [c.strip() for c in row.split('|')[1:-1]]
                if len(cols) >= 5 and cols[0] in ['**Τρέχον**', 'Τρέχον', '**Πριν 1 μήνα**', 'Πριν 1 μήνα']:
                    period = re.sub(r'\*\*', '', cols[0]).strip()
                    data['rates']['euribor'].append({
                        'period': period,
                        '1m': cols[1], '3m': cols[2], '6m': cols[3], '12m': cols[4]
                    })
            if not data['rates']['euribor']:
                warn("ΕΠΙΤΟΚΙΑ: δεν βρέθηκε πίνακας Euribor στο markdown.")

            ecb_m = re.search(r'Επιτόκιο ΕΚΤ.*?:\s*([\d,]+%?)', sec)
            if ecb_m:
                data['rates']['ecb_rate'] = ecb_m.group(1).strip()
            else:
                warn("ΕΠΙΤΟΚΙΑ: δεν βρέθηκε το επιτόκιο ΕΚΤ (deposit facility).")

            next_m = re.search(r'Επόμενη συνεδρίαση:\s*([^\n·]+)', sec)
            if next_m:
                data['rates']['next_ecb'] = next_m.group(1).strip()
            else:
                warn("ΕΠΙΤΟΚΙΑ: δεν βρέθηκε η ημερομηνία επόμενης συνεδρίασης ΕΚΤ.")

            cbc_m = re.search(r'Μέσο επιτόκιο νέων στεγαστικών.*?:.*?([\d,]+%)', sec)
            if cbc_m:
                data['rates']['cbc_mortgage_rate'] = cbc_m.group(1).strip()
            else:
                warn("ΕΠΙΤΟΚΙΑ: δεν βρέθηκε το μέσο επιτόκιο νέων στεγαστικών (ΚΤΚ).")

            # The instalment is computed here from the parsed loan terms — never
            # copied from the markdown — so the published figure always matches
            # the rate printed beside it.
            calc_m = re.search(
                r'Ενδεικτική δόση:\s*€?([\d.,]+)\s*/\s*(\d+)\s*έτη\s*με επιτόκιο\s*([\d,]+)\s*%',
                sec)
            if calc_m:
                data['rates']['loan_amount'] = parse_greek_number(calc_m.group(1))
                data['rates']['loan_years'] = parse_greek_number(calc_m.group(2))
                data['rates']['loan_rate'] = parse_greek_number(calc_m.group(3))
            else:
                warn("ΕΠΙΤΟΚΙΑ: δεν βρέθηκαν οι όροι της ενδεικτικής δόσης "
                     "(ποσό / διάρκεια / επιτόκιο).")
                data['rates']['loan_rate'] = parse_greek_number(
                    data['rates']['cbc_mortgage_rate'])

            payment = annuity_payment(data['rates']['loan_amount'],
                                      data['rates']['loan_years'],
                                      data['rates']['loan_rate'])
            if payment is None:
                warn("ΕΠΙΤΟΚΙΑ: αδύνατος ο υπολογισμός της ενδεικτικής δόσης — "
                     "εμφανίζεται «—».")
            else:
                months = data['rates']['loan_years'] * 12
                data['rates']['example_payment'] = format_euro(payment)
                data['rates']['example_total_interest'] = format_euro(
                    payment * months - data['rates']['loan_amount'])

            chg_m = re.search(r'Μεταβολή έναντι προηγούμενης έκδοσης:\s*([^\n]+)', sec)
            if chg_m:
                data['rates']['example_change'] = chg_m.group(1).strip().rstrip('. ')
            else:
                warn("ΕΠΙΤΟΚΙΑ: δεν βρέθηκε η μεταβολή δόσης έναντι προηγούμενης έκδοσης.")

            srcs_m = re.search(r'Πηγές:\s*(.+)', sec)
            if srcs_m:
                sources_raw = re.findall(r'\[(.*?)\]\((.*?)\)', srcs_m.group(1))
                data['rates']['sources'] = [{'name': name, 'url': url} for name, url in sources_raw]

        # CYPRUS
        elif 'ΚΥΠΡΟΣ' in sec_header:
            items_raw = re.split(r'\n###\s+', '\n' + sec)
            for raw_item in items_raw[1:]:
                lines_i = raw_item.strip().splitlines()
                if not lines_i:
                    continue
                title_line = lines_i[0].strip()
                tag_match = re.findall(r'\[([^\]]+)\]', title_line)
                tags = [t for t in tag_match if t not in ['Ο Φάκελός μου']]
                tag = tags[-1] if tags else 'Μονή πηγή'

                is_portfolio = '[Ο Φάκελός μου]' in title_line or 'Ο Φάκελός μου' in title_line
                clean_title = re.sub(r'^\d+\.\s*', '', title_line)
                clean_title = clean_title.replace('[Ο Φάκελός μου]', '').replace(f'[{tag}]', '').strip()

                why_match = re.search(r'\*\*Γιατί με αφορά:\*\*\s*(.+)', raw_item)
                why_text = why_match.group(1).strip() if why_match else ''

                src_match = re.search(r'\*\*Πηγή:\*\*\s*(.+)', raw_item)
                source = None
                if src_match:
                    src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', src_match.group(1))
                    if src_parsed:
                        source = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}

                body_lines = []
                for bl in lines_i[1:]:
                    bl_c = bl.strip()
                    if bl_c.startswith('**Γιατί με αφορά:') or bl_c.startswith('**Βάθος:') or bl_c.startswith('**Πηγή:'):
                        break
                    if bl_c.startswith('* **') or bl_c.startswith('- **') or bl_c.startswith('• **'):
                        break
                    if bl_c and not bl_c.startswith('---'):
                        body_lines.append(bl_c)
                body_text = ' '.join(body_lines)

                depth = {}
                bg_m = re.search(r'\*\*Το υπόβαθρο:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                pr_m = re.search(r'\*\*Τι σημαίνει πρακτικά:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                nw_m = re.search(r'\*\*Τι να παρακολουθήσω:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                an_m = re.search(r'\*\*Αντίλογος:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                if bg_m and bg_m.group(1).strip():
                    depth['background'] = bg_m.group(1).strip().replace('\n', ' ')
                if pr_m and pr_m.group(1).strip():
                    depth['practical'] = pr_m.group(1).strip().replace('\n', ' ')
                if nw_m and nw_m.group(1).strip():
                    depth['next_watch'] = nw_m.group(1).strip().replace('\n', ' ')
                if an_m and an_m.group(1).strip():
                    depth['antilogos'] = an_m.group(1).strip().replace('\n', ' ')

                data['cyprus'].append({
                    'title': clean_title,
                    'tag': tag,
                    'is_portfolio': is_portfolio,
                    'body': body_text,
                    'why': why_text,
                    'source': source,
                    'depth': depth
                })

        # WORLD
        elif 'ΔΙΕΘΝΗ' in sec_header:
            items_raw = re.split(r'\n###\s+', '\n' + sec)
            for raw_item in items_raw[1:]:
                lines_i = raw_item.strip().splitlines()
                if not lines_i:
                    continue
                title_line = lines_i[0].strip()
                tag_match = re.findall(r'\[([^\]]+)\]', title_line)
                tag = tag_match[-1] if tag_match else 'Μονή πηγή'
                clean_title = re.sub(r'^\d+\.\s*', '', title_line).replace(f'[{tag}]', '').strip()

                src_match = re.search(r'\*\*Πηγή:\*\*\s*(.+)', raw_item)
                source = None
                if src_match:
                    src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', src_match.group(1))
                    if src_parsed:
                        source = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}

                body_lines = []
                for bl in lines_i[1:]:
                    bl_c = bl.strip()
                    if bl_c.startswith('**Βάθος:') or bl_c.startswith('**Πηγή:'):
                        break
                    if bl_c.startswith('* **') or bl_c.startswith('- **') or bl_c.startswith('• **'):
                        break
                    if bl_c and not bl_c.startswith('---'):
                        body_lines.append(bl_c)
                body_text = ' '.join(body_lines)

                depth = {}
                bg_m = re.search(r'\*\*Το υπόβαθρο:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                pr_m = re.search(r'\*\*Τι σημαίνει πρακτικά:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                nw_m = re.search(r'\*\*Τι να παρακολουθήσω:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                an_m = re.search(r'\*\*Αντίλογος:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                if bg_m and bg_m.group(1).strip():
                    depth['background'] = bg_m.group(1).strip().replace('\n', ' ')
                if pr_m and pr_m.group(1).strip():
                    depth['practical'] = pr_m.group(1).strip().replace('\n', ' ')
                if nw_m and nw_m.group(1).strip():
                    depth['next_watch'] = nw_m.group(1).strip().replace('\n', ' ')
                if an_m and an_m.group(1).strip():
                    depth['antilogos'] = an_m.group(1).strip().replace('\n', ' ')

                data['world'].append({
                    'title': clean_title,
                    'tag': tag,
                    'body': body_text,
                    'source': source,
                    'depth': depth
                })

        # MARKETS TOP MOVERS
        elif 'ΑΓΟΡΕΣ' in sec_header or 'MOVERS' in sec_header:
            items_raw = re.split(r'\n###\s+', '\n' + sec)
            for raw_item in items_raw[1:]:
                lines_i = raw_item.strip().splitlines()
                if not lines_i:
                    continue
                header_line = lines_i[0].strip()
                cause_m = re.search(r'\*\*Αιτία:\*\*\s*(.+)', raw_item)
                cause = cause_m.group(1).strip() if cause_m else ''

                src_m = re.search(r'\*\*Πηγή:\*\*\s*(.+)', raw_item)
                source = None
                if src_m:
                    src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', src_m.group(1))
                    if src_parsed:
                        source = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}

                data['markets'].append({
                    'header': header_line,
                    'cause': cause,
                    'source': source
                })

        # SPORTS
        elif 'ΑΘΛΗΤΙΚΑ' in sec_header:
            team = None
            for sl in sec_lines:
                sl_c = sl.strip()
                sl_upper = sl_c.upper()
                if sl_c.startswith('###') or sl_c.startswith('##'):
                    if 'ΟΜΟΝΟΙΑ' in sl_upper:
                        team = 'omonoia'
                    elif 'MANCHESTER UNITED' in sl_upper or 'MAN UTD' in sl_upper:
                        team = 'manutd'
                    elif 'REAL MADRID' in sl_upper:
                        team = 'realmadrid'
                    elif 'FORMULA 1' in sl_upper or 'FORMULA1' in sl_upper or 'F1' in sl_upper:
                        team = 'formula1'
                    continue

                if team and (sl_c.startswith('*') or sl_c.startswith('-')):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    data['sports'][team]['raw'].append(item_text)

                    if 'Τελευταίο αποτέλεσμα:' in item_text:
                        val = re.sub(r'^\*?\*?Τελευταίο αποτέλεσμα:\*?\*?\s*', '', item_text).strip()
                        data['sports'][team]['last_result'] = val
                    elif 'Επόμενος αγώνας:' in item_text:
                        val = re.sub(r'^\*?\*?Επόμενος αγώνας:\*?\*?\s*', '', item_text).strip()
                        data['sports'][team]['next_match'] = val
                    elif 'Highlights:' in item_text or 'Βίντεο Highlights:' in item_text or 'Βίντεο:' in item_text or 'YouTube' in item_text:
                        hl_match = re.search(r'\[(.*?)\]\((.*?)\)', item_text)
                        if hl_match:
                            data['sports'][team]['highlights'] = {
                                'title': hl_match.group(1).strip(),
                                'url': hl_match.group(2).strip()
                            }
                        else:
                            u_match = re.search(r'https?://\S+', item_text)
                            if u_match:
                                data['sports'][team]['highlights'] = {
                                    'title': 'YouTube Highlights',
                                    'url': u_match.group(0).strip(')')
                                }
                    elif 'Πηγή:' in item_text:
                        src_match = re.search(r'\[(.*?)\]\((.*?)\)', item_text)
                        if src_match:
                            data['sports'][team]['source'] = {
                                'name': src_match.group(1).strip(),
                                'url': src_match.group(2).strip()
                            }
                    else:
                        clean_news = re.sub(r'^\*?\*?(?:Μία γραμμή νέων|Νέα):\*?\*?\s*', '', item_text).strip()
                        data['sports'][team]['news'].append(clean_news)

            # Fallback source search for any team missing source
            for t_key, t_val in data['sports'].items():
                if not t_val['source']:
                    for r in reversed(t_val['raw']):
                        candidates = re.findall(r'\[(.*?)\]\((https?://.*?)\)', r)
                        for name, url in candidates:
                            if 'youtube' not in url.lower():
                                t_val['source'] = {'name': name, 'url': url}
                                break
                        if t_val['source']:
                            break

        # WEATHER
        elif 'ΚΑΙΡΟΣ' in sec_header:
            w_data = {'raw_items': [], 'source': None}
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if not item_text or item_text in ['--', '---']:
                        continue
                    if 'Πηγή:' in item_text:
                        src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', item_text)
                        if src_parsed:
                            w_data['source'] = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}
                    else:
                        w_data['raw_items'].append(item_text)
            data['weather'] = w_data

        # DEVELOPMENTS
        elif 'ΕΞΕΛΙΞΕΙΣ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['developments'].append(item_text)

        # PORTFOLIO / STANDING INTERESTS
        elif 'Ο ΦΑΚΕΛΟΣ ΜΟΥ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['portfolio'].append(item_text)

        # DEADLINES
        elif 'ΤΙ ΝΑ ΚΑΝΩ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['deadlines'].append(item_text)

        # TOMORROW
        elif 'ΓΙΑ ΑΥΡΙΟ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if re.match(r'^\d+\.', sl_c):
                    item_text = re.sub(r'^\d+\.\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['tomorrow'].append(item_text)

        # FOOTNOTES
        elif 'Υποσημείωση' in sec_header or 'ΥΠΟΣΗΜΕΙΩΣΗ' in sec_header:
            for sl in sec_lines:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['footnotes'].append(item_text)

    # Editions write the footnotes as a bold **Υποσημείωση:** paragraph rather
    # than an "## " header, so the section loop above never sees them and the
    # page's footnote list came out empty. Pick the block up directly.
    if not data['footnotes']:
        fn_m = re.search(r'\*\*Υποσημείωση[^\n]*\*\*\s*\n([\s\S]*?)(?=\n##\s|\Z)',
                         md_content)
        if fn_m:
            for sl in fn_m.group(1).splitlines():
                sl_c = sl.strip()
                if not sl_c or sl_c.startswith('---') or sl_c.startswith('***'):
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['footnotes'].append(item_text)
        else:
            warn("Δεν βρέθηκε ενότητα «Υποσημείωση» στο markdown.")

    return data


def get_latest_house_search():
    if not os.path.exists(HOUSE_SEARCH_DIR):
        return None

    md_files = sorted(glob.glob(os.path.join(HOUSE_SEARCH_DIR, 'limassol-listings-*.md')))
    html_files = sorted(glob.glob(os.path.join(HOUSE_SEARCH_DIR, 'limassol-listings-*.html')))

    if not md_files:
        return None

    latest_md = md_files[-1]
    latest_html = html_files[-1] if html_files else None

    m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(latest_md))
    date_str = m.group(1) if m else 'Τελευταία Εβδομάδα'

    stats = {
        'date': date_str,
        'unique_properties': '1.427',
        'top_picks_count': '3',
        'top_pick_highlights': '2x 1Υ/Δ Ζακάκι + 1x 2Υ/Δ Ύψωνας (από €196k + ΦΠΑ)',
        'html_filename': os.path.basename(latest_html) if latest_html else None,
        'md_filename': os.path.basename(latest_md)
    }

    try:
        with open(latest_md, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            m_props = re.search(r'Πραγματικά Μοναδικά Φυσικά Ακίνητα\s*\|\s*\*\*([^\*]+)\*\*', content)
            if m_props:
                stats['unique_properties'] = m_props.group(1).strip()
            m_picks = re.search(r'Κύρια Λίστα \(Top Picks\)\s*\|\s*\*\*([^\*]+)\*\*', content)
            if m_picks:
                stats['top_picks_count'] = m_picks.group(1).strip()
    except Exception as e:
        print(f"Note: Could not parse deep House Search metrics: {e}")

    docs_target_dir = os.path.join(DOCS_DIR, 'house-search')
    os.makedirs(docs_target_dir, exist_ok=True)

    if latest_html and os.path.exists(latest_html):
        shutil.copy2(latest_html, os.path.join(docs_target_dir, 'latest.html'))
        stats['local_url'] = 'house-search/latest.html'
    else:
        stats['local_url'] = None

    return stats


def build_search_index():
    index_entries = []
    pattern = os.path.join(BRIEFINGS_DIR, 'oracle-briefing-*.md')
    briefing_files = sorted(glob.glob(pattern), reverse=True)

    for bpath in briefing_files:
        bfilename = os.path.basename(bpath)
        m_date = re.search(r'(\d{4}-\d{2}-\d{2})', bfilename)
        date_str = m_date.group(1) if m_date else bfilename

        try:
            with open(bpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            data = parse_markdown(content)

            def clean_plain(s):
                if not s: return ""
                s = re.sub(r'\[(.*?)\]\((https?://[^\s)]+)\)', r'\1', s)
                s = re.sub(r'\*+', '', s)
                return s.strip()

            if data['top_story'].get('title'):
                index_entries.append({
                    'date': date_str,
                    'section': '⭐ Πρώτο Θέμα',
                    'title': clean_plain(data['top_story']['title']),
                    'snippet': clean_plain(data['top_story']['body'][:180]) + '...',
                    'url': f"briefings/{date_str}.html#top-story" if date_str != datetime.now().strftime('%Y-%m-%d') else "#top-story"
                })

            for item in data['cyprus']:
                index_entries.append({
                    'date': date_str,
                    'section': '🇨🇾 Κύπρος',
                    'title': clean_plain(item['title']),
                    'snippet': clean_plain(item['body'][:160]) + '...',
                    'url': f"briefings/{date_str}.html#cyprus" if date_str != datetime.now().strftime('%Y-%m-%d') else "#cyprus"
                })

            for item in data['world']:
                index_entries.append({
                    'date': date_str,
                    'section': '🌍 Διεθνή',
                    'title': clean_plain(item['title']),
                    'snippet': clean_plain(item['body'][:160]) + '...',
                    'url': f"briefings/{date_str}.html#world" if date_str != datetime.now().strftime('%Y-%m-%d') else "#world"
                })

            for dl in data['deadlines']:
                clean_dl = clean_plain(dl)
                index_entries.append({
                    'date': date_str,
                    'section': '📅 Προθεσμίες',
                    'title': clean_dl.split('—')[0].strip(),
                    'snippet': clean_dl[:160] + '...',
                    'url': f"briefings/{date_str}.html#deadlines" if date_str != datetime.now().strftime('%Y-%m-%d') else "#deadlines"
                })

        except Exception as e:
            print(f"Error indexing {bpath}: {e}")

    docs_index_path = os.path.join(DOCS_DIR, 'search-index.json')
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(docs_index_path, 'w', encoding='utf-8') as f:
        json.dump(index_entries, f, ensure_ascii=False, indent=2)

    return index_entries


def render_template(context):
    """Fill scripts/templates/edition.html. The page was a ~1000-line f-string
    inside render_html(); markup, CSS and JS now live in the template and this
    module only prepares data. Placeholders are string.Template's ${name}, so
    a literal $ in the template is written $$."""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = string.Template(f.read())
    try:
        return template.substitute(context)
    except KeyError as e:
        print(f"Template placeholder {e} has no value in render_html().",
              file=sys.stderr)
        raise


def render_html(data, house_stats, search_index):
    date_display = data['date_str'] or '7 Σεπτεμβρίου 2026'
    time_display = data['time_str'] or '13:30'
    read_time = data['read_time'] or "7'"

    m_iso = re.search(r'(\d{4}-\d{2}-\d{2})', date_display)
    iso_date = m_iso.group(1) if m_iso else datetime.now().strftime('%Y-%m-%d')
    gen_iso = f"{iso_date}T{time_display}:00+03:00" if ':' in time_display else f"{iso_date}T13:30:00+03:00"

    # Ticker Items
    ticker_spans = []
    for d in data['dashboard']:
        color_cls = "text-[var(--up)]" if "+" in d['change'] else ("text-[var(--down)]" if "-" in d['change'] else "text-[var(--ink-quiet)]")
        ticker_spans.append(f'<span class="inline-flex items-center gap-1.5"><span class="font-bold text-[var(--ink)]">{d["asset"]}:</span> <span class="text-[var(--ink-body)]">{d["price"]}</span> <span class="{color_cls} font-semibold">{d["change"]}</span></span>')
    ticker_html = ' '.join(ticker_spans) + ' ' + ' '.join(ticker_spans)

    # Top Story Image Resolution
    top_url = data['top_story']['sources'][0]['url'] if data['top_story'].get('sources') else ''
    top_img, top_category = resolve_image(top_url, data['top_story'].get('title', ''), 'ΟΙΚΟΝΟΜΙΑ & ΑΞΙΟΧΡΕΟ')

    # House Search Nav Button & Card
    house_nav_html = ""
    house_card_html = ""
    if house_stats and house_stats.get('local_url'):
        house_nav_html = f'''<a href="{house_stats['local_url']}" target="_blank" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition font-medium flex items-center gap-1">🏠 <span>Ακίνητα</span></a>'''
        house_card_html = f'''
        <div class="card p-5 border-l-4 border-[var(--accent)] mb-6">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
            <span class="t-meta font-bold uppercase tracking-wider text-[var(--accent)] flex items-center gap-1.5">
              <span>🏠</span> REAL ESTATE RADAR — ΕΒΔΟΜΑΔΙΑΙΟ ΔΕΛΤΙΟ ΛΕΜΕΣΟΥ
            </span>
            <span class="t-meta font-mono text-[var(--ink-quiet)]">Έκδοση: {house_stats['date']}</span>
          </div>
          <p class="t-body-sm text-[var(--ink-body)] mb-3 leading-relaxed">
            Εντοπίστηκαν <strong>{house_stats['unique_properties']} μοναδικά ακίνητα</strong> (Bazaraki & BuySellCyprus) στον άξονα Ύψωνα → Γερμασόγειας. 
            <strong>{house_stats['top_picks_count']} Top Picks</strong> πέρασαν όλα τα φίλτρα: {house_stats['top_pick_highlights']}.
          </p>
          <a href="{house_stats['local_url']}" target="_blank" class="inline-flex items-center gap-1.5 t-meta font-bold text-[var(--accent)] hover:underline">
            <span>Άνοιγμα πλήρους εβδομαδιαίας έκθεσης ακινήτων</span> <span>➔</span>
          </a>
        </div>
        '''

    # Cyprus Cards with Images, Editorial Hierarchy & Real Depth
    cyprus_cards = []
    for idx, item in enumerate(data['cyprus'], 1):
        item_url = item['source']['url'] if item.get('source') else ''
        img_url, cat_name = resolve_image(item_url, item['title'], 'ΚΥΠΡΟΣ')

        is_lead = (idx == 1)
        is_p6 = (item['is_portfolio'] or idx == 6)

        if is_lead:
            card_cls = "card md:col-span-2 overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-64 sm:h-72"
            title_cls = "t-lead mb-3"
            body_cls = "t-body mb-4"
        else:
            p6_border = "border-l-4 border-[var(--accent)]" if is_p6 else ""
            card_cls = f"card {p6_border} overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-44"
            title_cls = "t-title mb-2.5"
            body_cls = "t-body-sm mb-3"

        if is_p6:
            cat_name = "Ο ΦΑΚΕΛΟΣ ΜΟΥ"
            cat_badge_cls = "bg-[var(--accent)] text-white"
        else:
            cat_badge_cls = "bg-[var(--ink)]/85 text-white"

        tag_cls = "bg-[var(--up)] text-white" if item['tag'] == 'Επιβεβαιωμένο' else ("bg-[var(--accent)] text-white" if item['tag'] == 'Εξελισσόμενο' else "bg-[var(--rule-strong)] text-white")

        why_html = f'''
        <div class="t-meta text-[var(--accent)] bg-[var(--paper)] p-3 rounded mb-3 border-l-2 border-[var(--accent)]">
          <strong class="font-bold">Γιατί με αφορά:</strong> {item["why"]}
        </div>''' if item.get('why') else ''

        src_html = f'''
        <div class="flex justify-between items-center t-meta pt-3 border-t border-[var(--rule)]">
          <a href="{item["source"]["url"]}" target="_blank" rel="noopener noreferrer" class="font-semibold text-[var(--accent)] hover:underline">
            {item["source"]["name"]}
          </a>
          <span class="font-mono text-[var(--ink-quiet)]">{item['tag']}</span>
        </div>''' if item.get('source') else ''

        depth_html = render_depth_html(item.get('depth', {}), is_world=False)

        cyprus_cards.append(f'''
        <article class="{card_cls}">
          <div>
            <div class="{img_h_cls} bg-[var(--paper)] relative overflow-hidden">
              <img src="{img_url}" alt="{item['title']}" class="w-full h-full object-cover" onerror="this.onerror=null; this.src='{TOPIC_FALLBACKS['general']}';">
              <span class="absolute top-2.5 left-2.5 {cat_badge_cls} t-meta px-2 py-0.5 rounded shadow-xs">{cat_name}</span>
              <span class="absolute top-2.5 right-2.5 {tag_cls} t-meta px-2 py-0.5 rounded shadow-xs">{item['tag']}</span>
            </div>
            <div class="p-5 sm:p-6">
              <h3 class="{title_cls}">
                {item['title']}
              </h3>
              <p class="{body_cls} leading-relaxed">
                {item['body']}
              </p>
              {why_html}
            </div>
          </div>
          <div class="p-5 sm:p-6 pt-0">
            {depth_html}
            {src_html}
          </div>
        </article>
        ''')
    cyprus_cards_html = '\n'.join(cyprus_cards)

    # World Cards with Images, Editorial Hierarchy & Real Depth
    world_cards = []
    for idx, item in enumerate(data['world'], 1):
        item_url = item['source']['url'] if item.get('source') else ''
        img_url, cat_name = resolve_image(item_url, item['title'], 'ΔΙΕΘΝΗ')

        is_lead = (idx == 1)
        if is_lead:
            card_cls = "card md:col-span-2 overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-64 sm:h-72"
            title_cls = "t-lead mb-3"
            body_cls = "t-body mb-4"
        else:
            card_cls = "card overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-44"
            title_cls = "t-title mb-2.5"
            body_cls = "t-body-sm mb-3"

        tag_cls = "bg-[var(--up)] text-white" if item['tag'] == 'Επιβεβαιωμένο' else ("bg-[var(--accent)] text-white" if item['tag'] == 'Εξελισσόμενο' else "bg-[var(--rule-strong)] text-white")

        src_html = f'''
        <div class="flex justify-between items-center t-meta pt-3 border-t border-[var(--rule)]">
          <a href="{item["source"]["url"]}" target="_blank" rel="noopener noreferrer" class="font-semibold text-[var(--accent)] hover:underline">
            {item["source"]["name"]}
          </a>
          <span class="font-mono text-[var(--ink-quiet)]">{item['tag']}</span>
        </div>''' if item.get('source') else ''

        depth_html = render_depth_html(item.get('depth', {}), is_world=True)

        world_cards.append(f'''
        <article class="{card_cls}">
          <div>
            <div class="{img_h_cls} bg-[var(--paper)] relative overflow-hidden">
              <img src="{img_url}" alt="{item['title']}" class="w-full h-full object-cover" onerror="this.onerror=null; this.src='{TOPIC_FALLBACKS['diplomacy']}';">
              <span class="absolute top-2.5 left-2.5 bg-[var(--ink)]/85 text-white t-meta px-2 py-0.5 rounded shadow-xs">{cat_name}</span>
              <span class="absolute top-2.5 right-2.5 {tag_cls} t-meta px-2 py-0.5 rounded shadow-xs">{item['tag']}</span>
            </div>
            <div class="p-5 sm:p-6">
              <h3 class="{title_cls}">
                {item['title']}
              </h3>
              <p class="{body_cls} leading-relaxed">
                {item['body']}
              </p>
            </div>
          </div>
          <div class="p-5 sm:p-6 pt-0">
            {depth_html}
            {src_html}
          </div>
        </article>
        ''')
    world_cards_html = '\n'.join(world_cards)

    # Markets Movers HTML
    movers_cards = []
    for item in data['markets']:
        src_html = f'<a href="{item["source"]["url"]}" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-semibold t-meta ml-auto">{item["source"]["name"]}</a>' if item.get('source') else ''
        hdr = item['header']
        icon = '📈' if '+' in hdr else ('📉' if '-' in hdr else '📊')
        badge_cls = "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30" if '+' in hdr else ("bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/30" if '-' in hdr else "bg-[var(--rule)]/40 text-[var(--ink)]")
        movers_cards.append(f'''
        <div class="card p-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="text-lg">{icon}</span>
              <span class="t-meta px-2 py-0.5 rounded font-mono font-bold {badge_cls}">
                {hdr.split('(')[-1].replace(')', '') if '(' in hdr and '%' in hdr else 'MOVER'}
              </span>
            </div>
            <div class="t-num font-mono font-bold text-sm sm:text-base text-[var(--ink)] mb-1">
              {hdr}
            </div>
            <p class="t-body-sm text-[var(--ink-body)] leading-relaxed mb-2">
              <strong class="text-[var(--ink)]">Αιτία:</strong> {item['cause']}
            </p>
          </div>
          <div class="flex items-center justify-end border-t border-[var(--rule)] pt-2 mt-2">
            {src_html}
          </div>
        </div>
        ''')
    movers_html = '\n'.join(movers_cards)

    # Dashboard rows with asset icons
    dash_rows = []
    asset_icons = {
        's&p': '📊', 'eur/usd': '💶', 'brent': '🛢️', 'gold': '🪙', 'χρυσός': '🪙',
        'bitcoin': '₿', 'treasury': '📑', 'euribor': '⚡'
    }
    for d in data['dashboard']:
        change_cls = "text-[var(--up)] font-bold" if "+" in d['change'] else ("text-[var(--down)] font-bold" if "-" in d['change'] else "text-[var(--ink-quiet)]")
        icon = '📈' if "+" in d['change'] else ('📉' if "-" in d['change'] else '⏺️')
        a_low = d['asset'].lower()
        a_icon = '🔹'
        for k, ico in asset_icons.items():
            if k in a_low:
                a_icon = ico
                break
        dash_rows.append(f'''
        <tr>
          <td class="py-2.5 font-semibold text-[var(--ink)] font-sans flex items-center gap-2">
            <span>{a_icon}</span> <span>{d['asset']}</span>
          </td>
          <td class="py-2.5 text-[var(--ink-body)] font-mono">{d['price']}</td>
          <td class="py-2.5 {change_cls} font-mono">
            <span class="inline-flex items-center gap-1">{icon} {d['change']}</span>
          </td>
          <td class="py-2.5 text-[var(--ink-quiet)] t-meta">{d['date_ref']}</td>
        </tr>
        ''')
    dash_rows_html = '\n'.join(dash_rows)

    # Mortgage-calculator seeds: taken from the parsed loan terms so the
    # sliders open on the same figures the rates box states. The 200k/25y/CBC
    # values below are only the slider's starting position when the edition
    # omits the terms — the displayed instalment stays "—" in that case.
    rates = data['rates']
    calc_amount = int(rates['loan_amount']) if rates['loan_amount'] else 200000
    calc_years = int(rates['loan_years']) if rates['loan_years'] else 25
    calc_rate = rates['loan_rate'] if rates['loan_rate'] is not None else 3.5
    calc_amount_label = format_euro(calc_amount)
    calc_rate_label = f"{calc_rate:.2f}".replace('.', ',') + '%'
    if rates['example_payment']:
        example_line = (f"{calc_amount_label} / {calc_years} έτη με επιτόκιο "
                        f"{calc_rate_label} → {rates['example_payment']} τον μήνα "
                        f"({dash(rates['example_change'])})")
    else:
        example_line = '—'

    # Euribor rows
    euribor_rows = []
    for er in data['rates']['euribor']:
        euribor_rows.append(f'''
        <tr>
          <td class="py-2.5 font-semibold text-[var(--ink)] font-sans">{er['period']}</td>
          <td class="py-2.5 text-center text-[var(--ink-body)]">{er['1m']}</td>
          <td class="py-2.5 text-center font-bold text-[var(--accent)]">{er['3m']}</td>
          <td class="py-2.5 text-center text-[var(--ink-body)]">{er['6m']}</td>
          <td class="py-2.5 text-center text-[var(--ink-body)]">{er['12m']}</td>
        </tr>
        ''')
    euribor_rows_html = '\n'.join(euribor_rows)

    # Stadium-Grade Executive Sports Cards
    SPORTS_META = {
        'omonoia': {
            'name': 'ΟΜΟΝΟΙΑ ΛΕΥΚΩΣΙΑΣ',
            'badge': 'CYPRUS LEAGUE & EUROPA LEAGUE',
            'icon': '☘️',
            'gradient': 'from-emerald-900 via-green-900 to-emerald-950',
            'border_cls': 'border-emerald-800/40 dark:border-emerald-700/50',
            'badge_bg': 'bg-emerald-950/70 text-emerald-200 border border-emerald-500/30',
            'default_hl_query': 'Omonoia+FC+highlights+2026',
            'default_source': {'name': 'OmonoiaFC.com.cy', 'url': 'https://www.omonoiafc.com.cy/'}
        },
        'manutd': {
            'name': 'MANCHESTER UNITED',
            'badge': 'PREMIER LEAGUE',
            'icon': '🔴',
            'gradient': 'from-red-950 via-zinc-950 to-black',
            'border_cls': 'border-red-900/40 dark:border-red-800/50',
            'badge_bg': 'bg-red-950/70 text-red-200 border border-red-500/30',
            'default_hl_query': 'Manchester+United+highlights+2026',
            'default_source': {'name': 'ManUtd.com', 'url': 'https://www.manutd.com/'}
        },
        'realmadrid': {
            'name': 'REAL MADRID',
            'badge': 'LA LIGA & CHAMPIONS LEAGUE',
            'icon': '👑',
            'gradient': 'from-slate-950 via-blue-950 to-indigo-950',
            'border_cls': 'border-blue-900/40 dark:border-blue-800/50',
            'badge_bg': 'bg-blue-950/70 text-blue-200 border border-blue-500/30',
            'default_hl_query': 'Real+Madrid+highlights+2026',
            'default_source': {'name': 'RealMadrid.com', 'url': 'https://www.realmadrid.com/'}
        },
        'formula1': {
            'name': 'FORMULA 1',
            'badge': 'FIA WORLD CHAMPIONSHIP',
            'icon': '🏎️',
            'gradient': 'from-neutral-950 via-zinc-900 to-red-950',
            'border_cls': 'border-red-900/40 dark:border-red-800/50',
            'badge_bg': 'bg-red-950/70 text-red-200 border border-red-500/30',
            'default_hl_query': 'Formula+1+highlights+2026',
            'default_source': {'name': 'Formula1.com', 'url': 'https://www.formula1.com/'}
        }
    }

    def build_sport_card(key, team_data):
        meta = SPORTS_META.get(key, {})
        last_res = team_data.get('last_result', '')
        nxt_match = team_data.get('next_match', '')
        hl_info = team_data.get('highlights')
        news_items = team_data.get('news', [])
        src_info = team_data.get('source') or meta.get('default_source')

        # 1. Scoreboard Box
        scoreboard_html = ""
        if last_res:
            if key == 'formula1':
                m_gp = re.search(r'\*\*([^*]+Grand Prix[^*]*)\*\*', last_res, re.I)
                gp_title = m_gp.group(1).strip() if m_gp else 'Italian Grand Prix 2026 (Monza)'
                scoreboard_html = f'''
                <div class="bg-[var(--paper)] border border-[var(--rule)] rounded-2xl p-5 mb-6 shadow-xs">
                  <div class="flex items-center justify-between text-xs font-mono text-[var(--ink-quiet)] uppercase mb-2.5">
                    <span class="flex items-center gap-2 font-bold">🏁 ΤΕΛΕΥΤΑΙΟ GRAND PRIX</span>
                    <span class="px-2.5 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-950/70 dark:text-red-300 font-bold">MONZA</span>
                  </div>
                  <div class="text-base sm:text-lg font-bold text-[var(--ink)] font-sans mb-2.5">{gp_title}</div>
                  <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-600/10 dark:bg-red-500/15 border border-red-500/30 text-xs sm:text-sm font-mono font-bold text-red-700 dark:text-red-300 mb-3">
                    <span>🏆</span> <span>P1 Antonelli · P2 Russell · P3 Verstappen</span>
                  </div>
                  <p class="text-sm text-[var(--ink-body)] leading-relaxed">
                    {md_to_inline_html(last_res)}
                  </p>
                </div>'''
            else:
                score_m = re.search(r'\b(\d+)\s*[-–]\s*(\d+)\b', last_res)
                score_str = f"{score_m.group(1)} – {score_m.group(2)}" if score_m else "FT"
                first_part = last_res.split('(')[0].replace('**', '').strip()
                fixture = re.sub(r'\s*\b\d+\s*[-–]\s*\d+\b\s*', '', first_part).strip(' –-')
                fixture = re.sub(r'\s*–\s*', ' vs ', fixture)
                scoreboard_html = f'''
                <div class="bg-[var(--paper)] border border-[var(--rule)] rounded-2xl p-5 mb-6 shadow-xs">
                  <div class="flex items-center justify-between text-xs font-mono text-[var(--ink-quiet)] uppercase mb-2.5">
                    <span class="flex items-center gap-2 font-bold">⚽ ΤΕΛΕΥΤΑΙΟ ΑΠΟΤΕΛΕΣΜΑ</span>
                    <span class="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300 font-bold">FT</span>
                  </div>
                  <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <div class="text-base sm:text-lg font-bold text-[var(--ink)]">{fixture}</div>
                    <div class="px-3.5 py-1.5 rounded-xl bg-slate-900 text-amber-400 font-mono font-black text-lg tracking-wider shadow-inner">
                      {score_str}
                    </div>
                  </div>
                  <p class="text-sm text-[var(--ink-body)] leading-relaxed">
                    {md_to_inline_html(last_res)}
                  </p>
                </div>'''

        # 2. YouTube Highlights Card
        if hl_info and hl_info.get('url'):
            hl_url = hl_info['url']
            hl_title = hl_info['title']
        else:
            hl_url = f"https://www.youtube.com/results?search_query={meta.get('default_hl_query', 'sports+highlights')}"
            hl_title = f"Δείτε τα Highlights ({meta.get('name')})"

        highlights_html = f'''
        <a href="{hl_url}" target="_blank" rel="noopener noreferrer" 
           class="group flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-red-600/10 via-red-600/5 to-transparent hover:from-red-600/20 hover:to-red-600/15 border border-red-500/30 hover:border-red-500/50 transition-all duration-200 mb-6 shadow-xs">
          <div class="flex items-center gap-3.5 min-w-0 flex-1">
            <span class="w-10 h-10 flex-shrink-0 rounded-xl bg-red-600 text-white flex items-center justify-center font-bold text-base shadow-sm group-hover:scale-110 transition-transform">
              ▶
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-xs font-mono uppercase tracking-wider text-red-600 dark:text-red-400 font-bold flex items-center gap-1.5">
                <span>🎬 YOUTUBE HIGHLIGHTS</span>
                <span class="text-[9px] px-1.5 py-0.2 rounded bg-red-600 text-white font-semibold">HD</span>
              </div>
              <div class="text-sm font-semibold text-[var(--ink)] group-hover:text-red-600 dark:group-hover:text-red-400 mt-1 break-words">
                {hl_title}
              </div>
            </div>
          </div>
          <span class="text-base text-red-600 dark:text-red-400 font-bold group-hover:translate-x-1.5 transition-transform ml-3 flex-shrink-0">↗</span>
        </a>'''

        # 3. Next Match / Grand Prix
        next_match_html = ""
        if nxt_match:
            lbl = "🏁 ΕΠΟΜΕΝΟ GRAND PRIX" if key == 'formula1' else "📅 ΕΠΟΜΕΝΟΣ ΑΓΩΝΑΣ"
            next_match_html = f'''
            <div class="p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] mb-6 shadow-xs">
              <div class="text-xs font-mono text-[var(--ink-quiet)] uppercase tracking-wider mb-2 flex items-center gap-1.5 font-bold">
                {lbl}
              </div>
              <div class="text-sm sm:text-base font-semibold text-[var(--ink)] leading-relaxed">
                {md_to_inline_html(nxt_match)}
              </div>
            </div>'''

        # 4. News & Squad Report
        news_html = ""
        if news_items:
            bullets = ''.join([f'<li class="leading-relaxed pl-1">{md_to_inline_html(n)}</li>' for n in news_items if n and n not in ['--', '---']])
            news_html = f'''
            <div class="mb-6">
              <div class="text-xs font-mono text-[var(--ink-quiet)] uppercase tracking-wider mb-3 font-bold flex items-center gap-2">
                <span>📋</span> <span>ΑΓΩΝΙΣΤΙΚΑ ΝΕΑ & ΡΕΠΟΡΤΑΖ</span>
              </div>
              <ul class="text-sm text-[var(--ink-body)] space-y-3 list-disc list-inside leading-relaxed">
                {bullets}
              </ul>
            </div>'''

        # Fallback raw list if neither scoreboard nor next match
        fallback_raw = ""
        if not scoreboard_html and not next_match_html and team_data.get('raw'):
            raw_bullets = ''.join([f'<li class="leading-relaxed pl-1">{md_to_inline_html(r)}</li>' for r in team_data['raw'] if r and r not in ['--', '---']])
            fallback_raw = f'<ul class="text-sm text-[var(--ink-body)] space-y-3 list-disc list-inside mb-6">{raw_bullets}</ul>'

        # 5. Source
        src_url = src_info.get('url', '#') if src_info else '#'
        src_name = src_info.get('name', 'Επίσημη Πηγή') if src_info else 'Επίσημη Πηγή'
        source_html = f'''
        <div class="pt-4 border-t border-[var(--rule)] mt-auto flex items-center justify-between t-meta">
          <span class="text-[var(--ink-quiet)] font-mono flex items-center gap-1.5">
            <span>🌐</span> <span>Επίσημο Κανάλι:</span>
          </span>
          <a href="{src_url}" target="_blank" rel="noopener noreferrer" class="font-semibold text-[var(--accent)] hover:underline">
            {src_name}
          </a>
        </div>'''

        return f'''
        <article class="card overflow-hidden flex flex-col justify-between border rounded-2xl shadow-sm {meta.get('border_cls', '')}">
          <div>
            <!-- Header -->
            <div class="bg-gradient-to-r {meta.get('gradient', 'from-slate-900 to-black')} p-5 sm:p-6 text-white">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                  <span class="text-3xl sm:text-4xl">{meta.get('icon', '⚽')}</span>
                  <h3 class="font-masthead font-bold text-base sm:text-lg tracking-wide text-white">{meta.get('name', key.upper())}</h3>
                </div>
                <span class="t-meta uppercase tracking-wider px-3 py-1 rounded-full text-xs {meta.get('badge_bg', 'bg-white/10 text-white/90')}">
                  {meta.get('badge', '')}
                </span>
              </div>
            </div>

            <!-- Content with generous spacing -->
            <div class="p-6 sm:p-7 lg:p-8">
              {scoreboard_html}
              {highlights_html}
              {next_match_html}
              {news_html}
              {fallback_raw}
            </div>
          </div>

          <div class="p-6 sm:p-7 lg:p-8 pt-0">
            {source_html}
          </div>
        </article>
        '''

    sports_cards_html = '\n'.join([
        build_sport_card('omonoia', data['sports'].get('omonoia', {})),
        build_sport_card('manutd', data['sports'].get('manutd', {})),
        build_sport_card('realmadrid', data['sports'].get('realmadrid', {})),
        build_sport_card('formula1', data['sports'].get('formula1', {}))
    ])

    # Weather narrative with rich emojis & badges (never showing -- separators)
    wx_formatted_items = []
    for raw in data['weather'].get('raw_items', []):
        if not raw or raw.strip() in ['--', '---'] or raw.startswith('---'):
            continue
        icon = '🌤️'
        low = raw.lower()
        if 'θερμοκρασία' in low:
            icon = '🌡️'
        elif 'υγρασία' in low:
            icon = '💧'
        elif 'άνεμος' in low or 'ανεμοι' in low:
            icon = '💨'
        elif 'προειδοποιήσεις' in low or 'προειδοποίηση' in low or 'uv' in low:
            icon = '⚠️'
        elif 'πρόγνωση' in low or 'αίθριος' in low:
            icon = '☀️'
        elif 'πηγή' in low:
            icon = '🌐'

        m_label = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', raw)
        if m_label:
            lbl = m_label.group(1).strip()
            rest = md_to_inline_html(m_label.group(2).strip())
            is_warn = (icon == '⚠️')
            bg_cls = "bg-amber-500/10 border border-amber-500/30 dark:bg-amber-950/30" if is_warn else "bg-[var(--paper)] border border-[var(--rule)]"
            wx_formatted_items.append(f'''
            <div class="flex items-start gap-3.5 p-3.5 rounded-xl {bg_cls} shadow-2xs">
              <span class="text-xl flex-shrink-0 mt-0.5">{icon}</span>
              <div class="text-xs sm:text-sm text-[var(--ink-body)] leading-relaxed">
                <span class="font-bold text-[var(--ink)]">{lbl}:</span> {rest}
              </div>
            </div>''')
        else:
            wx_formatted_items.append(f'''
            <div class="flex items-start gap-3.5 p-3.5 rounded-xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <span class="text-xl flex-shrink-0 mt-0.5">{icon}</span>
              <div class="text-xs sm:text-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(raw)}</div>
            </div>''')
    wx_items_html = '\n'.join(wx_formatted_items)

    # Developments Cards (clean executive blocks without raw asterisks)
    dev_cards = []
    for item in data['developments']:
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', item)
        if m:
            title = m.group(1).strip()
            body = md_to_inline_html(m.group(2).strip())
            dev_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs">
              <div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-2 flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-[var(--accent)] flex-shrink-0"></span>
                <span>{title}</span>
              </div>
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{body}</p>
            </div>''')
        else:
            dev_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(item)}</p>
            </div>''')
    dev_html = '\n'.join(dev_cards)

    # Portfolio Cards
    port_cards = []
    for item in data['portfolio']:
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', item)
        if m:
            title = m.group(1).strip()
            body = md_to_inline_html(m.group(2).strip())
            port_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs">
              <div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-2 flex items-center gap-2">
                <span>🎯</span> <span>{title}</span>
              </div>
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{body}</p>
            </div>''')
        else:
            port_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(item)}</p>
            </div>''')
    port_html = '\n'.join(port_cards)

    # Deadlines Cards (actionable timeline pills with active links)
    dead_cards = []
    for item in data['deadlines']:
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*\s*[—–-]\s*(.*)$', item)
        if m:
            date_str = m.group(1).strip()
            rest_str = m.group(2).strip()
            m_act = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', rest_str)
            if m_act:
                act_title = m_act.group(1).strip()
                det_body = md_to_inline_html(m_act.group(2).strip())
            else:
                act_title = ""
                det_body = md_to_inline_html(rest_str)
            
            dead_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs flex flex-col justify-between">
              <div>
                <div class="flex items-center justify-between gap-2 mb-2.5">
                  <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-[var(--accent)]/15 text-[var(--accent)] border border-[var(--accent)]/30">
                    <span>📅</span> <span>{date_str}</span>
                  </span>
                  <span class="t-meta text-[var(--ink-quiet)] uppercase font-mono font-semibold">ΠΡΟΘΕΣΜΙΑ</span>
                </div>
                {f'<div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-1.5">{act_title}</div>' if act_title else ''}
                <div class="t-body-sm text-[var(--ink-body)] leading-relaxed">{det_body}</div>
              </div>
            </div>''')
        else:
            dead_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <div class="t-body-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(item)}</div>
            </div>''')
    dead_html = '\n'.join(dead_cards)

    # Tomorrow Cards (numbered executive agenda points)
    tom_cards = []
    for idx, item in enumerate(data['tomorrow']):
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', item)
        if m:
            title = m.group(1).strip()
            desc = md_to_inline_html(m.group(2).strip())
            tom_cards.append(f'''
            <div class="flex items-start gap-4 p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs">
              <div class="w-9 h-9 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent)] flex items-center justify-center font-mono font-black text-sm flex-shrink-0">
                {idx+1:02d}
              </div>
              <div class="flex-1 min-w-0">
                <div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-1">{title}</div>
                <div class="t-body-sm text-[var(--ink-body)] leading-relaxed">{desc}</div>
              </div>
            </div>''')
        else:
            tom_cards.append(f'''
            <div class="flex items-start gap-4 p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <div class="w-9 h-9 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent)] flex items-center justify-center font-mono font-black text-sm flex-shrink-0">
                {idx+1:02d}
              </div>
              <div class="t-body-sm text-[var(--ink-body)] leading-relaxed flex-1 min-w-0">{md_to_inline_html(item)}</div>
            </div>''')
    tom_html = '\n'.join(tom_cards)

    # Footnotes. Any authored sentence claiming the links were verified is
    # dropped: only check-links.py's own report may make that claim.
    foot_items = []
    for item in data['footnotes']:
        if not item or item in ['--', '---'] or item.startswith('---'):
            continue
        if LINK_CLAIM_RE.search(item):
            warn("Το markdown ισχυρίζεται έλεγχο συνδέσμων· η πρόταση "
                 "αντικαταστάθηκε από την πραγματική αναφορά του check-links.py.")
            continue
        foot_items.append(item)
    foot_items.append(data['link_check_footnote'])
    foot_html = ''.join([f'<li class="leading-relaxed">{md_to_inline_html(item)}</li>'
                         for item in foot_items])

    # Top Story Source Links
    top_sources = []
    for s in data['top_story'].get('sources', []):
        top_sources.append(f'<a href="{s["url"]}" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-semibold">{s["name"]}</a>')
    top_sources_html = ' · '.join(top_sources)

    # Full HTML Document
    # Every value the template needs. Presentation lives in
    # scripts/templates/edition.html; this function only prepares data.
    context = {
        'calc_amount': calc_amount,
        'calc_amount_label': calc_amount_label,
        'calc_rate': calc_rate,
        'calc_rate_label': calc_rate_label,
        'calc_years': calc_years,
        'cbc_mortgage_rate': dash(data['rates']['cbc_mortgage_rate']),
        'cyprus_cards_html': cyprus_cards_html,
        'dash_rows_html': dash_rows_html,
        'date_display': date_display,
        'dead_html': dead_html,
        'dev_html': dev_html,
        'ecb_rate': dash(data['rates']['ecb_rate']),
        'euribor_rows_html': euribor_rows_html,
        'example_line': example_line,
        'example_payment': dash(data['rates']['example_payment']),
        'example_total_interest': dash(data['rates']['example_total_interest']),
        'fallback_economy_img': TOPIC_FALLBACKS['economy'],
        'foot_html': foot_html,
        'gen_iso': gen_iso,
        'house_card_html': house_card_html,
        'house_nav_html': house_nav_html,
        'movers_html': movers_html,
        'next_ecb': dash(data['rates']['next_ecb']),
        'number_of_day_number': data['number_of_day'].get('number', '—'),
        'number_of_day_text': data['number_of_day'].get('text', ''),
        'port_html': port_html,
        'read_time': read_time,
        'search_index_json': json.dumps(search_index, ensure_ascii=False),
        'sports_cards_html': sports_cards_html,
        'ticker_html': ticker_html,
        'time_display': time_display,
        'tom_html': tom_html,
        'top_category': top_category,
        'top_img': top_img,
        'top_sources_html': top_sources_html,
        'top_story_antilogos': data['top_story'].get('antilogos', 'Δεν καταγράφηκε ουσιαστικός αντίλογος.'),
        'top_story_body': data['top_story'].get('body', ''),
        'top_story_title': data['top_story'].get('title', ''),
        'world_cards_html': world_cards_html,
        'wx_items_html': wx_items_html,
    }
    html = render_template(context)
    return html


def main():
    target_md = None
    if len(sys.argv) > 1:
        target_md = os.path.abspath(sys.argv[1])
    else:
        target_md = find_latest_briefing()

    if not os.path.exists(target_md):
        print(f"Error: Target briefing markdown file does not exist: {target_md}")
        sys.exit(1)

    print(f"Reading briefing: {target_md}")
    with open(target_md, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    filename = os.path.basename(target_md)
    m_date = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    date_slug = m_date.group(1) if m_date else datetime.now().strftime('%Y-%m-%d')

    data = parse_markdown(content)
    data['link_check_footnote'] = link_check_footnote(date_slug)
    house_stats = get_latest_house_search()
    if house_stats:
        print(f"Linked House Search from: {house_stats['date']} ({house_stats['unique_properties']} properties)")

    print("Building cross-edition search index...")
    search_index = build_search_index()
    print(f"Indexed {len(search_index)} items across editions.")

    html_content = render_html(data, house_stats, search_index)

    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(DOCS_BRIEFINGS_DIR, exist_ok=True)

    # docs/ is the single published tree (GitHub Pages source). The dated copy
    # is the permanent archive URL; index.html is the "latest edition" alias.
    docs_index = os.path.join(DOCS_DIR, 'index.html')
    docs_briefing_html = os.path.join(DOCS_BRIEFINGS_DIR, f'{date_slug}.html')
    docs_briefing_md = os.path.join(DOCS_BRIEFINGS_DIR, f'{date_slug}.md')

    for path in [docs_index, docs_briefing_html]:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Generated: {path}")

    shutil.copy2(target_md, docs_briefing_md)
    print(f"Copied markdown to docs: {docs_briefing_md}")

    if BUILD_WARNINGS:
        print("\n" + "!" * 70)
        print(f"!! {len(BUILD_WARNINGS)} BUILD WARNING(S) — τιμές που ΔΕΝ βρέθηκαν στο markdown")
        print("!! Η έκδοση δημοσιεύεται με «—» στη θέση τους. Διορθώστε το markdown.")
        print("!" * 70)
        for w in BUILD_WARNINGS:
            print(f"  - {w}")
        print("!" * 70 + "\n")

    print("\nSUCCESS! The Oracle Sovereign web portal and archives have been built with full news-first layout and imagery.")


if __name__ == '__main__':
    main()
