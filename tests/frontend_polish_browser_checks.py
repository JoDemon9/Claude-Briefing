"""Check the user's visible lead, overview, sports and day-home requirements."""
import argparse
import copy
import functools
import importlib.util
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
    spec=importlib.util.spec_from_file_location('headline_preview_builder',ROOT/'scripts/v2/build.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
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
                        assert page.locator('.reading-layer,.reading-time').count()==0
                        if width<700:
                            assert not page.locator('.hub-guide').is_visible()
                            assert not page.locator('.publication-bar>.edition-desk').is_visible()
                            assert page.locator('.publication-bar').bounding_box()['height']<=72
                            menu=page.locator('.mobile-editions')
                            assert not menu.evaluate('(x)=>x.open')
                            if route!=model['url']:
                                assert {'morning':'Πρωινή','midday':'Μεσημεριανή','evening':'Βραδινή'}[edition['type']] in menu.locator('summary').inner_text()
                            trigger=menu.locator('summary');trigger.focus();page.keyboard.press('Enter')
                            assert menu.locator('.mobile-edition-panel').is_visible()
                            assert menu.locator('.mobile-edition-links a').count()==len(model['editions'])
                            trigger.click()
                            headline=page.locator('.hero h2').bounding_box()
                            photo=page.locator('.hero figure.photo').bounding_box()
                            abstract=page.locator('.hero .story-findings').bounding_box()
                            actions=page.locator('.hero .article-actions').bounding_box()
                            assert headline['y']+headline['height']<=photo['y']+1
                            assert photo['y']+photo['height']<=abstract['y']+1
                            assert abstract['y']+abstract['height']<=actions['y']+1
                        if route==model['url']:
                            for relation in model.get('follow_ups',[]):
                                link=page.locator('[data-follow-up-story-id="'+relation['to_story_id']+'"]')
                                target=link.get_attribute('href')
                                link.click()
                                assert page.locator(target).get_attribute('data-story-id')==relation['to_story_id']
                                assert page.url.endswith(target)

                        # Quick titles inherit the paper theme, not the old dark-panel ink.
                        for theme in ['light','dark']:
                            page.locator('html').evaluate('(x,t)=>x.dataset.theme=t',theme)
                            for title in page.locator('.brief-line a,.brief-line b').all():
                                contrast=title.evaluate("""(x)=>{
                                    const rgba=c=>c.match(/[0-9.]+/g).map(Number);
                                    let parent=x,bg;
                                    while(parent){bg=rgba(getComputedStyle(parent).backgroundColor);if(bg.length===3||bg[3]>0.99)break;parent=parent.parentElement;}
                                    const lum=c=>c.slice(0,3).map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4}).reduce((n,v,i)=>n+v*[0.2126,0.7152,0.0722][i],0);
                                    const a=lum(rgba(getComputedStyle(x).color)),b=lum(bg);
                                    return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
                                }""")
                                assert contrast>=4.5,('Quick-title contrast',theme,width,contrast)
                        page.locator('html').evaluate('(x)=>x.dataset.theme="light"')
                        findings=page.locator('.hero .story-findings')
                        assert not findings.evaluate('(x)=>x.open')
                        assert not findings.locator('.abstract').is_visible()
                        trigger=findings.locator('summary');trigger.focus();page.keyboard.press('Enter')
                        assert findings.locator('.abstract').is_visible()
                        assert findings.locator('.abstract').inner_text()==article['summary']
                        assert trigger.bounding_box()['height']>=44
                        trigger.click()
                        assert not findings.locator('.abstract').is_visible()
                        # DEC-005 keeps analysis optional; newer leads can link
                        # directly to their source without an invented expansion.
                        assert page.locator('.hero .lead-analysis').count()==int(bool(article.get('newspaper_analysis')))
                        assert not page.locator('.hero .card-context').is_visible()
                        if article.get('newspaper_analysis'):
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
                            assert card.locator('a.sport-news-link').count()==1
                            assert card.locator('details,p').count()==0
                            headlines=card.locator('a.sport-headline-link')
                            assert headlines.count()<=2
                            if team['updates']:assert headlines.count()>0
                            for index in range(headlines.count()):
                                headline=headlines.nth(index);headline.scroll_into_view_if_needed()
                                assert headline.is_visible()
                                assert headline.bounding_box()['height']>=44
                            assert card.locator('.sport-check-time').is_visible()
                            assert card.locator('.teamicon').get_attribute('aria-hidden')=='true'
                            logo=card.locator('img.sport-logo');logo.scroll_into_view_if_needed()
                            logo.evaluate('(x)=>x.decode()')
                            assert logo.evaluate('(x)=>x.naturalWidth>0&&x.naturalHeight>0')
                            assert logo.get_attribute('src').startswith('../assets/brands/')
                            assert logo.bounding_box()['width']<=38 and logo.bounding_box()['height']<=38
                            link=card.locator('a.sport-news-link');link.focus()
                            assert link.evaluate('(x)=>document.activeElement===x')
                            assert link.bounding_box()['height']>=44
                            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
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
                            for selector,name in [('.hero','lead'),('.day-summary','overview'),('#sports .sports','sports'),('.publication-bar' if width<700 else '.hub-guide','home')]+([] if is_day else [('.edition-changes','changes')]):
                                page.locator(selector).screenshot(path=str(output/f'{prefix}-{name}.png'),style=style)
                            page.locator('[data-theme-toggle]').click()
                            assert page.locator('html').get_attribute('data-theme')=='dark'
                            for selector,name in [('#sports .sports','sports'),('.day-summary','overview')]+([] if is_day else [('.edition-changes','changes')]):
                                page.locator(selector).screenshot(path=str(output/f'{prefix}-dark-{name}.png'),style=style)
                            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                            page.locator('[data-theme-toggle]').click()
                        checks.append(f'{width}px {route}, JavaScript={js}: visible full lead, native overview/sports, readable changes and canonical home passed')
                # Exercise the new metadata shape too, not only legacy updates.
                fixture=copy.deepcopy(edition);fixture['sports']['news_links']={}
                sports=builder.load_module('sports_news')
                for key,url in sports.LISTINGS.items():
                    article_url={'omonoia':'https://www.omonoiafc.com.cy/fixture-source-',
                        'manutd':'https://www.manutd.com/en/news/fixture-source-',
                        'realmadrid':'https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/actualidad/fixture-source-',
                        'formula1':'https://www.formula1.com/en/latest/article/fixture-source-'}[key]
                    fixture['sports']['news_links'][key]={'source_url':url,'checked_at':'2026-10-18T12:00:00Z',
                        'status':'unavailable' if key=='manutd' else 'available','note':'source_unavailable' if key=='manutd' else None,
                        'items':[{'url':article_url+str(i),'headline':'Επίσημη ενημέρωση για την προετοιμασία και τις εξελίξεις πριν από την επόμενη αγωνιστική υποχρέωση.',
                            'published_at':None if key=='formula1' else '2026-10-17T12:00:00Z','retrieved_at':'2026-10-18T11:00:00Z'} for i in range(2)]}
                html='<html><head><base href="'+base+'"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="assets/newspaper.css"><link rel="stylesheet" href="assets/newspaper-ui.css"></head><body><main class="wrap">'+builder.sports(fixture)+'</main></body></html>'
                for width in [320,375,390,1440]:
                    page.set_viewport_size({'width':width,'height':950});page.set_content(html,wait_until='networkidle')
                    assert page.locator('.sport-headline-link').count()==8
                    assert page.locator('.sports-links details').count()==0
                    assert 'παλιότεροι τίτλοι' in page.locator('.team-manutd').inner_text()
                    assert 'Η πηγή δεν δίνει ημερομηνία' in page.locator('.team-formula1').inner_text()
                    for link in page.locator('.sport-headline-link').all():
                        link.scroll_into_view_if_needed();assert link.is_visible()
                        link.focus();assert link.evaluate('(x)=>document.activeElement===x')
                        assert link.bounding_box()['height']>=44
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    if js and width in [375,1440]:page.locator('#sports').screenshot(path=str(output/f'{width}-favourite-headlines.png'))
                    checks.append(f'{width}px new favourite headlines, JavaScript={js}: all eight visible, dated/unknown/stale states, keyboard targets and no overflow passed')
                context.close()
            browser.close()
    finally:server.shutdown()
    (output/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(checks)} frontend polish browser checks passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path,default=ROOT/'.work/polish-detail-preview');args=parser.parse_args();run(args.screenshots)
