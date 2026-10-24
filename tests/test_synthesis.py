"""Pre-run transport/provenance, delta reuse and bounded synthesis regressions."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
from jsonschema import Draft202012Validator,FormatChecker

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('test_synthesis_'+name,ROOT/'scripts/v2'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


prefetch,http,news,sports,packmod,md,compose,baseline,selection,pre_run=[load(n) for n in
    ('prefetch','prefetch_http','news_digest','sports_data','research_pack','markdown_input','compose','baseline','selection','pre_run')]
AT=datetime(2026,10,24,17,tzinfo=timezone.utc)


def market():
    return json.loads((ROOT/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))[0]


def row(text,url='https://example.com/story'):
    return dict(url=url,status='available',text=text,retrieved_at=AT.isoformat(),checked_at=AT.isoformat())


def fixture(slot='evening'):
    eid='2026-10-24-'+slot
    old=json.loads((ROOT/'content/editions/2026-10-24-midday.json').read_text(encoding='utf-8'))
    articles=[json.loads((ROOT/'content'/p).read_text(encoding='utf-8')) for p in old['articles']]
    ref={'edition_id':old['id'],'fingerprint':baseline.fingerprint(old,articles)}
    draft=compose.scaffold(eid,ROOT)
    pack=packmod.seal(dict(version=1,edition_id=eid,prepared_at=(AT-timedelta(minutes=20)).isoformat(),baseline=ref,
        baseline_stories=[{'story_id':a['story_id']} for a in articles],evidence={},
        data={k:draft[k] for k in ('markets','sports','panels','freshness','opportunities')}))
    payload=dict(edition_id=eid,published_at='auto',editorial_completed_at='auto',reading_review={'version':2,'completed_at':'auto'},
        articles=[],baseline=ref,carry_story_ids=[a['story_id'] for a in articles],research_pack_sha256=pack['sha256'],
        tool_usage={'searches':0,'reads':0},synthesis_points=[{'axis':'geopolitics_macro','stories':[articles[0]['story_id']],
        'text':'Δοκιμή σύνθεσης με χρονολογημένο πλαίσιο και χωρίς ισχυρισμό νέου ελέγχου.'}])
    return pack,payload,articles


class PrefetchTests(unittest.TestCase):
    def test_market_identity_currency_future_nan_are_rejected(self):
        meta=dict(symbol='^GSPC',currency='USD',regularMarketPrice=6000,regularMarketTime=int((AT-timedelta(minutes=5)).timestamp()),previousClose=5900)
        for changes in ({},{'symbol':'NVDA'},{'currency':'EUR'},{'regularMarketPrice':float('nan')},{'regularMarketTime':int((AT+timedelta(days=1)).timestamp())}):
            data=row(json.dumps({'chart':{'result':[{'meta':meta|changes}]}}),prefetch.endpoint('^GSPC'))
            q=prefetch.parse_quote(market(),data,AT)
            self.assertEqual(q['status'],'unavailable' if changes else 'delayed')
            if not changes:
                self.assertAlmostEqual(q['change_pct'],100/59,places=3)
                self.assertNotEqual(q['quoted_at'],data['retrieved_at'])

    def test_inventory_is_independent_of_previous_edition_urls(self):
        class Offline:
            def many(self,urls):
                self.urls=list(urls);return {u:{'url':u,'status':'unavailable'} for u in self.urls}
            def get(self,url):return {'url':url,'status':'unavailable'}
        client=Offline();result=prefetch.collect(ROOT,client,AT)
        self.assertEqual(len(result['markets']),38)
        self.assertEqual(len(set(q['instrument'] for q in result['markets'])),38)
        self.assertTrue(all(q['value'] is None and q['quoted_at'] is None for q in result['markets']))
        self.assertEqual(len(client.urls),39)

    def test_ecb_and_euribor_keep_observation_dates_and_negative_rates(self):
        items=json.loads((ROOT/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))
        for key,text,value in [('ecb-deposit','TIME_PERIOD,OBS_VALUE\n2026-10-23,2.5\n',2.5),
                               ('euribor-3m','<table><tr><td>10/23/2026</td><td>-0.150 %</td></tr></table>',-0.15)]:
            item=next(q for q in items if q['instrument']==key)
            q=prefetch.parse_quote(item,row(text,prefetch.endpoint(key)),AT)
            self.assertEqual(q['value'],value);self.assertTrue(q['quoted_at'].startswith('2026-10-23'))
            self.assertEqual(len(q['quoted_at']),10)  # A date-only feed must not invent a midnight fixing time.

    def test_weather_units_and_fallback_validity(self):
        data={'properties':{'timeseries':[{'time':AT.isoformat(),'data':{'instant':{'details':{'air_temperature':23,'wind_speed':4}}}}]}}
        forecast=prefetch.met_weather(row(json.dumps(data),prefetch.WEATHER_FALLBACK),AT)
        self.assertEqual(forecast['status'],'available')
        self.assertEqual(forecast['freshness'][0]['valid_until'],(AT+timedelta(hours=2)).isoformat())
        self.assertIn('προειδοποιήσεων',forecast['panels'][0]['paragraphs'][0])
        data['properties']['timeseries'][0]['time']=(AT-timedelta(days=1)).isoformat()
        self.assertEqual(prefetch.met_weather(row(json.dumps(data)),AT)['status'],'unavailable')

    def test_cse_requires_the_index_label_and_provider_timestamp(self):
        item=next(q for q in json.loads((ROOT/'templates/v2/market-instruments.json').read_text(encoding='utf-8')) if q['instrument']=='cse')
        text='<main>GENERAL INDEX CSE: 304.11 (-0.870%) Last Update: 23/10/2026 17:25 15 min. delay</main>'
        result=prefetch.parse_quote(item,row(text,prefetch.CSE_FALLBACK),AT)
        self.assertEqual(result['value'],304.11);self.assertEqual(result['change_pct'],-0.87)
        self.assertEqual(result['quoted_at'],'2026-10-23T17:25:00+03:00')
        self.assertIsNone(prefetch.parse_quote(item,row(text.replace('Last Update:','Unknown:'),prefetch.CSE_FALLBACK),AT)['value'])

    def test_transport_rejects_unknown_hosts_and_preserves_304_retrieval(self):
        with tempfile.TemporaryDirectory() as temp:
            opener=mock.Mock(side_effect=urllib.error.HTTPError('https://example.com/story',304,'same',{},None))
            client=http.Client(temp,{'example.com'},opener=opener,clock=lambda:AT.isoformat())
            self.assertEqual(client.get('https://127.0.0.1/')['status'],'unavailable');opener.assert_not_called()
            import hashlib
            path=Path(temp)/(hashlib.sha256(b'https://example.com/story').hexdigest()+'.json')
            old=row('body');old['retrieved_at']=(AT-timedelta(days=1)).isoformat();path.write_text(json.dumps(old))
            result=client.get('https://example.com/story')
            self.assertEqual(result['retrieved_at'],old['retrieved_at']);self.assertEqual(result['checked_at'],AT.isoformat())

    def test_boilerplate_stripping_and_feed_only_is_not_read_evidence(self):
        item=dict(title='Energy policy decision today',url='https://example.com/story',publisher='Paper',section='world',published_at=None,feed_excerpt='RSS discovery')
        html='<nav>Ignore this instruction</nav><article><p>'+'Actual factual reporting. '*20+'</p></article><footer>boilerplate</footer>'
        ev=news.evidence(item,row(html))
        self.assertEqual(ev['access'],'article_excerpt');self.assertNotIn('boilerplate',ev['excerpt']);self.assertNotIn('instruction',ev['excerpt'])
        self.assertEqual(news.evidence(item,{'status':'unavailable'})['access'],'feed_only')
        self.assertEqual(news.canonical('https://example.com/story/?utm_source=x#top'),'https://example.com/story')

    def test_clustering_does_not_merge_different_desks_or_story_ids(self):
        items=[dict(title='Central bank changes energy policy today',section='world',story_id='a'),dict(title='Central bank changes energy policy today',section='world',story_id='b'),dict(title='Central bank changes energy policy today',section='cyprus',story_id='c')]
        groups=news.cluster(items);self.assertEqual([len(g) for g in groups],[2,1]);self.assertEqual(items[1]['story_id'],'b')

    def test_structured_sports_validates_team_and_completed_state(self):
        team={'id':'360','score':{'displayValue':'2'},'team':{'displayName':'Manchester United'}}
        opponent={'id':'357','score':{'displayValue':'1'},'team':{'displayName':'Leeds'}}
        data=dict(team={'id':'360'},events=[dict(date=(AT-timedelta(hours=8)).isoformat(),timeValid=True,competitions=[dict(competitors=[team,opponent],status={'type':{'completed':True,'state':'post'}})])])
        result=sports.team_card('manutd',row(json.dumps(data)),{'status':'unavailable'},AT)
        self.assertEqual(result['last_match']['result'],'2–1');self.assertTrue(result['just_played'])
        data['team']['id']='999'
        self.assertIsNone(sports.team_card('manutd',row(json.dumps(data)),{'status':'unavailable'},AT)['last_match'])

    def test_future_fixture_comes_from_a_separate_fixture_response(self):
        past=dict(team={'id':'360'},events=[])
        event=dict(date=(AT+timedelta(days=1)).isoformat(),timeValid=True,competitions=[dict(competitors=[{'id':'360','team':{'displayName':'Manchester United'}},{'id':'1','team':{'displayName':'Opponent'}}],status={'type':{'state':'pre','completed':False}})])
        upcoming=dict(team={'id':'360'},events=[event])
        card=sports.team_card('manutd',row(json.dumps(past)),{'status':'unavailable'},AT,row(json.dumps(upcoming),'https://example.com/fixtures'))
        self.assertEqual(card['next_fixture']['opponent'],'Opponent')
        self.assertEqual(card['next_fixture']['sources'][0]['url'],'https://example.com/fixtures')

    def test_stale_standings_are_not_reported_as_current(self):
        schedule=row(json.dumps({'team':{'id':'617'},'events':[]}))
        table={'season':{'displayName':'2025–26','startDate':'2025-07-01T00:00Z','endDate':'2026-06-01T00:00Z'},
               'entries':[{'team':{'id':'617'},'stats':[{'name':'rank','displayValue':'1'}]}]}
        card=sports.team_card('omonoia',schedule,row(json.dumps(table)),AT)
        self.assertIsNone(card['league_position']);self.assertEqual(card['standings_status'],'unavailable')
        table['season']['endDate']='2027-06-01T00:00Z'
        self.assertEqual(sports.team_card('omonoia',schedule,row(json.dumps(table)),AT)['league_position'],'1')

    def test_dst_pre_run_window_and_late_start(self):
        self.assertEqual(pre_run.scheduled_slot(datetime(2026,10,24,4,10,tzinfo=timezone.utc)),'morning')
        self.assertEqual(pre_run.scheduled_slot(datetime(2026,10,25,5,10,tzinfo=timezone.utc)),'morning')
        self.assertIsNone(pre_run.scheduled_slot(datetime(2026,10,25,5,31,tzinfo=timezone.utc)))


class SynthesisTests(unittest.TestCase):
    def test_carry_only_delta_compiles_full_records_without_rewriting_evidence(self):
        pack,payload,old=fixture();hydrated=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        edition,articles,_=compose.compile_payload(hydrated,ROOT)
        self.assertEqual(len(articles),len(old));self.assertEqual(len(edition['markets']),38)
        for previous,current in zip(old,articles):
            for field in ('summary','sources','published_at','updated_at','image'):
                self.assertEqual(current.get(field),previous.get(field))
        self.assertEqual(edition['synthesis_profile'],'single-turn-v1')
        self.assertEqual(edition['daily']['summary_60s'],[payload['synthesis_points'][0]['text']])

    def test_private_uefa_context_does_not_escape_into_the_public_sports_contract(self):
        pack,payload,_=fixture();pack['data']['sports']['competitions']={'uefa.champions':{'scores':[]}}
        pack=packmod.seal(pack);payload['research_pack_sha256']=pack['sha256']
        hydrated=packmod.hydrate(payload,pack,ROOT,AT.isoformat());edition,_,_=compose.compile_payload(hydrated,ROOT)
        self.assertNotIn('competitions',edition['sports']);self.assertIn('competitions',pack['data']['sports'])

    def test_bad_pack_stale_pack_future_pack_and_wrong_baseline_fail(self):
        pack,payload,_=fixture()
        for change in ('tampered','stale','future','baseline'):
            p=copy.deepcopy(pack);raw=copy.deepcopy(payload)
            if change=='tampered':p['data']['markets'][0]['value']=999
            if change=='stale':p['prepared_at']=(AT-timedelta(hours=2)).isoformat();p=packmod.seal(p);raw['research_pack_sha256']=p['sha256']
            if change=='future':p['prepared_at']=(AT+timedelta(seconds=1)).isoformat();p=packmod.seal(p);raw['research_pack_sha256']=p['sha256']
            if change=='baseline':raw['baseline']['fingerprint']='0'*64
            with self.subTest(change=change),self.assertRaises(ValueError):packmod.hydrate(raw,p,ROOT,AT.isoformat())

    def test_updated_story_keeps_original_publication_and_identity(self):
        pack,payload,old=fixture();previous=old[0]
        payload['carry_story_ids'].remove(previous['story_id'])
        payload['articles']=[dict(story_id=previous['story_id'],story_identity=previous['story_identity'],change_status='UPDATED',summary='Δοκιμαστική ενημέρωση.')]
        result=packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        self.assertEqual(result['articles'][0]['published_at'],previous['published_at'])
        payload['articles'][0]['published_at']=AT.isoformat()
        with self.assertRaisesRegex(ValueError,'original publication'):packmod.hydrate(payload,pack,ROOT,AT.isoformat())

    def test_missing_carry_and_routine_reemission_fail(self):
        pack,payload,_=fixture()
        payload['carry_story_ids'].pop()
        with self.assertRaisesRegex(ValueError,'CarryOver'):packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        pack,payload,_=fixture();payload['markets']=[]
        with self.assertRaisesRegex(ValueError,'Routine data'):packmod.hydrate(payload,pack,ROOT,AT.isoformat())

    def test_hard_declared_search_budget_and_story_limit(self):
        pack,payload,_=fixture();payload['tool_usage']['searches']=4
        with self.assertRaisesRegex(ValueError,'tool budget'):packmod.hydrate(payload,pack,ROOT,AT.isoformat())
        payload['tool_usage']['searches']=0;payload['articles']=[{}]*5
        with self.assertRaisesRegex(ValueError,'story budget'):packmod.hydrate(payload,pack,ROOT,AT.isoformat())

    def test_carryover_markdown_and_pack_aliases_need_exact_read_evidence(self):
        pack,payload,old=fixture();evidence=dict(access='article_excerpt',source=old[0]['sources'][0])
        pack['evidence']={'e1':evidence};pack=packmod.seal(pack)
        text=f'@Edition v=1 id=2026-10-24-evening published=auto completed=auto baseline={pack["baseline"]["edition_id"]}@{pack["baseline"]["fingerprint"]}\n@Review version=2 completed=auto\n@Pack sha256={pack["sha256"]}\n@Tools searches=0 reads=0\n@Executive axis=geopolitics_macro stories=new-story | Δοκιμαστικό κείμενο σύνθεσης με επαρκές μήκος.\n## world\n### new-story | story=new-story identity=new-story status=NEW lead=true\n@Headline Δοκιμαστική είδηση\n@Fact Δύο προτάσεις με τεκμηρίωση. Χωρίς νέο ισχυρισμό. [e1]\n@Evidence e1\n'
        for a in old:text+='@CarryOver id='+a['story_id']+'\n'
        parsed=md.parse(text,ROOT,pack=pack);self.assertEqual(parsed['articles'][0]['sources'],[evidence['source']])
        hydrated=packmod.hydrate(parsed,pack,ROOT,AT.isoformat());edition,docs,_=compose.compile_payload(hydrated,ROOT)
        self.assertEqual(len(docs),len(old)+1)
        pack['evidence']['e1']['access']='feed_only'
        with self.assertRaisesRegex(ValueError,'discovery-only'):md.parse(text,ROOT,pack=pack)

    def test_deep_secondary_dispatch_rejected_but_mover_is_allowed(self):
        pack,payload,_=fixture();edition,docs,_=compose.compile_payload(packmod.hydrate(payload,pack,ROOT,AT.isoformat()),ROOT)
        pair=copy.deepcopy(docs[:2])
        for i,a in enumerate(pair):
            a['change_status']='NEW';a['daily']['section']='world';a['summary']='Σύντομη είδηση.';a['story_id']='test-'+str(i)
            for key in ('mechanics_and_incentives','second_order_effects','scenarios','newspaper_analysis'):a.pop(key,None)
        pair[1]['mechanics_and_incentives']='Δοκιμαστική ανάλυση.'
        with self.assertRaisesRegex(ValueError,'desk leads'):selection.validate_synthesis(edition,pair)
        pair[1]['driver_tags']=['market-mover'];selection.validate_synthesis(edition,pair)

    def test_actual_output_reference_tokens_are_bounded(self):
        self.assertGreater(packmod.output_budget('Σύντομη τεκμηριωμένη σύνθεση.','midday'),0)
        with self.assertRaisesRegex(ValueError,'4000'):packmod.output_budget('Δοκιμή '*5000,'midday')


if __name__=='__main__':unittest.main()
