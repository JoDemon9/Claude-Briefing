#!/usr/bin/env python3
"""Bounded public-source collection into private caches. Never write news or verified_at."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[2]
OFFICIAL=('gov.cy','europa.eu','ecb.europa.eu','euribor-rates.eu')
EXACT={'query1.finance.yahoo.com','www.dom.org.cy','www.businessincyprus.gov.cy'}


def module(name):
    spec=importlib.util.spec_from_file_location('collection_'+name,Path(__file__).with_name(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def permitted(url):
    parsed=urlsplit(url);host=(parsed.hostname or '').lower()
    try:port=parsed.port
    except ValueError:return False
    return parsed.scheme=='https' and not parsed.username and not parsed.password and port in (None,443) and (host in EXACT or any(host==suffix or host.endswith('.'+suffix) for suffix in OFFICIAL))


def content(raw,kind):
    if 'html' in kind:
        doc=BeautifulSoup(raw,'html.parser')
        for node in doc.select('script,style,nav,footer'):node.decompose()
        text=' '.join(doc.get_text(' ',strip=True).split())
        return hashlib.sha256(text.encode()).hexdigest(),text
    return hashlib.sha256(raw).hexdigest(),raw.decode('utf-8') if 'json' in kind or kind.startswith('text/') else None


def fetch(url,cache,at,settings,opener=None):
    if not permitted(url):return {'url':url,'status':'manual_source_required','reason':'unsupported_provider'}
    opener=opener or urllib.request.urlopen
    key=hashlib.sha256(url.encode()).hexdigest();path=cache/(key+'.json');old={}
    if path.exists():
        try:old=json.loads(path.read_text())
        except (OSError,ValueError):old={}
    headers={'User-Agent':'OracleEditorialCollector/1.0','Accept':'application/json,text/html,application/pdf;q=0.9'}
    if old.get('etag'):headers['If-None-Match']=old['etag']
    if old.get('last_modified'):headers['If-Modified-Since']=old['last_modified']
    for attempt in range(settings['attempts']):
        try:
            with opener(urllib.request.Request(url,headers=headers),timeout=settings['timeout_seconds']) as response:
                if response.status!=200 or not permitted(response.geturl()):raise ValueError('Unexpected source response')
                raw=response.read(settings['max_bytes']+1)
                if len(raw)>settings['max_bytes']:raise ValueError('Source exceeded size budget')
                kind=response.headers.get_content_type()
                checksum,text=content(raw,kind)
                checked_at=at or datetime.now(timezone.utc).isoformat()
                record={'url':url,'content_sha256':checksum,'retrieved_at':checked_at,'checked_at':checked_at,'content_type':kind,
                    'etag':response.headers.get('ETag'),'last_modified':response.headers.get('Last-Modified'),
                    'text':text[:20000] if text else None,'text_truncated':bool(text and len(text)>20000)}
            module('atomic').write_json(path,record)
            return {**record,'status':'unchanged' if old.get('content_sha256')==checksum else 'changed' if old else 'baseline_requires_review',
                    'requests':attempt+1,'parsed_json':json.loads(raw) if 'json' in kind else None}
        except urllib.error.HTTPError as error:
            if error.code==304 and old.get('content_sha256'):
                record={**old,'checked_at':at or datetime.now(timezone.utc).isoformat()};module('atomic').write_json(path,record)
                return {**record,'status':'unchanged','requests':attempt+1,'retrieved_at':old['retrieved_at'],
                        'parsed_json':json.loads(old['text']) if old.get('text') and not old.get('text_truncated') and 'json' in old.get('content_type','') else None}
            if attempt+1==settings['attempts']:return {'url':url,'status':'unavailable','error_type':type(error).__name__,'requests':attempt+1}
        except (OSError,ValueError,TimeoutError) as error:
            if attempt+1==settings['attempts']:return {'url':url,'status':'unavailable','error_type':type(error).__name__,'requests':attempt+1}
        time.sleep(min(attempt+1,2))
    raise AssertionError('Invalid retry budget')


def yahoo_candidate(quote,result,at):
    """A regular-market snapshot with conservative status; never invent a completed close."""
    if result.get('status')=='unchanged' and not result.get('parsed_json'):return None
    data=result.get('parsed_json')
    if not data:return None
    try:
        chart=data['chart']['result'][0];meta=chart['meta']
        expected=unquote(urlsplit(result['url']).path.rsplit('/',1)[-1])
        instrument={'eurusd':'EURUSD=X','brent':'BZ=F'}.get(quote['instrument'],quote['instrument'])
        if instrument!=expected:return None
        if meta['symbol']!=expected or type(meta['regularMarketTime']) not in (int,float):return None
        value=meta['regularMarketPrice'];currency=meta['currency']
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0 or currency!=quote['currency']:return None
        quoted=datetime.fromtimestamp(meta['regularMarketTime'],timezone.utc)
        if quoted>module('research').instant(at):return None
        candidate={**quote,'value':value,'change_pct':None,'quoted_at':quoted.isoformat(),'status':'delayed',
            'sources':[{'publisher':'Yahoo Finance · δεδομένα αγοράς','url':result['url'],'published_at':None,
                'retrieved_at':result['retrieved_at'],'reporting_group':'Yahoo Finance · δεδομένα αγοράς',
                'kind':'primary','access':'read','used_for_claims':True}]}
        # Previous-close baselines can span several sessions in range=5d responses.
        # Only report a daily percentage when a matching regular-session baseline is explicit.
        daily_previous=meta.get('previousClose')
        candidate['change_pct']=(value/daily_previous-1)*100 if isinstance(daily_previous,(int,float)) and math.isfinite(daily_previous) and daily_previous>0 else None
        return {'quote':candidate,'proof':'Parsed provider regularMarketPrice/regularMarketTime; reported currency/symbol checked.',
                'editorial_checks':['Confirm completed-session labels separately.','Do not infer a price-move catalyst.'],
                'requires_close_review':quote['asset_class'] in ('index','equity')}
    except (KeyError,IndexError,TypeError,ValueError,OverflowError):return None


def collect(root,packet_path,private_root=None,opener=None):
    root=Path(root).resolve();research=module('research');packet=json.loads(Path(packet_path).read_text())
    policy=json.loads((root/'templates/v2/research-policy.json').read_text())
    settings=policy['network'];at=datetime.now(timezone.utc).isoformat()
    folder=research.private_folder(root,private_root) if private_root else root/'.work/research'
    cache=folder/'source-cache';cache.mkdir(parents=True,exist_ok=True)
    jobs={};quotes={};manual=[]
    previous=packet['market_reference']['edition_id']
    if previous:
        edition=json.loads((root/'content/editions'/f'{previous}.json').read_text())
        for quote in edition['markets']:
            sources=[s['url'] for s in quote['sources'] if urlsplit(s['url']).hostname=='query1.finance.yahoo.com' and '/v8/finance/chart/' in urlsplit(s['url']).path]
            if sources:
                url=sources[0];jobs.setdefault(url,[]).append({'kind':'quote','id':quote['instrument']});quotes[url]=quote
            else:
                manual.append({'instrument':quote['instrument'],'quoted_at':quote.get('quoted_at'),
                               'action':'Check a due source or carry the dated reference honestly; no automatic new fixing/close.'})
                for source in quote['sources']:
                    if permitted(source['url']):jobs.setdefault(source['url'],[]).append({'kind':'manual_quote','id':quote['instrument']})
    for item in packet['opportunities']:
        if item['review']['due']:
            for source in item['record']['sources']:
                if source['kind']=='primary':jobs.setdefault(source['url'],[]).append({'kind':'opportunity','id':item['record']['id']})
            application=item['record'].get('application_url')
            if application:jobs.setdefault(application,[]).append({'kind':'application_status','id':item['record']['id']})
    # Weather is always rechecked; source collection does not fabricate a parsed forecast.
    if previous:
        for panel in edition.get('panels',[]):
            if panel['id']=='weather':
                for source in panel['sources']:
                    if permitted(source['url']):jobs.setdefault(source['url'],[]).append({'kind':'weather','id':'weather'})
    def check(item):
        url,owners=item;record=fetch(url,cache,None,settings,opener)
        candidate=yahoo_candidate(quotes[url],record,record.get('retrieved_at',at)) if url in quotes else None
        # Full provider JSON stays in the private cache/report; compact output only links to it.
        record.pop('parsed_json',None)
        return {**record,'owners':owners,'quote_candidate':candidate}
    with ThreadPoolExecutor(max_workers=max(1,min(settings['workers'],6))) as pool:
        records=list(pool.map(check,sorted(jobs.items())))
    report={'schema_version':1,'edition_id':packet['edition_id'],'as_of':at,'packet_as_of':packet['as_of'],'completed_at':datetime.now(timezone.utc).isoformat(),'records':records,
        'manual_quotes':manual,'metrics':{'sources_requested':len(jobs),'http_attempts':sum(r.get('requests',0) for r in records),
            'unchanged_sources':sum(r['status']=='unchanged' for r in records),
            'opportunities_carried':sum(not o['review']['due'] for o in packet['opportunities'])},
        'policy':'No edition/article is modified. verified_at remains an editorial fact. Baseline/changed/failed/due-unknown sources require review.'}
    output=folder/'runs'/packet['edition_id']/'collection.json';module('atomic').write_json(output,report)
    summary={'edition_id':packet['edition_id'],'report':str(output),'metrics':report['metrics'],
        'attention':[{'url':r['url'],'status':r['status'],'owners':r['owners']} for r in records if r['status']!='unchanged' and not r.get('quote_candidate')],
        'quote_candidates':sum(bool(r['quote_candidate']) for r in records)}
    summary['manual_quotes']=manual
    return summary


def apply_quotes(root,edition_id,report_path,approved,at):
    root=Path(root);path=root/'content/editions'/f'{edition_id}.json'
    if not path.resolve().is_relative_to((root/'content/editions').resolve()):raise ValueError('Unsafe edition')
    edition=json.loads(path.read_text());report=json.loads(Path(report_path).read_text())
    if edition['id']!=edition_id or report['edition_id']!=edition_id or edition['status']!='draft':
        raise ValueError('Quote application requires its matching draft edition')
    cutoff=module('research').instant(at);candidates={}
    for row in report['records']:
        candidate=row.get('quote_candidate')
        if candidate:candidates[candidate['quote']['instrument']]=candidate['quote']
    known={q['instrument']:q for q in edition['markets']}
    if not set(approved)<=candidates.keys() or not set(approved)<=known.keys():raise ValueError('Unknown or unavailable approved quote')
    changed=[]
    for instrument in approved:
        new=candidates[instrument];old=known[instrument]
        if any(new[k]!=old[k] for k in ('currency','unit','asset_class')):raise ValueError('Quote identity/unit mismatch')
        if module('research').instant(new['quoted_at'])>cutoff or any(module('research').instant(s['retrieved_at'])>cutoff for s in new['sources']):raise ValueError('Quote evidence is later than its review')
        if not new['sources'] or all(module('research').instant(s['retrieved_at'])<module('research').instant(new['quoted_at']) for s in new['sources']):raise ValueError('Quote cannot be later than all its source retrievals')
        if old.get('quoted_at') and module('research').instant(new['quoted_at'])<module('research').instant(old['quoted_at']):raise ValueError('Never replace a quote with older data')
        if new['status']!='delayed' or not isinstance(new['value'],(int,float)) or not math.isfinite(new['value']):raise ValueError('Invalid provider quote')
        for key in ('value','change_pct','quoted_at','status','sources'):old[key]=new[key]
        changed.append(instrument)
    schema=json.loads((root/'templates/v2/content.schema.json').read_text())
    from jsonschema import Draft202012Validator,FormatChecker
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(edition)
    module('atomic').write_json(path,edition)
    return {'edition_id':edition_id,'updated_quotes':changed,'status':'draft; complete editorial and publication checks'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--packet',type=Path);parser.add_argument('--private-root',type=Path)
    parser.add_argument('--apply-report',type=Path);parser.add_argument('--edition');parser.add_argument('--approve',nargs='+');parser.add_argument('--at')
    args=parser.parse_args()
    result=apply_quotes(args.root,args.edition,args.apply_report,args.approve or [],args.at) if args.apply_report else collect(args.root,args.packet,args.private_root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
