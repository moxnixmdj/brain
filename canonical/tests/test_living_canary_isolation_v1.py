"""Validate fail-closed controls against the current worktree implementation."""
from pathlib import Path
import tempfile
import hashlib
import unittest
from unittest.mock import patch

from canonical.tools.living_canary_isolation_v1 import PINNED, evaluate_canary


def skill(**overrides):
    row = {'skill_id': 'count', 'description': 'count lines',
           'template': 'wc -l < {path}', 'slots': {'path': 'source.txt'},
           'postcondition': r'^[0-9]+$', 'canary_input': {'canary.txt': 'a\nb\nc\n'},
           'canary_expected': '3'}
    row.update(overrides)
    return row


class CanaryIsolationUnitTests(unittest.TestCase):
    def test_unpinned_source_rejected_before_process_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'canonical/runtime'
            root.mkdir(parents=True)
            for name in PINNED:
                (root / (name + '.py')).write_text('untrusted')
            with patch('subprocess.Popen') as proc:
                with self.assertRaisesRegex(ValueError, 'HISTORICAL_SOURCE_HASH_MISMATCH'):
                    evaluate_canary(tmp, skill())
                proc.assert_not_called()

    def test_missing_namespace_launcher_fails_closed(self):
        # The source is only staged: Popen is forced to fail before execution.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'canonical/runtime'
            root.mkdir(parents=True)
            (root / 'fixture.py').write_text('fixture')
            digest = hashlib.sha256(b'fixture').hexdigest()
            with patch('canonical.tools.living_canary_isolation_v1.PINNED', {'fixture': digest}), \
                 patch('subprocess.Popen', side_effect=FileNotFoundError):
                result = evaluate_canary(tmp, skill())
            self.assertEqual(result['status'], 'ISOLATION_UNAVAILABLE')
            self.assertFalse(result['pass'])
