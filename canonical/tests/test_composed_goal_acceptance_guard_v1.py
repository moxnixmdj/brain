"""Composition is not a goal verdict; uncertain effects forbid blind retries."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import composer_route_v1 as composer
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller


ROUTE = {'pass': True, 'chain': ['test.capability'], 'token': 'test.output', 'tried': []}
CHAIN = {'pass': True, 'status': 'PASS__COMPOSER_CHAIN_EXECUTED',
         'steps': [{'index': 0, 'capability_id': 'test.capability', 'result': {'ok': True}}],
         'produced': {}, 'created_paths': []}
UNVERIFIED = {'semantic_acceptance_complete': False, 'accepted_raw_obligation_ids': []}
VERIFIED = {'semantic_acceptance_complete': True, 'accepted_raw_obligation_ids': ['o1']}


class ComposedGoalAcceptanceGuardTests(unittest.TestCase):
    def test_front_composition_without_a_verdict_is_not_a_goal_success(self):
        with mock.patch.object(composer, 'route', return_value=ROUTE), \
             mock.patch.object(composer, 'execute_chain', return_value=CHAIN), \
             mock.patch.object(door, '_composed_acceptance', return_value=UNVERIFIED):
            result = door._try_composed('t', 'produce a result', time.perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertFalse(result['semantic_acceptance_complete'])
        self.assertEqual(result['status'], 'FAIL_CLOSED__COMPOSED_GOAL_NOT_VERIFIED')
        self.assertTrue(result['side_effects_may_exist'])
        self.assertIs(door._composed_holds_up(result, 'produce a result', []), result)

    def test_front_composition_with_verified_acceptance_still_passes(self):
        with mock.patch.object(composer, 'route', return_value=ROUTE), \
             mock.patch.object(composer, 'execute_chain', return_value=CHAIN), \
             mock.patch.object(door, '_composed_acceptance', return_value=VERIFIED):
            result = door._try_composed('t', 'produce a result', time.perf_counter_ns())
        self.assertTrue(result['pass'])
        self.assertTrue(result['semantic_acceptance_complete'])

    def test_verifier_exception_does_not_turn_execution_into_success(self):
        with mock.patch.object(composer, 'route', return_value=ROUTE), \
             mock.patch.object(composer, 'execute_chain', return_value=CHAIN), \
             mock.patch.object(door, '_composed_acceptance', side_effect=RuntimeError('verifier unavailable')):
            front = door._try_composed('t', 'produce a result', time.perf_counter_ns())
            self.assertFalse(front['pass'])
            self.assertTrue(front['side_effects_may_exist'])
            with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=None), \
                 mock.patch.object(door, 'solve', return_value={'pass': False, 'executed': False}), \
                 mock.patch.object(controller, 'discover_and_execute_semantic_web_form') as web:
                tier1 = controller.solve_or_learn({'task_id': 't', 'goal': 'produce a result'},
                                                  record_open_gap=False)
            self.assertFalse(tier1['pass'])
            self.assertTrue(tier1['side_effects_may_exist'])
            web.assert_not_called()

    def test_real_composed_text_write_is_reopened_and_checked(self):
        root = Path(__file__).resolve().parents[2]
        temp_root = root / 'canonical/astra_runtime/tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='composition_check_', dir=temp_root) as td:
            output = Path(td) / 'answer.txt'
            relative = output.relative_to(root).as_posix()
            result = door._try_composed('t', 'write the text hello to ' + relative, time.perf_counter_ns())
            self.assertTrue(result['pass'], result)
            self.assertTrue(result['semantic_acceptance_complete'])
            self.assertEqual(output.read_bytes(), b'hello')
            self.assertTrue(result['raw_goal_acceptance']['pass'])

    def test_controller_real_composition_requires_and_gets_acceptance(self):
        root = Path(__file__).resolve().parents[2]
        temp_root = root / 'canonical/astra_runtime/tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='composition_check_', dir=temp_root) as td:
            output = Path(td) / 'answer.txt'
            relative = output.relative_to(root).as_posix()
            front = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP', 'executed': False}
            with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=None), \
                 mock.patch.object(door, 'solve', return_value=front):
                result = controller.solve_or_learn({'task_id': 't',
                    'goal': 'write the text hello to ' + relative}, record_open_gap=False)
            self.assertTrue(result['pass'], result)
            self.assertTrue(result['semantic_acceptance_complete'])
            self.assertEqual(output.read_bytes(), b'hello')
            self.assertTrue(result['raw_goal_acceptance']['pass'])

    def test_real_verifier_refuses_wrong_output_despite_chain_pass(self):
        root = Path(__file__).resolve().parents[2]
        temp_root = root / 'canonical/astra_runtime/tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='composition_check_', dir=temp_root) as td:
            output = Path(td) / 'answer.txt'
            output.write_bytes(b'wrong')
            relative = output.relative_to(root).as_posix()
            goal = 'write the text hello to ' + relative
            bad = {'pass': True, 'status': 'PASS__COMPOSER_CHAIN_EXECUTED',
                   'steps': [{'index': 0, 'capability_id': 'text.file.write',
                              'args': {'content': 'hello', 'output_path': relative},
                              'result': {'output_path': relative}}], 'created_paths': []}
            route = dict(ROUTE, chain=['text.file.write'])
            with mock.patch.object(composer, 'route', return_value=route), \
                 mock.patch.object(composer, 'execute_chain', return_value=bad):
                result = door._try_composed('t', goal, time.perf_counter_ns())
            self.assertFalse(result['pass'], result)
            self.assertFalse(result['semantic_acceptance_complete'])
            self.assertTrue(result['side_effects_may_exist'])
            self.assertEqual(output.read_bytes(), b'wrong')

    def test_front_exception_after_execution_attempt_is_not_a_no_route(self):
        with mock.patch.object(composer, 'route', return_value=ROUTE), \
             mock.patch.object(composer, 'execute_chain', side_effect=RuntimeError('after dispatch')):
            result = door._try_composed('t', 'produce a result', time.perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'FAIL_CLOSED__COMPOSITION_EXECUTION_OUTCOME_UNKNOWN')
        self.assertTrue(result['side_effects_may_exist'])
        self.assertFalse(door._may_supersede_a_failed_attempt(result))

    def run_controller(self, chain, acceptance=None):
        front = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP', 'executed': False}
        with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=None), \
             mock.patch.object(door, 'solve', return_value=front), \
             mock.patch.object(composer, 'route', return_value=ROUTE), \
             mock.patch.object(composer, 'execute_chain', side_effect=chain if isinstance(chain, Exception) else None,
                               return_value=None if isinstance(chain, Exception) else chain), \
             mock.patch.object(door, '_composed_acceptance', return_value=acceptance or UNVERIFIED), \
             mock.patch.object(controller, 'discover_and_execute_semantic_web_form') as web:
            result = controller.solve_or_learn({'task_id': 't', 'goal': 'produce a result'}, record_open_gap=False)
        web.assert_not_called()
        return result

    def test_public_door_does_not_retry_unknown_prior_effects(self):
        prior = {'pass': False, 'status': 'FAIL__UNKNOWN', 'side_effects_may_exist': True}
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(door, '_serve_by_acting', return_value=None) as act, \
             mock.patch('canonical.swe_kernel.causal_trace_to_skill_compiler_v1.recall_and_execute_workflow') as recall:
            result = door.solve({'task_id': 't', 'goal': 'produce a result'})
        self.assertFalse(result['pass'])
        self.assertTrue(result['side_effects_may_exist'])
        act.assert_called_once(); recall.assert_not_called()

    def test_controller_does_not_retry_an_uncertain_front_result(self):
        front = {'pass': False, 'status': 'FAIL__UNKNOWN', 'executed': None,
                 'side_effects_may_exist': True}
        with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=None), \
             mock.patch.object(door, 'solve', return_value=front), \
             mock.patch.object(composer, 'route') as route:
            result = controller.solve_or_learn({'task_id': 't', 'goal': 'produce a result'}, record_open_gap=False)
        route.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertTrue(result['side_effects_may_exist'])
        self.assertFalse(door._may_supersede_a_failed_attempt(front))

    def test_controller_does_not_call_a_chain_success_a_goal_success(self):
        result = self.run_controller(CHAIN)
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'FAIL_CLOSED__COMPOSED_GOAL_NOT_VERIFIED')
        self.assertTrue(result['side_effects_may_exist'])

    def test_controller_retains_verified_composition(self):
        result = self.run_controller(CHAIN, VERIFIED)
        self.assertTrue(result['pass'])
        self.assertTrue(result['semantic_acceptance_complete'])

    def test_controller_does_not_retry_after_failed_dispatched_step(self):
        result = self.run_controller({'pass': False, 'status': 'FAIL__STEP',
                                      'steps': [{'index': 0, 'adapter_raised': 'RuntimeError'}]})
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'FAIL__STEP')
        self.assertTrue(result['side_effects_may_exist'])

    def test_controller_does_not_retry_after_uncertain_exception(self):
        result = self.run_controller(RuntimeError('after dispatch'))
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'FAIL_CLOSED__COMPOSITION_EXECUTION_OUTCOME_UNKNOWN')
        self.assertTrue(result['side_effects_may_exist'])


if __name__ == '__main__':
    unittest.main()
