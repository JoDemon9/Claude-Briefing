#!/usr/bin/env python3
"""Bounded official headline metadata; no sports reporting, inferred results or AI."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta, date
from email.utils import parsedate_to_datetime
import importlib.util
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
import urllib.request
from xml.etree import ElementTree
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[2]
LISTINGS={
    'omonoia':'https://www.omonoiafc.com.cy/feed/',
    'manutd':'https://www.manutd.com/en/news/listing/mens-news',
    'realmadrid':'https://www.realmadrid.com/en-US/news/football/first-team',
    'formula1':'https://www.formula1.com/en/latest',
}
MAX_BYTES=2000000
MAX_ITEMS=2
TIMEOUT=12
CACHE_MINUTES=45
MAX_CHECK_AGE_MINUTES=120
SKIP=re.compile(r'\b(women|academy|under-18|under-21|wsl|tickets|shop|sponsor|partnership)\b|εισιτήρ|προπώλη|κατάστημα|διαγωνισ',re.I)


def instant(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Headline checks need timezone offsets')
    return result


def allowed(key,url):
    p=urlsplit(url)
    try:port=p.port
    except ValueError:return False
    return p.scheme=='https' and p.hostname==urlsplit(LISTINGS[key]).hostname and not p.username and not p.password and port in (None,443)


def article_url(key,url):
    if not allowed(key,url):return False
    path=urlsplit(url).path
    if key=='manutd':return path.startswith('/en/news/') and not any(x in path for x in ('/listing/','/category/'))
    if key=='formula1':return path.startswith('/en/latest/article/')
    if key=='realmadrid':return any(path.startswith(p) for p in ('/es-ES/noticias/futbol/primer-equipo/actualidad/','/en-US/news/football/first-team/latest-news/'))
    return path not in ('/','/feed/','/category-news/') and not path.startswith(('/category/','/shop','/tag/'))


def clean(value):return ' '.join(BeautifulSoup(value or '', 'html.parser').get_text(' ',strip=True).split())


def published(value):
    if not value:return None
    value=str(value).strip()
    try:
        if len(value)==10:return date.fromisoformat(value).isoformat()
        return instant(value).isoformat()
    except ValueError:
        try:
            result=parsedate_to_datetime(value)
            return result.isoformat() if result.tzinfo else None
        except (TypeError,ValueError,OverflowError):return None


def not_future(value,at):
    return not value or (date.fromisoformat(value)<=instant(at).astimezone(ZoneInfo('Asia/Nicosia')).date() if len(value)==10 else instant(value)<=instant(at))


def objects(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from objects(child)
    elif isinstance(value,list):
        for child in value:yield from objects(child)


def candidates(key,raw):
    rows=[]
    if key=='omonoia':
        tree=ElementTree.fromstring(raw.lstrip())
        rows=[{'url':n.findtext('link'),'headline':n.findtext('title'),'published_at':published(n.findtext('pubDate'))} for n in tree.findall('.//item')]
    else:
        doc=BeautifulSoup(raw,'html.parser')
        if key=='realmadrid':
            node=doc.select_one('#ng-state')
            if node:
                state=json.loads(node.get_text())
                for item in objects(state):
                    if item.get('tag')=='realmadrid-com:noticias/futbol/primer-equipo/actualidad' and item.get('slug'):
                        # This official route is only a candidate. Fetch and check
                        # its canonical URL/H1 before including it in the output.
                        rows.append({'url':'https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/actualidad/'+item['slug'],
                                     'headline':item.get('title'),'published_at':published(item.get('date'))})
        scope=doc.find('main') or doc
        for a in scope.select('a[href]'):
            url=urljoin(LISTINGS[key],a['href'])
            heading=a.select_one('h1,h2,h3,h4')
            rows.append({'url':url,'headline':heading.get_text(' ',strip=True) if heading else a.get_text(' ',strip=True),'published_at':None})
    unique={}
    for row in rows:
        title=clean(row['headline']);url=row['url'] or ''
        if not article_url(key,url) or not 12<=len(title)<=280 or SKIP.search(title+' '+url):continue
        unique.setdefault(url,{**row,'headline':title})
    return list(unique.values())


def metadata(key,raw,url,fallback):
    doc=BeautifulSoup(raw,'html.parser')
    canonical=doc.select_one('link[rel=canonical]')
    target=urljoin(url,canonical['href']) if canonical and canonical.get('href') else url
    if not article_url(key,target):raise ValueError('Unexpected article canonical')
    title=doc.select_one('h1')
    og=doc.select_one('meta[property="og:title"]')
    headline=clean(title.get_text(' ',strip=True) if title else og.get('content') if og else '')
    if not 12<=len(headline)<=280 or SKIP.search(headline+' '+target):raise ValueError('Missing relevant article headline')
    stamp=doc.select_one('meta[property="article:published_time"],meta[name="date"],time[datetime]')
    timestamp=published(stamp.get('content') or stamp.get('datetime')) if stamp else None
    if not timestamp:
        for script in doc.select('script[type="application/ld+json"]'):
            try:
                for item in objects(json.loads(script.get_text())):
                    if item.get('@type') in ('NewsArticle','Article','BlogPosting'):
                        timestamp=published(item.get('datePublished'))
                        if timestamp:break
            except (ValueError,TypeError):continue
            if timestamp:break
    return {'url':target,'headline':headline,'published_at':timestamp or fallback.get('published_at')}


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,key):self.key=key
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not allowed(self.key,newurl):raise ValueError('Off-provider redirect blocked')
        raise ValueError('Automatic redirects disabled; maintain the official source URL')


def get(key,url,opener=None):
    if not allowed(key,url):raise ValueError('Non-official sports provider')
    open_url=opener or urllib.request.build_opener(OfficialRedirect(key)).open
    req=urllib.request.Request(url,headers={'User-Agent':'OracleSportsHeadlines/1.0','Accept':'text/html,application/rss+xml'})
    with open_url(req,timeout=TIMEOUT) as response:
        if response.status!=200 or not allowed(key,response.geturl()):raise ValueError('Unexpected sports response')
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise ValueError('Sports response exceeded budget')
        return raw,response.geturl()


def validate_record(key,row,at):
    if row['source_url']!=LISTINGS[key] or instant(row['checked_at'])>instant(at):raise ValueError('Invalid sports check provenance/time')
    if row['status'] not in ('available','cached','unavailable'):raise ValueError('Invalid sports source status')
    if row['status']=='unavailable' and not row.get('note'):raise ValueError('Unavailable sports source needs a reason')
    if len(row['items'])>MAX_ITEMS or (row['status']!='unavailable' and not row['items']):raise ValueError('Sports headline inventory missing/excessive')
    seen=set()
    for item in row['items']:
        if not article_url(key,item['url']) or item['url'] in seen:raise ValueError('Unsafe/duplicate sports article link')
        seen.add(item['url'])
        if not 12<=len(item['headline'])<=280:raise ValueError('Invalid sports headline')
        if instant(item['retrieved_at'])>instant(row['checked_at']) or not not_future(item.get('published_at'),item['retrieved_at']):raise ValueError('Future sports metadata')


def collect_one(key,cache,opener=None,now=None):
    clock=now or (lambda:datetime.now(timezone.utc).isoformat())
    at=clock();path=cache/(key+'.json');old={};requests=0
    if path.exists():
        try:
            old=json.loads(path.read_text());validate_record(key,old,at)
        except (ValueError,KeyError,TypeError):old={}
    if old.get('status') in ('available','cached') and timedelta(0)<=instant(at)-instant(old['checked_at'])<timedelta(minutes=CACHE_MINUTES):
        return {**old,'status':'cached'},0
    items=[];failure=None
    try:
        requests+=1;raw,_=get(key,LISTINGS[key],opener)
        rows=[r for r in candidates(key,raw) if not_future(r.get('published_at'),clock())]
        # The RSS headline/date/link is already publisher metadata. HTML article
        # candidates get at most two canonical/H1 checks. There are no retries.
        for row in rows[:MAX_ITEMS]:
            try:
                if key!='omonoia':
                    requests+=1;raw,url=get(key,row['url'],opener);row=metadata(key,raw,url,row)
                retrieved=clock()
                if not not_future(row.get('published_at'),retrieved):raise ValueError('Future article')
                if any(item['url']==row['url'] for item in items):continue
                items.append({**row,'retrieved_at':retrieved})
            except (OSError,ValueError,TimeoutError):failure='article_unavailable'
        if not items:failure=failure or 'no_recognized_headlines'
    except (OSError,ValueError,TimeoutError,ElementTree.ParseError,RecursionError):failure='source_unavailable'
    row={'source_url':LISTINGS[key],'checked_at':clock(),'status':'available' if items else 'unavailable',
         'items':items or old.get('items',[]),'note':failure}
    validate_record(key,row,row['checked_at'])
    # Failed attempts do not replace the last successful source check or make
    # retained metadata appear newly retrieved.
    if items:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
    return row,requests


def collect(cache,opener=None,now=None):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda k:collect_one(k,cache,opener,now),LISTINGS))
    return {'schema_version':1,'news_links':{key:row for key,(row,count) in zip(LISTINGS,results)},
            'http_attempts':sum(count for row,count in results),
            'limits':{'providers':4,'max_http_attempts':10,'attempts_per_url':1,'max_items_per_interest':2,'timeout_seconds':TIMEOUT,'max_response_bytes':MAX_BYTES},
            'scope':'Official headline metadata only; not independently verified reporting, source reading or new result/fixture claims.'}


def validate(edition,root=None):
    # build.validate has already checked any accepted historical contract and
    # source fingerprint. New rules must not invalidate unchanged older sources.
    current=(root is None or edition.get('producer_contract',{}).get('content_schema_sha256')==hashlib.sha256((Path(root)/'templates/v2/content.schema.json').read_bytes()).hexdigest())
    required=current and edition['status']=='published' and edition['date']>='2026-10-19'
    rows=edition['sports'].get('news_links')
    if rows is None:
        if required:raise ValueError('Each favourite needs an explicit headline/source-status check')
        return
    if set(rows)!=set(LISTINGS):raise ValueError('Four favourite headline checks required')
    at=edition.get('editorial_completed_at') or edition.get('published_at')
    for key,row in rows.items():
        validate_record(key,row,at or datetime.now(timezone.utc).isoformat())
        if required and instant(at)-instant(row['checked_at'])>timedelta(minutes=MAX_CHECK_AGE_MINUTES):
            raise ValueError('Favourite headline source check is stale; refresh metadata without redoing reporting')


def apply(root,edition_id,report):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(morning|midday|evening)',edition_id):raise ValueError('Invalid edition id')
    path=Path(root)/'content/editions'/(edition_id+'.json');edition=json.loads(path.read_text())
    if edition['id']!=edition_id or edition['status']!='draft':raise ValueError('Apply sports metadata only to its unpublished draft')
    # Retain an already reviewed translation only for the exact same source
    # headline and URL; changed publisher wording invalidates that translation.
    previous=edition['sports'].get('news_links',{})
    rows=json.loads(json.dumps(report['news_links']))
    for key,row in rows.items():
        for item in row['items']:
            old=next((r for r in previous.get(key,{}).get('items',[]) if r['url']==item['url'] and r['headline']==item['headline']),None)
            if old and old.get('headline_el'):item['headline_el']=old['headline_el']
    edition['sports']['news_links']=rows;validate(edition)
    from jsonschema import Draft202012Validator,FormatChecker
    schema=json.loads((Path(root)/'templates/v2/content.schema.json').read_text())
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(edition)
    spec=importlib.util.spec_from_file_location('sports_atomic',Path(__file__).with_name('atomic.py'));atomic=importlib.util.module_from_spec(spec);spec.loader.exec_module(atomic)
    atomic.write_json(path,edition)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--cache',type=Path);parser.add_argument('--edition',help='Optionally copy headline metadata into this draft')
    args=parser.parse_args();cache=args.cache or args.root/'.work/sports-news'
    if cache.resolve().is_relative_to((args.root/'docs').resolve()):raise ValueError('Source caches must stay private')
    report=collect(cache);target=cache/'report.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if args.edition:apply(args.root,args.edition,report)
    print(json.dumps({'report':str(target),'http_attempts':report['http_attempts'],'limits':report['limits'],
        'interests':{key:{'status':row['status'],'headlines':len(row['items']),'note':row['note']} for key,row in report['news_links'].items()}},ensure_ascii=False))
