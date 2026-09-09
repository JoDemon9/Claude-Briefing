#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — live market data

Every market figure in an edition has to come from somewhere real. This
fetches quotes from Yahoo Finance's chart endpoint and can check an edition's
published numbers against them.

    python scripts/fetch-markets.py --table          # markdown DASHBOARD block
    python scripts/fetch-markets.py --json           # machine-readable
    python scripts/fetch-markets.py --check <md>     # drift vs the edition

A quote that cannot be fetched is reported as unavailable and rendered "—".
It is never replaced by a placeholder: a fabricated 0,00% is indistinguishable
from a real flat close once it is on the page.

--check exits non-zero when a published figure drifts past --tolerance
(default 3%), which catches a stale number carried over from a previous
edition or a mistyped one. Symbols with no mapping are reported as
unverifiable — neither a pass nor a failure.
"""

import os
import re
import ssl
import sys
import json
import argparse
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

TIMEOUT = 15
WORKERS = 8
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# TLS is verified. The previous verifier in this repo set CERT_NONE, which
# turns a hijacked or expired-certificate response into a silent pass.
SSL_CTX = ssl.create_default_context()

# The standing dashboard. Order is the order of the emitted table.
DASHBOARD = [
    ('S&P 500', '^GSPC'),
    ('Nasdaq Composite', '^IXIC'),
    ('VIX', '^VIX'),
    ('US 10Y', '^TNX'),
    ('EUR/USD', 'EURUSD=X'),
    ('Brent Crude', 'BZ=F'),
    ('WTI Crude', 'CL=F'),
    ('Bitcoin (BTC)', 'BTC-USD'),
    ('Ethereum (ETH)', 'ETH-USD'),
]

# Names and short tickers an edition may use, mapped to Yahoo symbols.
ALIASES = {
    'sp 500': '^GSPC', 's&p 500': '^GSPC', 'gspc': '^GSPC',
    'nasdaq composite': '^IXIC', 'nasdaq': '^IXIC', 'ixic': '^IXIC',
    'vix': '^VIX', 'cboe volatility index': '^VIX',
    'us 10y': '^TNX', 'us 10y yield': '^TNX', 'tnx': '^TNX',
    'eur/usd': 'EURUSD=X', 'eurusd': 'EURUSD=X',
    'brent crude': 'BZ=F', 'brent': 'BZ=F',
    'wti crude': 'CL=F', 'wti': 'CL=F',
    'bitcoin': 'BTC-USD', 'btc': 'BTC-USD',
    'ethereum': 'ETH-USD', 'eth': 'ETH-USD',
    'gold': 'GC=F', 'silver': 'SI=F',
}

# Quoted in %, so the "price" is already a percentage. ^VIX is not one of
# them: it is an index level, and the editions print it as a bare number.
PERCENT_SYMBOLS = {'^TNX'}
DOLLAR_SYMBOLS = {'BZ=F', 'CL=F', 'BTC-USD', 'ETH-USD', 'GC=F', 'SI=F'}


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------

def format_greek(value, decimals=2):
    """1234.5 -> '1.234,50'; -0.16 -> '-0,16'; None -> '—'.

    The sign is applied to the formatted magnitude. Formatting the integer
    part alone loses it for every value between -1 and 0 — exactly the range
    a daily index move falls in, so a loss would print as flat.
    """
    if value is None:
        return '—'
    sign = '-' if value < 0 else ''
    body = f"{abs(value):,.{decimals}f}"
    body = body.replace(',', '\x00').replace('.', ',').replace('\x00', '.')
    return sign + body


def format_price(symbol, value):
    if value is None:
        return '—'
    if symbol in PERCENT_SYMBOLS:
        return format_greek(value, 3) + '%'
    prefix = '$' if symbol in DOLLAR_SYMBOLS else ''
    decimals = 4 if symbol.endswith('=X') else 2
    return prefix + format_greek(value, decimals)


def format_change(value):
    if value is None:
        return '—'
    sign = '+' if value > 0 else ''
    return sign + format_greek(value, 2) + '%'


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch_quote(symbol):
    """Live quote for one symbol. Missing fields stay None."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?interval=1d&range=5d")
    quote = {'symbol': symbol, 'price': None, 'previous_close': None,
             'change_pct': None, 'currency': None, 'error': None}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as r:
            meta = json.loads(r.read().decode('utf-8'))['chart']['result'][0]['meta']
    except urllib.error.HTTPError as e:
        quote['error'] = f'HTTP {e.code}'
        return quote
    except Exception as e:
        quote['error'] = f'{type(e).__name__}: {e}'
        return quote

    price = meta.get('regularMarketPrice')
    prev = meta.get('chartPreviousClose') or meta.get('previousClose')
    if price is None:
        quote['error'] = 'no price in response'
        return quote

    quote['price'] = price
    quote['currency'] = meta.get('currency')
    if prev:
        quote['previous_close'] = prev
        quote['change_pct'] = (price - prev) / prev * 100.0
    return quote


def fetch_all(symbols):
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return {q['symbol']: q for q in pool.map(fetch_quote, symbols)}


# --------------------------------------------------------------------------
# Reading an edition
# --------------------------------------------------------------------------

def parse_greek_number(raw):
    """'7.673,52' / '$78.762,29' / '-0,16%' -> float, or None."""
    if raw is None:
        return None
    txt = re.sub(r'[^\d.,\-]', '', str(raw))
    if not txt or txt in ('-', '.', ','):
        return None
    neg = txt.startswith('-')
    txt = txt.lstrip('-')
    if '.' in txt and ',' in txt:
        txt = txt.replace('.', '').replace(',', '.')
    elif ',' in txt:
        txt = txt.replace(',', '.')
    elif txt.count('.') == 1 and len(txt.split('.')[1]) == 3:
        txt = txt.replace('.', '')
    try:
        return -float(txt) if neg else float(txt)
    except ValueError:
        return None


def resolve_symbol(label):
    """Yahoo symbol for an edition's asset label, or None if unmapped."""
    label = label.replace('**', '').strip()
    paren = re.search(r'\(([^)]+)\)\s*$', label)
    if paren:
        inner = paren.group(1).strip()
        if re.fullmatch(r'[\^A-Z][A-Z0-9.=^\-]{0,9}', inner):
            if inner in {s for _n, s in DASHBOARD} or '=' in inner or inner.startswith('^'):
                return inner
            if inner.lower() in ALIASES:
                return ALIASES[inner.lower()]
        label = label[:paren.start()].strip()
    return ALIASES.get(label.lower())


def read_edition_figures(md_path):
    """[(label, published_price, published_change)] from DASHBOARD and ΑΓΟΡΕΣ."""
    with open(md_path, 'r', encoding='utf-8', errors='replace') as f:
        md = f.read()
    figures = []

    dash = re.search(r'##[^\n]*DASHBOARD([\s\S]*?)(?=\n##\s|\Z)', md)
    if dash:
        for row in dash.group(1).splitlines():
            row = row.strip()
            if not row.startswith('|') or '---' in row:
                continue
            cols = [c.strip() for c in row.split('|')[1:-1]]
            if len(cols) >= 3 and not cols[0].startswith('Δείκτης'):
                figures.append(('DASHBOARD', cols[0].replace('**', '').strip(),
                                parse_greek_number(cols[1]),
                                parse_greek_number(cols[2])))

    movers = re.search(r'##[^\n]*ΑΓΟΡΕΣ([\s\S]*?)(?=\n##\s|\Z)', md)
    if movers:
        for line in movers.group(1).splitlines():
            m = re.match(r'^[*\-]\s+\*\*(.+?)\*\*\s*[—–-]\s*([^(]+)\(([^)]+)\)',
                         line.strip())
            if m:
                figures.append(('ΑΓΟΡΕΣ', m.group(1).strip(),
                                parse_greek_number(m.group(2)),
                                parse_greek_number(m.group(3))))
    return figures


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

def emit_table(quotes):
    today = datetime.now().strftime('%d/%m/%Y')
    print("## 📊 DASHBOARD\n")
    print("| Δείκτης / Περιουσιακό Στοιχείο | Τιμή | Μεταβολή | Ημ. αναφοράς |")
    print("| :--- | :--- | :--- | :--- |")
    missing = []
    for name, symbol in DASHBOARD:
        q = quotes.get(symbol, {})
        if q.get('error'):
            missing.append(f"{name} ({symbol}): {q['error']}")
        print(f"| **{name}** | {format_price(symbol, q.get('price'))} "
              f"| {format_change(q.get('change_pct'))} | {today} |")
    if missing:
        print("\nΔΕΝ ΑΝΑΚΤΗΘΗΚΑΝ (εμφανίζονται «—» — μην τα συμπληρώσετε με εκτίμηση):",
              file=sys.stderr)
        for m in missing:
            print(f"  !! {m}", file=sys.stderr)
        return 1
    return 0


def run_check(md_path, tolerance):
    figures = read_edition_figures(md_path)
    if not figures:
        print(f"Δεν βρέθηκαν αριθμοί αγορών στο {md_path}.", file=sys.stderr)
        return 1

    wanted, resolved = [], []
    for section, label, price, change in figures:
        symbol = resolve_symbol(label)
        resolved.append((section, label, price, change, symbol))
        if symbol:
            wanted.append(symbol)

    quotes = fetch_all(sorted(set(wanted)))

    checked = drifted = unverifiable = 0
    print(f"Σύγκριση {len(figures)} αριθμών του {os.path.basename(md_path)} "
          f"με ζωντανές τιμές (ανοχή {tolerance:.1f}%)\n")
    for section, label, price, _change, symbol in resolved:
        if not symbol:
            unverifiable += 1
            print(f"  ?  {section:<9} {label[:34]:<34} χωρίς αντιστοίχιση συμβόλου")
            continue
        q = quotes.get(symbol, {})
        if q.get('error') or q.get('price') is None:
            unverifiable += 1
            print(f"  ?  {section:<9} {label[:34]:<34} {symbol:<10} "
                  f"δεν ανακτήθηκε ({q.get('error')})")
            continue
        if price is None:
            unverifiable += 1
            print(f"  ?  {section:<9} {label[:34]:<34} {symbol:<10} "
                  f"μη αναγνώσιμη δημοσιευμένη τιμή")
            continue
        checked += 1
        live = q['price']
        diff = abs(live - price) / abs(live) * 100.0 if live else 0.0
        mark = '!!' if diff > tolerance else 'ok'
        if diff > tolerance:
            drifted += 1
        print(f"  {mark} {section:<9} {label[:34]:<34} {symbol:<10} "
              f"έκδοση {format_greek(price)} · ζωντανά {format_greek(live)} "
              f"· απόκλιση {diff:.2f}%")

    print(f"\n{checked} ελέγχθηκαν · {drifted} εκτός ανοχής · "
          f"{unverifiable} μη επαληθεύσιμα")
    if drifted:
        print(f"\nFAIL: {drifted} δημοσιευμένοι αριθμοί αποκλίνουν πάνω από "
              f"{tolerance:.1f}% από την αγορά.", file=sys.stderr)
        return 1
    print("PASS: κάθε αντιστοιχισμένος αριθμός συμφωνεί με την αγορά.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--table', action='store_true',
                    help='emit a live markdown DASHBOARD block')
    ap.add_argument('--json', action='store_true', help='emit raw quotes as JSON')
    ap.add_argument('--out', help='write the JSON to this path instead of stdout')
    ap.add_argument('--check', metavar='BRIEFING_MD',
                    help="compare an edition's published figures against live quotes")
    ap.add_argument('--tolerance', type=float, default=3.0,
                    help='allowed drift in percent for --check (default 3.0)')
    args = ap.parse_args()

    if args.check:
        if not os.path.isfile(args.check):
            print(f"Error: no such briefing: {args.check}", file=sys.stderr)
            return 2
        return run_check(args.check, args.tolerance)

    quotes = fetch_all([s for _n, s in DASHBOARD])

    if args.json or args.out:
        payload = {'fetched_at': datetime.now().replace(microsecond=0).isoformat(),
                   'quotes': quotes}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"Wrote {args.out}")
        else:
            print(text)
        return 0

    return emit_table(quotes)


if __name__ == '__main__':
    sys.exit(main())
