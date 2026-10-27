"""Saved prompts retain usable date paths and explicit budgets after text copying."""
import importlib.util
from pathlib import Path
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('saved_task_prompts', ROOT/'scripts/v2/task_prompts.py')
prompts = importlib.util.module_from_spec(spec); spec.loader.exec_module(prompts)


class TaskPromptTests(unittest.TestCase):
    def test_rich_text_copy_preserves_date_variables_paths_and_slot_budget(self):
        for slot in prompts.SLOTS:
            with self.subTest(slot=slot):
                text = (ROOT/'prompts'/f'{slot}.md').read_text(encoding='utf-8')
                # The previous unescaped <today> became an HTML element and
                # disappeared when the rendered prompt was copied into Scheduled.
                self.assertEqual(BeautifulSoup(text,'html.parser').get_text(),text)
                self.assertNotIn('<',text)
                self.assertNotIn('|',text)  # No budget table to flatten on copy.
                self.assertIn('Europe/Athens as RUN_DATE in YYYY-MM-DD form',text)
                self.assertIn(f'RUN_DATE followed by -{slot}',text)
                resolved = text.replace('EDITION_ID',f'2026-10-28-{slot}')
                self.assertIn(f'research/runs/2026-10-28-{slot}/digest.md',resolved)
                self.assertIn(f'sources/synthesis/2026-10-28-{slot}.md',resolved)
                self.assertNotIn(f'research/runs/-{slot}',text)
                labels = [name.title()+' budget:' for name in prompts.SLOTS]
                self.assertEqual(sum(text.count(label) for label in labels),1)
                self.assertIn(slot.title()+' budget:',text)
                for value in (('5 targeted searches','2 URL opens','10 total tool calls','10 authored stories','6,500')
                              if slot=='morning' else
                              ('3 targeted searches','1 URL open','7 total tool calls','6 changed authored stories','4,000')):
                    self.assertIn(value,text)
                self.assertIn('one review',text)
                self.assertIn('Never overwrite a submission',text)

    def test_both_prompt_sets_match_the_canonical_execution_contract(self):
        prompts.generate(ROOT,check=True)
        for slot in prompts.SLOTS:
            self.assertEqual((ROOT/'prompts'/f'{slot}.md').read_bytes(),
                             (ROOT/'templates/v2/task-prompts'/f'{slot}.txt').read_bytes())


if __name__=='__main__':unittest.main()
