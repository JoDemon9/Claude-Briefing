import copy
from datetime import datetime,timezone
import importlib.util
import io
import json
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('sports_test_'+name,ROOT/'scripts/v2'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
news=load('sports_news');build=load('build');context=load('context_view')
AT='2026-10-18T12:00:00+00:00'


class Response(io.BytesIO):
    status=200
    def __init__(self,url,body):super().__init__(body);self.url=url
    def geturl(self):return self.url


def listing(key):
    if key=='omonoia':
        return b'\n\n<?xml version="1.0"?><rss><channel>'+b''.join(('<item><title>Official first-team update '+str(i)+'</title><link>https://www.omonoiafc.com.cy/first-team-update-'+str(i)+'/</link><pubDate>Sat, 17 Oct 2026 12:00:00 GMT</pubDate></item>').encode() for i in range(5))+b'</channel></rss>'
    if key=='realmadrid':
        records=[{'tag':'realmadrid-com:noticias/futbol/primer-equipo/actualidad','slug':'official-first-team-update-'+str(i),'title':'Official first-team update '+str(i),'date':'2026-10-17'} for i in range(5)]
        return ('<script id="ng-state" type="application/json">'+json.dumps(records)+'</script>').encode()
    prefix='/en/news/' if key=='manutd' else '/en/latest/article/'
    return ('<main>'+''.join('<a href="'+prefix+'official-first-team-update-'+str(i)+'"><h3>Official first-team update '+str(i)+'</h3></a>' for i in range(5))+'</main>').encode()


class SportsNewsTests(unittest.TestCase):
    def opener(self,calls,fail=None):
        def open_url(request,timeout):
            url=request.full_url;calls.append(url)
            key=next(k for k in news.LISTINGS if news.allowed(k,url))
            if key==fail:raise OSError('temporary source failure')
            if url==news.LISTINGS[key]:return Response(url,listing(key))
            body='<html><link rel="canonical" href="'+url+'"><h1>Official first-team article headline</h1><meta property="article:published_time" content="2026-10-17T12:00:00Z"></html>'
            return Response(url,body.encode())
        return open_url

    def test_all_four_official_providers_stay_within_ten_requests_and_reuse_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[];report=news.collect(tmp,self.opener(calls),lambda:AT)
            self.assertEqual(report['http_attempts'],10);self.assertEqual(len(calls),10)
            self.assertTrue(all(len(r['items'])==2 for r in report['news_links'].values()))
            original=copy.deepcopy(report['news_links'])
            cached=news.collect(tmp,self.opener(calls),lambda:'2026-10-18T12:10:00+00:00')
            self.assertEqual(cached['http_attempts'],0)
            for key,row in cached['news_links'].items():
                self.assertEqual(row['checked_at'],AT)
                self.assertEqual(row['items'],original[key]['items'])

    def test_failed_source_retains_old_headlines_and_original_retrieval_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[];old=news.collect(tmp,self.opener(calls),lambda:AT)
            result=news.collect(tmp,self.opener(calls,fail='manutd'),lambda:'2026-10-18T15:00:00+00:00')
            row=result['news_links']['manutd']
            self.assertEqual(row['status'],'unavailable');self.assertEqual(row['note'],'source_unavailable')
            self.assertEqual(row['items'],old['news_links']['manutd']['items'])
            self.assertEqual(json.loads((Path(tmp)/'manutd.json').read_text())['checked_at'],AT)
            edition=json.loads((ROOT/'content/editions/2026-10-15-midday.json').read_text())
            edition['sports']['news_links']=result['news_links']
            doc=BeautifulSoup(build.sports(edition),'html.parser')
            self.assertIn('παλιότεροι τίτλοι',doc.select_one('.team-manutd').text)

    def test_oversize_and_redirect_sources_cannot_escape_collection_budget(self):
        with self.assertRaisesRegex(ValueError,'budget'):
            news.get('manutd',news.LISTINGS['manutd'],lambda request,timeout:Response(request.full_url,b'x'*(news.MAX_BYTES+1)))
        redirect=news.OfficialRedirect('manutd')
        with self.assertRaisesRegex(ValueError,'Off-provider'):
            redirect.redirect_request(None,None,302,'',{},'https://example.org/private')
        with self.assertRaisesRegex(ValueError,'redirects disabled'):
            redirect.redirect_request(None,None,302,'',{},news.LISTINGS['manutd'])
        for url in ['https://www.manutd.com.evil.test/en/news/story','https://user@www.manutd.com/en/news/story','javascript:alert(1)']:
            self.assertFalse(news.article_url('manutd',url))

    def test_missing_dates_remain_unknown_and_future_articles_are_not_published(self):
        url='https://www.formula1.com/en/latest/article/official-source-news.example'
        row=news.metadata('formula1',b'<h1>Official championship news headline</h1>',url,{'published_at':None})
        self.assertIsNone(row['published_at'])
        record={'source_url':news.LISTINGS['formula1'],'status':'available','checked_at':AT,'items':[{**row,'retrieved_at':AT}],'note':None}
        news.validate_record('formula1',record,AT)
        record['items'][0]['published_at']='2026-10-19T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'Future'):news.validate_record('formula1',record,AT)

    def test_new_editions_need_fresh_explicit_checks_and_old_snapshots_stay_unchanged(self):
        edition={'sports':{},'status':'published','date':'2026-10-18'};news.validate(edition)
        edition['date']='2026-10-19'
        with self.assertRaisesRegex(ValueError,'Each favourite'):news.validate(edition)
        with tempfile.TemporaryDirectory() as tmp:
            report=news.collect(tmp,self.opener([]),lambda:AT)
            edition.update(published_at='2026-10-19T07:30:00+03:00',sports={'news_links':report['news_links']})
            with self.assertRaisesRegex(ValueError,'stale'):news.validate(edition)
            for row in edition['sports']['news_links'].values():row['checked_at']='2026-10-19T07:00:00+03:00'
            news.validate(edition)

    def test_new_headlines_escape_markup_keep_unknown_dates_and_render_without_disclosures(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=news.collect(tmp,self.opener([]),lambda:AT)
        edition=json.loads((ROOT/'content/editions/2026-10-15-midday.json').read_text())
        row=report['news_links']['formula1']['items'][0]
        row.update(headline='<script>bad()</script> official headline',published_at=None)
        edition['sports']['news_links']=report['news_links']
        original=copy.deepcopy(edition)
        doc=BeautifulSoup(build.sports(edition),'html.parser')
        self.assertFalse(doc.select('script,.sports-links details'))
        self.assertEqual(len(doc.select('.sport-headline-link')),8)
        self.assertIn('Η πηγή δεν δίνει ημερομηνία',doc.select_one('.team-formula1').text)
        self.assertEqual(edition,original)

    def test_published_editions_cannot_be_rewritten_by_metadata_collector(self):
        with self.assertRaisesRegex(ValueError,'unpublished draft'):
            news.apply(ROOT,'2026-10-18-morning',{'news_links':{}})

    def test_draft_copy_keeps_full_data_and_only_exact_matching_translations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=news.collect(root/'cache',self.opener([]),lambda:AT)
            (root/'templates/v2').mkdir(parents=True)
            shutil.copyfile(ROOT/'templates/v2/content.schema.json',root/'templates/v2/content.schema.json')
            edition=json.loads((ROOT/'content/editions/2026-10-18-morning.json').read_text())
            edition.update(status='draft',published_at=None,editorial_completed_at=None)
            edition['sports']['news_links']=copy.deepcopy(report['news_links'])
            edition['sports']['news_links']['manutd']['items'][0]['headline_el']='Ακριβής παλιότερη μετάφραση του ίδιου τίτλου'
            edition['sports']['news_links']['formula1']['items'][0]['headline_el']='Μετάφραση παλιότερου τίτλου'
            report['news_links']['formula1']['items'][0]['headline']='Changed official article headline'
            target=root/'content/editions/2026-10-18-morning.json';target.parent.mkdir(parents=True);target.write_text(json.dumps(edition))
            news.apply(root,edition['id'],report);result=json.loads(target.read_text())
            self.assertEqual(result['markets'],edition['markets']);self.assertEqual(result['opportunities'],edition['opportunities'])
            self.assertIn('headline_el',result['sports']['news_links']['manutd']['items'][0])
            self.assertNotIn('headline_el',result['sports']['news_links']['formula1']['items'][0])


class ContextBudgetTests(unittest.TestCase):
    def test_pagination_has_a_hard_byte_limit_and_no_silently_lost_records(self):
        rows=[{'kind':'story','id':str(i),'finding':'Επαληθευμένο εύρημα. '*45} for i in range(31)]
        found=[];index=0
        while True:
            result=context.page({'scope':'private'},rows,index,max_bytes=4000)
            self.assertLessEqual(len(context.encoded(result).encode()),4000)
            found.extend(result['rows'])
            if result['next_page'] is None:break
            index=result['next_page']
        self.assertEqual(found,rows)
        with self.assertRaises(ValueError):context.page({},rows,max_bytes=12001)
        with self.assertRaisesRegex(ValueError,'One record'):context.page({},[{'kind':'story','finding':'x'*13000}])

    def test_projection_preserves_due_metadata_and_sports_without_full_raw_bodies(self):
        packet={'edition_id':'2026-10-18-evening','as_of':AT,'stories':[{'story_id':'stable','headline':'Known headline','finding':'Known supported finding','sources':[{'retrieved_at':AT}],'editorial_notes':{'unresolved':['Read new official evidence']}}],
                'opportunities':[{'record':{'id':'grant','status':'open','verified_at':AT,'long_terms':'PRIVATE-LARGE-BODY'*200},'review':{'due':True,'due_at':AT,'reasons':['near_deadline']}}]}
        collection={'edition_id':packet['edition_id'],'records':[{'url':'https://example.org','status':'unchanged','owners':[{'kind':'opportunity','id':'grant'}],'text':'FULL-RAW-EVIDENCE'*1000}]}
        header,rows=context.project(packet,collection)
        result=context.page(header,rows)
        text=context.encoded(result)
        self.assertNotIn('FULL-RAW-EVIDENCE',text);self.assertNotIn('PRIVATE-LARGE-BODY',text)
        self.assertIn('Read new official evidence',text);self.assertIn('near_deadline',text)
        self.assertTrue(next(r for r in rows if r['kind']=='source')['evidence_on_disk'])
        collection['edition_id']='another-slot'
        with self.assertRaisesRegex(ValueError,'another packet'):context.project(packet,collection)


if __name__=='__main__':unittest.main()
