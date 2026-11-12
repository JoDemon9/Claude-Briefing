"""Regression coverage for the private host timer's deployed reference."""
from datetime import datetime
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

REFERENCE = Path(__file__).resolve().parents[1] / 'deployment/private-prefetch-window.py.example'
SPEC = spec_from_loader('private_prefetch_window', SourceFileLoader('private_prefetch_window', str(REFERENCE)))
CLOCK = module_from_spec(SPEC)
SPEC.loader.exec_module(CLOCK)
EDITION = '2026-11-12-evening'


class PrivatePrefetchWindowTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.run = self.root / 'research/runs' / EDITION
        self.submission = self.root / 'sources/synthesis' / (EDITION + '.md')

    def pack(self, prepared='2026-11-12T16:21:23+00:00', ready=True):
        self.run.mkdir(parents=True, exist_ok=True)
        (self.run / 'research_pack.json').write_text('{}', encoding='utf-8')
        (self.run / 'digest.md').write_text('\n'.join([
            '# Prepared synthesis digest · oracle-synthesis/1',
            'Prepared at ' + prepared + '; expires after 90 minutes.',
            'Private submission workflow installed: True',
            'submission_ready=' + str(ready).lower() + '.',
            'Copy the header.',
            '@Edition v=1 id=' + EDITION + ' published=auto',
            '@Pack sha256=' + 'a' * 64,
        ]), encoding='utf-8')

    def select(self, stamp):
        return CLOCK.select_slot('schedule', '', datetime.fromisoformat(stamp), self.root)

    def test_observed_delay_is_eligible_after_expiry(self):
        self.pack()
        self.assertEqual(self.select('2026-11-12T18:35:04+00:00'), 'evening')
        self.assertIsNone(self.select('2026-11-12T19:31:00+00:00'))

    def test_fresh_pack_and_submission_are_left_in_place(self):
        self.pack()
        self.assertIsNone(self.select('2026-11-12T17:51:23+00:00'))
        self.submission.parent.mkdir(parents=True)
        self.submission.write_text('submitted', encoding='utf-8')
        self.assertIsNone(self.select('2026-11-12T18:35:04+00:00'))
        self.assertIsNone(self.select('2026-11-12T16:55:00+00:00'))

    def test_missing_pack_is_eligible_only_in_recovery_or_original_window(self):
        self.assertEqual(self.select('2026-11-12T16:55:00+00:00'), 'evening')
        self.assertIsNone(self.select('2026-11-12T17:25:00+00:00'))
        self.assertEqual(self.select('2026-11-12T18:35:04+00:00'), 'evening')

    def test_unready_pack_fails_closed(self):
        self.pack(ready=False)
        with self.assertRaisesRegex(ValueError, 'Submission not ready'):
            self.select('2026-11-12T18:35:04+00:00')

    def test_explicit_dispatch_keeps_its_slot(self):
        at = datetime.fromisoformat('2026-11-12T18:35:04+00:00')
        self.assertEqual(CLOCK.select_slot('workflow_dispatch', 'midday', at, self.root), 'midday')
