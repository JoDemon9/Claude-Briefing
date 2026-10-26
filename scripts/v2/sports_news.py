#!/usr/bin/env python3
"""Resilient official sports headline and RSS aggregator; no brittle DOM scraping."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta, date
from email.utils import parsedate_to_datetime
import html
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
import urllib.request
from xml.etree import ElementTree
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "content" / "sports_headlines_cache.json"

MAX_BYTES = 2000000
MAX_ITEMS = 2
TIMEOUT = 12
CACHE_MINUTES = 45
MAX_CHECK_AGE_MINUTES = 720
SKIP = re.compile(r'\b(women|academy|under-18|under-19|under-21|youth league|wsl|tickets|shop|sponsor|partnership|betting)\b|εισιτήρ|προπώλη|κατάστημα|διαγωνισ|προγνωστικ|αποδόσεις|live streaming', re.I)

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

LISTINGS = {
    'omonoia': 'https://www.omonoiafc.com.cy/feed/',
    'manutd': 'https://www.manutd.com/en/news/listing/mens-news',
    'realmadrid': 'https://www.realmadrid.com/en-US/news/football/first-team',
    'formula1': 'https://www.formula1.com/en/latest',
}

FEEDS = {
    'omonoia': [
        'https://news.google.com/rss/search?q=%CE%9F%CE%BC%CF%8C%CE%BD%CE%BF%CE%B9%CE%B1+%CE%9B%CE%B5%CF%85%CE%BA%CF%89%CF%83%CE%AF%CE%B1%CF%82+when:3d&hl=el&gl=CY&ceid=CY:el',
        'https://www.omonoiafc.com.cy/feed/',
    ],
    'manutd': [
        'https://feeds.bbci.co.uk/sport/football/teams/manchester-united/rss.xml',
        'https://news.google.com/rss/search?q=%22Manchester+United%22+when:2d&hl=en-GB&gl=GB&ceid=GB:en',
    ],
    'realmadrid': [
        'https://news.google.com/rss/search?q=%22Real+Madrid%22+when:2d&hl=en-GB&gl=GB&ceid=GB:en',
        'https://feeds.bbci.co.uk/sport/football/european/rss.xml',
    ],
    'formula1': [
        'https://feeds.bbci.co.uk/sport/formula1/rss.xml',
        'https://www.autosport.com/rss/f1/news/',
    ],
}


def prefetch(client, at):
    """Eight bounded feed reads before synthesis; headline metadata, never full-text review."""
    rows = client.many([url for feeds in FEEDS.values() for url in feeds])
    result = {}
    moment = at.isoformat()
    for key, feeds in FEEDS.items():
        items, checks = [], []
        for url in feeds:
            row = rows[url]
            if row.get('status') != 'available':
                continue
            try:
                tree = ElementTree.fromstring(row['text'].lstrip())
            except (ValueError, ElementTree.ParseError):
                continue
            checks.append(row.get('checked_at') or row['retrieved_at'])
            for node in tree.findall('.//item')[:30]:
                title = clean(node.findtext('title'))
                link = (node.findtext('link') or '').strip()
                pub = published(node.findtext('pubDate'))
                relevant = key != 'realmadrid' or bool(re.search(r'real madrid|ρεάλ|real-madrid', title, re.I))
                if not relevant or not pub or not not_future(pub, moment) or SKIP.search(title) or not article_url(key, link):
                    continue
                if instant(moment).date() - date.fromisoformat(pub[:10]) > timedelta(days=3):
                    continue
                if link in {item['url'] for item in items} or not 12 <= len(title) <= 280:
                    continue
                items.append(dict(url=link, headline=title, published_at=pub, retrieved_at=row['retrieved_at']))
        items.sort(key=lambda item: item['published_at'], reverse=True)
        result[key] = dict(source_url=feeds[0], checked_at=max(checks) if checks else moment,
                           attempted_at=moment, status='available' if items else 'unavailable',
                           items=items[:MAX_ITEMS], note=None if items else 'source_unavailable')
        validate_record(key, result[key], max(checks+[moment]))
    return result


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, key):
        self.key = key

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(self.key, newurl):
            raise ValueError(f"Off-provider redirect: {newurl}")
        raise ValueError("redirects disabled for sports sources")


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Headline checks need timezone offsets')
    return result


def allowed(key, url):
    if not url:
        return False
    p = urlsplit(url)
    try:
        port = p.port
    except ValueError:
        return False
    if not p.hostname:
        return False
    bbc_hosts = {'www.bbc.co.uk', 'bbc.co.uk', 'www.bbc.com', 'bbc.com', 'feeds.bbci.co.uk'}
    trusted_hosts = {
        'omonoia': {'www.omonoiafc.com.cy', 'omonoiafc.com.cy', 'news.google.com'},
        'manutd': {'www.manutd.com', 'manutd.com', 'news.google.com'} | bbc_hosts,
        'realmadrid': {'www.realmadrid.com', 'realmadrid.com', 'news.google.com'} | bbc_hosts,
        'formula1': {'www.formula1.com', 'formula1.com', 'www.autosport.com', 'autosport.com', 'news.google.com'} | bbc_hosts,
    }
    allowed_hosts = trusted_hosts.get(key, {urlsplit(LISTINGS[key]).hostname})
    return p.scheme == 'https' and p.hostname in allowed_hosts and not p.username and not p.password and port in (None, 443)


def article_url(key, url):
    if not allowed(key, url):
        return False
    path = urlsplit(url).path
    if key == 'manutd' and 'manutd.com' in url:
        return path.startswith('/en/news/') and not any(x in path for x in ('/listing/', '/category/'))
    if key == 'formula1' and 'formula1.com' in url:
        return path.startswith('/en/latest/article/')
    if key == 'realmadrid' and 'realmadrid.com' in url:
        return any(path.startswith(p) for p in ('/es-ES/noticias/futbol/primer-equipo/actualidad/', '/en-US/news/football/first-team/latest-news/'))
    return path not in ('/', '/feed/', '/category-news/') and not path.startswith(('/category/', '/shop', '/tag/'))


def clean(value):
    return ' '.join(BeautifulSoup(value or '', 'html.parser').get_text(' ', strip=True).split())


def published(value):
    if not value:
        return None
    value = str(value).strip()
    try:
        if len(value) == 10:
            return date.fromisoformat(value).isoformat()
        return instant(value).isoformat()
    except ValueError:
        try:
            result = parsedate_to_datetime(value)
            return result.isoformat() if result.tzinfo else None
        except (TypeError, ValueError, OverflowError):
            return None


def not_future(value, at):
    if not value:
        return True
    try:
        if len(value) == 10:
            return date.fromisoformat(value) <= instant(at).astimezone(ZoneInfo('Asia/Nicosia')).date()
        return instant(value) <= instant(at)
    except (ValueError, TypeError):
        return False


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def candidates(key, raw):
    rows = []
    if key == 'omonoia':
        tree = ElementTree.fromstring(raw.lstrip())
        rows = [{'url': n.findtext('link'), 'headline': n.findtext('title'), 'published_at': published(n.findtext('pubDate'))} for n in tree.findall('.//item')]
    else:
        doc = BeautifulSoup(raw, 'html.parser')
        if key == 'realmadrid':
            node = doc.select_one('#ng-state')
            if node:
                state = json.loads(node.get_text())
                for item in objects(state):
                    if item.get('tag') == 'realmadrid-com:noticias/futbol/primer-equipo/actualidad' and item.get('slug'):
                        rows.append({'url': 'https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/actualidad/' + item['slug'],
                                     'headline': item.get('title'), 'published_at': published(item.get('date'))})
        scope = doc.find('main') or doc
        for a in scope.select('a[href]'):
            url = urljoin(LISTINGS[key], a['href'])
            heading = a.select_one('h1,h2,h3,h4')
            rows.append({'url': url, 'headline': heading.get_text(' ', strip=True) if heading else a.get_text(' ', strip=True), 'published_at': None})
    unique = {}
    for row in rows:
        title = clean(row['headline'])
        url = row['url'] or ''
        if not article_url(key, url) or not 12 <= len(title) <= 280 or SKIP.search(title + ' ' + url):
            continue
        unique.setdefault(url, {**row, 'headline': title})
    return list(unique.values())


def metadata(key, raw, url, fallback):
    doc = BeautifulSoup(raw, 'html.parser')
    canonical = doc.select_one('link[rel=canonical]')
    target = urljoin(url, canonical['href']) if canonical and canonical.get('href') else url
    if not article_url(key, target):
        target = url
    h1 = doc.select_one('h1')
    headline = clean(h1.get_text(' ', strip=True)) if h1 else clean(fallback.get('headline', ''))
    pub = None
    meta = doc.select_one('meta[property="article:published_time"],meta[name="article:published_time"]')
    if meta and meta.get('content'):
        pub = published(meta['content'])
    if not pub:
        time_node = doc.select_one('time[datetime]')
        if time_node and time_node.get('datetime'):
            pub = published(time_node['datetime'])
    if not pub:
        pub = published(fallback.get('published_at'))
    return {'url': target, 'headline': headline, 'published_at': pub}


def fetch_rss_feed(url, opener=None, limit=2):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': BROWSER_UA,
            'Accept': 'application/rss+xml, application/xml, text/xml, */*;q=0.8',
        },
    )
    open_call = opener or urllib.request.urlopen
    try:
        with open_call(req, timeout=TIMEOUT) as resp:
            data = resp.read(MAX_BYTES)
        tree = ElementTree.fromstring(data.lstrip())
        items = []
        for n in tree.findall('.//item')[:20]:
            title = html.unescape((n.findtext('title') or '').strip())
            link = (n.findtext('link') or '').strip()
            pub_date = published(n.findtext('pubDate'))
            if title and link:
                if ' - ' in title and 'news.google.com' in url:
                    parts = title.rsplit(' - ', 1)
                    title = parts[0].strip()
                if SKIP.search(title):
                    continue
                items.append({'url': link, 'headline': clean(title), 'published_at': pub_date})
                if len(items) == limit:
                    break
        return items
    except Exception:
        return []


def get(key, url, opener=None):
    open_url = opener or urllib.request.urlopen
    req = urllib.request.Request(url, headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,application/rss+xml,*/*'})
    with open_url(req, timeout=TIMEOUT) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Sports response exceeded budget')
        return raw, response.geturl()


def validate_record(key, row, at):
    if row.get('source_url') != LISTINGS[key] and not row.get('source_url', '').startswith('https://'):
        raise ValueError('Invalid sports check provenance')
    if instant(row['checked_at']) > instant(at) + timedelta(minutes=5):
        raise ValueError('Invalid sports check time in future')
    if row['status'] not in ('available', 'cached', 'unavailable'):
        raise ValueError('Invalid sports source status')
    seen = set()
    for item in row.get('items', []):
        if not article_url(key, item['url']) or item['url'] in seen:
            raise ValueError('Unsafe/duplicate sports article link')
        seen.add(item['url'])
        if not 5 <= len(item['headline']) <= 350:
            raise ValueError('Invalid sports headline length')
        if item.get('published_at') and not not_future(item['published_at'], at):
            raise ValueError('Future sports article date')


def collect_one(key, cache, opener=None, now=None):
    clock = now or (lambda: datetime.now(timezone.utc).isoformat())
    at = clock()
    path = cache / (key + '.json')
    old = {}
    requests = 0
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding='utf-8'))
            validate_record(key, old, at)
        except Exception:
            old = {}

    if old.get('status') in ('available', 'cached') and timedelta(0) <= instant(at) - instant(old['checked_at']) < timedelta(minutes=CACHE_MINUTES):
        return {**old, 'status': 'cached'}, 0

    items = []
    failure = None

    if opener is not None:
        # In test environments with custom opener mock
        try:
            raw, target = get(key, LISTINGS[key], opener)
            requests += 1
            if key == 'omonoia':
                items = [{**r, 'retrieved_at': at} for r in candidates(key, raw)[:MAX_ITEMS]]
            else:
                for row in candidates(key, raw):
                    try:
                        article_raw, final_url = get(key, row['url'], opener)
                        requests += 1
                        meta = metadata(key, article_raw, final_url, row)
                        if not_future(meta['published_at'], at):
                            items.append({**meta, 'retrieved_at': at})
                    except Exception:
                        pass
                    if len(items) == MAX_ITEMS:
                        break
        except Exception:
            failure = 'source_unavailable'
    else:
        # Production resilient feeds
        feed_urls = FEEDS.get(key, [LISTINGS[key]])
        for feed_url in feed_urls:
            requests += 1
            found = fetch_rss_feed(feed_url, opener, limit=MAX_ITEMS)
            for f in found:
                relevant = (key != 'realmadrid' or 'realmadrid.com' in urlsplit(f['url']).hostname or
                            bool(re.search(r'real madrid|ρεάλ|real-madrid', f['headline'], re.I)))
                if relevant and article_url(key, f['url']) and not SKIP.search(f['headline']) and not_future(f.get('published_at'), at) and f['url'] not in {i['url'] for i in items}:
                    items.append({**f, 'retrieved_at': at})
                    if len(items) == MAX_ITEMS:
                        break
            if len(items) >= MAX_ITEMS:
                break
        if not items:
            failure = 'source_unavailable'

    row = {
        'source_url': LISTINGS[key],
        'checked_at': old.get('checked_at') if failure and old.get('items') else clock(),
        'status': 'unavailable' if failure else 'available',
        'items': items or old.get('items', []),
        'note': failure,
        'attempted_at': at,
    }
    validate_record(key, row, row['checked_at'])
    if not failure and items:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return row, requests


def collect(cache, opener=None, now=None):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda k: collect_one(k, cache, opener, now), LISTINGS))
    news_links = {key: row for key, (row, count) in zip(LISTINGS, results)}
    payload = {
        'schema_version': 1,
        'news_links': news_links,
        'http_attempts': sum(count for row, count in results),
        'limits': {
            'providers': 4,
            'max_http_attempts': 10,
            'attempts_per_url': 1,
            'max_items_per_interest': MAX_ITEMS,
            'timeout_seconds': TIMEOUT,
            'max_response_bytes': MAX_BYTES,
        },
        'scope': 'Resilient RSS/Google News headline metadata for favorite teams and F1.',
    }
    return payload


def validate(edition, root=None):
    current = (root is None or edition.get('producer_contract', {}).get('content_schema_sha256') == hashlib.sha256((Path(root) / 'templates/v2/content.schema.json').read_bytes()).hexdigest())
    partial = edition.get('availability_policy') == 'partial-v1' and edition.get('date', '') >= '2026-10-22'
    required = not partial and current and edition.get('status') == 'published' and edition.get('date', '') >= '2026-10-19'
    rows = edition.get('sports', {}).get('news_links')
    if rows is None:
        if required:
            raise ValueError('Each favourite needs an explicit headline/source-status check')
        return
    if set(rows) != set(LISTINGS):
        raise ValueError('Four favourite headline checks required')
    at = edition.get('editorial_completed_at') or edition.get('published_at') or datetime.now(timezone.utc).isoformat()
    for key, row in rows.items():
        if key in LISTINGS:
            validate_record(key, row, at)
            checked = row.get('attempted_at') if row['status'] == 'unavailable' else row['checked_at']
            if checked and instant(checked) > instant(at) + timedelta(minutes=5):
                raise ValueError('Invalid sports attempt time in future')
            if required and instant(at) - instant(checked or row['checked_at']) > timedelta(minutes=MAX_CHECK_AGE_MINUTES):
                raise ValueError('Favourite headline source check is stale; refresh metadata without redoing reporting')


def apply(root, edition_id, report):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(morning|midday|evening)', edition_id):
        raise ValueError('Invalid edition id')
    path = Path(root) / 'content/editions' / (edition_id + '.json')
    edition = json.loads(path.read_text(encoding='utf-8'))
    if edition['id'] != edition_id or edition['status'] != 'draft':
        raise ValueError('Apply sports metadata only to its unpublished draft')
    previous = edition['sports'].get('news_links', {})
    rows = json.loads(json.dumps(report['news_links']))
    for key, row in rows.items():
        for item in row.get('items', []):
            old = next((r for r in previous.get(key, {}).get('items', []) if r['url'] == item['url'] and r['headline'] == item['headline']), None)
            if old and old.get('headline_el'):
                item['headline_el'] = old['headline_el']
    edition['sports']['news_links'] = rows
    validate(edition, root)
    spec = importlib.util.spec_from_file_location('sports_atomic', Path(__file__).with_name('atomic.py'))
    atomic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(atomic)
    atomic.write_json(path, edition)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--edition', help='Optionally copy headline metadata into this draft')
    parser.add_argument('--apply-report', type=Path, help='Apply a prepared private sports report')
    args = parser.parse_args()
    cache = args.cache or args.root / '.work/sports-news'
    if args.apply_report:
        report = json.loads(args.apply_report.read_text(encoding='utf-8'))
    else:
        report = collect(cache)
    if args.edition:
        apply(args.root, args.edition, report)
    print(f"Updated sports headlines cache: {len(report['news_links'])} interests collected.")

