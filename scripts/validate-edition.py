#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Pre-publish edition validator

One gate in front of publication. Was check-duplication.py, which only
measured how much a card's <details> block repeated its own visible text;
every other house invariant went unenforced, so an edition could ship with
the wrong number of items, seven stories off one masthead, the same URL cited
twice, or no [Ο Φάκελός μου] item at all.

    python scripts/validate-edition.py briefings/oracle-briefing-2026-09-09.md
    python scripts/validate-edition.py <briefing.md> [built.html]

The HTML defaults to docs/briefings/<date>.html. Exits non-zero on any
failure — nothing may be pushed until it passes.
"""

import os
import re
import sys
from collections import defaultdict

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOCS_BRIEFINGS_DIR = os.path.join(BASE_DIR, 'docs', 'briefings')

# House invariants (.antigravity/rules/oracle-briefing.md)
SECTION_COUNTS = {'ΚΥΠΡΟΣ': 6, 'ΔΙΕΘΝΗ': 5, 'ΑΓΟΡΕΣ': 5}
MAX_ITEMS_PER_OUTLET = 2
PORTFOLIO_TAG = '[Ο Φάκελός μου]'
PORTFOLIO_ITEM_INDEX = 6  # the 6th ΚΥΠΡΟΣ item

LINK_CLAIM_RE = re.compile(
    r'(σύνδεσμοι ελέγχθηκαν|200\s*OK|broken/404|Έλεγχος και Επαλήθευση Συνδέσμων)',
    re.IGNORECASE)

failures = []
notes = []


def fail(check, message):
    failures.append(f"{check}: {message}")


def split_sections(md):
    """{section header: body} for every '## ' section."""
    out = {}
    for chunk in re.split(r'\n##\s+', '\n' + md)[1:]:
        lines = chunk.splitlines()
        out[lines[0].strip()] = '\n'.join(lines[1:])
    return out


def section_body(sections, keyword):
    for header, body in sections.items():
        if keyword in header:
            return header, body
    return None, None


def h3_items(body):
    """'### ...' blocks, as (title, block) pairs."""
    items = []
    for chunk in re.split(r'\n###\s+', '\n' + body)[1:]:
        lines = chunk.splitlines()
        items.append((lines[0].strip(), chunk))
    return items


def bullet_items(body):
    """Top-level '*   **Title**' bullets with their indented continuation."""
    items, current = [], None
    for line in body.splitlines():
        if re.match(r'^[*\-]\s+\*\*', line):
            if current:
                items.append(current)
            current = [line]
        elif current is not None:
            if line.strip() and not line.startswith((' ', '\t')):
                items.append(current)
                current = None
            else:
                current.append(line)
    if current:
        items.append(current)
    out = []
    for block in items:
        text = '\n'.join(block)
        title = re.sub(r'^[*\-]\s+', '', text.strip().splitlines()[0])
        out.append((title.replace('**', '').strip(), text))
    return out


def cited_links(block):
    """(outlet, url) pairs from the item's Πηγή / Πηγές lines only."""
    links = []
    for line in block.splitlines():
        if re.search(r'\*{0,2}Πηγ(ή|ές)\*{0,2}\s*:', line):
            links.extend(re.findall(r'\[([^\]]+)\]\(([^)\s]+)', line))
    return links


def normalise_outlet(name):
    return re.sub(r'\s+', ' ', name).strip().lower()


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_section_counts(sections):
    counts = {}
    for keyword, expected in SECTION_COUNTS.items():
        header, body = section_body(sections, keyword)
        if body is None:
            fail('ΕΝΟΤΗΤΕΣ', f"λείπει η ενότητα {keyword}.")
            continue
        items = h3_items(body) or bullet_items(body)
        counts[keyword] = len(items)
        if len(items) != expected:
            fail('ΕΝΟΤΗΤΕΣ',
                 f"{keyword}: {len(items)} items, αναμένονταν {expected}.")
    if counts:
        notes.append("Items: " + " · ".join(f"{k} {v}" for k, v in counts.items()))


def check_portfolio_tag(sections):
    _header, body = section_body(sections, 'ΚΥΠΡΟΣ')
    if body is None:
        return
    items = h3_items(body)
    if len(items) < PORTFOLIO_ITEM_INDEX:
        fail('ΦΑΚΕΛΟΣ',
             f"η ΚΥΠΡΟΣ έχει {len(items)} items — δεν υπάρχει "
             f"{PORTFOLIO_ITEM_INDEX}ο για τη σήμανση {PORTFOLIO_TAG}.")
        return
    title = items[PORTFOLIO_ITEM_INDEX - 1][0]
    if PORTFOLIO_TAG not in title:
        fail('ΦΑΚΕΛΟΣ',
             f"το item {PORTFOLIO_ITEM_INDEX} της ΚΥΠΡΟΣ δεν φέρει "
             f"{PORTFOLIO_TAG} — «{title[:80]}»")
    stray = [i + 1 for i, (t, _) in enumerate(items)
             if PORTFOLIO_TAG in t and i + 1 != PORTFOLIO_ITEM_INDEX]
    if stray:
        fail('ΦΑΚΕΛΟΣ',
             f"η σήμανση {PORTFOLIO_TAG} εμφανίζεται και στα items {stray}.")


def collect_items(sections):
    """(label, block) for every sourced item in the edition."""
    collected = []
    for keyword in ('ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ', 'ΚΥΠΡΟΣ', 'ΔΙΕΘΝΗ', 'ΑΓΟΡΕΣ', 'ΑΘΛΗΤΙΚΑ'):
        _header, body = section_body(sections, keyword)
        if body is None:
            continue
        items = h3_items(body) or bullet_items(body)
        for title, block in items:
            collected.append((f"{keyword} · {title[:60]}", block))
    return collected


def check_outlet_cap(items):
    per_outlet = defaultdict(list)
    for label, block in items:
        for outlet, _url in {(normalise_outlet(o), u) for o, u in cited_links(block)}:
            if label not in per_outlet[outlet]:
                per_outlet[outlet].append(label)
    for outlet, labels in sorted(per_outlet.items()):
        if len(labels) > MAX_ITEMS_PER_OUTLET:
            fail('ΜΕΣΑ',
                 f"«{outlet}» σε {len(labels)} items (όριο {MAX_ITEMS_PER_OUTLET}): "
                 + "; ".join(labels))
    if per_outlet:
        notes.append(f"Μέσα: {len(per_outlet)} διακριτά")


def check_url_reuse(items):
    per_url = defaultdict(list)
    for label, block in items:
        for _outlet, url in cited_links(block):
            if label not in per_url[url]:
                per_url[url].append(label)
    for url, labels in per_url.items():
        if len(labels) > 1:
            fail('URL', f"το {url} χρησιμοποιείται σε {len(labels)} items: "
                        + "; ".join(labels))
    if per_url:
        notes.append(f"URLs πηγών: {len(per_url)} μοναδικά")


def check_link_claim(md):
    for line in md.splitlines():
        if LINK_CLAIM_RE.search(line):
            fail('ΣΥΝΔΕΣΜΟΙ',
                 "το markdown ισχυρίζεται ότι οι σύνδεσμοι ελέγχθηκαν. Μόνο το "
                 "scripts/check-links.py επιτρέπεται να το δηλώσει· αφαιρέστε "
                 f"την πρόταση: «{line.strip()[:110]}»")
            return


def check_details_overlap(html_path):
    """The original check: a card's <details> must add context, not repeat."""
    if not html_path or not os.path.exists(html_path):
        fail('ΕΠΑΝΑΛΗΨΗ',
             f"δεν βρέθηκε το χτισμένο HTML ({html_path}). Τρέξτε πρώτα "
             f"το build-html.py.")
        return
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    def strip(s):
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip().lower()

    checked = 0
    for i, card in enumerate(html.split('<article')[1:]):
        det = re.search(r'<details[\s\S]*?</details>', card)
        if not det:
            continue
        hidden = strip(det.group(0))
        visible = strip(card.replace(det.group(0), ''))
        hid_words = set(w for w in hidden.split(' ') if len(w) > 4)
        if not hid_words:
            continue
        checked += 1
        overlap = sum(1 for w in hid_words if w in visible) / len(hid_words)
        if overlap > 0.5:
            fail('ΕΠΑΝΑΛΗΨΗ',
                 f"κάρτα #{i + 1}: το «Βάθος» επαναλαμβάνει το ορατό κείμενο "
                 f"κατά {overlap * 100:.0f}%.")
    notes.append(f"Κάρτες με «Βάθος» που ελέγχθηκαν: {checked}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate-edition.py <briefing.md> [built.html]",
              file=sys.stderr)
        sys.exit(2)

    md_path = sys.argv[1]
    if not os.path.isfile(md_path):
        print(f"Error: no such briefing: {md_path}", file=sys.stderr)
        sys.exit(2)

    if len(sys.argv) > 2:
        html_path = sys.argv[2]
    else:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(md_path))
        html_path = (os.path.join(DOCS_BRIEFINGS_DIR, f'{m.group(1)}.html')
                     if m else None)

    with open(md_path, 'r', encoding='utf-8', errors='replace') as f:
        md = f.read()

    sections = split_sections(md)
    items = collect_items(sections)

    check_section_counts(sections)
    check_portfolio_tag(sections)
    check_outlet_cap(items)
    check_url_reuse(items)
    check_link_claim(md)
    check_details_overlap(html_path)

    print(f"Έλεγχος έκδοσης: {os.path.basename(md_path)} ({len(items)} items)")
    for n in notes:
        print(f"  · {n}")

    if failures:
        print(f"\n{len(failures)} ΠΑΡΑΒΙΑΣΕΙΣ — η έκδοση ΔΕΝ πρέπει να δημοσιευθεί:",
              file=sys.stderr)
        for f_msg in failures:
            print(f"  !! {f_msg}", file=sys.stderr)
        sys.exit(1)

    print("\nPASS: όλοι οι κανόνες της έκδοσης τηρούνται.")


if __name__ == '__main__':
    main()
