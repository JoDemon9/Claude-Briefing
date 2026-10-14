"""Check the user's visible lead, overview, sports and day-home requirements."""
import argparse
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PUBLIC='https://jodemon9.github.io/Claude-Briefing/'
HUB='https://jodemon9.github.io/oracle-briefing/'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def run(output):
    output.mkdir(parents=True,exist_ok=True)
    descriptor=json.loads((ROOT/'docs/data/day-latest.json').read_text())
    model=json.loads((ROOT/'docs/data/days'/f'{descriptor["day_id"]}.json').read_text())
    edition=json.loads((ROOT/'content/editions'/f'{model["editions"][-1]["id"]}.json').read_text())
    lead=next(s for s in model['stories'] if s['story_id']==model['lead_story_id'])
    article=json.loads((ROOT/'docs/data/articles'/lead['selected']['edition_id']/f'{lead["selected"]["article_id"]}.json').read_text())
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/';checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            for js in [True,False]:
                context=browser.new_context(java_script_enabled=js,reduced_motion='reduce')
                context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
                page=context.new_page()
                for width in [320,375,390,1440]:
                    page.set_viewport_size({'width':width,'height':950})
                    for route in [model['url'],edition['url']]:
                        page.goto(base+route,wait_until='networkidle')
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        assert page.locator('.hub-home').get_attribute('href')==HUB
                        archive=page.locator('.hub-links a').last.get_attribute('href')
                        assert (ROOT/'docs'/route).parent.joinpath(archive).resolve().is_file()
                        assert page.locator('.hero h2').inner_text()==article['headline']
                        assert not page.locator('.hero .card-context').is_visible()
                        detail=page.locator('.hero .lead-analysis>summary');detail.focus();page.keyboard.press('Enter')
                        assert page.locator('.hero .card-context').is_visible()
                        assert page.locator('.hero .card-context p').all_text_contents()==article['newspaper_analysis']
                        detail.click()
                        img=page.locator('.hero img');img.scroll_into_view_if_needed()
                        img.evaluate('(x)=>x.decode()')
                        assert img.evaluate('(x)=>x.naturalWidth>0&&x.naturalHeight>0')
                        summary=page.locator('.day-summary>summary');summary.focus();page.keyboard.press('Enter')
                        assert page.locator('.summary-point:visible').count()==(len(model['overview']['points']) if route==model['url'] else len(edition['summary_60s']))
                        assert page.locator('.summary-point').first.evaluate('(x)=>getComputedStyle(x).fontSize')
                        assert page.locator('.summary-points').evaluate('(x)=>getComputedStyle(x).gridTemplateColumns.split(" ").length')==(3 if width>=1100 else 1)
                        for key,team in edition['sports']['coverage'].items():
                            card=page.locator('.team-'+key)
                            assert team['summary'] in card.inner_text()
                            assert float(card.locator('p').first.evaluate('(x)=>parseFloat(getComputedStyle(x).fontSize)'))>=16
                            assert card.locator('.teamicon').get_attribute('aria-hidden')=='true'
                            more=card.locator('details>summary');more.focus();page.keyboard.press('Enter')
                            assert card.locator('details').evaluate('(x)=>x.open')
                            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                            more.click()
                        is_day=route==model['url']
                        if not is_day:
                            assert page.locator('.edition-change').count()==len(edition['changes'])
                            for para,record in zip(page.locator('.edition-change p').all(),edition['changes']):
                                assert para.inner_text()==record['text']
                                assert para.evaluate('(x)=>parseFloat(getComputedStyle(x).fontSize)')>=16
                                assert para.evaluate('(x)=>parseFloat(getComputedStyle(x).lineHeight)')>=25
                        if js and width in [375,1440]:
                            prefix=f'{width}-'+('day' if is_day else 'edition')
                            style='.stickybar,.back-top,.skip-link{visibility:hidden!important}'
                            for selector,name in [('.hero','lead'),('.day-summary','overview'),('#sports .sports','sports'),('.hub-guide','home')]+([] if is_day else [('.edition-changes','changes')]):
                                page.locator(selector).screenshot(path=str(output/f'{prefix}-{name}.png'),style=style)
                            page.locator('[data-theme-toggle]').click()
                            assert page.locator('html').get_attribute('data-theme')=='dark'
                            for selector,name in [('#sports .sports','sports'),('.day-summary','overview')]+([] if is_day else [('.edition-changes','changes')]):
                                page.locator(selector).screenshot(path=str(output/f'{prefix}-dark-{name}.png'),style=style)
                            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                            page.locator('[data-theme-toggle]').click()
                        checks.append(f'{width}px {route}, JavaScript={js}: visible full lead, native overview/sports, readable changes and canonical home passed')
                context.close()
            browser.close()
    finally:server.shutdown()
    (output/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(checks)} frontend polish browser checks passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path,default=ROOT/'.work/polish-detail-preview');args=parser.parse_args();run(args.screenshots)
