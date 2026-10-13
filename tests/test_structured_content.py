import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from jsonschema import ValidationError

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('structured_builder',ROOT/'scripts/v2/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class StructuredContentTests(unittest.TestCase):
    def setUp(self):
        build.ROOT=ROOT
        self.edition=json.loads((ROOT/'content/editions/2026-10-12-morning.json').read_text(encoding='utf-8'))
        self.articles=[json.loads((ROOT/'content'/p).read_text(encoding='utf-8')) for p in self.edition['articles']]

    def candidate(self,scenario):
        e=copy.deepcopy(self.edition);aa=copy.deepcopy(self.articles)
        e.update({k:scenario[k] for k in ['date','type','published_at']});e['id']=e['date']+'-'+e['type'];e['url']=e['type']+'/'+e['date']+'.html';e['aliases']=[];e['reader_routes']=[]
        e['articles']=[f'articles/{e["id"]}/{a["id"]}.json' for a in aa]
        for a in aa:a.update(edition_id=e['id'],url=f'articles/{e["id"]}/{a["id"]}.html')
        if scenario['case']=='limited_sports':
            e['sports']['major_stories']=[];e['sports']['major_stories_reason']='Δεν βρέθηκε ουσιαστική νέα είδηση.'
            for t in e['sports']['coverage'].values():t['updates']=[];t['no_update_reason']='Δεν έχει επαληθευτεί ουσιαστική νέα ενημέρωση.'
        if scenario['case']=='missing_fixture':e['sports']['coverage']['manutd']['next_fixture']=None
        if scenario['case']=='missing_market':e['markets']=[{'name':'Μη διαθέσιμο δεδομένο','value':None,'currency':'USD','unit':'μετοχή','status':'unavailable','quoted_at':None,'sources':[]}]
        return e,aa

    def fixture_root(self,directory,e,aa):
        root=Path(directory)
        shutil.copytree(ROOT/'templates',root/'templates')
        shutil.copytree(ROOT/'docs/assets',root/'docs/assets')
        (root/'content/editions').mkdir(parents=True)
        (root/'content/legacy-editions.json').write_text('[]')
        (root/'content/editions'/(e['id']+'.json')).write_text(json.dumps(e))
        for path,a in zip(e['articles'],aa):
            target=root/'content'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(a))
        return root

    def test_three_editions_with_real_missing_data_render_truthful_states(self):
        scenarios=json.loads((ROOT/'tests/fixtures/scenarios.json').read_text(encoding='utf-8'))
        for scenario in scenarios:
            with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as directory:
                e,aa=self.candidate(scenario);root=self.fixture_root(directory,e,aa);build.build(root)
                html=BeautifulSoup((root/'docs'/e['url']).read_text(encoding='utf-8'),'html.parser')
                current=html.select_one('[aria-current=page]')
                self.assertIn(build.TYPES[e['type']],current.text)
                self.assertEqual(len(html.select('[aria-current=page]')),1)
                self.assertEqual(html.select('.edition-desk span')[0]['aria-label'].count('Δεν έχει δημοσιευτεί'),1)
                self.assertIn(e['date'],html.title.text)
                if scenario['case']=='limited_sports':self.assertIn('Δεν βρέθηκε ουσιαστική νέα είδηση.',html.text)
                if scenario['case']=='missing_market':self.assertIn('Μη διαθέσιμη',html.text);self.assertNotIn('7.811,54',html.text)

    def test_missing_article_fails_before_modifying_published_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture_root(directory,self.edition,self.articles)
            marker=root/'docs/index.html';marker.write_text('existing archive')
            (root/'content'/self.edition['articles'][0]).unlink()
            with self.assertRaises(FileNotFoundError):build.build(root)
            self.assertEqual(marker.read_text(encoding='utf-8'),'existing archive')

    def test_scheduled_slot_and_evidence_panels_survive_rebuild(self):
        self.edition['scheduled_slot']='07:30'
        self.edition['summary_60s']=['Η σύντομη επισκόπηση παραμένει χωριστή από την ώρα δημοσίευσης.']
        self.edition['panels']=[{'id':'weather','heading':'Καιρός <script>','paragraphs':['Η πρόγνωση είναι επαληθευμένη και δεν ενημερώνεται αυτόματα.'],'sources':[self.articles[0]['sources'][0]]}]
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture_root(directory,self.edition,self.articles)
            build.build(root)
            rendered=(root/'docs'/self.edition['url']).read_text()
            html=BeautifulSoup(rendered,'html.parser')
            self.assertEqual(html.html['data-edition'],'morning')
            self.assertEqual(html.select_one('meta[name=oracle-edition]')['content'],'morning')
            self.assertIn('07:30',html.select_one('.introbar').text)
            self.assertIn(build.stamp(self.edition['published_at']),html.select_one('.introbar').text)
            self.assertIn(self.edition['summary_60s'][0],html.select_one('#summary').text)
            self.assertIsNone(html.select_one('#weather script'))
            self.assertIn(self.articles[0]['sources'][0]['url'],str(html.select_one('#weather')))

    def test_article_cannot_resolve_to_different_historical_edition(self):
        self.articles[0]['edition_id']='2026-10-11-evening'
        with self.assertRaisesRegex(ValueError,'Historical'):build.validate(self.edition,self.articles)

    def test_readers_are_pinned_to_different_historical_content(self):
        routes=json.loads((ROOT/'docs/data/reader-routes.json').read_text(encoding='utf-8'))
        self.assertEqual(routes['reader.html']['edition_id'],'2026-10-11-evening')
        self.assertEqual(routes['readers/2026-10-12.html']['edition_id'],'2026-10-12-morning')
        old=routes['articles']['2026-10-11-evening']['cyprus-1'];new=routes['articles']['2026-10-12-morning']['cyprus-1']
        self.assertNotEqual(old,new)
        self.assertIn('Μόρφου',(ROOT/'docs'/old).read_text(encoding='utf-8'))
        self.assertIn('Προϋπολογισμός',(ROOT/'docs'/new).read_text(encoding='utf-8'))

    def test_source_indicator_distinguishes_wire_copies_and_inaccessible_content(self):
        first=copy.deepcopy(self.articles[0]['sources'][0]);first['publisher']='Μέσο Α';first['reporting_group']='AFP'
        second=copy.deepcopy(first);second['publisher']='Μέσο Β'
        self.assertEqual(build.sources_label([first,second]),'2 εκδοτικές πηγές · 1 γνωστή αλυσίδα αναφοράς')
        second['reporting_group']='Independent B'
        self.assertIn('2 γνωστές',build.sources_label([first,second]))
        second['access']='inaccessible'
        self.assertIn('1 γνωστή',build.sources_label([first,second]))

    def test_inaccessible_article_cannot_be_used_for_claims(self):
        self.articles[0]['sources'][0].update(access='inaccessible',used_for_claims=True)
        with self.assertRaisesRegex(ValueError,'Inaccessible'):build.validate(self.edition,self.articles)

    def test_private_notes_cannot_be_exported_as_undeclared_article_fields(self):
        self.articles[0]['private_notes']='Personal information must remain private'
        with self.assertRaises(ValidationError):
            build.validate(self.edition,self.articles)

    def test_us_session_is_not_completed_close_at_1930_cyprus(self):
        quote=self.edition['markets'][0]
        quote.update(status='previous_close',quoted_at='2026-10-12T19:30:00+03:00',market_timezone='America/New_York')
        with self.assertRaisesRegex(ValueError,'Ongoing US'):build.validate(self.edition,self.articles)
        quote['status']='delayed';build.validate(self.edition,self.articles)

    def test_dst_conversion_is_not_fixed_utc_plus_three(self):
        self.assertEqual(build.stamp('2026-10-24T21:00:00+00:00'),'25/10/2026 · 00:00 EEST')
        self.assertEqual(build.stamp('2026-10-25T20:00:00+00:00'),'25/10/2026 · 22:00 EET')
        self.assertEqual(build.stamp('2026-10-14T21:00:00+02:00'),'14/10/2026 · 22:00 EEST')

    def test_wrong_publication_day_is_rejected(self):
        self.edition['published_at']='2026-10-12T23:30:00+00:00'
        with self.assertRaisesRegex(ValueError,'local edition date'):build.validate(self.edition,self.articles)

    def test_duplicate_archive_entries_are_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture_root(directory,self.edition,self.articles)
            duplicate={k:self.edition[k] for k in ['id','date','type','status','published_at','title','url']}
            (root/'content/legacy-editions.json').write_text(json.dumps([duplicate]))
            with self.assertRaisesRegex(ValueError,'Duplicate archive'):build.build(root)

    def test_draft_never_becomes_available(self):
        with tempfile.TemporaryDirectory() as directory:
            self.edition['status']='draft';root=self.fixture_root(directory,self.edition,self.articles);build.build(root)
            self.assertEqual(json.loads((root/'docs/data/editions.json').read_text(encoding='utf-8')),[])
            self.assertFalse((root/'docs'/self.edition['url']).exists())

    def test_search_includes_extended_text_and_correct_dated_url(self):
        index=json.loads((ROOT/'docs/search-index.json').read_text(encoding='utf-8'))
        item=next(x for x in index if x['edition_id']=='2026-10-12-morning' and 'Προϋπολογισμός' in x['headline'])
        self.assertIn('παρονομαστής',item['body'])
        self.assertEqual(item['url'],'articles/2026-10-12-morning/cyprus-1.html')

    def test_unsafe_article_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.fixture_root(directory,self.edition,self.articles)
            self.edition['articles'][0]='../private.json'
            (root/'content/editions'/(self.edition['id']+'.json')).write_text(json.dumps(self.edition))
            with self.assertRaisesRegex(ValueError,'Unsafe article path'):build.build(root)

    def test_sports_fixture_without_evidence_is_rejected(self):
        self.edition['sports']['coverage']['realmadrid']['next_fixture']['sources']=[]
        with self.assertRaises(ValidationError):build.validate(self.edition,self.articles)

    def test_published_articles_are_independent_of_edition_html(self):
        a=self.articles[1]
        html=(ROOT/'docs'/a['url']).read_text(encoding='utf-8')
        self.assertIn(a['sections'][1]['paragraphs'][0],html)
        self.assertNotIn('DOMParser',html)
        self.assertNotIn('fetch(',html)

if __name__=='__main__':unittest.main()
