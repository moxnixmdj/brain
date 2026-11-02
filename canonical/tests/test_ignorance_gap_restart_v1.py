"""An observed knowledge gap must remain the same gap after process restart."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKER = r'''
import json, sys
from canonical.runtime import ignorance_ledger_v1 as ledger
path, action = sys.argv[1:]
if action == 'note':
    print(json.dumps({'id': ledger.note('independent verification for repair',
        why='bound execution blocked', path=path)}))
elif action == 'resolve':
    rows = ledger.rank(path=path)
    print(json.dumps({'id': rows[0]['id'],
        'updated': ledger.resolve(rows[0]['id'], helped=False, close=False, path=path)}))
elif action == 'close':
    rows = ledger.rank(path=path)
    print(json.dumps({'id': rows[0]['id'],
        'updated': ledger.resolve(rows[0]['id'], helped=True, close=True, path=path)}))
elif action == 'other':
    print(json.dumps({'id': ledger.note('independent verification for audit',
        why='bound execution blocked', path=path)}))
'''


class IgnoranceGapRestartTests(unittest.TestCase):
    def _worker(self, path, action, seed):
        env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPATH=str(ROOT))
        proc = subprocess.run([sys.executable, '-c', WORKER, str(path), action],
                              cwd=ROOT, env=env, capture_output=True, text=True,
                              check=True, timeout=30)
        return json.loads(proc.stdout)

    def test_same_gap_accumulates_across_fresh_interpreters(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'gaps.json'
            first = self._worker(state, 'note', 1)['id']
            resolution = self._worker(state, 'resolve', 2)
            second = self._worker(state, 'note', 3)['id']
            self.assertTrue(resolution['updated'])
            self.assertEqual(first, resolution['id'])
            self.assertEqual(first, second)
            data = json.loads(state.read_text())['gaps']
            self.assertEqual(len(data), 1)
            self.assertEqual(data[first]['trials'], 1)
            self.assertEqual(data[first]['helped'], 0)
            self.assertFalse(data[first]['resolved'])
            other = self._worker(state, 'other', 4)['id']
            self.assertNotEqual(first, other)
            self.assertEqual(len(json.loads(state.read_text())['gaps']), 2)

    def test_recurring_gap_reopens_without_erasing_history(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'gaps.json'
            first = self._worker(state, 'note', 1)['id']
            self.assertTrue(self._worker(state, 'close', 2)['updated'])
            self.assertTrue(json.loads(state.read_text())['gaps'][first]['resolved'])
            self.assertEqual(self._worker(state, 'note', 3)['id'], first)
            row = json.loads(state.read_text())['gaps'][first]
            self.assertFalse(row['resolved'])
            self.assertEqual((row['trials'], row['helped']), (1, 1))

    def test_conflicting_stable_id_fails_closed_without_overwriting(self):
        from canonical.runtime import ignorance_ledger_v1 as ledger
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'gaps.json'
            gid = ledger._key('independent verification for repair', 'bound execution blocked')
            original = json.dumps({'schema': ledger.SCHEMA, 'gaps': {gid: {
                'id': gid, 'what': 'different thing', 'why': '', 'trials': 7}}})
            state.write_text(original)
            with self.assertRaisesRegex(ValueError, 'IGNORANCE_GAP_IDENTITY_CONFLICT'):
                ledger.note('independent verification for repair',
                            why='bound execution blocked', path=str(state))
            self.assertEqual(state.read_text(), original)

    def test_legacy_id_and_learning_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'gaps.json'
            state.write_text(json.dumps({'schema': 'PROJECT_BRAIN_IGNORANCE_LEDGER_V1',
                'gaps': {'g123': {'id': 'g123', 'what': 'bound execution blocked',
                    'why': 'independent verification for repair', 'cost': 1.0,
                    'trials': 3, 'helped': 1, 'created': 1, 'last_seen': 1,
                    'resolved': False}}}))
            first = self._worker(state, 'note', 100)['id']
            second = self._worker(state, 'note', 200)['id']
            self.assertEqual(first, 'g123')
            self.assertEqual(second, 'g123')
            data = json.loads(state.read_text())['gaps']
            self.assertEqual(len(data), 1)
            self.assertEqual((data['g123']['trials'], data['g123']['helped']), (3, 1))
            self.assertEqual(data['g123']['created'], 1)


if __name__ == '__main__':
    unittest.main()
