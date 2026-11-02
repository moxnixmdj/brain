"""A retained workflow may not execute an unconfined CLI stage.

The temporary programs in this test are trusted benign fixtures; no subprocess,
filesystem or network primitive is mocked. No host file outside the temporary
fixture is modified.
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import curriculum_v1 as curriculum
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller


class CompiledCliConfinementGuardTests(unittest.TestCase):
    def test_preflight_refuses_cli_before_any_earlier_file_step(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for layer in ('cli_exec', 'cli_pipeline'):
                with self.subTest(layer=layer):
                    early = root / ('early-' + layer)
                    marker = root / ('executed-' + layer)
                    command = [sys.executable, '-c', 'from pathlib import Path; Path(%r).write_text("ran")' % str(marker)]
                    stage = ({'layer': 'cli_exec', 'argv': command} if layer == 'cli_exec'
                             else {'layer': 'cli_pipeline', 'stages': [command, [sys.executable, '-c', 'pass']]})
                    steps = [{'layer': 'python_file_op', 'path': str(early), 'content': 'written too early'}, stage]
                    result = compiler.execute_compiled_steps(steps, cwd=root)
                    self.assertFalse(result['ok'])
                    self.assertEqual(result['status'], boundary.STATUS)
                    self.assertEqual(result['step_receipts'], [])
                    self.assertFalse(early.exists())
                    self.assertFalse(marker.exists())

    def test_non_cli_file_workflow_is_not_disabled_by_cli_guard(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'out.txt'
            result = compiler.execute_compiled_steps([{'layer': 'python_file_op', 'path': str(target),
                                                       'content': 'fixture'}], cwd=td)
            self.assertTrue(result['ok'])
            self.assertEqual(target.read_text(), 'fixture')

    def test_recall_propagates_boundary_refusal_without_executing_or_trying_more_skills(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'ran'
            skill = {'skill_id': 'fixture', 'skeleton_tokens': [], 'abstract_postcondition': {},
                     'abstract_steps': [{'layer': 'cli_exec', 'argv': [sys.executable, '-c',
                         'from pathlib import Path; Path(%r).write_text("ran")' % str(marker)]}]}
            later = {'skill_id': 'later', 'skeleton_tokens': [], 'abstract_postcondition': {},
                     'abstract_steps': [{'layer': 'python_file_op', 'path': str(marker), 'content': 'later'}]}
            with mock.patch.object(compiler, '_candidate_skills_for_words', return_value=[skill, later]), \
                 mock.patch.object(compiler, 'bind_goal_parameters', return_value={}), \
                 mock.patch.object(compiler, 'check_step_preconditions', return_value=(True, 'OK')):
                result = compiler.recall_and_execute_workflow('a task', cwd=td)
            self.assertFalse(result['pass'])
            self.assertEqual(result['status'], boundary.STATUS)
            self.assertFalse(result['executed'])
            self.assertFalse(marker.exists())

    def test_recall_retains_uncertainty_when_an_earlier_skill_had_effects(self):
        with tempfile.TemporaryDirectory() as td:
            earlier = Path(td) / 'earlier'
            first = {'skill_id': 'first', 'skeleton_tokens': [], 'abstract_postcondition': {},
                     'abstract_steps': [{'layer': 'python_file_op', 'path': str(earlier), 'content': 'attempt'}]}
            second = {'skill_id': 'second', 'skeleton_tokens': [], 'abstract_postcondition': {},
                      'abstract_steps': [{'layer': 'cli_exec', 'argv': [sys.executable, '-c', 'pass']}]}
            with mock.patch.object(compiler, '_candidate_skills_for_words', return_value=[first, second]), \
                 mock.patch.object(compiler, 'bind_goal_parameters', return_value={}), \
                 mock.patch.object(compiler, 'check_step_preconditions', return_value=(True, 'OK')), \
                 mock.patch.object(compiler, 'verify_postcondition', return_value=(False, 'not achieved')):
                result = compiler.recall_and_execute_workflow('a task', cwd=td)
            self.assertEqual(result['status'], boundary.STATUS)
            self.assertIsNone(result['executed'])
            self.assertTrue(result['side_effects_may_exist'])
            self.assertEqual(earlier.read_text(), 'attempt')

    def test_controller_stops_on_recalled_workflow_refusal(self):
        refused = {'pass': False, 'status': boundary.STATUS, 'failure_class': boundary.FAILURE_CLASS,
                   'executed': False, 'side_effects_may_exist': False}
        with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=refused), \
             mock.patch.object(door, 'solve', return_value={'pass': True}) as solve:
            result = controller.solve_or_learn({'task_id': 'T', 'goal': 'examine widget'},
                                               allow_tier1_composition=False, record_open_gap=False)
        solve.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)

    def test_door_and_curriculum_do_not_hide_recalled_workflow_refusal(self):
        refused = {'pass': False, 'status': boundary.STATUS, 'failure_class': boundary.FAILURE_CLASS,
                   'executed': False, 'side_effects_may_exist': False}
        # Recall may safely be considered only when the preceding failure
        # explicitly reports no possible effects; it can itself execute work.
        prior = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP', 'executed': False,
                 'side_effects_may_exist': False}
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(door, '_serve_by_acting', return_value=None), \
             mock.patch.object(compiler, 'recall_and_execute_workflow', return_value=refused) as recall:
            result = door.solve({'task_id': 'T', 'goal': 'examine widget'})
        recall.assert_called_once()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertTrue(result['side_effects_may_exist'])
        # The same prior failure with uncertain effects must never reach recall,
        # even if this particular mocked workflow would have refused safely.
        prior = dict(prior, executed=True, side_effects_may_exist=True)
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(door, '_serve_by_acting', return_value=None), \
             mock.patch.object(compiler, 'recall_and_execute_workflow', return_value=refused) as recall:
            uncertain = door.solve({'task_id': 'T', 'goal': 'examine widget'})
        recall.assert_not_called()
        self.assertFalse(uncertain['pass'])
        self.assertEqual(uncertain['status'], prior['status'])
        self.assertTrue(uncertain['side_effects_may_exist'])
        with mock.patch.object(door, 'solve', return_value={'pass': False, 'status': 'OTHER'}), \
             mock.patch.object(compiler, 'recall_and_execute_workflow', return_value=refused):
            out = curriculum._try_solve('examine widget')
        self.assertFalse(out['closed'])
        self.assertEqual(out['status'], boundary.STATUS)


if __name__ == '__main__':
    unittest.main()
