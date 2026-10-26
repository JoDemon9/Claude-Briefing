"""Small daily preview: edition/day at mobile JS-on and desktop JS-off."""
import argparse
import functools
import importlib.util
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ORIGIN='https://jodemon9.github.io/Claude-Briefing/'
CASES=((390,True),(1440,False))


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def preview_plan(root,edition_ids=()):
    root=Path(root).resolve()
    spec=importlib.util.spec_from_file_location('preview_checks',root/'scripts/v2/checks.py')
    checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
    editions=checks.selected_editions(root,edition_ids);pages={}
    def article(e,aid):
        return json.loads((root/'content/articles'/e/(aid+'.json')).read_text())
    for e in editions:
        articles=[json.loads((root/'content'/p).read_text()) for p in e['articles']]
        lead=next((a for a in articles if a['story_id']==e.get('daily',{}).get('lead_story_id')),articles[0])
        pages[e['url']]=lead
        day_path=root/'docs/data/days'/(e['date']+'.json')
        if not day_path.exists() and e.get('preserve_legacy_html') and not e.get('published_at'):
            continue  # Unknown original publication time: preview its repaired edition only.
        day=json.loads(day_path.read_text())
        selected=next(s['selected'] for s in day['stories'] if s['story_id']==day['lead_story_id'])
        pages[day['url']]=article(selected['edition_id'],selected['article_id'])
    return editions,pages


def check_local_links(root,relative):
    """Check current-page local links/assets once without opening every reader."""
    docs=Path(root)/'docs';path=docs/relative
    doc=BeautifulSoup(path.read_text(),'html.parser')
    if not doc.select_one('main'):raise ValueError('Preview has no main content: '+relative)
    for node in doc.select('a[href],img[src],link[href],script[src]'):
        value=node.get('href') or node.get('src');resolved=urljoin(ORIGIN+relative,value)
        if not resolved.startswith(ORIGIN):continue
        parsed=urlsplit(resolved);target=(docs/parsed.path.removeprefix('/Claude-Briefing/')).resolve()
        if not target.is_relative_to(docs.resolve()) or not target.is_file():
            raise ValueError('Missing/unsafe local preview link: '+relative+' -> '+value)
        if len(value)>1 and value.startswith('#') and not doc.find(id=parsed.fragment):
            raise ValueError('Missing preview anchor: '+relative+' -> '+value)


def run(root,edition_ids=(),output=None):
    root=Path(root).resolve();editions,pages=preview_plan(root,edition_ids)
    output=Path(output) if output else None
    if output:output.mkdir(parents=True,exist_ok=True)
    for relative in pages:check_local_links(root,relative)
    if sync_playwright is None:
        raise ValueError('Playwright is required for the blocking preview gate; local links alone are insufficient')
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/';count=0
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            for width,js in CASES:
                context=browser.new_context(java_script_enabled=js,reduced_motion='reduce',viewport={'width':width,'height':950})
                def route(request):
                    value=request.request.url
                    if value.startswith(base):return request.continue_()
                    if value.startswith(ORIGIN):
                        path=root/'docs'/urlsplit(value).path.removeprefix('/Claude-Briefing/')
                        if path.is_file():return request.fulfill(path=str(path))
                    return request.abort()
                context.route('**/*',route);page=context.new_page();errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                for relative,lead in sorted(pages.items()):
                    print(json.dumps({'preview':relative,'width':width,'javascript':js}),flush=True)
                    response=page.goto(urljoin(base,relative),wait_until='load')
                    assert response and response.status==200,relative
                    assert page.locator('main').is_visible(),relative
                    assert page.locator('.hero h2').inner_text()==lead['headline'],relative
                    findings=page.locator('.hero .story-findings')
                    if findings.count():
                        initially_open=bool(page.locator('html[data-intelligence="1"]').count())
                        assert findings.evaluate('(x)=>x.open')==initially_open
                        toggle=findings.locator('summary');toggle.focus();page.keyboard.press('Enter')
                        if initially_open:page.keyboard.press('Enter')
                        assert findings.locator('.abstract').is_visible()
                        assert findings.locator('.abstract').inner_text()==lead['summary']
                        assert toggle.bounding_box()['height']>=44
                        toggle.click();assert not findings.locator('.abstract').is_visible()
                    else:
                        assert page.locator('.hero .abstract').inner_text()==lead['summary']
                    if lead.get('image'):
                        image=page.locator('.hero img').first;image.scroll_into_view_if_needed()
                        image.evaluate('(x)=>x.decode()')
                        assert image.evaluate('(x)=>x.naturalWidth>0&&x.naturalHeight>0')
                    assert not errors,(relative,errors)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),relative
                    count+=1
                    if output:page.screenshot(path=str(output/(str(width)+'-'+relative.replace('/','-')+'.png')))
                context.close()
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'status':'passed','browser_cases':count,'pages':list(pages),'editions':[e['id'] for e in editions],
        'configurations':[{'width':width,'javascript':js} for width,js in CASES]}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--edition',action='append',default=[]);parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    run(args.root,args.edition,args.screenshots)
