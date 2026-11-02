"""The raw front door must recognize, not authorize, a missing verifier."""
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import unified_cognitive_fabric_v1 as fabric

CID = 'python.software.repair.apply.verified.v1'
CODE = 'BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT'


class VerificationGapTests(unittest.TestCase):
    def test_exact_refusal_records_only_capability_and_reason(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'state.json'
            out = {'pass': False, 'compiled_capability_id': CID,
                   'reason': 'Blocker:BoundExecutionError:' + CODE + ':' + CID,
                   'raw_goal': 'private goal should not be copied'}
            result = fabric._notice_missing_bound_verification(out, {'state_path': str(state)})
            self.assertEqual(result['status'], 'RECORDED')
            self.assertFalse(result['execution_authority'])
            path = Path(str(state) + '.ignorance.json')
            data = json.loads(path.read_text())
            self.assertEqual(len(data['gaps']), 1)
            self.assertIn(result['gap_id'], data['gaps'])
            self.assertNotIn(out['raw_goal'], path.read_text())

    def test_disabled_learning_or_wrong_refusal_never_writes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'gaps.json'
            base = {'pass': False, 'compiled_capability_id': CID,
                    'reason': CODE + ':' + CID}
            cases = [
                (base, {'learn': False, 'ignorance_state_path': str(path)}),
                ({**base, 'pass': True}, {'ignorance_state_path': str(path)}),
                ({**base, 'pass': None}, {'ignorance_state_path': str(path)}),
                ({**base, 'reason': CODE + ':' + CID + '.extra'}, {'ignorance_state_path': str(path)}),
                ({**base, 'reason': 'different failure'}, {'ignorance_state_path': str(path)}),
                ({**base, 'compiled_capability_id': '../unsafe'}, {'ignorance_state_path': str(path)}),
            ]
            for out, options in cases:
                self.assertIsNone(fabric._notice_missing_bound_verification(out, options))
                self.assertFalse(path.exists())

    def test_empty_custom_state_path_fails_instead_of_using_default(self):
        out = {'pass': False, 'compiled_capability_id': CID, 'reason': CODE + ':' + CID}
        result = fabric._notice_missing_bound_verification(out, {'ignorance_state_path': ''})
        self.assertEqual(result['status'], 'RECORD_FAILED')
        self.assertEqual(result['error'], 'ValueError')
        self.assertFalse(result['execution_authority'])

    def test_unwritable_ledger_is_reported_without_granting_authority(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td) / 'not-a-directory'
            parent.write_text('preserve me')
            out = {'pass': False, 'compiled_capability_id': CID, 'reason': CODE + ':' + CID}
            result = fabric._notice_missing_bound_verification(out, {'ignorance_state_path': str(parent / 'x')})
            self.assertEqual(result['status'], 'RECORD_FAILED')
            self.assertFalse(result['execution_authority'])
            self.assertEqual(parent.read_text(), 'preserve me')


if __name__ == '__main__':
    unittest.main()
