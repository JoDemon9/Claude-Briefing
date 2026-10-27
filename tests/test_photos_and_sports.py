"""Real-photo coverage, exact reporting history, and Python-rendered sports regressions."""
import copy
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('photos_test_'+name,ROOT/'scripts/v2'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def read(path):return json.loads(path.read_text(encoding='utf-8'))


class RealPhotoTests(unittest.TestCase):
    def test_all_published_articles_have_local_real_photo_assets(self):
        for path in (ROOT/'content/editions').glob('*.json'):
            edition=read(path)
            if edition['status']!='published':continue
            for relative in edition['articles']:
                article=read(ROOT/'content'/relative)
                with self.subTest(article=relative):
                    self.assertTrue(article.get('image'))
                    self.assertTrue(article['image']['url'].endswith('.webp'))
                    self.assertTrue((ROOT/'docs'/article['image']['url']).is_file())

    def test_automatic_assignment_preserves_licensed_bytes_without_ai_photo_fields(self):
        policy=load('photo_policy');compose=load('compose')
        e=read(ROOT/'content/editions/2026-10-25-evening.json')
        a=read(ROOT/'content'/e['articles'][0]);raw=copy.deepcopy(a)
        raw.update(slug=a['id'],section=a['daily']['section']);raw.pop('image_selection',None)
        catalog=policy.extend_catalog(read(ROOT/'docs/data/photo-library.json'),ROOT)
        doc,asset=compose.article(raw,'2026-10-26-morning',0,ROOT,catalog,'2026-10-26T07:30:00+02:00','2026-10-26T07:30:00+02:00',True)
        import hashlib
        self.assertEqual(hashlib.sha256(asset).hexdigest(),doc['image']['reuse_review']['sha256'])
        self.assertEqual(doc['sources'],a['sources'])
        self.assertTrue(doc['image']['caption'].startswith('Φωτογραφία αρχείου'))
        raw['image_selection']={'photo_id':'0'*64,'relevance_and_archive_date_checked':True,'reviewed_at':'2026-10-26T07:00:00+02:00'}
        with self.assertRaisesRegex(ValueError,'Required real photograph'):
            compose.article(raw,'2026-10-26-morning',0,ROOT,catalog,require_photo=True)

    def test_subject_rules_and_broad_context_are_explicit_real_photos(self):
        p=load('photo_policy');policy=p.load(ROOT)
        for raw,key in [({'story_id':'brazil-presidential-runoff-voting-2026-10-25','section':'world'},'brazil'),
                        ({'headline':'Manchester United injury update','section':'sports'},'manutd'),
                        ({'story_id':'kyiv-university-missile-strike-2026-10-26','headline':'Κίεβο: πλήγματα κοντά σε πανεπιστήμιο','section':'world'},'ukraine'),
                        ({'headline':'ΗΠΑ: παράνομη κρίθηκε η απόλυση εισαγγελέως','section':'world'},'us'),
                        ({'headline':'Unmatched subject','section':'world'},'earth')]:
            self.assertEqual(p.selection(raw,ROOT)['photo_id'],policy['photos'][key]['id'])
        self.assertTrue(all(v['media_type']=='photograph' and v['visually_reviewed'] for v in policy['photos'].values()))

    def test_image_only_history_exception_cannot_hide_changed_reporting(self):
        b=load('backend');e=read(ROOT/'content/editions/2026-10-22-morning.json');aa=[read(ROOT/'content'/p) for p in e['articles']]
        old=b.reporting_fingerprint(e,aa);changed=copy.deepcopy(aa)
        changed[0]['image']['caption']='New archive caption';self.assertEqual(old,b.reporting_fingerprint(e,changed))
        changed[0]['summary']+=' Changed reporting.';self.assertNotEqual(old,b.reporting_fingerprint(e,changed))
        changed=copy.deepcopy(aa);changed[0]['sources'][0]['retrieved_at']='2099-01-01T00:00:00Z'
        self.assertNotEqual(old,b.reporting_fingerprint(e,changed))


class SportsDeskTests(unittest.TestCase):
    def test_eight_python_feed_reads_filter_irrelevant_old_and_future_headlines(self):
        news=load('sports_news');at=datetime(2026,10,26,5,tzinfo=timezone.utc)
        def item(title,url,date):return f'<item><title>{title}</title><link>{url}</link><pubDate>{date}</pubDate></item>'
        xml='<rss><channel>'+item('Real Madrid first team update','https://www.bbc.com/sport/football/articles/real','Sun, 25 Oct 2026 20:00:00 GMT')+item('Barcelona first team update','https://www.bbc.com/sport/football/articles/barca','Sun, 25 Oct 2026 21:00:00 GMT')+item('Real Madrid future news','https://www.bbc.com/sport/football/articles/future','Tue, 27 Oct 2026 21:00:00 GMT')+item('Real Madrid old news','https://www.bbc.com/sport/football/articles/old','Mon, 19 Oct 2026 21:00:00 GMT')+'</channel></rss>'
        class Client:
            def many(self,urls):
                self.urls=urls
                return {u:dict(status='available',text=xml,retrieved_at=at.isoformat(),checked_at=at.isoformat()) if 'european/rss' in u else dict(status='unavailable') for u in urls}
        c=Client();result=news.prefetch(c,at)
        self.assertEqual(len(c.urls),8)
        self.assertEqual([r['headline'] for r in result['realmadrid']['items']],['Real Madrid first team update'])
        self.assertEqual(result['omonoia']['status'],'unavailable')

    def test_f1_tables_uefa_and_selected_sports_article_are_visible(self):
        b=load('build');sports=load('sports');e=read(ROOT/'content/editions/2026-10-25-evening.json')
        aa=[read(ROOT/'content'/p) for p in e['articles']]
        e['sports']['major_stories']=[]
        f1=e['sports']['coverage']['formula1']
        f1['latest_session']={'name':'Fixture GP','date':'2026-10-25','results':[{'position':'1','driver':'Fixture Winner','status':'Finished'}]}
        f1['standings']=[{'position':'1','driver':'Fixture Leader','points':'300'}]
        html=sports.render(SimpleNamespace(**vars(b)),e,aa)
        dom=BeautifulSoup(html,'html.parser')
        self.assertEqual(len(dom.select('.sport-photo img')),4)
        self.assertIn('Fixture Winner',dom.get_text());self.assertIn('Fixture Leader',dom.get_text())
        self.assertIn('Champions League',dom.get_text())
        sport=next(a for a in aa if a.get('daily',{}).get('section')=='sports')
        self.assertIn(sport['headline'],dom.get_text())
        self.assertTrue(dom.select('.sports-europe table'))


if __name__=='__main__':unittest.main()
