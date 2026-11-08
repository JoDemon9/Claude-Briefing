"""Historical source continuity without guessed IDs or refreshed evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location('continuity_test_'+name,ROOT/'scripts/v2'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
continuity=load('story_continuity')
AT='2026-11-08T06:00:00+00:00'
URL='https://example.com/event'

def record(sid='established-event',url=URL,**changes):
    return dict(story_id=sid,identity=sid,edition_id='2026-11-04-evening',
        available_at='2026-11-04T18:00:00Z',published_at='2026-11-04T17:00:00Z',
        headline='The original event',sources=[dict(url=url)],**changes)

def candidate(url=URL,title='A translated headline'):
    return dict(id='c1',section='world',title=title,baseline_matches=[],
                evidence=[dict(url=url,access='article_excerpt',source=dict(url=url),
                               excerpt='Previously read source passages.',retrieved_at=AT)])

class StoryContinuityTests(unittest.TestCase):
    def test_exact_older_source_survives_outside_baseline_with_original_dates(self):
        old=record('old-alias');c=[candidate(URL+'/?utm_source=rss')]
        original=copy.deepcopy(c)
        result=continuity.match(c,[old],{'old-alias':'established-event'},{},AT,'2026-11-08-morning')
        hint=result[0]['known_story_matches'][0]
        self.assertEqual((hint['story_id'],hint['identity']),('established-event',)*2)
        self.assertEqual(hint['published_at'],old['published_at'])
        self.assertEqual(result[0]['evidence'],c[0]['evidence'])
        self.assertEqual(c,original)
        self.assertEqual(result[0]['baseline_matches'],[])

    def test_reviewed_veeam_reporting_url_refers_to_exact_vendor_incident(self):
        review={'https://paper.example/veeam':dict(story_id='veeam-boot',supporting_url=URL,
             reviewed_at='2026-11-08T05:00:00Z',reason='Same appliance boot failure verified against the vendor KB.')}
        result=continuity.match([candidate('https://paper.example/veeam')],[record('veeam-boot')],{},review,AT,'new')
        self.assertEqual(result[0]['known_story_matches'][0]['story_id'],'veeam-boot')
        self.assertEqual(result[0]['known_story_matches'][0]['match'],'reviewed_source_identity')
        review['https://paper.example/veeam']['supporting_url']='https://example.com/different-kb'
        with self.assertRaisesRegex(ValueError,'supporting URL'):
            continuity.match([candidate()],[record('veeam-boot')],{},review,AT,'new')

    def test_future_current_edition_and_similar_headlines_do_not_establish_identity(self):
        future=record();future['available_at']='2026-11-09T18:00:00Z'
        current=record();current['edition_id']='current'
        for rows in ([future],[current],[record(url='https://example.com/unrelated')]):
            result=continuity.match([candidate(title='The original event')],rows,{}, {},AT,'current')
            self.assertNotIn('known_story_matches',result[0])

    def test_shared_roundup_keeps_both_review_candidates_and_actionable_gate(self):
        result=continuity.match([candidate()],[record('first'),record('second')],{},{},AT,'new')
        self.assertEqual([r['story_id'] for r in result[0]['known_story_matches']],['first','second'])
        self.assertNotIn('story_id',result[0])  # No automatic merge or assignment.
        backend=load('backend')
        docs=[dict(id=sid,story_id=sid,story_identity=sid,url=sid+'.html',headline=sid,
                   sources=[dict(url=URL,access='read',used_for_claims=True)]) for sid in ('first','second')]
        edition=dict(id='2026-11-08-morning',date='2026-11-08')
        with self.assertRaisesRegex(ValueError,'shared_reporting_url: first, second; https://example.com/event'):
            backend.story_registry([(edition,docs)],{})

    def test_new_financial_digest_preserves_identity_hints_and_byte_budget(self):
        from test_financial_insights import current,view
        pack,_,_=current()
        hints=[dict(story_id='original-event',identity='original-event',headline='Original event',
                    published_at='2026-10-20T08:00:00Z',match='exact_reporting_url')]
        pack['candidates'][0]['known_story_matches']=hints
        before=copy.deepcopy(pack)
        digest=view.synthesis(pack)
        headers=[json.loads(l) for l in digest.splitlines() if l.startswith('{"id":') and '"section":' in l]
        self.assertEqual(headers[0]['known_story_matches'],hints)
        self.assertIn('not new evidence or automatic merges',digest)
        self.assertLessEqual(len(digest.encode()),48000)
        self.assertEqual(pack,before)

    def test_real_archive_maps_asian_source_and_reviewed_veeam_url(self):
        cnbc='https://www.cnbc.com/2026/11/06/tech-stocks-sk-hynix-samsung-softbank.html'
        bleep='https://www.bleepingcomputer.com/news/security/veeam-software-appliance-vms-fail-to-boot-on-amd-epyc-hosts/'
        result=continuity.annotate(ROOT,[candidate(cnbc),candidate(bleep)],AT,'2026-11-08-morning')
        self.assertEqual([h['story_id'] for h in result[0]['known_story_matches']],['big-tech-post-midterms-rally-2026-11-04'])
        self.assertEqual([h['story_id'] for h in result[1]['known_story_matches']],['veeam-epyc-appliance-boot-2026-11-04'])

if __name__=='__main__':unittest.main()
