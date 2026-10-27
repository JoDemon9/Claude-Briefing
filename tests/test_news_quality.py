"""More useful evidence within the same bounded collection and model input."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/v2'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


news,view=load('news_digest'),load('context_view')
AT=datetime(2026,10,25,12,tzinfo=timezone.utc)


class NewsQualityTests(unittest.TestCase):
    def test_general_feed_and_wire_geography_and_preview_filter(self):
        title='ΝΑΤΟ: Τα ρωσικά drones αναδεικνύουν κενά στην προστασία υποδομών'
        self.assertEqual(news.geography(title,'https://www.philenews.com/oikonomia/capital/forbes/article/1/x','cyprus'),'world')
        self.assertEqual(news.geography('Η Κύπρος συζητά συνεργασία με το ΝΑΤΟ','https://example.com/a','cyprus'),'cyprus')
        self.assertEqual(news.geography('Δικαστική απόφαση','https://www.philenews.com/kosmos/article/1/x','cyprus'),'world')
        self.assertFalse(news.news_report('Ο Χάρης Γεωργιάδης σε λίγο στο vidcast του philenews'))
        self.assertTrue(news.news_report('Ο Χάρης Γεωργιάδης εξήγησε τις θέσεις του στο vidcast'))

    def test_same_election_discovery_cluster_keeps_all_sources_and_ids(self):
        titles=["What does Israel's election mean for Gaza?",'Israel heads to polls for pivotal election','Israeli elections: voters turnout reaches 16.7%']
        rows=[{'title':title,'section':'world','story_id':str(i)} for i,title in enumerate(titles)]
        rows.extend([{'title':'US Senate election campaign spending','section':'world','story_id':'us'},
                     {'title':titles[0],'section':'cyprus','story_id':'local'}])
        groups=news.cluster(rows)
        self.assertEqual([len(g) for g in groups],[3,1,1])
        self.assertEqual([i['story_id'] for i in groups[0]],['0','1','2'])

    def test_cartoon_column_does_not_take_a_news_slot(self):
        self.assertFalse(news.news_report('Το σκίτσο του Νίκου Πογιατζή'))
        self.assertFalse(news.news_report('Cartoon of the day: elections'))
        self.assertTrue(news.news_report('Court rules on cartoon publication dispute'))
        self.assertTrue(news.news_report('Σκιτσογράφος κέρδισε δικαστική προσφυγή'))
        feed={'publisher':'Paper','section':'cyprus','hosts':['example.com']}
        row={'status':'available','retrieved_at':AT.isoformat(),'text':'<rss><channel><item><title>Το σκίτσο του Νίκου Πογιατζή</title><link>https://example.com/cartoon</link></item></channel></rss>'}
        self.assertEqual(news.feed_items(row,feed,AT),[])

    def test_full_news_inventory_survives_rich_sports_and_duplicate_evidence(self):
        source={'publisher':'Paper','url':'https://example.com/report','retrieved_at':AT.isoformat(),
                'published_at':AT.isoformat(),'reporting_group':'Paper','kind':'reporting','access':'read','used_for_claims':True}
        greek='Η αλλαγή αφορά συγκεκριμένες υπηρεσίες και επηρεάζει τους κατοίκους. '*50
        candidates=[]
        for desk,count in [('cyprus',5),('world',6),('sports',2)]:
            for i in range(count):
                cid=f'{desk}-{i}'
                candidates.append({'id':cid,'section':desk,'title':cid,'baseline_matches':[],
                    'evidence':[{'id':f'{cid}-e{j}','access':'article_excerpt','source':dict(source,url=f'https://example.com/{cid}/{j}'),
                                 'excerpt':greek} for j in range(2)]})
        # Feed-only discovery is not counted as usable evidence or given a full excerpt budget.
        candidates[6]['evidence']=[{'id':'blocked','access':'feed_only','source':None,'excerpt':'RSS headline only'}]
        event={'name':'Real Madrid vs Opponent','starts_at':AT.isoformat(),'sources':[source]}
        pack={'edition_id':'2026-10-27-morning','prepared_at':AT.isoformat(),'sha256':'a'*64,'baseline':None,
              'baseline_stories':[{'story_id':f'old-{i}','identity':f'old-{i}','headline':'Προηγούμενη είδηση',
                'finding':greek,'section':'world','published_at':AT.isoformat()} for i in range(10)],'weather_status':'unavailable',
              'data':{'markets':[{'instrument':f'quote-{n}','value':n,'status':'delayed'} for n in range(38)],'panels':[],
                      'sports':{'coverage':{},'competitions':{f'uefa-{i}':{'scores':[event]*6,'fixtures':[event]*6,
                        'standings':[{'name':f'Team {n}','sources':[source]} for n in range(5)]} for i in range(3)}}},'candidates':candidates}
        before=copy.deepcopy(pack);digest=view.synthesis(pack)
        headers=[json.loads(line) for line in digest.splitlines() if line.startswith('{"id":') and '"section":' in line]
        for desk in ('cyprus','world'):
            self.assertEqual(sum(h['section']==desk for h in headers),5)
        self.assertNotIn('"id":"blocked","access"',digest)
        self.assertIn('"usable_evidence":0',digest)
        self.assertIn('Omitted candidate clusters due to input byte cap: 0',digest)
        self.assertIn('quote-37',digest)
        self.assertLessEqual(len(digest.encode()),48000)
        self.assertEqual(pack,before)  # Full sports tables and exact carry records stay intact.

    def test_foreign_rss_category_overrides_cyprus_publisher(self):
        item=ET.fromstring('<item><category>World</category></item>')
        self.assertEqual(news.feed_section(item,{'section':'cyprus'}),'world')
        local=ET.fromstring('<item><category>Κύπρος</category></item>')
        self.assertEqual(news.feed_section(local,{'section':'world'}),'cyprus')
        self.assertEqual(news.feed_section(ET.fromstring('<item/>'),{'section':'cyprus'}),'cyprus')

    def test_significant_followup_outweighs_routine_recency(self):
        routine=[{'title':'New city cafe opens this afternoon','publisher':'a'}]
        follow=[{'title':'Central bank interest rate decision affects mortgage costs','publisher':'a'}]
        baseline=[{'headline':'Central bank interest rate decision expected today'}]
        score,reasons=news.priority(follow,baseline)
        self.assertGreater(score,news.priority(routine,baseline)[0])
        self.assertIn('possible_baseline_followup',reasons)
        self.assertNotIn('story_id',follow[0])

    def test_greek_excerpt_keeps_sentence_beyond_old_byte_ceiling(self):
        text=('Η απόφαση επηρεάζει το κόστος χρηματοδότησης. '*22)+'Ο επόμενος έλεγχος αφορά την εφαρμογή.'
        self.assertGreater(len(text.encode()),1000)
        kept=news.excerpt(text,1600)
        self.assertEqual(kept,text)
        self.assertNotIn('\ufffd',news.excerpt(text,600))

    def test_article_collection_is_capped_and_all_desks_keep_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'templates/v2').mkdir(parents=True)
            feeds=[{'publisher':desk,'section':desk,'url':f'https://example.com/{desk}.rss','hosts':['example.com']} for desk in ('world','cyprus','sports')]
            feeds.append({'publisher':'second-world-publisher','section':'world','url':'https://example.com/second.rss','hosts':['example.com']})
            (root/'templates/v2/prefetch-feeds.json').write_text(json.dumps(feeds))
            # Each unique token occurs three times, preventing accidental discovery clustering.
            titles=['alpha','bravo','charlie','delta','echo','foxtrot','golf','hotel','india','juliet','kilo','lima']
            class Client:
                def __init__(self):self.calls=[]
                def many(self,urls):
                    rows={}
                    for url in set(urls):
                        self.calls.append(url)
                        if url.endswith('.rss'):
                            desk=url.rsplit('/',1)[1].split('.')[0]
                            text='<rss><channel>'+''.join(f'<item><title>{word} {word} development update</title><link>https://example.com/{desk}/{word}</link></item>' for word in titles)+'</channel></rss>'
                        else:text='<article><p>'+'Evidence of a specific reported development. '*15+'</p></article>'
                        rows[url]={'status':'available','text':text,'url':url,'retrieved_at':AT.isoformat()}
                    return rows
            client=Client()
            result=news.collect(root,{'stories':[]},client,AT,root/'private')
            self.assertLessEqual(result['metrics']['article_requests'],14)
            self.assertEqual({c['section'] for c in result['candidates']},{'world','cyprus','sports'})
            self.assertEqual(result['metrics']['article_requests'],14)
            # A provider failure consumes a request, not a scarce usable news slot.
            class Blocked(Client):
                def many(self,urls):
                    rows=super().many(urls)
                    for url,row in rows.items():
                        if '/cyprus/lima' in url or '/cyprus/kilo' in url:row['status']='unavailable'
                    return rows
            retry=Blocked();retried=news.collect(root,{'stories':[]},retry,AT,root/'retry-private')
            usable=[c for c in retried['candidates'] if any(e['access']=='article_excerpt' for e in c['evidence'])]
            self.assertGreaterEqual(sum(c['section']=='cyprus' for c in usable),4)
            self.assertGreaterEqual(sum(c['section']=='world' for c in usable),4)
            self.assertLessEqual(retried['metrics']['article_requests'],14)

    def test_digest_retains_provenance_and_greek_evidence_without_mutating_pack(self):
        source={'url':'https://example.com/table','retrieved_at':AT.isoformat()}
        greek='Συγκεκριμένα δεδομένα για την απόφαση και την εφαρμογή της. '*25
        pack={'edition_id':'2026-10-25-evening','prepared_at':AT.isoformat(),'sha256':'a'*64,
              'baseline':None,'baseline_stories':[],'weather_status':'unavailable',
              'data':{'markets':[{'instrument':f'quote-{n}','value':n,'status':'available'} for n in range(38)],'panels':[],
                      'sports':{'coverage':{},'competitions':{'uefa':{'scores':[{'name':str(n),'sources':[source]} for n in range(6)]}}}},
              'candidates':[{'id':'c1','section':'cyprus','title':'Δοκιμή',
                             'evidence':[{'id':'e1','access':'article_excerpt','source':source,'url':source['url'],'excerpt':greek}]}]}
        before=copy.deepcopy(pack);digest=view.synthesis(pack)
        self.assertEqual(pack,before)
        self.assertIn(greek,digest)
        self.assertEqual(digest.count('https://example.com/table'),2)  # routine reference plus article provenance
        self.assertIn('quote-37',digest)
        self.assertIn('Omitted candidate clusters due to input byte cap: 0',digest)
        self.assertLessEqual(len(digest.encode()),48000)


    def test_priority_club_survives_compact_competition_view(self):
        rows=[{'name':f'Club {n} vs Opponent','starts_at':AT.isoformat()} for n in range(6)]
        rows[-1]['name']='Real Madrid vs Opponent'
        pack={'edition_id':'2026-10-25-evening','prepared_at':AT.isoformat(),'sha256':'a'*64,
              'baseline':None,'baseline_stories':[],'weather_status':'unavailable','candidates':[],
              'data':{'markets':[],'panels':[],'sports':{'coverage':{},'competitions':{'uefa':{'fixtures':rows}}}}}
        digest=view.synthesis(pack)
        self.assertIn('Real Madrid vs Opponent',digest)
        self.assertNotIn('Club 4 vs Opponent',digest)
        self.assertIn('"fixtures_omitted":2',digest)


if __name__=='__main__':unittest.main()
