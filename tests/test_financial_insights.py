"""News-led financial analysis, session comparisons, provenance and unchanged budgets."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from bs4 import BeautifulSoup

from test_market_briefing import prepared, load, ROOT, AT

finance, packmod, compose, view, md, build, news, prefetch = [load(n) for n in
    ('financial_insights','research_pack','compose','context_view','markdown_input','build','news_digest','prefetch')]

REPORTED = ('Η Alphabet ανακοίνωσε αύξηση εσόδων, αλλά η διοίκηση προειδοποίησε για υψηλότερες επενδυτικές δαπάνες. '
            'Το δημοσίευμα αποδίδει την αρνητική αντίδραση στις ανησυχίες για την ταμειακή ροή. '
            'Η σύγκριση με τον δείκτη αφορά τις ίδιες ολοκληρωμένες συνεδριάσεις και προσφέρει πλαίσιο, χωρίς να αποδεικνύει αιτιότητα.')
MEANING = ('Η συντακτική εκτίμηση είναι ότι η ανάπτυξη μπορεί να συνοδεύεται από πίεση στη διαθέσιμη ρευστότητα, '
           'εφόσον οι δαπάνες προηγούνται των νέων εσόδων. Παραμένει αβέβαιο πότε θα αποδώσουν οι επενδύσεις.')
WATCH = 'Παρακολουθούμε την επόμενη δημοσιευμένη ενημέρωση για τις δαπάνες και την ταμειακή ροή.'


def chart(symbol, values, dates=None, **updates):
    dates=dates or ['2026-10-22T13:30:00+00:00','2026-10-23T13:30:00+00:00','2026-10-26T13:30:00+00:00']
    meta=dict(symbol=symbol,currency='USD',currentTradingPeriod={'regular':{'end':int(datetime(2026,10,26,20,tzinfo=timezone.utc).timestamp())}})
    data={'meta':meta,'timestamp':[int(datetime.fromisoformat(d).timestamp()) for d in dates],
          'indicators':{'quote':[{'close':values}]}}
    data.update(updates)
    return dict(status='available',url=prefetch.endpoint(symbol),retrieved_at=AT.isoformat(),
                text=json.dumps({'chart':{'result':[data]}}))


def statistics():
    inventory=json.loads((ROOT/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))
    rows={prefetch.endpoint('GOOGL'):chart('GOOGL',[100,97,10]),
          prefetch.endpoint('^IXIC'):chart('^IXIC',[200,198,400])}
    return finance.context(inventory,rows,AT,prefetch.endpoint)


def current():
    pack,payload,old=prepared()
    pack['evidence']['e1']['source']['url']='https://example.com/alphabet-financial-report'
    pack.update(financial_policy=finance.POLICY,market_context=statistics(),baseline_financial=[])
    pack['candidates']=[dict(id='c1',section='world',title='Alphabet earnings',finance_candidate=True,
                              evidence=[pack['evidence']['e1']])]
    pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
    payload['financial_briefs']=[dict(headline='Επενδύσεις και ταμειακή ροή Alphabet',reported=REPORTED,meaning=MEANING,
        watch=WATCH,instruments=['GOOGL','^IXIC'],evidence=['e1'],statistics=['m1'])]
    payload['financial_shortfall_reason']='Μόνο ένα διακριτό οικονομικό γεγονός τεκμηριώνεται στο διαθέσιμο απόσπασμα.'
    return pack,payload,old


class FinancialInsightTests(unittest.TestCase):
    def test_matching_completed_sessions_exclude_open_and_future_bars(self):
        result=statistics()
        self.assertEqual(len(result),1)
        stat=result[0]
        self.assertEqual((stat['start'],stat['end']),('2026-10-22','2026-10-23'))
        self.assertAlmostEqual(stat['return_pct'],-3)
        self.assertAlmostEqual(stat['benchmark_return_pct'],-1)
        self.assertAlmostEqual(stat['excess_pp'],-2)
        self.assertEqual(len(stat['points']),2)

    def test_missing_mismatched_split_and_future_series_are_withheld(self):
        item=next(q for q in json.loads((ROOT/'templates/v2/market-instruments.json').read_text()) if q['instrument']=='GOOGL')
        for row in (chart('AMZN',[100,97,90]), chart('GOOGL',[100,97,90],events={'splits':{'s':{'date':123}}}),
                    chart('GOOGL',[None,None,None]), chart('GOOGL',[100,97,90])|{'retrieved_at':(AT+timedelta(minutes=1)).isoformat()}):
            self.assertIsNone(finance.completed_series(item,row,AT))
        rows={prefetch.endpoint('GOOGL'):chart('GOOGL',[100,97,10]),
              prefetch.endpoint('^IXIC'):chart('^IXIC',[200,198,400],dates=['2026-10-20T13:30:00+00:00','2026-10-21T13:30:00+00:00','2026-10-26T13:30:00+00:00'])}
        inventory=json.loads((ROOT/'templates/v2/market-instruments.json').read_text())
        self.assertEqual(finance.context(inventory,rows,AT,prefetch.endpoint),[])

    def test_sourced_insight_replaces_price_only_overview_and_renders_chart(self):
        pack,payload,_=current()
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertEqual(result['market_summary'],[]);self.assertEqual(result['market_movers'],[])
        self.assertEqual(result['executive_scan']['markets_tech'],REPORTED)
        edition,_,_=compose.compile_payload(result,ROOT)
        finance.validate(edition)
        page=BeautifulSoup(build.markets(edition),'html.parser')
        self.assertIn(REPORTED,page.select_one('.financial-insight').get_text())
        self.assertIsNone(page.select_one('.market-overview'))
        self.assertIsNotNone(page.select_one('svg[role="img"]'))
        self.assertEqual(len(page.select('.financial-chart tbody tr')),2)
        self.assertIn('-2,00',page.select_one('figcaption').get_text())
        self.assertEqual(len(page.select('[data-quote-key]')),39)
        self.assertFalse(page.select('script'))

    def test_insights_need_article_evidence_word_bounds_and_specific_shortfalls(self):
        for change,error in [('feed','readable article'),('short','70–100'),('reason','FinanceReason'),('stats','statistics'),('duplicate','same reporting')]:
            pack,payload,_=current()
            if change=='feed':pack['evidence']['e1']['access']='feed_only'
            elif change=='short':payload['financial_briefs'][0]['reported']='Μόνο μία φράση.'
            elif change=='reason':payload.pop('financial_shortfall_reason')
            elif change=='stats':payload['financial_briefs'][0]['statistics']=['m99']
            else:payload['financial_briefs']*=2
            pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,error):
                packmod.hydrate(payload,pack,ROOT,AT.isoformat())

    def test_macro_insight_and_unavailable_quotes_do_not_require_a_large_move(self):
        pack,payload,_=current()
        pack['data']['markets']=[q|dict(value=None,change_pct=None,quoted_at=None,status='unavailable',sources=[])
                                 for q in pack['data']['markets']]
        brief=payload['financial_briefs'][0];brief.update(instruments=[],statistics=[])
        pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertEqual(len(result['financial_insights']),1)
        self.assertEqual(result['financial_insights'][0]['statistics'],[])

    def test_insight_evidence_satisfies_priority_without_duplicate_news(self):
        pack,payload,_=current();pack['candidates'][0]['priority_required']=True
        pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertEqual(result['selection_review']['priority_candidates']['c1'],'covered:financial-insight')

    def test_same_day_carry_preserves_original_analysis_and_chart_times(self):
        pack,payload,_=current();result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        pack['baseline_financial']=copy.deepcopy(result['financial_insights'])
        pack['baseline']['edition_id']='2026-10-26-midday'
        pack['prepared_at']=(AT+timedelta(minutes=20)).isoformat()
        carried=dict(carry_financial_insights=[1],financial_shortfall_reason=payload['financial_shortfall_reason'])
        finance.hydrate(carried,pack,load('market_briefing'))
        self.assertEqual(carried['financial_insights'],result['financial_insights'])
        pack['baseline']['edition_id']='2026-10-25-midday'
        with self.assertRaisesRegex(ValueError,'same-day'):
            finance.hydrate(dict(carry_financial_insights=[1],financial_shortfall_reason='Παραμένει η ίδια τεκμηριωμένη ανάλυση.'),pack,load('market_briefing'))

    def test_digest_protects_three_financial_reads_and_seven_sports_lanes(self):
        pack,_,_=current();pack['data']['sports']={'briefing_policy':'intelligence-v1','coverage':{}}
        pack['candidates']=[]
        pack['baseline_stories']=[dict(story_id='baseline-'+str(i),headline='Σημαντική εξέλιξη με επιπτώσεις στην οικονομία και στην καθημερινότητα. '*2,
            finding='Συγκεκριμένες αποφάσεις, χρονολογημένα στοιχεία και συνέπειες για τους ενδιαφερόμενους. '*4,
            section='world' if i%2 else 'cyprus',published_at=AT.isoformat()) for i in range(10)]
        lanes=('omonoia','manutd','realmadrid','formula1','padel','football','other')
        for desk,count in [('cyprus',6),('world',8),('sports',7)]:
            for i in range(count):
                ev=copy.deepcopy(pack['evidence']['e1']);ev.update(id=f'{desk}-e{i}',excerpt='Συγκεκριμένα γεγονότα και αναλυτικά στοιχεία για την απόφαση. '*100)
                ev['source']['url']='https://example.com/'+('a-long-reported-development-'*15)+str(i)
                pack['candidates'].append(dict(id=f'{desk}-{i}',section=desk,title=('Συγκεκριμένη σημαντική εξέλιξη και πρακτικές επιπτώσεις στην οικονομία. '*3)[:220],
                    finance_candidate=desk=='world' and i>=5,sports_lane=lanes[i] if desk=='sports' else None,evidence=[ev]))
        before=copy.deepcopy(pack);digest=view.synthesis(pack)
        self.assertLessEqual(len(digest.encode()),48000)
        self.assertIn('@Insight',digest);self.assertNotIn('optionally @Market',digest)
        self.assertNotIn('"points":',digest)
        for i in range(5,8):self.assertIn('"id":"world-e'+str(i)+'"',digest)
        for i in range(7):self.assertIn('"id":"sports-e'+str(i)+'"',digest)
        self.assertEqual(pack,before)

    def test_financial_excerpt_retains_reported_catalyst_beyond_the_intro(self):
        intro='Alphabet reported quarterly earnings and revenue growth. '
        filler='The company presented an extensive overview of its activities and regional operations. '
        catalyst='Analysts said shares fell because spending guidance exceeded expectations and pressured cash flow margins. '
        selected=news.focused_excerpt(intro+'\n'+filler*30+'\n'+catalyst*2,'Alphabet earnings and guidance',600)
        self.assertIn('cash flow',selected)

    def test_read_budget_reserves_finance_general_news_and_sports(self):
        groups=[]
        for desk,count in [('cyprus',9),('world',10),('sports',7)]:
            for i in range(count):
                item=dict(title=f'{desk} reported decision {i}',url=f'https://example.com/{desk}/{i}',publisher=f'Paper-{i%3}',
                    section=desk,published_at=AT.isoformat(),feed_excerpt='',finance_candidate=desk=='world' and i<3,
                    sports_lane=('omonoia','manutd','realmadrid','formula1','padel','football','other')[i] if desk=='sports' else None)
                groups.append([item])
        class Client:
            def many(self,urls):return {u:dict(url=u,status='available',retrieved_at=AT.isoformat(),
                text='<article><p>'+('Reported policy details, financial consequences and decision timing. '*12)+'</p></article>') for u in urls}
        chosen,pages,evidence=news.financial_collection(groups,Client(),AT)
        self.assertLessEqual(len(pages),24)
        self.assertEqual(sum(i['finance_candidate'] for i in chosen),3)
        self.assertGreaterEqual(sum(i['section']=='world' and not i['finance_candidate'] for i in chosen),4)
        self.assertEqual(sum(i['section']=='sports' for i in chosen),7)
        self.assertTrue(all(e['access']=='article_excerpt' for e in evidence.values()))

    def test_finance_discovery_catches_quiet_macro_and_earnings_but_not_generic_technology(self):
        markets=load('market_briefing')
        for title in ('Inflation expectations rise after tariff announcement','Amazon raises spending guidance','ECB interest rates unchanged','Binance investigates stolen crypto wallets'):
            self.assertTrue(finance.candidate(title,None,markets))
        self.assertFalse(finance.candidate('New phone wallpaper feature launched','technology',markets))

    def test_grammar_parses_structured_insight_and_rejects_old_duplicate_format(self):
        pack,payload,_=current()
        text='\n'.join(['@Edition v=1 id=2026-10-26-evening published=auto completed=auto baseline=none',
            '@Review version=2 completed=auto',
            '@Insight instruments=GOOGL,^IXIC evidence=e1 stats=m1 reported='+json.dumps(REPORTED,ensure_ascii=False)+
            ' meaning='+json.dumps(MEANING,ensure_ascii=False)+' watch='+json.dumps(WATCH,ensure_ascii=False)+' | Επενδύσεις και ταμειακή ροή Alphabet',
            '@FinanceReason Μόνο ένα διακριτό γεγονός διαθέτει πλήρη άρθρα στην παρούσα έκδοση.'])
        parsed=md.parse(text,ROOT,pack)
        self.assertEqual(parsed['financial_briefs'][0]['statistics'],['m1'])
        payload['market_briefs']=[dict(instrument='GOOGL',evidence=['e1'],text='Εξήγηση '*12)]
        with self.assertRaisesRegex(ValueError,'instead of duplicate'):
            packmod.hydrate(payload,pack,ROOT,AT.isoformat())

    def test_public_validation_rejects_tampered_chart_math_and_future_analysis(self):
        pack,payload,_=current()
        edition,_,_=compose.compile_payload(packmod.hydrate(payload,pack,ROOT,AT.isoformat()),ROOT)
        altered=copy.deepcopy(edition);altered['financial_insights'][0]['statistics'][0]['excess_pp']=99
        with self.assertRaisesRegex(ValueError,'statistics disagree'):finance.validate(altered)
        altered=copy.deepcopy(edition);altered['financial_insights'][0]['as_of']=(AT+timedelta(hours=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'future time'):finance.validate(altered)

    def test_insight_and_comparison_are_readable_on_mobile_and_without_javascript(self):
        from playwright.sync_api import sync_playwright
        pack,payload,_=current()
        edition,_,_=compose.compile_payload(packmod.hydrate(payload,pack,ROOT,AT.isoformat()),ROOT)
        html='<html lang="el"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+''.join(
            '<link rel="stylesheet" href="/assets/'+name+'">' for name in ('newspaper.css','accessibility.css','newspaper-ui.css'))+(
            '</head><body><main class="wrap">'+build.markets(edition)+'</main></body></html>')
        folder=ROOT/'.work/check-logs/financial-preview';folder.mkdir(parents=True,exist_ok=True)
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
                self.assertTrue(page.locator('.financial-insight').is_visible())
                self.assertTrue(page.locator('.financial-chart svg').is_visible())
                self.assertIn('συντακτική εκτίμηση',page.locator('.financial-insight').inner_text())
                page.locator('.financial-chart summary').click()
                self.assertTrue(page.locator('.financial-chart table').is_visible())
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width+1)
                page.screenshot(path=str(folder/f'insight-{width}.png'),full_page=True)
                context.close()
            browser.close()


if __name__=='__main__':unittest.main()
