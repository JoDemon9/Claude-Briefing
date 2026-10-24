"""Contract, authoring, reuse and authentication regressions for DEC-024."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from bs4 import BeautifulSoup
from test_compose import payload_fixture

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('intelligence_test_'+name, ROOT/'scripts/v2'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


compose, markdown, baseline, intelligence, build, publish = [load(name) for name in ('compose','markdown_input','baseline','intelligence','build','publish')]


class IntelligenceTests(unittest.TestCase):
    def test_quoted_attribute_values_preserve_separators_and_json_escapes(self):
        self.assertEqual(markdown.attributes('caption="A | B \\n Greek \\"quote\\"" | v=1'),{'caption':'A | B \n Greek "quote"','v':'1'})
    def test_markdown_and_json_compile_to_identical_canonical_records(self):
        raw=payload_fixture()
        raw['articles'][0].update(driver_tags=['EastMed','Energy'])
        parsed=markdown.parse(markdown.export(raw), ROOT)
        expected=compose.compile_payload(raw, ROOT)
        actual=compose.compile_payload(parsed, ROOT)
        self.assertEqual(actual, expected)
        self.assertEqual(actual[1][0]['driver_tags'], ['eastmed','energy'])

    def test_parser_rejects_injection_unknown_directives_and_ambiguous_fields(self):
        text=markdown.export(payload_fixture())
        for value in (text+'\n@Unexpected arbitrary\n', text.replace('@Headline ', '@Headline <script>alert(1)</script>',1),
                      text.replace('v="1"','v="1" v="1"',1), text.replace('v="1"','v="99"',1),
                      text.replace('@Headline ', '@Tags energy\n@Tags eastmed\n@Headline ',1)):
            with self.subTest(value=value[:80]),self.assertRaises(ValueError):markdown.parse(value,ROOT)

    def test_source_aliases_and_analytical_review_are_required(self):
        text=markdown.export(payload_fixture())
        with self.assertRaisesRegex(ValueError,'source reference'):
            markdown.parse(text.replace('@Fact ','@Fact [missing] ',1),ROOT)
        raw=payload_fixture();raw['articles']=raw['articles'][:1]
        for key in ('analysis_sources','mechanics_and_incentives','second_order_effects','scenarios','newspaper_analysis'):
            raw['articles'][0].pop(key,None)
        with self.assertRaisesRegex(ValueError,'AnalysisSources'):
            markdown.parse(markdown.export(raw).replace('@Fact ','@Mechanism causal test\n@Fact ',1),ROOT)

    def test_shared_gate_rejects_slot_and_inventory_drift(self):
        edition, articles, _=compose.compile_payload(payload_fixture(),ROOT)
        edition['edition_mode']='midday_delta'
        with self.assertRaisesRegex(ValueError,'scheduled slot'):intelligence.validate(edition,articles,ROOT)
        edition['edition_mode']='evening_synthesis';edition['markets'].pop()
        with self.assertRaisesRegex(ValueError,'every market'):intelligence.validate(edition,articles,ROOT)
        edition.pop('intelligence_contract')
        with self.assertRaisesRegex(ValueError,'Current producer'):intelligence.validate(edition,articles,ROOT)

    def test_explicit_carry_retains_evidence_and_fails_when_baseline_changes(self):
        old=json.loads((ROOT/'content/editions/2026-10-23-evening.json').read_text(encoding='utf-8'))
        records=[json.loads((ROOT/'content'/path).read_text(encoding='utf-8')) for path in old['articles']]
        raw=payload_fixture();raw.update(edition_id='2026-10-24-evening',published_at='2026-10-24T20:15:00+03:00',editorial_completed_at='2026-10-24T20:15:00+03:00',baseline={'edition_id':old['id'],'fingerprint':baseline.fingerprint(old,records)})
        first=records[0];raw['articles']=[a for a in raw['articles'] if a['story_id']!=first['story_id'] and a['slug']!=first['id']];raw['carry_story_ids']=[first['story_id']]
        raw['articles']=raw['articles'][:1]
        edition, docs, _=compose.compile_payload(raw,ROOT)
        carried=next(a for a in docs if a['story_id']==first['story_id'])
        for key in ('published_at','updated_at','sources','image','summary'):
            self.assertEqual(carried[key],records[0][key])
        self.assertEqual(carried['change_status'],'UNCHANGED')
        baseline.validate_carried(carried,ROOT,edition['published_at'])
        carried['summary']='A forged replacement summary'
        with self.assertRaisesRegex(ValueError,'changed'):baseline.validate_carried(carried,ROOT,edition['published_at'])
        raw['baseline']['fingerprint']='0'*64
        with self.assertRaisesRegex(ValueError,'fingerprint'):compose.compile_payload(raw,ROOT)

    def test_carry_does_not_silently_inherit_prices_or_weather(self):
        old=json.loads((ROOT/'content/editions/2026-10-23-evening.json').read_text(encoding='utf-8'))
        records=[json.loads((ROOT/'content'/path).read_text(encoding='utf-8')) for path in old['articles']]
        raw={'edition_id':'2026-10-24-evening','published_at':'2026-10-24T20:15:00+03:00','editorial_completed_at':'2026-10-24T20:15:00+03:00',
             'reading_review':{'version':2,'completed_at':'2026-10-24T20:15:00+03:00'},'articles':[],
             'baseline':{'edition_id':old['id'],'fingerprint':baseline.fingerprint(old,records)},'carry_story_ids':[records[0]['story_id']]}
        edition, _, _=compose.compile_payload(raw,ROOT)
        self.assertTrue(all(q['value'] is None for q in edition['markets']))
        self.assertFalse(edition['panels'])

    def test_scenarios_are_escaped_complete_and_not_forced(self):
        value=build.article_layers({'id':'test','change_status':'UNKNOWN','scenarios':{'base_case':'base & evidence','alternative_case':'alternative','tail_risk':'<unsafe>','watch_next':'a dated trigger'}})
        doc=BeautifulSoup(value,'html.parser')
        self.assertEqual(len(doc.select('[data-scenario-panel]')),3)
        self.assertIn('&lt;unsafe&gt;',value)
        self.assertIn('a dated trigger',doc.text)
        self.assertFalse(doc.select('[data-scenario-panel][hidden]'))
        self.assertEqual(build.article_layers({}),'')

    def test_role_credentials_survive_worktrees_without_command_line_secrets(self):
        token='test-credential-not-a-real-secret'
        with mock.patch.dict(os.environ,{'ORACLE_PORTAL_PUSH_TOKEN':token,'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'test.key','GIT_CONFIG_VALUE_0':'existing'}):
            adapter=publish.GitPublisher(ROOT,'portal');env=adapter.environment()
            self.assertEqual(env['GIT_CONFIG_COUNT'],'3')
            self.assertEqual(env['GIT_CONFIG_VALUE_1'],'')
            self.assertEqual(env['GIT_CONFIG_KEY_2'],'http.https://github.com/.extraheader')
            with mock.patch.object(subprocess,'check_output',return_value='ok') as call:
                adapter.git('status','--short')
                self.assertNotIn(token,str(call.call_args.args))
                self.assertIn('AUTHORIZATION: basic ',call.call_args.kwargs['env']['GIT_CONFIG_VALUE_2'])

    def test_denied_preflight_is_actionable_and_cannot_claim_success(self):
        adapter=publish.GitPublisher(ROOT,'portal')
        with mock.patch.object(adapter,'git',side_effect=['',subprocess.CalledProcessError(128,['git','push'])]):
            with self.assertRaisesRegex(ValueError,'Contents write'):adapter.preflight()


if __name__=='__main__':unittest.main()
