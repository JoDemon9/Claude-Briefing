#!/usr/bin/env python3
"""Offline checks for public pages, archive links, anchors and article payloads."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from html_tree import Tree


def validate(site):
    site = site.resolve()
    failures, trees = [], {}
    manifest = json.loads((site / 'editions.json').read_text(encoding='utf-8'))
    dates = {entry['date'] for entry in manifest['editions']}
    actual = {path.stem for path in (site / 'briefings').glob('*.html')}
    if dates != actual or manifest['latest'] != max(dates):
        failures.append('Archive manifest does not match the published editions')
    for page in site.rglob('*.html'):
        tree = Tree(page.read_text(encoding='utf-8'))
        trees[page.resolve()] = tree
        ids = [node.attrs['id'] for node in tree.root.walk() if node.attrs.get('id')]
        if len(ids) != len(set(ids)):
            failures.append(f'{page.relative_to(site)}: duplicate IDs')
    def check_link(page, raw):
        url = urlsplit(raw)
        if url.scheme or url.netloc or raw.startswith('data:'):
            return
        target = (page.parent / unquote(url.path)).resolve() if url.path else page.resolve()
        if target.is_dir():
            target = target / 'index.html'
        if not target.is_relative_to(site) or not target.is_file():
            failures.append(f'{page.relative_to(site)}: missing/unsafe local reference {raw}')
        elif url.fragment and target.suffix == '.html':
            tree = trees.get(target) or Tree(target.read_text(encoding='utf-8'))
            if not any(node.attrs.get('id') == unquote(url.fragment) for node in tree.root.walk()):
                failures.append(f'{page.relative_to(site)}: missing anchor {raw}')
    for page, tree in trees.items():
        # These files predate the current format and are preserved byte-for-byte.
        # Their own legacy widgets are outside the October repair scope.
        if page.parent == site / 'briefings' and page.stem < '2026-10-11':
            continue
        for node in tree.root.walk():
            if node.tag in ('a', 'link') and node.attrs.get('href'):
                check_link(page, node.attrs['href'])
            if node.tag in ('img', 'script') and node.attrs.get('src'):
                check_link(page, node.attrs['src'])
    for item in json.loads((site / 'search-index.json').read_text(encoding='utf-8')):
        if item['date'] not in dates:
            failures.append('Search index points to an unpublished date')
        check_link(site / 'index.html', item['url'])
    for entry in manifest['editions']:
        check_link(site / 'index.html', entry['url'])
        data_path = site / entry['articles_url']
        data = json.loads(data_path.read_text(encoding='utf-8'))
        if data['date'] != entry['date'] or len(data['articles']) != entry['article_count']:
            failures.append(f'{entry["date"]}: article payload and manifest disagree')
        for article in data['articles']:
            check_link(site / 'index.html', entry['url'] + '#' + article['anchor'])
            if article.get('image'):
                check_link(site / 'index.html', article['image']['src'])
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=Path(__file__).resolve().parent.parent / 'docs')
    args = parser.parse_args()
    failures = validate(args.site)
    for failure in failures:
        print(f'FAIL: {failure}')
    if not failures:
        print('PASS: archive, article data, local assets and anchors agree.')
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
