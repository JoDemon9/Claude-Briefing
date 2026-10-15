"""DEC-012: explicit later coverage, with the original findings preserved."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('follow_up_builder',ROOT/'scripts/v2/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
daily=build.load_module('daily')
FROM='global-markets-ai-rates-october-15-2026'
TO='tsmc-q3-2026-results-preview'


class FollowUpTests(unittest.TestCase):
    def setUp(self):
        build.ROOT=ROOT
        self.bundles=[]
        for slot in ('morning','midday'):
            e=json.loads((ROOT/'content/editions'/f'2026-10-15-{slot}.json').read_text())
            self.bundles.append((e,[json.loads((ROOT/'content'/p).read_text()) for p in e['articles']]))

    def compose(self):
        return daily.compose('2026-10-15',self.bundles)

    def test_preview_links_to_selected_published_outcome_without_changing_either(self):
        before=copy.deepcopy(self.bundles)
        model=self.compose();daily.validate(ROOT,model,self.bundles)
        self.assertEqual(model['follow_ups'],[{'from_story_id':FROM,'to_story_id':TO,'reviewed_in':'2026-10-15-midday'}])
        doc=BeautifulSoup(daily.render(build,model,self.bundles),'html.parser')
        earlier=doc.select_one('[data-story-id="'+FROM+'"]')
        self.assertIn('Πρωινό πλαίσιο',earlier.select_one('.story-status').text)
        link=earlier.select_one('.story-follow-up a')
        target=doc.select_one(link['href'])
        self.assertEqual(target['data-story-id'],TO)
        self.assertIn(target.h3.text,link.text)
        original=next(a for _,aa in self.bundles for a in aa if a['story_id']==FROM)
        self.assertEqual(earlier.select_one('.abstract').text,original['summary'])
        self.assertEqual(len(doc.select('[data-story-id]')),len(model['stories']))
        self.assertEqual(self.bundles,before)

    def test_absent_draft_or_self_reference_is_rejected(self):
        records=self.bundles[-1][0]['daily']['follow_ups']
        records[0]['to_story_id']='unpublished-draft'
        with self.assertRaisesRegex(ValueError,'unavailable'):self.compose()
        records[0]['to_story_id']=FROM
        with self.assertRaisesRegex(ValueError,'itself'):self.compose()

    def test_unknown_future_edition_cannot_be_linked_by_an_earlier_snapshot(self):
        self.bundles[0][0]['daily']['follow_ups']=[{'from_story_id':FROM,'to_story_id':'cyprus-gsi-navtex-payment-october-2026'}]
        with self.assertRaisesRegex(ValueError,'future or draft'):self.compose()

    def test_similar_headlines_do_not_create_a_relationship(self):
        self.bundles[-1][0]['daily']['follow_ups']=[]
        self.assertEqual(self.compose()['follow_ups'],[])

    def test_same_edition_or_stale_pointer_is_not_presented_as_a_later_update(self):
        self.bundles[-1][0]['daily']['follow_ups']=[{'from_story_id':FROM,'to_story_id':'european-council-october-15-16-2026'}]
        self.assertEqual(self.compose()['follow_ups'],[])
        self.bundles[-1][0]['daily']['follow_ups']=[{'from_story_id':FROM,'to_story_id':TO}]
        update=copy.deepcopy(self.bundles[0][1][0]);update['id']='market-context-update'
        update.get('daily',{}).pop('events',None)
        self.bundles[-1][1].append(update)
        self.assertEqual(self.compose()['follow_ups'],[])

    def test_explicit_aliases_resolve_and_conflicting_targets_are_rejected(self):
        records=self.bundles[-1][0]['daily']['follow_ups']
        records[0]={'from_story_id':'old-context-id','to_story_id':'old-results-id'}
        model=daily.compose('2026-10-15',self.bundles,aliases={'old-context-id':FROM,'old-results-id':TO})
        daily.validate(ROOT,model,self.bundles)
        self.assertEqual(model['follow_ups'][0]['to_story_id'],TO)
        records[:]=[{'from_story_id':FROM,'to_story_id':TO},{'from_story_id':FROM,'to_story_id':'european-council-october-15-16-2026'}]
        with self.assertRaisesRegex(ValueError,'only one follow-up'):self.compose()

    def test_model_validation_rejects_a_tampered_backwards_link(self):
        model=self.compose()
        model['follow_ups'][0].update(from_story_id=TO,to_story_id=FROM)
        with self.assertRaisesRegex(ValueError,'later published'):daily.validate(ROOT,model,self.bundles)

    def test_mobile_menu_reapplication_keeps_links_and_real_publication_identity(self):
        model=self.compose();e=self.bundles[-1][0]
        html=daily.render(build,model,self.bundles)
        doc=BeautifulSoup(html,'html.parser')
        frontend=build.load_module('newspaper_ui')
        reapplied=frontend.decorate(build,html,e,model)
        self.assertEqual(frontend.decorate(build,reapplied,e,model),reapplied)
        self.assertEqual(len(doc.select('.mobile-editions')),1)
        self.assertFalse(doc.select_one('.mobile-editions').has_attr('open'))
        self.assertEqual([a['href'] for a in doc.select('.mobile-edition-links a')],[a['href'] for a in doc.select('.edition-desk a')])
        self.assertEqual(doc.select_one('.mobile-publication-date')['datetime'],model['date'])
        self.assertFalse(doc.select('.reading-layer,.reading-time'))
        self.assertNotIn('Η είδηση · 30 δευτερόλεπτα',html)


if __name__=='__main__':unittest.main()
