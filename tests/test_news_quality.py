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
