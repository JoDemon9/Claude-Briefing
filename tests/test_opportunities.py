import copy,importlib.util,json,unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('opportunities',ROOT/'scripts/v2/opportunities.py');op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)
spec=importlib.util.spec_from_file_location('opportunity_build',ROOT/'scripts/v2/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class OpportunitiesTests(unittest.TestCase):
    def setUp(self):
        self.records=json.loads((ROOT/'content/editions/2026-10-14-evening.json').read_text())['opportunities']
    def test_verified_official_records_and_deadline_time_conversion(self):
        op.validate(self.records)
        html=op.render(b,self.records)
        self.assertIn('04/11/2026 · 18:00 Κύπρου',html)
        self.assertIn('30/12/2026 · 23:59 Κύπρου',html)
        self.assertIn('Συνεχής υποβολή',html)
        doc=BeautifulSoup(html,'html.parser')
        self.assertEqual(len(doc.select('.opportunities-grid')[0].find_all('article',recursive=False)),3)
        closed=doc.find(id='opportunity-cy-new-entrepreneurship-2024-call2')
        self.assertEqual(closed.find_parent('details')['class'],['opportunity-watch'])
        self.assertIn('2024',closed.get_text())
    def test_reject_expired_and_premature_open_calls(self):
        for key,value in [('deadline','2020-01-01T12:00:00+03:00'),('status','open')]:
            records=copy.deepcopy(self.records);records[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):op.validate(records)
    def test_requires_read_primary_sources_and_real_verification(self):
        for key,value in [('access','inaccessible'),('kind','reporting'),('retrieved_at',None),('retrieved_at','2099-01-01T00:00:00+00:00')]:
            records=copy.deepcopy(self.records);records[0]['sources'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):op.validate(records)
    def test_do_not_invent_deadlines_times_or_forms(self):
        records=copy.deepcopy(self.records);r=records[0];r.update(deadline='2026-12-30',opens_at='2026-10-20')
        html=op.render(b,records);self.assertIn('30/12/2026 · ώρα μη δημοσιευμένη',html)
        r['deadline_type']='rolling'
        with self.assertRaises(ValueError):op.validate(records)
        r.update(deadline_type='fixed',application_url='javascript:alert(1)')
        with self.assertRaises(ValueError):op.validate(records)
        r.update(application_url=None,application_kind='none')
        with self.assertRaises(ValueError):op.validate(records)
    def test_stable_id_selects_latest_verification_not_latest_slot_and_deduplicates(self):
        original=self.records[0];later=copy.deepcopy(original);later.update(verified_at='2026-10-16T09:00:00+03:00',action='Νέο επαληθευμένο βήμα.')
        result=op.collect([({'opportunities':[later]},[]),({'opportunities':[original]},[]),({},[])])
        self.assertEqual(result,[later])
        with self.assertRaises(ValueError):op.validate([original,original])
