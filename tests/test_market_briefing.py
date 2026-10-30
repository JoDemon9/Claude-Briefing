"""Richer summaries, bounded priority selection and visible market explanations."""
import copy
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bs4 import BeautifulSoup

from test_synthesis import fixture, AT

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('market_test_'+name,ROOT/'scripts/v2'/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

market,packmod,md,compose,selection,view,news,build,prefetch=[load(n) for n in
    ('market_briefing','research_pack','markdown_input','compose','selection','context_view','news_digest','build','prefetch')]

def prepared():
    pack,payload,old=fixture()
    pack['briefing_policy']=market.POLICY;pack['candidates']=[];pack['weather_status']='unavailable'
    q=next(q for q in pack['data']['markets'] if q['instrument']=='GOOGL')
    q.update(value=283.82,change_pct=-12.641,quoted_at=AT.isoformat(),status='delayed',sources=[old[0]['sources'][0]])
    pack['evidence']={'e1':{'id':'e1','title':'Alphabet earnings and guidance','access':'article_excerpt',
        'excerpt':'Alphabet announced new guidance and reported revenue.', 'source':copy.deepcopy(old[0]['sources'][0])}}
    pack['prepared_at']=AT.isoformat()
    pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
    return pack,payload,old


class MarketBriefingTests(unittest.TestCase):
    def test_exceptional_alphabet_move_beats_fixed_core_order_without_invented_cause(self):
        pack,payload,_=prepared()
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertIn('GOOGL',result['market_summary'][0]['text'])
        self.assertIn('-12,64%',result['market_summary'][0]['text'])
        self.assertIn('αιτία δεν έχει επιβεβαιωθεί',result['market_summary'][0]['text'])
        self.assertEqual(result['market_summary'][0]['sources'],pack['data']['markets'][16]['sources'])
        self.assertIn('GOOGL',result['executive_scan']['markets_tech'])
        edition,articles,_=compose.compile_payload(result,ROOT)
        page=BeautifulSoup(build.markets(edition),'html.parser')
        self.assertIn('GOOGL',page.select_one('.market-summary').get_text())
        self.assertIn('Amazon',page.select_one('.tech-table').get_text())
        self.assertEqual(len(edition['markets']),39)

    def test_legacy_presentation_keeps_every_quote_even_with_an_extra_instrument(self):
        pack,payload,_=prepared()
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        edition,_,_=compose.compile_payload(result,ROOT)
        edition.pop('briefing_policy')
        page=BeautifulSoup(build.markets(edition),'html.parser')
        self.assertEqual(len(page.select('[data-quote-key]')),len(edition['markets']))
        self.assertEqual(len(page.select('[data-quote-key="AMZN"]')),1)

    def test_stale_future_nan_and_unavailable_quotes_do_not_generate_alerts(self):
        pack,_,_=prepared();quote=next(q for q in pack['data']['markets'] if q['instrument']=='GOOGL')
        for changes in ({'status':'unavailable'},{'change_pct':float('nan')},
                        {'value':None},{'quoted_at':(AT+timedelta(minutes=1)).isoformat()},
                        {'quoted_at':(AT-timedelta(days=5)).isoformat()},{'sources':[]}):
            self.assertEqual(market.alerts([quote|changes],AT.isoformat()),[])
        self.assertEqual(market.alerts([quote|{'change_pct':1.2}],AT.isoformat()),[])

    def test_amazon_after_hours_move_is_distinct_from_regular_session(self):
        inventory=json.loads((ROOT/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))
        item=next(q for q in inventory if q['instrument']=='AMZN')
        regular=int((AT-timedelta(hours=1)).timestamp());post=int((AT-timedelta(minutes=5)).timestamp())
        meta={'symbol':'AMZN','currency':'USD','regularMarketPrice':200,'regularMarketTime':regular,
              'previousClose':198,'postMarketPrice':180,'postMarketTime':post}
        row={'status':'available','url':prefetch.endpoint('AMZN'),'retrieved_at':AT.isoformat(),
             'text':json.dumps({'chart':{'result':[{'meta':meta}]}})}
        quote=prefetch.parse_quote(item,row,AT)
        self.assertEqual(quote['session'],'post');self.assertEqual(quote['change_pct'],-10)
        self.assertEqual(quote['value'],180)
        note=market.quote_note(market.alerts([quote],AT.isoformat())[0])
        self.assertIn('μετά το κλείσιμο',note['text'])
        self.assertIn('κλείσιμο της κανονικής συνεδρίασης',note['text'])
        meta['postMarketTime']=int((AT+timedelta(minutes=1)).timestamp())
        row['text']=json.dumps({'chart':{'result':[{'meta':meta}]}})
        self.assertEqual(prefetch.parse_quote(item,row,AT)['session'],'regular')
        meta['currentTradingPeriod']={'regular':{'start':regular-7200,'end':regular}}
        row['text']=json.dumps({'chart':{'result':[{'meta':meta}]}})
        self.assertEqual(prefetch.parse_quote(item,row,AT)['status'],'previous_close')

    def test_split_or_inconsistent_reference_does_not_create_false_crash(self):
        item={'instrument':'AMZN','name':'Amazon','currency':'USD','asset_class':'equity'}
        timestamp=int((AT-timedelta(minutes=5)).timestamp())
        meta={'symbol':'AMZN','currency':'USD','regularMarketPrice':100,'regularMarketTime':timestamp,
              'previousClose':200,'regularMarketChangePercent':0}
        row={'status':'available','url':prefetch.endpoint('AMZN'),'retrieved_at':AT.isoformat(),
             'text':json.dumps({'chart':{'result':[{'meta':meta}]}})}
        self.assertIsNone(prefetch.parse_quote(item,row,AT)['change_pct'])
        meta.pop('regularMarketChangePercent')
        row['text']=json.dumps({'chart':{'result':[{'meta':meta,'events':{'splits':{'split':{'date':timestamp}}}}]}})
        self.assertIsNone(prefetch.parse_quote(item,row,AT)['change_pct'])

    def test_market_directive_uses_article_evidence_and_resolves_sources(self):
        pack,payload,_=prepared()
        text='Η Alphabet ανακοίνωσε νέα καθοδήγηση σύμφωνα με το δημοσίευμα, με αβεβαιότητα για την πορεία των εσόδων.'
        payload['market_briefs']=[{'instrument':'GOOGL','evidence':['e1'],'text':text}]
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertIn(text,result['market_movers'][0]['text'])
        self.assertNotIn('αιτία δεν έχει επιβεβαιωθεί',result['market_movers'][0]['text'])
        pack['evidence']['e1']['access']='feed_only';pack=packmod.seal(pack)
        payload['research_pack_sha256']=pack['sha256']
        with self.assertRaisesRegex(ValueError,'article evidence'):
            packmod.hydrate(payload,pack,ROOT,AT.isoformat())

    def test_financial_company_explanation_cannot_use_unrelated_earnings_evidence(self):
        pack,payload,_=prepared()
        q=next(q for q in pack['data']['markets'] if q['instrument']=='GS')
        q.update(value=200,change_pct=-6,quoted_at=AT.isoformat(),status='delayed',sources=[pack['evidence']['e1']['source']])
        payload['market_briefs']=[{'instrument':'GS','evidence':['e1'],
            'text':'Συγκεκριμένη εξήγηση με τεκμηρίωση και διακριτή συνέπεια για τους ενδιαφερόμενους αναγνώστες της έκδοσης.'}]
        pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
        with self.assertRaisesRegex(ValueError,'identify the explained instrument'):
            packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        pack['evidence']['e1']['title']='Goldman Sachs earnings and guidance'
        pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertIn('GS',result['market_movers'][0]['text'])

    def test_priority_is_covered_or_explicitly_omitted_without_fabricated_shortage(self):
        pack,payload,_=prepared()
        ev=copy.deepcopy(pack['evidence']['e1']);ev['source']['url']='https://example.com/binance-security'
        pack['candidates']=[{'id':'c1','priority_required':True,'evidence':[ev]}]
        pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
        with self.assertRaisesRegex(ValueError,'Cover priority candidate c1'):
            packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        payload['priority_skips']={'c1':'Το απόσπασμα δεν επιβεβαιώνει ποιο σύστημα επηρεάστηκε.'}
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertEqual(result['selection_review']['priority_candidates']['c1'],payload['priority_skips']['c1'])
        payload.pop('priority_skips');payload['articles']=[{'story_id':'binance-incident','sources':[ev['source']],
            'headline':'Binance security incident','slug':'binance-incident','summary':'A reported incident requires verification.',
            'driver_tags':['cybersecurity'], 'change_status':'NEW'}]
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertEqual(result['selection_review']['priority_candidates']['c1'],'covered:binance-incident')
        self.assertEqual(result['technology_briefing'][0]['story_id'],'binance-incident')

    def test_secondary_summary_adds_detail_and_sourced_meaning_with_hard_bounds(self):
        pack,payload,_=prepared()
        edition,docs,_=compose.compile_payload(packmod.hydrate(payload,pack,ROOT,AT.isoformat()),ROOT)
        pair=copy.deepcopy(docs[:2])
        for i,article in enumerate(pair):
            article.update(change_status='NEW',story_id='test-'+str(i),summary='λέξη '*72,driver_tags=[])
            article['daily']['section']='world'
            for key in ('mechanics_and_incentives','second_order_effects','scenarios','newspaper_analysis'):article.pop(key,None)
        pair[1]['newspaper_analysis']=['συνέπεια '*18]
        pair[1]['analysis_sources']=[pair[1]['sources'][0]['url']]
        selection.validate_synthesis(edition,pair)
        pair[1]['newspaper_analysis']=['συνέπεια '*19]
        with self.assertRaisesRegex(ValueError,'90 words'):selection.validate_synthesis(edition,pair)
        pair[1]['newspaper_analysis']=[];pair[1]['summary']='λέξη '*76
        with self.assertRaisesRegex(ValueError,'word cap'):selection.validate_synthesis(edition,pair)
        edition.pop('briefing_policy');pair[1]['summary']='λέξη '*72
        with self.assertRaisesRegex(ValueError,'word cap'):selection.validate_synthesis(edition,pair)

    def test_new_directives_parse_without_typed_blocks_or_source_reemission(self):
        pack,_,_=prepared()
        text='''@Edition v=1 id=2026-10-26-evening published=auto completed=auto baseline=none
@Review version=2 completed=auto
## world
### alphabet | story=alphabet identity=alphabet status=NEW lead=true
@Headline Alphabet earnings
@Fact Συγκεκριμένα γεγονότα με τεκμηρίωση. [e1]
@Meaning Διακριτή συνέπεια με πηγή. [e1]
@Evidence e1
@AnalysisSources e1
@Market instrument=GOOGL evidence=e1 | Σύντομη εξήγηση με άρθρο και συγκεκριμένο επόμενο έλεγχο που παραμένει υπό τεκμηρίωση.
@SkipPriority candidate=c2 reason="Το δημοσίευμα δεν επιβεβαιώνει την ταυτότητα του θύματος."
'''
        parsed=md.parse(text,ROOT,pack)
        self.assertEqual(parsed['articles'][0]['newspaper_analysis'],['Διακριτή συνέπεια με πηγή. '])
        self.assertEqual(parsed['market_briefs'][0]['instrument'],'GOOGL')
        self.assertIn('c2',parsed['priority_skips'])

    def test_reservations_and_company_aliases_prioritize_discovery_without_identity_merge(self):
        general=[{'title':'Election report '+str(i),'section':'world','publisher':'a'} for i in range(8)]
        tech={'title':'Amazon earnings guidance cut','section':'world','publisher':'b','topic':'technology','market_priority':8}
        breach={'title':'Binance investigates security breach','section':'world','publisher':'c','topic':'security','market_priority':6}
        ordered=market.reserve([[g] for g in general]+[[tech],[breach]])
        self.assertEqual([g[0] for g in ordered[:2]],[tech,breach])
        self.assertEqual(len(ordered),10)
        self.assertGreater(market.discovery_score('Amazon earnings guidance cut',market_alerts=[{'instrument':'AMZN'}]),
                           market.discovery_score('Election report'))
        self.assertNotIn('story_id',tech)

    def test_legal_breach_and_physical_theft_are_not_cybersecurity(self):
        for title in ('Court finds breach of contract','Ceasefire breach reported overnight','Stolen paintings recovered',
                      'Παραβίαση κατάπαυσης του πυρός','Κλοπή αυτοκινήτου στη Λευκωσία'):
            self.assertNotEqual(market.topic(title),'security')
        for title in ('Binance investigates security breach','Crypto protocol exploit drains wallets','Ransomware attack hits hospital',
                      'Παραβίαση δεδομένων σε εταιρεία'):
            self.assertEqual(market.topic(title),'security')
        groups=[[{'title':str(i),'topic':'security','market_priority':6}] for i in range(8)]
        general=[[{'title':'general-'+str(i)}] for i in range(4)]
        queue=market.reserve(groups+general)
        self.assertEqual(queue[2:6],general)

    def test_enriched_digest_keeps_required_evidence_and_original_budget(self):
        pack,_,_=prepared()
        ev=pack['evidence']['e1'];ev['excerpt']=('Alphabet reported revenue and changed its guidance. '*80)
        pack['candidates']=[{'id':'c1','section':'world','title':'Alphabet earnings','priority_required':True,'evidence':[ev]}]
        before=copy.deepcopy(pack)
        digest=view.synthesis(pack)
        self.assertIn('@Meaning',digest);self.assertIn('@Market',digest)
        self.assertIn('"priority_required":true',digest)
        self.assertIn('"instrument":"GOOGL"',digest)
        self.assertLessEqual(len(digest.encode()),48000)
        self.assertEqual(pack,before)

    def test_busy_digest_preserves_both_priority_candidates_and_seven_sports_lanes(self):
        pack,_,_=prepared()
        pack['data']['sports']={'briefing_policy':'intelligence-v1','coverage':{},'competitions':{}}
        pack['candidates']=[]
        for desk,count in [('cyprus',6),('world',8),('sports',7)]:
            for i in range(count):
                ev=copy.deepcopy(pack['evidence']['e1'])
                ev.update(id=f'{desk}-e{i}',excerpt='Συγκεκριμένα γεγονότα και στοιχεία για τη νέα απόφαση. '*100)
                lane=('omonoia','manutd','realmadrid','formula1','padel','football','other')[i] if desk=='sports' else None
                pack['candidates'].append({'id':f'{desk}-{i}','section':desk,'sports_lane':lane,
                    'title':f'{desk} development {i}','priority_required':desk=='world' and i>=6,'evidence':[ev]})
        digest=view.synthesis(pack)
        headers=[json.loads(line) for line in digest.splitlines() if line.startswith('{"id":') and '"section":' in line]
        self.assertLessEqual(len(digest.encode()),48000)
        self.assertTrue({'world-6','world-7'}<={h['id'] for h in headers})
        self.assertEqual(sum(h['section']=='sports' for h in headers),7)
        self.assertGreaterEqual(sum(h['section']=='cyprus' for h in headers),5)
        self.assertGreaterEqual(sum(h['section']=='world' for h in headers),5)

    def test_topic_fetches_are_reserved_and_repaired_within_24_requests(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'templates/v2').mkdir(parents=True)
            feeds=[dict(publisher=desk,section=desk,url=f'https://example.com/{desk}.rss',hosts=['example.com'])
                   for desk in ('cyprus','world','sports')]
            feeds.append(dict(publisher='Technology',section='world',topic='technology',url='https://example.com/technology.rss',hosts=['example.com']))
            (root/'templates/v2/prefetch-feeds.json').write_text(json.dumps(feeds))
            tokens=('alpha','bravo','charlie','delta','echo','foxtrot','golf','hotel')
            class Client:
                def many(self,urls):
                    result={}
                    for url in urls:
                        if url.endswith('.rss'):
                            lane=url.rsplit('/',1)[1].split('.')[0]
                            items=('indigo','juliet','kilo','lima') if lane=='technology' else tokens
                            text='<rss><channel>'+''.join(f'<item><title>{t} {t} {t} development report</title><link>https://example.com/{lane}/{t}</link></item>' for t in items)+'</channel></rss>'
                        else:text='<article><p>'+'The report describes a specific development with evidence. '*12+'</p></article>'
                        result[url]={'url':url,'text':text,'status':'unavailable' if '/technology/lima' in url else 'available',
                                     'retrieved_at':AT.isoformat()}
                    return result
            collected=news.collect(root,{'stories':[]},Client(),AT,root/'private')
            tech=[c for c in collected['candidates'] if c.get('topic')=='technology' and any(e['access']=='article_excerpt' for e in c['evidence'])]
            self.assertGreaterEqual(len(tech),2)
            self.assertLessEqual(collected['metrics']['article_requests'],24)
            self.assertGreaterEqual(collected['metrics']['pipeline']['cyprus']['readable'],6)

    def test_market_highlights_are_visible_on_mobile_and_without_javascript(self):
        from playwright.sync_api import sync_playwright
        pack,payload,old=prepared()
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        edition,_,_=compose.compile_payload(result,ROOT)
        edition['technology_briefing']=[{'story_id':old[0]['story_id'],'headline':'Δοκιμαστικό θέμα τεχνολογίας','url':old[0]['url']}]
        html='<html lang="el"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+''.join(
            '<link rel="stylesheet" href="/assets/'+name+'">' for name in ('newspaper.css','accessibility.css','newspaper-ui.css'))+(
            '</head><body><main class="wrap">'+build.markets(edition)+'</main></body></html>')
        screenshots=ROOT/'.work/check-logs/market-preview';screenshots.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            for width,js in ((390,True),(1440,False)):
                context=browser.new_context(viewport={'width':width,'height':950},java_script_enabled=js)
                def route(request):
                    path=request.request.url.removeprefix('http://oracle.test/')
                    if path=='preview':return request.fulfill(body=html,content_type='text/html')
                    asset=ROOT/'docs'/path
                    if path.startswith('assets/') and asset.is_file():return request.fulfill(path=str(asset))
                    return request.abort()
                context.route('**/*',route)
                page=context.new_page();page.goto('http://oracle.test/preview',wait_until='load')
                self.assertTrue(page.locator('.market-summary').is_visible())
                self.assertIn('GOOGL',page.locator('.market-summary').inner_text())
                self.assertIn('Η εικόνα των αγορών',page.locator('.market-overview').inner_text())
                self.assertTrue(page.locator('.technology-briefing').is_visible())
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width+1)
                page.locator('.tech-quotes > summary').click()
                self.assertTrue(page.locator('[data-quote-key="AMZN"]').is_visible())
                page.screenshot(path=str(screenshots/f'markets-{width}.png'),full_page=True)
                context.close()
            browser.close()


if __name__=='__main__':unittest.main()
