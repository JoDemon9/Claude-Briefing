"""Bounded deterministic transport. Caches/evidence stay in the private checkout."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit
import urllib.request
import urllib.error


def now():
    return datetime.now(timezone.utc).isoformat()


def source(publisher, url, retrieved, published=None, kind='primary'):
    return dict(publisher=publisher, url=url, published_at=published, retrieved_at=retrieved,
                reporting_group=publisher, kind=kind, access='read', used_for_claims=True)


def safe(url, hosts):
    p = urlsplit(url)
    return (p.scheme == 'https' and p.hostname in hosts and not p.username and not p.password
            and p.port in (None, 443))


class Redirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe(newurl, self.hosts):
            raise ValueError('Off-provider redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    """One attempt/request, eight workers, 8s timeout, 2MB response cap. No AI calls."""
    def __init__(self, cache, hosts, opener=None, clock=now):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.hosts = set(hosts)
        self.open = opener or urllib.request.build_opener(Redirect(self.hosts)).open
        self.clock = clock
        self.records = []
        self.lock = threading.Lock()

    def get(self, url):
        if not safe(url, self.hosts):
            return {'url':url, 'status':'unavailable', 'reason':'provider_not_allowed'}
        path = self.cache / (hashlib.sha256(url.encode()).hexdigest()+'.json')
        old = {}
        try:
            old = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
        headers = {'User-Agent':'OraclePrefetch/1.0', 'Accept':'application/json,application/xml,text/html,text/csv,*/*'}
        if urlsplit(url).hostname == 'site.api.espn.com':
            headers = {}
        if urlsplit(url).hostname == 'api.met.no':
            headers['User-Agent'] = 'OraclePrefetch/1.0 https://github.com/JoDemon9/Claude-Briefing'
        if old.get('etag'):
            headers['If-None-Match'] = old['etag']
        if old.get('modified'):
            headers['If-Modified-Since'] = old['modified']
        try:
            with self.open(urllib.request.Request(url, headers=headers), timeout=8) as response:
                if response.status != 200 or not safe(response.geturl(), self.hosts):
                    raise ValueError('Unexpected response')
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError('Response exceeds budget')
                stamp = self.clock()
                row = dict(url=url, status='available', retrieved_at=stamp, checked_at=stamp,
                           text=raw.decode('utf-8-sig', errors='replace'),
                           etag=response.headers.get('ETag'), modified=response.headers.get('Last-Modified'))
                temp = path.with_suffix('.tmp')
                temp.write_text(json.dumps(row, ensure_ascii=False), encoding='utf-8')
                temp.replace(path)
        except urllib.error.HTTPError as error:
            if error.code == 304 and old.get('text') and old.get('retrieved_at'):
                row = {**old, 'checked_at':self.clock(), 'status':'available'}
            else:
                row = dict(url=url, status='unavailable', attempted_at=self.clock(), reason='HTTP '+str(error.code))
        except (OSError, ValueError, TimeoutError) as error:
            row = dict(url=url, status='unavailable', attempted_at=self.clock(), reason=type(error).__name__)
        with self.lock:
            self.records.append({k:v for k,v in row.items() if k not in ('text','etag','modified')})
        return row

    def many(self, urls):
        urls = sorted(set(urls))
        with ThreadPoolExecutor(max_workers=8) as pool:
            return dict(zip(urls, pool.map(self.get, urls)))


def data(row):
    return json.loads(row['text']) if row.get('status') == 'available' else None
