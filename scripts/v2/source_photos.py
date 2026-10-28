"""Source-bound photographs prepared before synthesis. No AI calls or compiler network."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
import urllib.request

from PIL import Image, ImageOps

MAX_DOWNLOADS = 24
MAX_BYTES = 5_000_000
MAX_ASSET = 300_000
ARTICLE_TYPES = {'Article', 'NewsArticle', 'ReportageNewsArticle'}
BAD_IMAGE = re.compile(r'\b(logo|avatar|icon|advertisement|illustration|rendering|infographic|AI.generated|computer.generated|γράφημα|εικονογράφηση)\b', re.I)
PHOTO = re.compile(r'\b(photo(?:graph)?s?|φωτογραφία|φωτογραφίες|φωτογραφια|φωτο)\b', re.I)


def clean(value):
    from bs4 import BeautifulSoup
    text = str(value or '')
    if '<' in text: text = BeautifulSoup(text, 'html.parser').get_text(' ', strip=True)
    return ' '.join(text.split())[:800]


def https(url):
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and bool(p.hostname) and not p.username and not p.password and p.port in (None, 443)
    except (ValueError, TypeError):
        return False


def identity(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path.rstrip('/'), '', ''))


def license_name(url):
    # Only an image-level licence is accepted, never the article/footer licence.
    match = re.fullmatch(r'https://creativecommons.org/(licenses/(by|by-sa)/(2.0|2.5|3.0|4.0)|publicdomain/(zero|mark)/1.0)/?', url or '')
    if not match:
        return None
    return ('CC '+match[2].upper()+' '+match[3]) if match[2] else ('CC0 1.0' if match[4] == 'zero' else 'Public domain')


def extract(soup, page_url):
    """Capture candidates from this article's existing HTML, without fetching anything."""
    result = {}
    def add(url, method, caption='', credit='', license_url='', photograph=False):
        if not isinstance(url, str):
            return
        url = urljoin(page_url, url)
        if not https(url) or BAD_IMAGE.search(urlsplit(url).path+' '+caption):
            return
        row = result.setdefault(url, dict(url=url, method=method, caption='', attribution='', license_url='', photograph=False))
        for key, value in (('caption', caption), ('attribution', credit), ('license_url', license_url)):
            if value and not row[key]:
                row[key] = clean(value)
        row['photograph'] |= photograph or bool(PHOTO.search(caption))

    nodes = []
    def graph(value):
        if isinstance(value, list):
            for child in value: yield from graph(child)
        elif isinstance(value, dict):
            yield value
            yield from graph(value.get('@graph', []))
    for script in soup.select('script[type="application/ld+json"]'):
        try: nodes.extend(graph(json.loads(script.string or script.get_text())))
        except (ValueError, TypeError): continue
    references = {n['@id']: n for n in nodes if isinstance(n.get('@id'), str)}
    articles = [n for n in nodes if any(t in ARTICLE_TYPES for t in
                (n.get('@type', []) if isinstance(n.get('@type'), list) else [n.get('@type')]) if isinstance(t, str))]
    for article in articles:
        declared = article.get('url') or article.get('mainEntityOfPage')
        if isinstance(declared, dict): declared = declared.get('@id')
        if declared and (not isinstance(declared, str) or identity(urljoin(page_url, declared)) != identity(page_url)):
            continue
        if not declared and len(articles) != 1:
            continue
        images = article.get('image', [])
        for obj in images if isinstance(images, list) else [images]:
            if isinstance(obj, str): obj = references.get(obj, {'url':obj})
            if not isinstance(obj, dict): continue
            ref = obj.get('@id')
            obj = {**(references.get(ref, {}) if isinstance(ref, str) else {}), **obj}
            author = obj.get('creator') or obj.get('author') or ''
            if isinstance(author, dict): author = author.get('name', '')
            if not isinstance(author, str): author = ''
            add(obj.get('contentUrl') or obj.get('url'), 'article-jsonld',
                clean(obj.get('caption') or obj.get('description')), clean(obj.get('creditText') or obj.get('copyrightNotice') or author),
                obj.get('license') if isinstance(obj.get('license'), str) else '', obj.get('@type') == 'Photograph')
    region = soup.select_one('[itemprop="articleBody"], .ArticleBody-articleBody, .article-body, .entry-content') or soup.find('article')
    if region:
        for figure in region.find_all('figure'):
            if len(figure.find_all('img')) != 1: continue
            img = figure.find('img'); caption = figure.find('figcaption')
            caption = clean(caption.get_text(' ', strip=True)) if caption else clean(img.get('alt'))
            credit = figure.select_one('[itemprop="creditText"], [itemprop="copyrightNotice"], .credit, .image-credit')
            rights = figure.select_one('a[rel~="license"]')
            url = img.get('data-src') or img.get('src')
            add(url, 'article-figure', caption, clean(credit.get_text()) if credit else '',
                urljoin(page_url, rights.get('href', '')) if rights else '')
    for selector in ('meta[property="og:image"]', 'meta[name="twitter:image"]'):
        for node in soup.select(selector): add(node.get('content'), 'social-metadata')
    return list(result.values())[:8]


def policy(root):
    return json.loads((Path(root)/'templates/v2/source-photo-policy.json').read_text(encoding='utf-8'))


def eligible(candidate, source_url, rules):
    """An allowed CDN is transport permission, never a copyright grant."""
    row = dict(candidate)
    if not https(source_url) or not https(row.get('url')): return None
    hosts = rules['publishers'].get(urlsplit(source_url).hostname, [])
    if urlsplit(row['url']).hostname not in hosts: return None
    grant = next((g for g in rules.get('reviewed_images', [])
                  if g['article_url'] == source_url and g['image_url'] == row['url']), None)
    if grant:
        row.update({k:grant[k] for k in ('license_url','attribution','caption','photograph')})
    licence = license_name(row.get('license_url'))
    if not licence or not row.get('photograph') or len(row.get('caption', '')) < 15 or len(row.get('attribution', '')) < 3:
        return None
    if BAD_IMAGE.search(row['caption']): return None
    row.update(license=licence, rights_basis='reviewed-image' if grant else 'image-license', source_url=source_url)
    return row


def image_bytes(raw):
    with Image.open(io.BytesIO(raw)) as decoded:
        if decoded.format not in ('JPEG', 'PNG', 'WEBP') or getattr(decoded, 'is_animated', False):
            raise ValueError('Unsupported photo encoding')
        if decoded.width * decoded.height > 24_000_000:
            raise ValueError('Photo exceeds pixel budget')
        decoded.load()
        image = ImageOps.exif_transpose(decoded).convert('RGB')
        if min(image.size) < 200 or max(image.size) / min(image.size) > 3:
            raise ValueError('Photo is too small or banner-shaped')
        image.thumbnail((1200, 1200))
        output = io.BytesIO(); image.save(output, 'WEBP', quality=78, method=4)
        if output.tell() > MAX_ASSET: raise ValueError('Optimized photo exceeds budget')
        data = output.getvalue()
        with Image.open(io.BytesIO(data)) as optimized:
            return data, dhash(optimized)


def dhash(image):
    small = image.convert('L').resize((9, 8))
    pixels = [small.getpixel((x,y)) for y in range(8) for x in range(9)]
    return f'{sum((pixels[y*9+x] > pixels[y*9+x+1]) << (y*8+x) for y in range(8) for x in range(8)):016x}'


def fetch(candidate, rules, cache, opener=None):
    hosts = set(rules['publishers'][urlsplit(candidate['source_url']).hostname])
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not https(newurl) or urlsplit(newurl).hostname not in hosts:
                raise ValueError('Off-provider image redirect')
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
    path = cache/(key+'.json')
    try:
        old = json.loads(path.read_text())
        validate(old)
        # Fixed TTL: cache hits never invent a new retrieval time.
        if (datetime.now(timezone.utc)-datetime.fromisoformat(old['image']['retrieved_at'])).total_seconds() < 86400:
            return old
    except (OSError, ValueError, KeyError, TypeError): pass
    open_url = opener or urllib.request.build_opener(Redirect()).open
    request = urllib.request.Request(candidate['url'], headers={'User-Agent':'OraclePrefetch/1.0','Accept':'image/jpeg,image/png,image/webp'})
    with open_url(request, timeout=5) as response:
        if response.status != 200 or not https(response.geturl()) or urlsplit(response.geturl()).hostname not in hosts:
            raise ValueError('Invalid image response')
        if response.headers.get_content_type() not in ('image/jpeg', 'image/png', 'image/webp'):
            raise ValueError('Not an image response')
        raw = response.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES: raise ValueError('Photo download exceeds budget')
    data, visual_hash = image_bytes(raw)
    sha = hashlib.sha256(data).hexdigest()
    at = datetime.now(timezone.utc).isoformat()
    prefix = 'Φωτογραφία αρχείου · ' if re.search(r'\b(file|archive|archival|αρχείου)\b', candidate['caption'], re.I) else 'Φωτογραφία από το άρθρο της πηγής · '
    image = dict(url=f'assets/editorial/source/{sha}.webp', original_url=candidate['url'],
        source_url=candidate['source_url'], retrieved_at=at, license=candidate['license'], license_url=candidate['license_url'],
        attribution=candidate['attribution'], alt=candidate['caption'],
        caption=prefix+candidate['caption']+' · Προσαρμογή μεγέθους και μετατροπή σε WebP.',
        source_review=dict(method='publisher-metadata-v1', sha256=sha, perceptual_hash=visual_hash,
                           rights_basis=candidate['rights_basis'], checked_at=at))
    result = dict(image=image, data=base64.b64encode(data).decode('ascii'))
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(result)); temp.replace(path)
    return result


def prepare(evidence, root, cache, opener=None):
    rules = policy(root); jobs = []; skipped = 0
    for eid, row in evidence.items():
        if row.get('access') != 'article_excerpt' or not row.get('source'): continue
        selected = next((photo for c in row.get('image_candidates', [])
                         if (photo := eligible(c, row['source']['url'], rules))), None)
        if selected: jobs.append((eid, selected))
        else: skipped += 1
    def download(job):
        eid, candidate = job
        try: return eid, fetch(candidate, rules, cache, opener), None
        except (OSError, ValueError, KeyError, TypeError, Image.DecompressionBombError) as error:
            return eid, None, type(error).__name__
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(download, jobs[:MAX_DOWNLOADS]))
    return dict(version=1, photos={eid:photo for eid,photo,error in results if photo},
                metrics=dict(eligible=len(jobs), prepared=sum(photo is not None for _,photo,_ in results),
                             no_eligible_image=skipped, failed=sum(error is not None for _,_,error in results)))


def validate(record):
    image = record['image']; review = image['source_review']
    if len(record['data']) > (MAX_ASSET*4//3+4): raise ValueError('Oversized sealed photo')
    raw = base64.b64decode(record['data'], validate=True)
    validate_image(image, raw)
    return image, raw


def validate_image(image, raw):
    review = image['source_review']
    sha = hashlib.sha256(raw).hexdigest()
    if review['method'] != 'publisher-metadata-v1' or image['url'] != f'assets/editorial/source/{sha}.webp' or review['sha256'] != sha:
        raise ValueError('Source photo integrity mismatch')
    if not license_name(image['license_url']) or image['license'] != license_name(image['license_url']):
        raise ValueError('Source photo lacks a supported image licence')
    if not all(https(image[k]) for k in ('source_url','original_url')):
        raise ValueError('Unsafe source photo provenance')
    if review['rights_basis'] not in ('image-license', 'reviewed-image') or min(len(image[k]) for k in ('caption','alt','attribution')) < 3:
        raise ValueError('Missing source photo credits')
    for field in (image['retrieved_at'], review['checked_at']):
        if datetime.fromisoformat(field).tzinfo is None: raise ValueError('Photo times need a timezone')
    with Image.open(io.BytesIO(raw)) as decoded:
        if decoded.format != 'WEBP' or min(decoded.size) < 200 or max(decoded.size) > 1200 or len(raw) > MAX_ASSET:
            raise ValueError('Invalid sealed photo dimensions/encoding')
        decoded.load()
        if dhash(decoded) != review['perceptual_hash']: raise ValueError('Source photo visual hash mismatch')


def attach(payload, pack):
    """Only bind assets from the exact sealed evidence actually cited by this article."""
    photos = pack.get('source_photos', {}).get('photos', {})
    for article in payload['articles']:
        article.pop('_source_photos', None)
        urls = [s['url'] for s in article.get('sources', []) if s.get('access') == 'read' and s.get('used_for_claims')]
        selected = [photos[eid] for url in urls for eid,ev in pack['evidence'].items()
                    if eid in photos and ev.get('access') == 'article_excerpt' and ev.get('source', {}).get('url') == url
                    and photos[eid]['image']['source_url'] == url]
        for photo in selected: validate(photo)
        if selected: article['_source_photos'] = selected


def select(article, used):
    sources = {s['url'] for s in article.get('sources', []) if s.get('access') == 'read' and s.get('used_for_claims')}
    for record in article.get('_source_photos', []):
        image, raw = validate(record)
        if image['source_url'] not in sources: raise ValueError('Photo is not bound to cited article evidence')
        visual = image['source_review']['perceptual_hash']
        if image['source_review']['sha256'] in used or any(isinstance(v, str) and len(v) == 16 and (int(v,16)^int(visual,16)).bit_count() <= 4 for v in used):
            continue
        return image, raw
    return None
