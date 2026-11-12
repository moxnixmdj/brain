"""Fallback refusal must not erase the primary route's diagnostic evidence."""
import unittest
from unittest import mock

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler


class PrimaryFailureEvidenceTests(unittest.TestCase):
    def test_blocked_acting_fallback_retains_primary_evidence_and_uncertainty(self):
        primary = {'pass': False, 'status': 'FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN',
                   'failure_class': 'STEP_RAISED_OUTCOME_UNKNOWN', 'executed': True,
                   'side_effects_may_exist': True, 'compiled_capability_id': 'example',
                   'composer_execution': {'steps': [{'adapter_raised': 'RuntimeError:SOURCE_ROOT_MISSING'}]}}
        request = {'task_id': 'T', 'goal': 'compress notes.txt into notes.txt.gz'}
        with mock.patch.object(door, '_solve_request', return_value=primary), \
             mock.patch.object(compiler, 'recall_and_execute_workflow') as recall:
            result = door.solve(request)
        self.assertEqual(result['status'], 'FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT')
        self.assertEqual(result['served_after'], primary['status'])
        self.assertEqual(result['primary_result'], primary)
        self.assertFalse(result['fallback_executed'])
        self.assertTrue(result['side_effects_may_exist'])
        recall.assert_not_called()

    def test_blocked_workflow_retains_primary_evidence(self):
        primary = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP',
                   'executed': True, 'side_effects_may_exist': False,
                   'compiled_capability_id': 'example'}
        request = {'task_id': 'T', 'goal': 'an unfamiliar operation'}
        with mock.patch.object(door, '_solve_request', return_value=primary), \
             mock.patch.object(door, '_serve_by_acting', return_value=None), \
             mock.patch.object(compiler, 'recall_and_execute_workflow', return_value={
                 'status': 'FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT'}):
            result = door.solve(request)
        self.assertEqual(result['status'], 'FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT')
        self.assertEqual(result['primary_result'], primary)
        self.assertTrue(result['side_effects_may_exist'])
        self.assertFalse(result['pass'])


if __name__ == '__main__':
    unittest.main()
