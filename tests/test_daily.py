import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
import shutil
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts/v2'/f'{name}.py')
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value
daily = module('daily'); build = module('build'); compact = module('compact_markets')

class DailyTests(unittest.TestCase):
    def setUp(self):
        self.bundles = []
        for slot in daily.SLOTS:
            e = json.loads((ROOT/'content/editions'/f'2026-10-13-{slot}.json').read_text())
            aa = [json.loads((ROOT/'content'/p).read_text()) for p in e['articles']]
            self.bundles.append((e, aa))
        self.now = datetime(2026,10,13,21,tzinfo=timezone.utc)
    def compose(self, bundles=None, previous=None, now=None):
        return daily.compose('2026-10-13', bundles or self.bundles, previous, now=now or self.now)
    def test_three_slots_preserve_distinct_morning_stories_and_select_latest_reader(self):
        morning = self.compose(self.bundles[:1])
        midday = self.compose(self.bundles[:2], morning)
        evening = self.compose(previous=midday)
        self.assertEqual(len(morning['editions']),1)
        self.assertEqual(len(midday['editions']),2)
        self.assertEqual(len(evening['editions']),3)
        first = {s['story_id'] for s in morning['stories']}
        self.assertTrue(first.issubset({s['story_id'] for s in evening['stories']}))
        lead = next(s for s in evening['stories'] if s['story_id']=='2026-10-13-lead')
        self.assertEqual(lead['selected']['edition_id'],'2026-10-13-evening')
        self.assertEqual(len(lead['references']),2)
    def test_hash_text_or_image_change_alone_never_proves_novelty(self):
        e,aa=self.bundles[1]; e['changes']=[]
        aa[0]['story_id']='2026-10-13-lead'
        result=self.compose(self.bundles[:2])
        before=[x for x in result['updates'] if x['origin']['edition_id']==e['id']]
        aa[0]['headline']='Άλλη διατύπωση για την ίδια ιστορία'
        aa[0]['image']['caption']='Άλλη πραγματική λεζάντα φωτογραφίας'
        after=self.compose(self.bundles[:2],result)
        self.assertEqual(before,[x for x in after['updates'] if x['origin']['edition_id']==e['id']])
        self.assertTrue(all(x['kind'] in ('provenance','enrichment') for x in before))
    def test_explicit_substantive_event_records_actual_evidence_and_time(self):
        e,aa=self.bundles[-1]; a=aa[0]
        a['daily']={'events':[{'id':'leaders-result-v1','kind':'substantive_update','at':'2026-10-13T18:20:00+03:00','summary':'Δημοσιεύτηκε τεκμηριωμένη συνέχεια επαφών μετά τη συνάντηση.','source_urls':[a['sources'][0]['url']]}]}
        result=self.compose()
        event=next(x for x in result['updates'] if x['id']=='leaders-result-v1')
        self.assertEqual(event['at'],'2026-10-13T18:20:00+03:00')
        self.assertEqual(event['kind'],'substantive_update')
    def test_correction_and_enrichment_are_separate_from_substantive_development(self):
        e,aa=self.bundles[-1]; e['changes']=[]
        a=aa[0]; original_published=a['published_at']; sources=copy.deepcopy(a['sources'])
        initial=self.compose()
        e['image_revision_at']='2026-10-13T21:15:00+03:00'
        a['daily']={'events':[{'id':'correction-1','kind':'correction','at':'2026-10-13T21:15:00+03:00','summary':'Διόρθωση της διατύπωσης χωρίς νέο πραγματικό γεγονός.','source_urls':[a['sources'][0]['url']]}]}
        result=self.compose(previous=initial,now=datetime(2026,10,13,22,tzinfo=timezone.utc))
        added=[x for x in result['updates'] if x['id'] not in {y['id'] for y in initial['updates']}]
        self.assertEqual({x['kind'] for x in added},{'correction','enrichment'})
        self.assertEqual(a['published_at'],original_published);self.assertEqual(a['sources'],sources)
        self.assertEqual(result['created_at'],initial['created_at'])
        self.assertNotEqual(result['updated_at'],initial['updated_at'])
    def test_reexecution_is_byte_identical_without_duplicate_events(self):
        first=self.compose()
        second=self.compose(previous=first,now=datetime(2026,10,14,3,tzinfo=timezone.utc))
        self.assertEqual(first,second)
        self.assertEqual(len(second['updates']),len({e['id'] for e in second['updates']}))
    def test_partial_day_never_fabricates_morning(self):
        result=self.compose(self.bundles[1:])
        self.assertEqual(result['missing_slots'],['morning'])
        self.assertFalse(any(x['type']=='morning' for x in result['editions']))
    def test_new_day_never_recycles_previous_stories(self):
        first=self.compose()
        e,aa=copy.deepcopy(self.bundles[:1][0]);e['date']='2026-10-14';e['id']='2026-10-14-morning';e['published_at']='2026-10-14T07:30:00+03:00'
        aa=aa[:1];aa[0]['story_id']='different-next-day';e['changes']=[]
        result=daily.compose(e['date'],[(e,aa)],now=self.now)
        self.assertEqual([x['story_id'] for x in result['stories']],['different-next-day'])
        self.assertNotEqual(result['input_sha256'],first['input_sha256'])
    def test_editorial_lead_and_priority_are_explicit(self):
        e,aa=self.bundles[-1];e['daily']={'lead_story_id':aa[1]['story_id']};aa[1]['daily']={'priority':1}
        result=self.compose()
        self.assertEqual(result['lead_story_id'],aa[1]['story_id'])
        self.assertEqual(result['stories'][0]['story_id'],aa[1]['story_id'])
    def test_alias_migration_merges_only_documented_ids(self):
        result=daily.compose('2026-10-13',self.bundles,aliases={'2026-10-13-world-3':'riyadh-airport-disruption'},now=self.now)
        story=next(s for s in result['stories'] if s['story_id']=='riyadh-airport-disruption')
        self.assertEqual(len(story['references']),2)
        self.assertNotIn('2026-10-13-world-3',{s['story_id'] for s in result['stories']})
    def test_unsupported_evidence_rejected_and_no_evidence_is_neutral(self):
        a=self.bundles[-1][1][0]
        event={'id':'one','kind':'substantive_update','at':'2026-10-13T18:20:00+03:00','summary':'Δεν υπάρχει τεκμήριο νέου γεγονότος.','source_urls':[]}
        a['daily']={'events':[event]}
        self.assertEqual(next(x for x in self.compose()['updates'] if x['id']=='one')['kind'],'provenance')
        event['source_urls']=['https://example.com/unreviewed']
        with self.assertRaisesRegex(ValueError,'reviewed article'):self.compose()
    def test_dst_athens_and_nicosia_use_zone_database(self):
        for tz in ['Europe/Athens','Asia/Nicosia']:
            self.assertIn('00:00',build.stamp('2026-10-24T21:00:00Z',tz))
            self.assertIn('22:00',build.stamp('2026-10-25T20:00:00Z',tz))
    def test_quote_instants_and_unknown_same_day_close_remain_truthful(self):
        old={'status':'delayed','quoted_at':'2026-10-13T19:30:00+03:00'}
        new={'status':'delayed','quoted_at':'2026-10-13T17:00:00Z'}
        self.assertTrue(daily.newer_quote(new,old,'Europe/Athens'))
        self.assertFalse(daily.newer_quote(old,new,'Europe/Athens'))
        closed={'status':'previous_close','quoted_at':'2026-10-13'}
        self.assertTrue(daily.newer_quote(closed,new,'Europe/Athens'))
        self.assertFalse(daily.newer_quote({'status':'unavailable','quoted_at':None},new,'Europe/Athens'))
        self.assertEqual(closed['quoted_at'],'2026-10-13')
    def test_daily_page_uses_published_refs_and_contributing_slots(self):
        build.ROOT=ROOT
        model=self.compose();daily.validate(ROOT,model,self.bundles)
        rendered=BeautifulSoup(daily.render(build,model,self.bundles),'html.parser')
        self.assertFalse(rendered.select('.edition-desk [aria-current]'))
        self.assertEqual(len(rendered.select('[data-story-id]')),len(model['stories']))
        self.assertIn('Συμμετέχουσες',rendered.select_one('.edition-desk').text)
        self.assertTrue(all('articles/' in a['href'] for a in rendered.select('.story-history a')))
    def test_missing_reader_or_edition_rejected(self):
        model=self.compose();model['stories'][0]['selected']['url']='articles/not-found.html'
        with self.assertRaisesRegex(ValueError,'unavailable reader'):daily.validate(ROOT,model,self.bundles)
    def test_compact_markets_preserves_every_quote_without_initial_long_table(self):
        e=self.bundles[-1][0];doc=BeautifulSoup(build.markets(e),'html.parser')
        self.assertLessEqual(len(doc.select('.core-quotes>.quote-card')),6)
        self.assertEqual(len(doc.select('[data-quote-key]')),len(e['markets']))
        self.assertFalse(doc.select('.quotes'))
        self.assertLessEqual(len(doc.select('.market-movers>.market-note')),3)
        for q in e['markets']:
            self.assertIn(build.stamp(q['quoted_at']),doc.text)
        self.assertNotIn('Ζωντανή',doc.text)
    def test_core_selection_can_change_without_deleting_full_dataset(self):
        e=self.bundles[-1][0];e['market_core']=['^FTSE','^GSPC']
        doc=BeautifulSoup(build.markets(e),'html.parser')
        self.assertEqual([x['data-quote-key'] for x in doc.select('.core-quotes>.quote-card')],['^FTSE','^GSPC'])
        self.assertEqual(len(doc.select('[data-quote-key]')),len(e['markets']))

    def fixture(self, directory):
        root=Path(directory)
        for folder in ('content','templates','docs'):
            shutil.copytree(ROOT/folder,root/folder)
        return root

    def test_invalid_image_preserves_previous_day_and_independent_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory)
            before={p:(root/'docs'/p).read_bytes() for p in ('today.html','latest.html','daily/2026-10-13.html')}
            image=self.bundles[-1][1][0]['image']['url']
            (root/'docs'/image).write_bytes(b'not an image')
            with self.assertRaises(Exception):build.build(root)
            for p,raw in before.items():self.assertEqual((root/'docs'/p).read_bytes(),raw)

    def test_correction_build_updates_day_without_changing_publication_or_quotes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory)
            e=self.bundles[-1][0];quote_times=[q['quoted_at'] for q in e['markets']]
            target=root/'content'/e['articles'][0];a=json.loads(target.read_text())
            published=a['published_at']
            a['headline']+=' · συντακτική διόρθωση'
            a['daily']={'events':[{'id':'integrated-correction','kind':'correction','at':'2026-10-13T22:00:00+03:00','summary':'Διόρθωση διατύπωσης χωρίς νέο γεγονός.','source_urls':[a['sources'][0]['url']]}]}
            target.write_text(json.dumps(a,ensure_ascii=False))
            build.build(root)
            corrected_day=root/'docs/daily'/f'{e["date"]}.html'
            first=corrected_day.read_bytes()
            self.assertIn('συντακτική διόρθωση',first.decode())
            latest_day=json.loads((root/'docs/data/day-latest.json').read_text())['day_id']
            if latest_day!=e['date']:
                self.assertNotIn('συντακτική διόρθωση',(root/'docs/today.html').read_text())
            model=json.loads((root/'docs/data/days/2026-10-13.json').read_text())
            self.assertEqual(next(x for x in model['updates'] if x['id']=='integrated-correction')['kind'],'correction')
            build.build(root)
            self.assertEqual(corrected_day.read_bytes(),first)
            self.assertEqual(json.loads(target.read_text())['published_at'],published)
            self.assertEqual([q['quoted_at'] for q in json.loads((root/'content/editions'/f'{e["id"]}.json').read_text())['markets']],quote_times)

    def test_changing_original_publication_timestamp_is_rejected_before_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture(directory)
            marker=(root/'docs/today.html').read_bytes()
            target=root/'content/editions/2026-10-13-evening.json';e=json.loads(target.read_text());e['published_at']='2026-10-13T21:30:00+03:00';target.write_text(json.dumps(e))
            with self.assertRaisesRegex(ValueError,'original edition published_at'):build.build(root)
            self.assertEqual((root/'docs/today.html').read_bytes(),marker)

    def test_all_quotes_reachable_in_partial_dashboard_and_movers_are_limited(self):
        e=self.bundles[0][0]
        e['market_movers']=[{'text':'Πραγματική κίνηση με συγκεκριμένη τεκμηρίωση '+str(i),'sources':[e['markets'][0]['sources'][0]]} for i in range(5)]
        doc=BeautifulSoup(build.markets(e),'html.parser')
        self.assertEqual(len(doc.select('.market-movers>.market-note')),3)
        self.assertEqual(len(doc.select('.market-movers>details .market-note')),2)
        self.assertEqual(len(doc.select('[data-quote-key]')),len(e['markets']))

if __name__=='__main__':unittest.main()
