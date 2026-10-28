"""Sports annotations stay sourced, compact and separate from news coverage."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('brief_test_'+name,ROOT/'scripts/v2'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

brief,news,view,md=map(load,('sports_briefing','news_digest','context_view','markdown_input'))
SOURCE={'publisher':'Test report','url':'https://example.com/report','retrieved_at':'2026-10-28T05:00:00Z',
        'published_at':'2026-10-28T04:00:00Z','access':'read','used_for_claims':True,'kind':'reporting','reporting_group':'Test report'}


class SportsBriefingTests(unittest.TestCase):
    def test_annotation_resolves_exact_article_evidence_and_rejects_feed_only_or_wrong_club(self):
        note={'evidence':['e1'],'changed':'Η ομάδα ανακοίνωσε αλλαγή στην προετοιμασία της.',
              'meaning':'Η διαθέσιμη προετοιμασία περιορίζεται πριν από τον αγώνα.', 'watch':'Επόμενο τεστ είναι η επίσημη αποστολή του αγώνα.'}
        ev={'access':'article_excerpt','source':SOURCE,'sports_lane':'manutd'}
        pack={'data':{'sports':{'briefing_policy':brief.POLICY}},'evidence':{'e1':ev}}
        payload={'sports':copy.deepcopy(pack['data']['sports']),'sport_briefs':{'manutd':note}}
        before=copy.deepcopy(pack)
        brief.hydrate(payload,pack)
        self.assertEqual(payload['sports']['briefings']['manutd']['sources'],[SOURCE])
        self.assertEqual(pack,before)
        for mutation in ({'access':'feed_only'},{'sports_lane':'realmadrid'}):
            p=copy.deepcopy(pack);p['evidence']['e1'].update(mutation)
            with self.assertRaisesRegex(ValueError,'readable evidence'):
                brief.hydrate({'sports':{},'sport_briefs':{'manutd':note}},p)

    def test_news_and_wider_sports_have_independent_bounded_allowances(self):
        sports={'briefing_policy':brief.POLICY}
        newsrows=[{'section':'cyprus' if i<5 else 'world','change_status':'NEW'} for i in range(10)]
        extra=[{'section':'sports','change_status':'NEW'} for _ in range(3)]
        brief.article_budget(newsrows+extra,'morning',sports)
        for rows in (newsrows+extra+[extra[0]],newsrows+extra+[newsrows[0]]):
            with self.assertRaisesRegex(ValueError,'budget'):brief.article_budget(rows,'morning',sports)
        with self.assertRaisesRegex(ValueError,'budget'):brief.article_budget(newsrows+extra,'morning',{})

    def test_wider_sports_excludes_favourites_repeated_topics_and_summary_only_copy(self):
        sports={'briefing_policy':brief.POLICY,'major_stories_reason':'Only one supported sports report in the visible evidence.'}
        a={'section':'sports','sports_interest':'other','driver_tags':['padel'],'summary':'Reported result in a major tournament.',
           'second_order_effects':'The result changes the ranking contest.','analysis_sources':[SOURCE['url']]}
        brief.validate(sports,[a])
        for rows in ([a,a],[dict(a,sports_interest='manutd')],[dict(a,second_order_effects='')]):
            with self.assertRaises(ValueError):brief.validate(sports,rows)
        with self.assertRaisesRegex(ValueError,'Explain'):brief.validate(dict(sports,major_stories_reason=''),[])

    def test_directive_has_no_routine_data_or_silent_duplicate_override(self):
        text='@Edition v=1 id=2026-10-29-morning published=auto completed=auto baseline=none\n@Review version=2 completed=auto\n@SportBrief interest=manutd evidence=e1 changed="Reported change" meaning="Supported implication" watch="Next observable test"\n@SportsReason Only one readable wider-sports report was available.\n'
        payload=md.parse(text,ROOT)
        self.assertEqual(payload['sport_briefs']['manutd']['evidence'],['e1'])
        self.assertNotIn('sports',payload)
        with self.assertRaisesRegex(ValueError,'Duplicate favourite'):
            md.parse(text+text.splitlines()[2]+'\n',ROOT)

    def test_current_layout_keeps_data_closed_and_reporting_before_tables(self):
        b,sports=load('build'),load('sports')
        e=json.loads((ROOT/'content/editions/2026-10-28-morning.json').read_text())
        aa=[json.loads((ROOT/'content'/p).read_text()) for p in e['articles']]
        dom=BeautifulSoup(sports.render(b,e,aa),'html.parser')
        self.assertEqual(len(dom.select('.sports-compact .sport-details')),4)
        self.assertFalse(dom.select('.sport-photo'))
        self.assertFalse(dom.select('details[open]'))
        for table in dom.select('table'):self.assertIsNotNone(table.find_parent('details'))
        self.assertIn('Γιουνάιτεντ',dom.get_text())
        self.assertIn('τρέχουσα βαθμολογία δεν είναι διαθέσιμη',dom.get_text())


class EvidenceRegressionTests(unittest.TestCase):
    def test_late_cyprus_funding_facts_survive_both_excerpt_stages(self):
        intro='Η διεθνής οικονομική κατάσταση επηρεάζει πολλά κράτη και διαφορετικές αγορές. '
        late='Για την Κύπρο, η ενίσχυση των αγροτών ανέρχεται στα €1.501.200, με δύο σχέδια για λιπάσματα και καύσιμα.'
        text='\n'.join([intro*6 for _ in range(8)]+[late])
        title='Κύπρος: ενίσχυση αγροτών για λιπάσματα και καύσιμα'
        collected=news.focused_excerpt(text,title,6500)
        visible=news.focused_excerpt(collected,title,1000)
        self.assertIn('€1.501.200',visible)
        self.assertIn(late,visible)
        self.assertLessEqual(len(visible),1000)

    def test_jsonld_article_body_fallback_and_explicit_extraction_failure(self):
        item={'title':'Budget changes for public services','url':SOURCE['url'],'publisher':'Test report','section':'world','feed_excerpt':'Headline only','published_at':SOURCE['published_at']}
        body='The government announced funding for public services. '*8
        html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','articleBody':body})+'</script>'
        row={'status':'available','text':html,'url':SOURCE['url'],'retrieved_at':SOURCE['retrieved_at']}
        self.assertEqual(news.evidence(item,row)['access'],'article_excerpt')
        row['text']='<nav>'+body+'</nav>'
        self.assertEqual(news.evidence(item,row)['rejection_reason'],'article_body_missing_or_short')

    def test_sports_routing_does_not_fill_other_sport_with_favourites(self):
        for title,key in [('Manchester United manager update','manutd'),('Real Madrid win','realmadrid'),('Ομόνοια: αλλαγές','omonoia'),('Formula 1 rules','formula1'),('Padel world championship','padel')]:
            self.assertEqual(news.sports_lane(title,'football'),key)
        self.assertEqual(news.sports_lane('Tennis championship result','other'),'other')


if __name__=='__main__':unittest.main()
