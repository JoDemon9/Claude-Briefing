#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Link Checker

Requests every URL in an edition's markdown and refuses to let a dead link
reach the published page. Editions used to carry the footnote «όλοι οι
σύνδεσμοι ελέγχθηκαν (200 OK)» while nothing in the pipeline had ever opened
a socket; this script is what makes that sentence true, and it writes a report
that build-html.py renders verbatim so the footnote can only ever state what
actually ran.

    python scripts/check-links.py briefings/oracle-briefing-2026-09-09.md

Exit codes:
    0  every URL resolved (blocked-by-bot-protection URLs are reported, not fatal)
    1  at least one URL is dead (404/410, DNS failure, timeout, TLS error, 5xx)
    2  bad invocation
"""

import os
import re
import ssl
import sys
import json
import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRIEFINGS_DIR = os.path.join(BASE_DIR, 'briefings')

TIMEOUT = 20
WORKERS = 8
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Bot protection is not a dead link. These are reported as unverified rather
# than failing the run, and the footnote says so rather than claiming 200 OK.
BLOCKED_STATUSES = {401, 403, 429}

SSL_CTX = ssl.create_default_context()


def extract_urls(md_text):
    """Every distinct http(s) URL in the markdown, in order of appearance."""
    urls = []
    seen = set()

    def add(u):
        u = u.strip().rstrip('.,;)')
        if u.startswith('http') and u not in seen:
            seen.add(u)
            urls.append(u)

    for url in re.findall(r'\[[^\]]*\]\(([^)\s]+)[^)]*\)', md_text):
        add(url)
    for url in re.findall(r'(?<![(\[<])\bhttps?://[^\s<>"\')\]]+', md_text):
        add(url)
    return urls


def probe(url):
    """(url, status, detail). status is an int, or one of the string codes below."""
    for method in ('HEAD', 'GET'):
        req = urllib.request.Request(url, method=method, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
            'Accept-Language': 'el,en;q=0.8',
        })
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as r:
                return url, r.status, r.url
        except urllib.error.HTTPError as e:
            # A server that dislikes HEAD often answers a GET fine.
            if method == 'HEAD' and e.code in (403, 405, 400, 501):
                continue
            return url, e.code, e.reason
        except urllib.error.URLError as e:
            if method == 'HEAD':
                continue
            return url, 'unreachable', str(e.reason)
        except (socket.timeout, TimeoutError):
            if method == 'HEAD':
                continue
            return url, 'timeout', f'no response in {TIMEOUT}s'
        except Exception as e:  # malformed URL, unsupported scheme, ...
            return url, 'error', f'{type(e).__name__}: {e}'
    return url, 'unreachable', 'no response to HEAD or GET'


def classify(status):
    if isinstance(status, int):
        if 200 <= status < 400:
            return 'ok'
        if status in BLOCKED_STATUSES:
            return 'blocked'
        return 'dead'
    return 'dead'


def report_path(md_path):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(md_path))
    date_slug = m.group(1) if m else datetime.now().strftime('%Y-%m-%d')
    return os.path.join(BRIEFINGS_DIR, f'.link-check-{date_slug}.json')


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check-links.py <briefing.md>", file=sys.stderr)
        sys.exit(2)

    md_path = sys.argv[1]
    if not os.path.isfile(md_path):
        print(f"Error: no such briefing: {md_path}", file=sys.stderr)
        sys.exit(2)

    with open(md_path, 'r', encoding='utf-8', errors='replace') as f:
        urls = extract_urls(f.read())

    if not urls:
        print("Error: the briefing contains no URLs — every item must cite a source.",
              file=sys.stderr)
        sys.exit(1)

    print(f"Έλεγχος {len(urls)} μοναδικών συνδέσμων από {os.path.basename(md_path)}...")
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(probe, urls))

    ok, blocked, dead = [], [], []
    for url, status, detail in results:
        verdict = classify(status)
        line = f"  [{status}] {url}"
        if verdict == 'ok':
            ok.append({'url': url, 'status': status})
        elif verdict == 'blocked':
            blocked.append({'url': url, 'status': status, 'detail': str(detail)})
            print(f"?? BLOCKED{line} — {detail}")
        else:
            dead.append({'url': url, 'status': str(status), 'detail': str(detail)})
            print(f"!! DEAD   {line} — {detail}")

    checked_at = datetime.now().replace(microsecond=0).isoformat()
    report = {
        'briefing': os.path.basename(md_path),
        'checked_at': checked_at,
        'total': len(urls),
        'ok': len(ok),
        'blocked': blocked,
        'dead': dead,
        'passed': not dead,
    }
    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    with open(report_path(md_path), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{len(ok)}/{len(urls)} OK · {len(blocked)} blocked · {len(dead)} dead")
    if dead:
        print("\nFAIL: η έκδοση περιέχει νεκρούς συνδέσμους και δεν πρέπει να δημοσιευθεί.",
              file=sys.stderr)
        sys.exit(1)
    print("PASS: κανένας νεκρός σύνδεσμος.")


if __name__ == '__main__':
    main()
