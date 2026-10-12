#!/usr/bin/env python3
"""Exercise served pages and failure states using Chromium. Fixtures stay temporary."""
import argparse
import functools
import importlib.util
import json
import shutil
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def run(screenshots=None):
    with tempfile.TemporaryDirectory() as directory:
        serving=Path(directory)
        shutil.copytree(ROOT/'docs',serving/'real')
        # Representative morning, midday and evening editions are built only here.
        spec=importlib.util.spec_from_file_location('fixture_tests',ROOT/'tests/test_structured_content.py')
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        helper=fixture.StructuredContentTests();helper.setUp()
        scenarios=json.loads((ROOT/'tests/fixtures/scenarios.json').read_text())
        for scenario in scenarios:
            e,aa=helper.candidate(scenario)
            folder=serving/scenario['type'];root=helper.fixture_root(folder,e,aa);fixture.build.build(root)
        handler=functools.partial(QuietHandler,directory=str(serving))
        server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}'
        checks=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,headless=True,args=['--no-sandbox'])
                context=browser.new_context()
                # Tests use local artifacts. No analytics, weather, market API or messaging calls.
                context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) or route.request.url.startswith('data:') else route.abort())
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                paths=['/real/morning/2026-10-12.html','/real/articles/2026-10-12-morning/cyprus-1.html','/real/index.html','/real/search.html']
                for s in scenarios:paths.append('/'+s['type']+'/docs/'+s['type']+'/'+s['date']+'.html')
                for width in [320,375,390,1440]:
                    page.set_viewport_size({'width':width,'height':900})
                    for path in paths:
                        page.goto(base+path,wait_until='networkidle')
                        if not page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'):
                            print(page.evaluate('JSON.stringify([...document.querySelectorAll("*")].filter(e=>e.getBoundingClientRect().right>innerWidth+1||e.scrollWidth>e.clientWidth+2).slice(0,15).map(e=>({tag:e.tagName,cls:e.className,width:e.clientWidth,scroll:e.scrollWidth,whiteSpace:getComputedStyle(e).whiteSpace})))'))
                            if screenshots:
                                screenshots.mkdir(parents=True,exist_ok=True)
                                page.screenshot(path=str(screenshots/('overflow-'+str(width)+'.png')),full_page=True)
                            raise AssertionError(f'Horizontal overflow {width} {path}')
                        for button in page.locator('button:visible').all():
                            rect=button.bounding_box();assert rect['height']>=43,f'Touch target {path} {rect}'
                        assert not errors,(path,errors)
                        checks.append(f'{width}px {path}: no overflow or JavaScript errors')
                        if screenshots and width in [375,1440] and path in paths[:2]:
                            screenshots.mkdir(parents=True,exist_ok=True)
                            page.screenshot(path=str(screenshots/(str(width)+'-'+('edition' if '/morning/' in path else 'article')+'.png')),full_page=True)
                page.set_viewport_size({'width':375,'height':900})
                page.goto(base+'/real/morning/2026-10-12.html')
                summary=page.locator('#sports summary').first
                summary.focus();page.keyboard.press('Enter')
                assert summary.evaluate('(x)=>x.parentElement.open')
                assert page.locator('.edition-desk [aria-current=page]').count()==1
                page.locator('[data-theme-toggle]').click();assert page.locator('html').get_attribute('data-theme')=='dark'
                checks.append('Keyboard sports details, current edition and dark theme passed')
                page.goto(base+'/real/articles/2026-10-12-morning/cyprus-1.html')
                page.locator('[data-bookmark]').click();assert page.locator('[data-bookmark]').get_attribute('aria-pressed')=='true'
                page.evaluate('scrollTo(0,document.documentElement.scrollHeight/2)');page.wait_for_timeout(350)
                page.reload();page.wait_for_timeout(350);page.reload();assert page.locator('[data-resume]').is_visible();page.locator('[data-resume]').click()
                assert page.evaluate('scrollY')>100
                assert page.locator('a[href="../../morning/2026-10-12.html"]').count()>=1
                checks.append('Bookmark, retained reading progress and dated return link passed')
                page.goto(base+'/real/search.html');page.locator('#saved-only').check();page.wait_for_function('document.querySelectorAll(".search-result").length>0')
                assert page.locator('.search-result a').first.get_attribute('href')=='articles/2026-10-12-morning/cyprus-1.html'
                checks.append('Local bookmark list opens the saved dated article')
                page.goto(base+'/real/search.html');page.locator('#query').fill('παρονομαστής');page.wait_for_function('document.querySelectorAll(".search-result").length>0')
                first=page.locator('.search-result a').first;assert first.get_attribute('href')=='articles/2026-10-12-morning/cyprus-1.html'
                first.click();assert '/articles/2026-10-12-morning/cyprus-1.html' in page.url
                checks.append('Search finds body-only terms and opens the correct dated article')
                for path,expected in [('/real/reader.html?story=cyprus-1','Μόρφου'),('/real/readers/2026-10-12.html?story=cyprus-1','Προϋπολογισμός')]:
                    page.goto(base+path);page.wait_for_url('**/articles/**');assert expected in page.locator('h1').inner_text()
                page.goto(base+'/real/readers/2026-10-12.html?story=does-not-exist');page.wait_for_function('document.querySelector("#reader-status").textContent.includes("δεν είναι διαθέσιμο")')
                checks.append('Historical readers and unknown-story error passed')
                page.route('**/data/reader-routes.json',lambda r:r.fulfill(status=404,body='not found'))
                page.goto(base+'/real/readers/2026-10-12.html?story=lead');page.wait_for_function('document.querySelector("#reader-status").textContent.includes("δεν είναι διαθέσιμο")')
                page.unroute('**/data/reader-routes.json')
                page.route('**/search-index.json',lambda r:r.fulfill(status=404,body='not found'))
                page.goto(base+'/real/search.html');page.wait_for_function('document.querySelector("#search-status").textContent.includes("δεν φορτώθηκε")')
                page.unroute('**/search-index.json')
                checks.append('Reader registry failure and missing search content show working error states')
                blocked=browser.new_context()
                blocked.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw new Error("storage blocked")}})')
                blocked.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) or r.request.url.startswith('data:') else r.abort())
                other=blocked.new_page();other.goto(base+'/real/articles/2026-10-12-morning/cyprus-1.html');other.locator('[data-bookmark]').click()
                assert 'δεν είναι διαθέσιμη' in other.locator('[data-storage-status]').inner_text()
                other.locator('[data-theme-toggle]').click();assert other.locator('html').get_attribute('data-theme')=='dark'
                checks.append('Browser storage failure preserves article reading and theme controls')
                browser.close()
        finally:server.shutdown();server.server_close()
        print('\n'.join(checks));print(f'{len(checks)} browser checks passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screenshots',type=Path);args=parser.parse_args();run(args.screenshots)
