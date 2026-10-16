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
        scenarios=json.loads((ROOT/'tests/fixtures/scenarios.json').read_text(encoding='utf-8'))
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
                paths=['/real/morning/2026-10-12.html','/real/articles/2026-10-12-morning/cyprus-1.html','/real/midday/2026-10-12.html','/real/evening/2026-10-12.html','/real/index.html','/real/search.html','/real/daily/2026-10-12.html','/real/daily/2026-10-13.html','/real/daily/index.html']
                registry=json.loads((ROOT/'docs/data/editions.json').read_text())
                latest=registry[0]
                latest_path='/real/'+latest['url']
                if latest_path not in paths:paths.append(latest_path)
                latest_day_path='/real/daily/'+latest['date']+'.html'
                if latest_day_path not in paths:paths.append(latest_day_path)
                latest_source=ROOT/'content/editions'/(latest['id']+'.json')
                photographed=json.loads(latest_source.read_text()) if latest_source.exists() else {}
                if photographed.get('image_review'):
                    for source in (ROOT/'content/editions').glob('*.json'):
                        reviewed=json.loads(source.read_text())
                        if reviewed.get('reading_review'):
                            edition_path='/real/'+reviewed['url']
                            if edition_path not in paths:paths.append(edition_path)
                            paths.extend('/real/articles/'+reviewed['id']+'/'+Path(a).stem+'.html' for a in reviewed['articles'])
                    paths.append('/real/articles/'+latest['id']+'/lead.html')
                    dated_reader=ROOT/'docs/readers'/((latest['date'] if latest['type']=='morning' else latest['id'])+'.html')
                    if dated_reader.exists():paths.append('/real/readers/'+dated_reader.name+'?story=lead')
                for s in scenarios:paths.append('/'+s['type']+'/docs/'+s['type']+'/'+s['date']+'.html')
                for width in [320,375,390,1440]:
                    page.set_viewport_size({'width':width,'height':900})
                    for path in paths:
                        print(f'Checking {width}px {path}',flush=True)
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
                        if '/real/' in path and any('/'+edition+'/' in path for edition in ['morning','midday','evening']):
                            current=page.locator('.edition-desk [aria-current=page]')
                            assert current.count()==1
                            assert current.first.evaluate('(a)=>new URL(a.href).pathname')==path
                        for img in page.locator('[data-editorial-image] img').all():
                            img.evaluate('(img)=>{for(let x=img.parentElement;x;x=x.parentElement)if(x.tagName==="DETAILS")x.open=true}')
                            img.scroll_into_view_if_needed()
                            img.evaluate('(img)=>Promise.race([img.decode(),new Promise((_,reject)=>setTimeout(()=>reject(Error("Image decode timeout")),10000))])')
                            assert img.evaluate('(img)=>img.naturalWidth>=200&&img.naturalHeight>=200'),f'Broken photograph: {path}'
                        if '/real/' in path and page.locator('#cyprus .g3').count():
                            expected_columns=3 if width>=1100 else 1
                            for grid in page.locator('#cyprus .g3,#world .g3').all():
                                assert grid.evaluate('(x)=>getComputedStyle(x).gridTemplateColumns.split(" ").length')==expected_columns,(width,path)
                        if '/real/daily/' in path and not path.endswith('/index.html'):
                            assert page.locator('.edition-desk [aria-current]').count()==0
                            assert page.locator('.core-quotes>.quote-card:visible').count()<=6
                            assert page.locator('.market-movers>.market-note:visible').count()<=3
                            assert page.locator('#markets table.quotes').count()==0
                            assert page.locator('details.day-summary>summary').count()==1
                        checks.append(f'{width}px {path}: no overflow or JavaScript errors')
                        if screenshots and width in [375,1440] and (path in paths[:2] or path in [latest_path,latest_day_path]):
                            screenshots.mkdir(parents=True,exist_ok=True)
                            page.screenshot(path=str(screenshots/(str(width)+'-'+('latest-day' if path==latest_day_path else ('latest-edition' if path==latest_path else ('edition' if '/morning/' in path else 'article')))+'.png')),full_page=True)
                page.set_viewport_size({'width':375,'height':900})
                page.goto(base+'/real/morning/2026-10-12.html')
                link=page.locator('#sports .sport-news-link').first
                link.focus()
                assert link.evaluate('(x)=>document.activeElement===x')
                assert page.locator('#sports .sports-links details').count()==0
                assert page.locator('.edition-desk [aria-current=page]').count()==1
                page.locator('[data-theme-toggle]').click();assert page.locator('html').get_attribute('data-theme')=='dark'
                checks.append('Keyboard sports links, current edition and dark theme passed')
                if photographed.get('image_review'):
                    page.goto(base+latest_path)
                    photos=page.locator('[data-editorial-image] img')
                    expected=sum(json.loads((ROOT/'content'/p).read_text()).get('sports_interest','other')=='other' for p in photographed['articles'])
                    assert photos.count()==expected,'Every rendered article must have a photograph'
                    for relative in photographed['articles']:
                        article=json.loads((ROOT/'content'/relative).read_text())
                        if article.get('sports_interest','other')!='other':continue
                        photo=page.locator('article[id="'+article['id']+'"] [data-editorial-image] img')
                        assert photo.count()==1, f'{latest_path}: article {article["id"]} must render its own photograph'
                        actual_path=photo.evaluate('(img)=>new URL(img.currentSrc||img.src,document.baseURI).pathname')
                        assert actual_path=='/real/'+article['image']['url'],f'{latest_path}: wrong photograph for {article["id"]}: {actual_path}'
                    photos.first.evaluate('(img)=>{img.dispatchEvent(new Event("error"))}')
                    assert page.locator('[data-image-fallback]').first.is_visible()
                    assert page.locator('#main').is_visible()
                    checks.append('Local photographs decode in edition/articles/readers; failed photograph shows readable fallback')
                page.goto(base+'/real/articles/2026-10-12-morning/cyprus-1.html')
                initial=page.evaluate('parseFloat(getComputedStyle(document.querySelector(".prose")).fontSize)')
                page.locator('[data-font-step="1"]').click()
                assert page.evaluate('parseFloat(getComputedStyle(document.querySelector(".prose")).fontSize)')>initial
                page.reload();assert page.evaluate('parseFloat(getComputedStyle(document.querySelector(".prose")).fontSize)')>initial
                assert page.locator('.reader-toc a').count()>0
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
                for edition in ['midday','evening']:
                    page.goto(base+'/real/readers/2026-10-12-'+edition+'.html?story=cyprus-1')
                    page.wait_for_url('**/articles/2026-10-12-'+edition+'/cyprus-1.html')
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
