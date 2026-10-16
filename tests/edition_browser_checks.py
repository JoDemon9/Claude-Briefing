"""Blocking content-only browser gates for affected editions/readers and the complete current day."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urljoin,urlsplit
from playwright.sync_api import sync_playwright


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def run(root,edition_ids=(),output=None):
    root=Path(root).resolve();output=Path(output or root/'.work/changed-preview');output.mkdir(parents=True,exist_ok=True)
    editions=[json.loads(p.read_text()) for p in (root/'content/editions').glob('*.json')]
    editions=[e for e in editions if e['status']=='published' and e.get('published_at')]
    selected=[e for e in editions if e['id'] in edition_ids]
    if not selected:selected=[max(editions,key=lambda e:e['published_at'])]
    pages={'today.html'}
    for e in selected:
        pages.add(e['url']);pages.add('daily/'+e['date']+'.html')
        for relative in e['articles']:
            article=json.loads((root/'content'/relative).read_text());pages.add(article['url'])
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/';checks=0
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            for js in (True,False):
                context=browser.new_context(java_script_enabled=js,reduced_motion='reduce')
                def route(request):
                    value=request.request.url
                    if value.startswith(base):return request.continue_()
                    if value.startswith('https://jodemon9.github.io/Claude-Briefing/'):
                        name=urlsplit(value).path.removeprefix('/Claude-Briefing/');path=root/'docs'/name
                        if path.is_file():return request.fulfill(path=str(path))
                    return request.abort()
                context.route('**/*',route)
                page=context.new_page()
                for width in (390,1440):
                    page.set_viewport_size({'width':width,'height':950})
                    for relative in sorted(pages):
                        response=page.goto(urljoin(base,relative),wait_until='networkidle')
                        assert response and response.status==200,relative
                        assert page.locator('main').count() and not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),relative
                        # Older sports cards can be inside a native archive disclosure.
                        # Open it as a reader would before testing its lazy photographs.
                        for disclosure in page.locator('details:has(img)').all():
                            if disclosure.get_attribute('open') is None:disclosure.locator(':scope>summary').click()
                        for image in page.locator('img').all():
                            image.scroll_into_view_if_needed()
                            # Native loading still works with page JavaScript disabled;
                            # do not rely on an injected requestAnimationFrame poller.
                            for _ in range(100):
                                if image.evaluate('(x)=>x.complete&&x.naturalWidth>0&&x.naturalHeight>0'):break
                                page.wait_for_timeout(100)
                            else:raise AssertionError((relative,js,width,'Image decode failed',image.get_attribute('src')))
                        for link in page.locator('a[href]').all():
                            href=link.get_attribute('href');resolved=urlsplit(urljoin(urljoin(base,relative),href))
                            if resolved.netloc==urlsplit(base).netloc and not href.startswith('#'):
                                assert (root/'docs'/resolved.path.lstrip('/')).is_file(),(relative,href)
                            elif href.startswith('#') and len(href)>1:
                                assert page.locator('[id="'+href[1:]+'"]').count(),(relative,href)
                        # All native expansion controls remain operable in the no-JS variant.
                        summary=page.locator('.article-actions details>summary').first
                        if summary.count():
                            summary.focus();page.keyboard.press('Enter')
                            assert summary.evaluate('(x)=>x.parentElement.open')
                        checks+=1
                    page.screenshot(path=str(output/f'{width}-{js}.png'),full_page=True)
                context.close()
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'status':'passed','browser_cases':checks,'editions':[e['id'] for e in selected],'viewports':[390,1440],'javascript':[True,False]}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--edition',action='append',default=[]);parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    run(args.root,args.edition,args.screenshots)
