"""Synthetic regressions for failure shapes observed in the 7–9 November packs.

No private pack, cache, source Markdown or publisher body is stored here.
Use audit_news_packs.py separately against the immutable private packets.
"""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('regression_'+name,ROOT/'scripts/v2'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


news,view,adapter,audit,selection=map(load,('news_digest','context_view','markdown_input','audit_news_packs','selection'))
AT='2026-11-09T05:00:00+00:00'
AD='Security agents analyze mail. Start your free read-only scan with no MX changes. '*4
BODY='The authority approved the new operating plan. Residents can apply from January under the published eligibility rules. Funding and staffing are subject to parliamentary approval. '


def item(title='Security authority operating plan',section='world',url='https://example.com/report'):
    return dict(title=title,section=section,url=url,publisher='Paper',published_at=AT,reporting_group='Paper')


def evidence(html,title='Security authority operating plan'):
    i=item(title)
    return news.evidence(i,dict(status='available',url=i['url'],retrieved_at=AT,text=html))


def pack():
    candidates=[]
    for desk in ('cyprus','world','sports'):
        for n in range(7):
            i=item(f'Reported decision {desk} {n}',desk,f'https://example.com/{desk}/{n}')
            lane=('omonoia','manutd','realmadrid','formula1','padel','football','other')[n]
            e=dict(i,id=f'e{len(candidates)+1}',access='article_excerpt',source=dict(i,retrieved_at=AT),
                   excerpt=BODY*6+'\nThe application deadline is 30 January 2027; only 42 households are eligible.\n'+BODY*6)
            candidates.append(dict(id=f'c{len(candidates)+1}',title=i['title'],section=desk,
                                   sports_lane=lane if desk=='sports' else None,evidence=[e]))
    return dict(edition_id='2026-11-09-morning',prepared_at=AT,sha256='a'*64,baseline=None,baseline_stories=[],
        weather_status='unavailable',financial_policy='news-insights-v1',briefing_policy='depth-markets-v1',
        data=dict(markets=[],panels=[],sports=dict(briefing_policy='intelligence-v1',coverage={})),
        candidates=candidates,evidence={e['id']:e for c in candidates for e in c['evidence']})


class NovemberRegressions(unittest.TestCase):
    def test_7_ad_sharing_headline_security_words_is_not_readable(self):
        e=evidence('<main><p>'+AD+'</p></main>')
        self.assertEqual(e['access'],'feed_only')
        self.assertIsNone(e['source'])
        self.assertEqual(e['rejection_reason'],'promotional_body_without_article')

    def test_json_ld_advertisement_cannot_bypass_admission(self):
        html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','articleBody':AD})+'</script>'
        self.assertEqual(evidence(html)['access'],'feed_only')

    def test_failed_first_region_does_not_hide_later_reporting(self):
        html='<div class="article-body"><p>'+AD+'</p></div><article><p>'+BODY+'</p></article>'
        e=evidence(html)
        self.assertEqual(e['access'],'article_excerpt')
        self.assertIn('parliamentary approval',e['excerpt'])
        self.assertNotIn('free',e['excerpt'])

    def test_nested_ad_and_unlabelled_promotion_do_not_enter_reporting(self):
        for promotion in ('<aside><p>'+AD+'</p></aside>','<p>'+AD+'</p>'):
            with self.subTest(promotion=promotion[:20]):
                e=evidence('<article>'+promotion+'<p>'+BODY+'</p></article>')
                self.assertEqual(e['access'],'article_excerpt')
                self.assertNotIn('scan',e['excerpt'])

    def test_reporting_about_advertising_is_still_reporting(self):
        e=evidence('<article><p>'+('The regulator fined an advertising company for false claims. '*5)+'</p></article>','Regulator fines advertising company')
        self.assertEqual(e['access'],'article_excerpt')

    def test_7_and_9_general_cyprus_feed_geography(self):
        for title,url,expected in (
            ('New Zealand election count ends','https://cyprus-mail.com/2026/11/07/count','world'),
            ('Delhi pollution rises before Diwali','https://cyprus-mail.com/2026/11/07/pollution','world'),
            ('Man Utd in relegation zone after chaotic draw','https://cyprus-mail.com/2026/11/08/match','sports'),
            ('Formula E boss criticises F1','https://cyprus-mail.com/2026/11/07/race','sports'),
            ('Κειμήλια στο μουσείο στη Θεσσαλονίκη','https://www.philenews.com/kipros/koinonia/article/1/report','world'),
            ('Health model predicts global benefit','https://www.philenews.com/igia-news/zoi-evexia/article/1/report','world'),
            ('Cyprus discusses defence ties with US','https://cyprus-mail.com/2026/11/09/ties','cyprus'),
            ('Olympic champion in presidential election in France','https://example.com/news','world')):
            with self.subTest(title=title):
                self.assertEqual(news.geography(title,url,'world' if 'Olympic' in title else 'cyprus'),expected)

    def test_9_two_nvidia_sources_are_one_event_not_two_slots(self):
        rows=[item("Nvidia launches investigation into CEO's affair with suspected spy"),
              item('Nvidia board opens inquiry after foreign intelligence report',url='https://other.example/report'),
              item('Nvidia reports quarterly earnings',url='https://example.com/earnings')]
        before=copy.deepcopy(rows)
        groups=news.cluster(rows)
        self.assertEqual([len(g) for g in groups],[2,1])
        self.assertEqual(rows,before)
        self.assertIsNone(news.event_hint('Nvidia artificial intelligence chip launch'))
        self.assertIsNone(news.event_hint('Nvidia faces an antitrust investigation'))
        later=dict(rows[0],published_at='2026-12-09T05:00:00+00:00')
        self.assertEqual(len(news.cluster([rows[0],later])),2)

    def test_failed_event_can_use_another_source_within_24_reads(self):
        first=item();second=item(url='https://other.example/report')
        class Client:
            def many(self,urls):return {u:{} for u in urls}
        def ev(i,row):return dict(access='feed_only' if i['url']==first['url'] else 'article_excerpt',published_at=AT)
        with mock.patch.object(news,'evidence',side_effect=ev):
            chosen,pages,_=news.financial_collection([[first,second]],Client(),datetime.fromisoformat(AT))
        self.assertEqual(len(pages),2)
        self.assertLessEqual(len(chosen),24)

    def test_8_two_stage_excerpt_keeps_late_deadline_and_qualification(self):
        decisive='The application deadline is 30 January 2027; only 42 households are eligible.'
        qualifier='There is no reason to believe the reported incident compromised national security.'
        body='\n'.join([BODY]*45+[decisive,qualifier])
        first=news.focused_excerpt(body,'Authority operating plan',6500)
        second=news.focused_excerpt(first,'Authority operating plan',800)
        self.assertIn(decisive,second)
        self.assertIn(qualifier,second)
        self.assertIn('\n[…]\n',first)

    def test_digest_preserves_critical_passages_and_reports_omitted_ids(self):
        p=pack();before=copy.deepcopy(p)
        digest=view.synthesis(p)
        self.assertLessEqual(len(digest.encode()),48000)
        self.assertIn('only 42 households are eligible',digest)
        self.assertIn('Excluded article-backed candidates:',digest)
        self.assertEqual(p,before)

    def test_ad_only_pack_has_honest_shortfall_and_no_readable_credit(self):
        p=pack();p['candidates']=p['candidates'][:2]
        for c in p['candidates']:c['evidence'][0]['excerpt']=AD
        before=copy.deepcopy(p)
        replay,report=audit.replay(p)
        self.assertEqual(replay['metrics']['pipeline']['cyprus']['readable'],0)
        self.assertEqual(len(report['excluded']),2)
        digest=view.synthesis(replay)
        self.assertIn('Evidence shortfall cyprus:',digest)
        self.assertIn('promotional_body_without_article',digest)
        self.assertEqual(p,before)

    def test_counts_separate_updates_carries_and_unknowns(self):
        articles=[dict(story_id=str(n),change_status=status,daily={'section':'world'})
                  for n,status in enumerate(('NEW','UPDATED','CORRECTION','REVERSAL','UNCHANGED','UNKNOWN'))]
        report=selection.coverage(dict(id='test',date='2026-11-09',type='midday',selection_policy='balanced-v1'),articles)
        self.assertEqual([report[k]['world'] for k in ('new_counts','updated_counts','carried_counts','unknown_counts')],[1,3,1,1])
        self.assertEqual(report['counts']['world'],6)

    def test_shortfall_requires_reasons_for_each_readable_unselected_event(self):
        p=pack();p['coverage_policy']='auditable-v1';p['candidates']=p['candidates'][:2]
        payload={'articles':[],'candidate_exclusions':{'c1':'This repeats an already covered development.'}}
        with self.assertRaisesRegex(ValueError,'@Exclude candidate=c2'):
            load('research_pack').review_candidates(copy.deepcopy(payload),p,{})
        payload['candidate_exclusions']['c2']='The available detail does not support a useful report.'
        load('research_pack').review_candidates(payload,p,{})
        self.assertEqual(set(payload['selection_review']['candidate_exclusions']),{'c1','c2'})

    def test_same_day_carry_counts_toward_complete_coverage(self):
        p=pack();p['coverage_policy']='auditable-v1';p['candidates']=p['candidates'][:5]
        records={str(n):dict(story_id=str(n),daily={'section':'cyprus'},sources=[]) for n in range(4)}
        payload={'articles':[],'carry_story_ids':list(records)}
        load('research_pack').review_candidates(payload,p,records)
        self.assertEqual(payload['selection_review']['candidate_exclusions'],{})

    def test_two_sources_for_one_explicit_event_cannot_fill_two_story_slots(self):
        p=pack();p['coverage_policy']='auditable-v1';p['candidates']=p['candidates'][:1]
        c=p['candidates'][0];c['title']='Nvidia opens security investigation'
        other=copy.deepcopy(c['evidence'][0]);other['id']='e99';other['source']['url']='https://other.example/report'
        c['evidence'].append(other)
        payload={'articles':[dict(story_id=str(n),section='cyprus',sources=[e['source']]) for n,e in enumerate(c['evidence'])]}
        with self.assertRaisesRegex(ValueError,'one explicit event'):
            load('research_pack').review_candidates(payload,p,{})


class GroupedCitations(unittest.TestCase):
    def markdown(self,marker):
        return ('@Edition v=1 id=2026-11-09-morning published=auto completed=auto baseline=none\n'
                '@Review version=2 completed=auto\n## world\n'
                '### report | story=report identity=report status=NEW lead=false\n'
                '@Headline Report\n@Fact Reported facts.'+marker+'\n@Meaning A consequence '+marker+'\n'
                '@AnalysisSources s1,s2\n@Watch A next test '+marker+'\n'+
                '\n'.join('@Source '+s+' | publisher="Paper" url=https://example.com/'+s+
                    ' published=null retrieved='+AT+' group="Paper" kind=reporting access=read claims=true' for s in ('s1','s2')))

    def test_groups_validate_every_member_and_strip_every_prose_field(self):
        for marker in ('[s1,s2]','[s1, s2]','[s1; s2]','[s1][s2]'):
            with self.subTest(marker=marker):
                a=adapter.parse(self.markdown(marker),ROOT)['articles'][0]
                self.assertEqual(a['summary'],'Reported facts.')
                self.assertEqual(a['newspaper_analysis'],['A consequence'])
                self.assertEqual(a['scenarios']['watch_next'],'A next test')
                self.assertEqual(len(a['sources']),2)
        for marker in ('[s1,s9]','[s1,]','[s1 s2]'):
            with self.subTest(marker=marker),self.assertRaisesRegex(ValueError,'source reference'):
                adapter.parse(self.markdown(marker),ROOT)

    def test_nested_prose_and_historical_render_output_do_not_leak(self):
        citations=load('citations')
        self.assertEqual(citations.resolve({'paragraphs':['A fact.[s1,s2]']},{'s1':{},'s2':{}}),{'paragraphs':['A fact.']})
        build=load('build')
        self.assertEqual(build.esc('A fact.[e10,e11]'),'A fact.')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'article.html'
            build.write(path,'<p>A fact.[e10,e11]</p>')
            self.assertEqual(path.read_text(encoding='utf-8'),'<p>A fact.</p>')
        self.assertEqual(citations.public_text('A legitimate [editorial note].'),'A legitimate [editorial note].')


if __name__=='__main__':unittest.main()
