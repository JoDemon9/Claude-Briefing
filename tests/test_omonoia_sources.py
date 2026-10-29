"""Club-specific discovery remains bounded, dated and separate from evidence."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('omonoia_news',ROOT/'scripts/v2/news_digest.py')
news=importlib.util.module_from_spec(spec);spec.loader.exec_module(news)
AT=datetime(2026,10,29,10,tzinfo=timezone.utc)


class OmonoiaSourcesTests(unittest.TestCase):
    def test_kerkida_listing_uses_exact_club_paths_and_real_timestamps(self):
        feed={'publisher':'Kerkida','format':'kerkida-listing','url':'https://www.kerkida.net/eidiseis/a-katigoria/omonoia',
              'hosts':['www.kerkida.net'],'section':'sports','sports_lane':'omonoia'}
        def link(path,date='2026-10-29T09:55:16+02:00'):
            return f'<div class="article-item"><a href="{path}"><span class="title">Νεότερη ενημέρωση για την προετοιμασία</span><time datetime="{date}">Today</time></a></div>'
        good='/eidiseis/a-katigoria/omonoia/preparation'
        html=link(good)*2+link('/eidiseis/a-katigoria/omonoia-aradippoy/preparation')+link('/eidiseis/a-katigoria/omonoia-29is-maioy/preparation')
        html+=link('https://untrusted.example/eidiseis/a-katigoria/omonoia/preparation')
        html+=link(good+'-future','2026-10-30T12:00:00Z')+link(good+'-old','2026-10-20T12:00:00Z')+link(good+'-undated','')
        rows=news.feed_items({'status':'available','text':html,'retrieved_at':AT.isoformat()},feed,AT)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['published_at'],'2026-10-29T07:55:16+00:00')
        self.assertEqual(rows[0]['sports_lane'],'omonoia')
        self.assertNotIn('source',rows[0])
        self.assertEqual(rows[0]['feed_excerpt'],'')

    def test_other_omonoia_clubs_never_enter_favourite_lane(self):
        for title in ('Ομόνοια Αραδίππου: νέα μεταγραφή','Ομόνοια 29ης Μαΐου: αλλαγή προπονητή',
                      'Omonoia Aradippou announce transfer','Ομόνοια 29Μ ανακοίνωση'):
            self.assertEqual(news.sports_lane(title,'omonoia'),'football')
        self.assertEqual(news.sports_lane('Ομόνοια: νεότερα για τους τραυματίες','omonoia'),'omonoia')

    def test_goal_category_does_not_promote_cross_posted_league_columns(self):
        feed={'publisher':'Goal/Philenews','section':'sports','sports_lane':'omonoia',
              'hosts':['goal.philenews.com'],'article_path_prefix':'/podosfero/kypros/a-katigoria/omonoia/'}
        paths=['/podosfero/kypros/a-katigoria/omonoia/preparation/',
               '/podosfero/kypros/a-katigoria/general-court-column/',
               '/podosfero/kypros/a-katigoria/omonoia-aradippou/preparation/']
        xml='<rss><channel>'+''.join('<item><title>Ενημέρωση για το κυπριακό ποδόσφαιρο</title><link>https://goal.philenews.com'+p+'</link><pubDate>Thu, 29 Oct 2026 07:23:00 GMT</pubDate></item>' for p in paths)+'</channel></rss>'
        rows=news.feed_items({'status':'available','text':xml,'retrieved_at':AT.isoformat()},feed,AT)
        self.assertEqual([r['url'] for r in rows],['https://goal.philenews.com'+paths[0].rstrip('/')])

    def test_goal_retains_philenews_group_and_ads_are_not_article_evidence(self):
        feed={'publisher':'Goal/Philenews','reporting_group':'Philenews','section':'sports',
              'sports_lane':'omonoia','hosts':['goal.philenews.com']}
        xml='<rss><channel><item><title>Ομόνοια: νεότερα για την προετοιμασία</title><link>https://goal.philenews.com/report/</link><pubDate>Thu, 29 Oct 2026 07:23:00 GMT</pubDate></item></channel></rss>'
        row={'status':'available','text':xml,'retrieved_at':AT.isoformat()}
        item=news.feed_items(row,feed,AT)[0]
        body='Η ομάδα συνεχίζει την προετοιμασία και η τελική απόφαση θα ληφθεί μετά την προπόνηση. '*4
        row.update(url=item['url'],text='<article><p>'+body+'</p><p>Μπόνους Εγγραφής €300 και freebet. Η δημοσίευση συνιστά πληρωμένη διαφήμιση.</p></article>')
        evidence=news.evidence(item,row)
        self.assertEqual(evidence['access'],'article_excerpt')
        self.assertEqual(evidence['source']['reporting_group'],'Philenews')
        self.assertEqual(evidence['source']['published_at'],'2026-10-29T07:23:00+00:00')
        self.assertNotIn('freebet',evidence['excerpt'])
        row['text']='<article><p>Μπόνους Εγγραφής €300 και freebet. '+body+'</p></article>'
        self.assertEqual(news.evidence(item,row)['access'],'feed_only')


if __name__=='__main__':unittest.main()
