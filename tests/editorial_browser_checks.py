"""DEC-004/005: actual reading layers, cumulative links and original-source access."""
import argparse,functools,json,threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def run(output):
    output.mkdir(parents=True,exist_ok=True)
    model=json.loads((ROOT/'docs/data/days/2026-10-14.json').read_text())
    records={s['story_id']:json.loads((ROOT/'content/articles'/s['selected']['edition_id']/(s['selected']['article_id']+'.json')).read_text()) for s in model['stories']}
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/';checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            for js in [True,False]:
                context=browser.new_context(java_script_enabled=js,reduced_motion='reduce')
                context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
                page=context.new_page()
                for width in [320,375,390,768,1100,1200,1440]:
                    page.set_viewport_size({'width':width,'height':950});page.goto(base+model['url'],wait_until='networkidle')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    assert page.locator('.editorial-revision').is_visible()
                    for sid,a in records.items():
                        card=page.locator('[data-story-id="'+sid+'"]')
                        bar=card.locator('.article-actions')
                        controls=bar.locator(':scope > details > summary,:scope > .story-actions > a')
                        # Compare one layout frame. Separate protocol calls can
                        # straddle native-disclosure scrolling/lazy-image shifts.
                        boxes=controls.evaluate_all('(nodes)=>nodes.map(n=>{const b=n.getBoundingClientRect();return {y:b.y,height:b.height}})')
                        assert len(boxes)==(3 if a['newspaper_analysis'] else 2)
                        assert max(box['y'] for box in boxes)-min(box['y'] for box in boxes)<2,(sid,width,boxes)
                        assert all(box['height']>=44 for box in boxes)
                        assert card.locator('figcaption,.photo-credit').count()==0
                        assert card.locator('.abstract').inner_text()==a['summary']
                        assert card.locator('.reading-layer').is_visible()
                        if a['newspaper_analysis']:
                            assert not card.locator('.card-context').is_visible()
                            trigger=card.locator('.card-analysis>summary');trigger.focus();page.keyboard.press('Enter')
                            assert card.locator('.card-context').is_visible()
                            expanded=card.locator('.card-context').bounding_box()
                            assert expanded['width']>=bar.bounding_box()['width']-2
                            boxes=controls.evaluate_all('(nodes)=>nodes.map(n=>{const b=n.getBoundingClientRect();return {y:b.y,height:b.height}})')
                            aligned=max(box['y'] for box in boxes)-min(box['y'] for box in boxes)<2
                            if not aligned:
                                page.screenshot(path=str(output/f'{width}-{sid}-expanded-alignment-failure.png'),full_page=True)
                            assert aligned,(sid,width,'expanded',boxes)
                            assert all(box['height']>=44 for box in boxes)
                            assert card.locator('.card-context p').all_text_contents()==a['newspaper_analysis']
                            trigger.click()
                        else:assert card.locator('.card-analysis').count()==0
                        if a['reader_mode']=='source':
                            link=card.locator('.original-report');url=link.get_attribute('href')
                            assert url in {s['url'] for s in a['sources'] if s.get('access')=='read' and s.get('used_for_claims')}
                            assert '?from=daily/' not in url
                        else:
                            assert card.locator('.story-actions a[href*="articles/'+a['edition_id']+'/'+a['id']+'.html"]').count()==1
                    if width<1100:
                        page.locator('.section-menu>summary').click()
                        jump=page.locator('.section-menu a[href="#opportunities"]')
                    else:jump=page.locator('.navs a[href="#opportunities"]')
                    assert jump.is_visible();jump.click();assert page.url.endswith('#opportunities')
                    funding=page.locator('#opportunities')
                    assert funding.locator('.opportunities-grid').first.locator(':scope > article').count()==3
                    assert '30/12/2026 · 23:59 Κύπρου' in funding.inner_text()
                    assert '04/11/2026 · 18:00 Κύπρου' in funding.inner_text()
                    assert not funding.locator('#opportunity-cy-new-entrepreneurship-2024-call2').is_visible()
                    funding.locator('.opportunity-watch>summary').click()
                    assert funding.locator('#opportunity-cy-new-entrepreneurship-2024-call2').is_visible()
                    assert page.locator('.image-credits-link').count()==1
                    overview=page.locator('#summary>summary');overview.focus();page.keyboard.press('Enter')
                    assert page.locator('.summary-point:visible').count()==6
                    for link in page.locator('.summary-story-links a').all():
                        assert page.locator(link.get_attribute('href')).count()==1
                    if js and width in [375,1440]:
                        for selector,name in [('#summary','day-overview'),('.day-lead','lead')]:
                            page.locator(selector).screenshot(path=str(output/f'{width}-{name}.png'),style='.stickybar,.skip-link,.back-top{visibility:hidden!important}')
                        cpi=page.locator('[data-story-id="us-september-2026-cpi"]');cpi.locator('.card-analysis>summary').click()
                        cpi.screenshot(path=str(output/f'{width}-cpi-expanded.png'),style='.stickybar,.skip-link,.back-top{visibility:hidden!important}')
                    checks.append({'width':width,'javascript':js,'articles':len(records),'overview_points':6,'result':'passed'})
                context.close()
            browser.close()
    finally:server.shutdown()
    (output/'checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(f'{len(checks)} editorial browser checks passed across {len(records)} articles')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path,default=ROOT/'.work/editorial-preview');run(parser.parse_args().screenshots)
