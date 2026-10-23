"""Publish a complete latest edition and prepare a portable portal snapshot."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup

BASE = 'https://jodemon9.github.io/Claude-Briefing/'
PORTAL = 'https://jodemon9.github.io/oracle-briefing/'


def compact_document(text, edition_navigation=None):
    """Repair preserved editions without removing their reporting or credits."""
    doc = BeautifulSoup(text, 'html.parser')
    lead = doc.select_one('.hero-grid > .hero')
    if lead:
        content = lead.select_one('.story-content')
        abstract = lead.select_one('.abstract')
        photo = lead.select_one('figure.photo')
        if content and abstract and photo and not lead.select_one('.lead-overview'):
            overview = doc.new_tag('div', attrs={'class': 'lead-overview'})
            abstract.replace_with(overview)
            overview.append(abstract)
            overview.append(photo.extract())
        grid = lead.parent
        analysis = grid.find('section', class_='analysis-grid', recursive=False)
        if analysis and content:
            more = doc.new_tag('details', attrs={'class': 'story-more'})
            summary = doc.new_tag('summary')
            summary.string = 'Περισσότερα για το κύριο θέμα'
            more.append(summary)
            more.append(analysis.extract())
            content.append(more)
    for content in doc.select('.hero .story-content, .newscard .story-content'):
        card=content.parent
        depth=card.find('details',class_='depth',recursive=False)
        if depth:
            depth['class']=list(dict.fromkeys(depth.get('class',[])+['story-more']))
            depth.select_one('summary').string='Περισσότερα μέσα στην έκδοση'
            content.append(depth.extract())
        read_link=content.find('a',class_='read-link',recursive=False)
        if read_link:
            read_link.string='Ξεχωριστό άρθρο ↗'
            more=content.find('details',class_='story-more',recursive=False)
            if more:
                read_link.insert_before(more.extract())
        sources = content.find('div', class_='source-links', recursive=False)
        if sources:
            details = doc.new_tag('details', attrs={'class': 'sources-disclosure'})
            summary = doc.new_tag('summary')
            summary.string = 'Πηγές και χρόνοι αναφοράς'
            sources.replace_with(details)
            details.append(summary)
            details.append(sources)
    for node in doc.select('.edition-desk a, .edition-desk span'):
        text = node.get_text(' ', strip=True)
        if node.name == 'span' and ' · ' in text:
            label=text.split(' · ')[0]
            node['title']=label+' · Δεν έχει δημοσιευτεί'
            node['aria-label']=node['title']
            node.string=label+' · —'
            continue
        if ' · ' in text:
            node['title'] = text
            node['aria-label'] = text
            node.string = text.split(' · ')[0]
    if edition_navigation:
        current=doc.select_one('.edition-desk')
        if current:
            current.replace_with(BeautifulSoup(edition_navigation,'html.parser').nav)
    return str(doc)


def newest(records):
    published = [r for r in records if r['status'] == 'published']
    def order(record):
        value = record.get('published_at')
        if value:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        return datetime.fromisoformat(record['date']).replace(tzinfo=timezone.utc).timestamp()
    return max(published, key=order) if published else None


def version_resources(text, root, page_url):
    """Make CSS, scripts and photographs independent of stale browser caches."""
    doc=BeautifulSoup(text,'html.parser')
    docs=(Path(root)/'docs').resolve()
    for node in doc.select('link[href], script[src], img[src]'):
        attr='href' if node.name=='link' else 'src'
        value=node[attr]
        resolved=urljoin(BASE+page_url,value)
        if not resolved.startswith(BASE+'assets/'):
            continue
        relative=urlsplit(resolved).path.removeprefix('/Claude-Briefing/')
        path=(docs/relative).resolve()
        if not path.is_relative_to(docs) or not path.is_file():
            raise ValueError('Missing or unsafe versioned asset: '+relative)
        version=hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        node[attr]=urlsplit(value)._replace(query='v='+version).geturl()
    return str(doc)


def publish(root, records):
    root = Path(root)
    record = newest(records)
    if not record:
        return
    doc = BeautifulSoup(version_resources((root/'docs'/record['url']).read_text(encoding='utf-8'),root,record['url']), 'html.parser')
    source = urljoin(BASE, record['url'])
    for node in doc.find_all(True):
        for attr in ['href', 'src', 'poster']:
            value = node.get(attr)
            if value and not value.startswith(('#', 'data:', 'mailto:', 'tel:')):
                node[attr] = urljoin(source, value)
    for name, value in [('oracle-edition-id', record['id']),
                        ('oracle-published-at', record.get('published_at') or '')]:
        old = doc.find('meta', attrs={'name': name})
        if old:
            old.decompose()
        doc.head.append(doc.new_tag('meta', attrs={'name': name, 'content': value}))
    tools = doc.select_one('.stickybar .tools')
    if tools:
        link = doc.new_tag('a', href=PORTAL+'portal-archive.html#liveWireBar')
        link.string = 'Ροή'
        link['aria-label'] = 'Ροή ειδήσεων'
        link['title'] = 'Ροή ειδήσεων'
        (tools.select_one('.utility-list') or tools).append(link)
    text = str(doc)
    (root/'docs/latest.html').write_text(text, encoding='utf-8', newline='\n')
    asset_hashes={}
    for node in doc.select('link[href], script[src], img[src]'):
        value=node.get('href') or node.get('src')
        if value.startswith(BASE+'assets/'):
            relative=urlsplit(value).path.removeprefix('/Claude-Briefing/')
            path=(root/'docs'/relative).resolve()
            if not path.is_relative_to((root/'docs').resolve()) or not path.is_file():
                raise ValueError('Missing or unsafe latest asset: '+relative)
            asset_hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    html_hash=hashlib.sha256(text.encode('utf-8')).hexdigest()
    version=hashlib.sha256(json.dumps({'html':html_hash,'assets':asset_hashes},sort_keys=True).encode()).hexdigest()
    descriptor = {'schema_version': 1, 'status': 'published', 'edition_id': record['id'],
                  'published_at': record.get('published_at'), 'edition_url': source,
                  'html_url': BASE+'latest.html',
                  'html_sha256': html_hash, 'version':version}
    (root/'docs/data/latest.json').write_text(json.dumps(descriptor, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    return descriptor


def portal_snapshot(public_root, descriptor, page="latest.html"):
    """Return a complete fallback plus only its referenced public assets."""
    public_root = Path(public_root).resolve()
    text = (public_root/'docs'/page).read_text(encoding='utf-8')
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != descriptor['html_sha256']:
        raise ValueError('Latest edition and descriptor do not match')
    doc = BeautifulSoup(text, 'html.parser')
    assets = {}
    for node in doc.select('link[href], script[src], img[src]'):
        attr = 'href' if node.name == 'link' else 'src'
        value = node[attr]
        if not value.startswith(BASE+'assets/'):
            continue
        relative = urlsplit(value).path.removeprefix('/Claude-Briefing/')
        path = (public_root/'docs'/relative).resolve()
        if not path.is_relative_to(public_root/'docs') or not path.is_file():
            raise ValueError('Missing or unsafe snapshot asset: '+relative)
        # Each immutable object is stored once even across many saved releases.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        target = 'assets/snapshot-objects/'+digest+path.suffix.lower()
        assets[target] = path
        node[attr] = target
    doc.head.append(doc.new_tag('meta', attrs={'name': 'oracle-snapshot-sha256', 'content': descriptor['html_sha256']}))
    doc.head.append(doc.new_tag('meta', attrs={'name': 'oracle-snapshot-version', 'content': descriptor['version']}))
    loader = doc.new_tag('script', src='assets/latest-briefing.js')
    loader['defer'] = ''
    doc.head.append(loader)
    return str(doc), assets
