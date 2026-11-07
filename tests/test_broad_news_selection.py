"""Regression coverage for broad news selection and sponsored-body rejection."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('broad_news',ROOT/'scripts/v2/news_digest.py')
news=importlib.util.module_from_spec(spec);spec.loader.exec_module(news)
AT=datetime(2026,11,7,8,tzinfo=timezone.utc)


class BroadNewsTests(unittest.TestCase):
    def test_real_article_body_takes_precedence_over_sponsored_component(self):
        item=dict(title='SonicWall releases authentication security updates',publisher='BleepingComputer',
                  url='https://example.com/story',section='world',published_at=AT.isoformat())
        body='SonicWall releases authentication security updates for affected customers. '*8
        html='<div class="article-body"><p>Adaptive agents offer a read-only scan with no MX changes. '*8+'</p></div>'
        html+='<div class="articleBody"><p>'+body+'</p></div>'
        row=dict(status='available',url=item['url'],retrieved_at=AT.isoformat(),text=html)
        with mock.patch.object(news,'module',return_value=mock.Mock(extract=lambda *args:[])):
            result=news.evidence(item,row)
        self.assertEqual(result['access'],'article_excerpt')
        self.assertIn('SonicWall',result['excerpt'])
        self.assertNotIn('read-only scan',result['excerpt'])

    def test_advertisement_alone_is_not_readable_article_evidence(self):
        item=dict(title='SonicWall authentication updates',publisher='Paper',
                  url='https://example.com/story',section='world',published_at=AT.isoformat())
        html='<main><p>'+('Adaptive agents offer a read-only scan with no MX changes. '*8)+'</p></main>'
        row=dict(status='available',url=item['url'],retrieved_at=AT.isoformat(),text=html)
        result=news.evidence(item,row)
        self.assertEqual(result['access'],'feed_only')
        self.assertEqual(result['rejection_reason'],'promotional_body_without_article')

    def test_broad_news_and_cyprus_publishers_survive_high_scoring_security_queue(self):
        def group(n,desk,publisher,topic=None):
            return [dict(title=n,url='https://example.com/'+n,section=desk,publisher=publisher,
                         reporting_group=publisher,topic=topic,published_at=AT.isoformat())]
        groups=[group('security-'+str(i),'world','Security','security') for i in range(6)]
        groups += [group('local-'+str(i),'cyprus','Local') for i in range(7)]
        groups += [group('local-other-'+str(i),'cyprus','Other') for i in range(3)]
        groups += [group('broad-'+str(i),'world','World-'+str(i)) for i in range(4)]
        class Client:
            def many(self,urls):
                return {u:{} for u in urls}
        with mock.patch.object(news,'evidence',side_effect=lambda item,row:
                               dict(access='article_excerpt',published_at=AT.isoformat())):
            chosen,pages,_=news.financial_collection(groups,Client(),AT)
        first_world=[i for i in chosen[:10] if i['section']=='world']
        self.assertEqual(sum(i.get('topic') is None for i in first_world),3)
        self.assertEqual(sum(i.get('topic')=='security' for i in first_world),1)
        self.assertIn('Other',{i['publisher'] for i in chosen[:6]})
        self.assertLessEqual(len(pages),news.MAX_ARTICLE_REQUESTS)
        self.assertEqual(len(chosen),len({i['url'] for i in chosen}))

    def test_failed_news_uses_bounded_repair_candidates(self):
        groups=[]
        for desk in ('cyprus','world'):
            for i in range(9):
                groups.append([dict(title=desk+str(i),url='https://example.com/'+desk+str(i),
                                    section=desk,publisher=desk+str(i%3))])
        class Client:
            def many(self,urls):return {u:{} for u in urls}
        def ev(item,row):
            return dict(access='feed_only' if item['title'].endswith(('0','1')) else 'article_excerpt',
                        published_at=AT.isoformat())
        with mock.patch.object(news,'evidence',side_effect=ev):
            chosen,pages,found=news.financial_collection(groups,Client(),AT)
        for desk,minimum in [('cyprus',6),('world',4)]:
            self.assertGreaterEqual(sum(i['section']==desk and found[i['url']]['access']=='article_excerpt' for i in chosen),minimum)
        self.assertLessEqual(len(pages),24)

if __name__=='__main__':unittest.main()
