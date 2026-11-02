"""Guard the known local arbitrary-command adapter before host dispatch."""
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

from canonical.runtime import capability_composer_v1 as graph
from canonical.runtime import composer_route_v1 as composer
from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller


class LocalCliAdapterConfinementGuardTests(unittest.TestCase):
    def test_direct_local_adapter_refuses_before_running_named_program(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'ran'
            entry = graph.load_registry()['shell.command.run']
            action = {'args': {'argv': [sys.executable, '-c',
                       'from pathlib import Path; Path(%r).write_text("ran")' % str(marker)]}}
            with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
                door.run_adapter_locally(entry, action)
            self.assertFalse(marker.exists())

    def test_adapter_path_alias_does_not_bypass_the_guard(self):
        entry = dict(graph.load_registry()['shell.command.run'])
        entry['adapter_module'] = 'alternate_name'
        entry['source'] = {'adapter_path': './canonical/runtime/bound_capabilities/../bound_capabilities/cli_command.py'}
        self.assertTrue(boundary.is_unconfined_cli_entry(entry))
        with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
            door.run_adapter_locally(entry, {'args': {'argv': [sys.executable, '-c', 'pass']}})

    def test_composer_preflights_command_before_any_earlier_step(self):
        registry = {'first': {'adapter_module': 'some_other_adapter'},
                    'last': {'adapter_module': 'cli_command'}}
        with mock.patch.object(door, 'run_adapter_locally') as dispatch:
            result = composer.execute_chain(['first', 'last'], 'some task', registry=registry)
        dispatch.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertEqual(result['steps'], [])
        self.assertFalse(result['executed'])

    def test_primary_local_wrapper_reports_a_boundary_refusal(self):
        entry = graph.load_registry()['shell.command.run']
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'ran'
            action = {'args': {'argv': [sys.executable, '-c',
                       'from pathlib import Path; Path(%r).write_text("ran")' % str(marker)]}}
            result = door._execute_locally('T', 'run a command', {'selected_capability': 'shell.command.run'},
                                           entry, action, {}, time.perf_counter_ns())
            self.assertFalse(result['pass'])
            self.assertEqual(result['status'], boundary.STATUS)
            self.assertFalse(result['executed'])
            self.assertFalse(marker.exists())

    def test_primary_execution_does_not_retry_cli_through_kernel(self):
        entry = graph.load_registry()['shell.command.run']
        compiled = {'selected_capability': 'shell.command.run', 'inputs': {}, 'target_effects': ['shell.command.result']}
        with mock.patch.object(door, 'compile_contract', return_value={'pass': True}), \
             mock.patch.object(door, 'kernel_refuses', return_value=False), \
             mock.patch.object(door.goal_compiler, '_render_template', return_value={'args': {}}), \
             mock.patch.object(door, '_execute_locally', return_value={'pass': False, 'status': boundary.STATUS}) as local, \
             mock.patch.object(door.live_integrated_brain_v1, 'drive_controller', return_value=({}, 'STOP')) as kernel:
            result = door._execute('T', 'run a command', compiled, {'shell.command.run': entry}, time.perf_counter_ns())
        local.assert_not_called(); kernel.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])

    def test_controller_action_list_cannot_skip_cli_preflight(self):
        entry = graph.load_registry()['shell.command.run']
        compiled = {'selected_capability': '', 'target_effects': ['shell.command.result'],
                    'controller_actions': [{'type': 'invoke_capability',
                                            'args': {'capability_id': 'shell.command.run', 'argv': ['fixture']}}]}
        with mock.patch.object(door, 'compile_contract', return_value={'pass': True}), \
             mock.patch.object(door.live_integrated_brain_v1, 'drive_controller', return_value=({}, 'STOP')) as kernel:
            result = door._execute('T', 'run a command', compiled, {'shell.command.run': entry}, time.perf_counter_ns())
        kernel.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])

    def test_controller_does_not_fall_through_a_planning_refusal(self):
        prior = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP', 'executed': True}
        with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=None), \
             mock.patch.object(door, 'solve', return_value=prior), \
             mock.patch.object(composer, 'route', return_value={'pass': False, 'status': boundary.STATUS}), \
             mock.patch.object(composer, 'execute_chain') as execute:
            result = controller.solve_or_learn({'task_id': 'T', 'goal': 'examine widget'}, record_open_gap=False)
        execute.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertTrue(result['side_effects_may_exist'])
        self.assertFalse(result['composer_fallback_executed'])

    def test_controller_does_not_fall_through_a_composed_refusal(self):
        prior = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP', 'executed': True}
        routed = {'pass': True, 'chain': ['shell.command.run']}
        blocked = {'pass': False, 'status': boundary.STATUS, 'steps': [], 'executed': False}
        with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=None), \
             mock.patch.object(door, 'solve', return_value=prior), \
             mock.patch.object(composer, 'route', return_value=routed), \
             mock.patch.object(composer, 'execute_chain', return_value=blocked):
            result = controller.solve_or_learn({'task_id': 'T', 'goal': 'examine widget'}, record_open_gap=False)
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertTrue(result['executed'])
        self.assertTrue(result['side_effects_may_exist'])
        self.assertFalse(result['composer_fallback_executed'])

    def test_composer_planning_refusal_is_not_discarded(self):
        with mock.patch.object(composer, 'route', return_value={'pass': False, 'status': boundary.STATUS}), \
             mock.patch.object(composer, 'execute_chain') as execute:
            result = door._try_composed('T', 'run a command', time.perf_counter_ns())
        execute.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)

    def test_composed_refusal_is_not_discarded_as_an_unmatched_route(self):
        with mock.patch.object(composer, 'route', return_value={'pass': True, 'chain': ['shell.command.run']}), \
             mock.patch.object(composer, 'execute_chain', return_value={'pass': False, 'status': boundary.STATUS,
                                                                        'steps': [], 'executed': False}):
            result = door._try_composed('T', 'run a command', time.perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])
        held = door._composed_holds_up(dict(result), 'write missing.txt', ['missing.txt'])
        self.assertEqual(held['status'], boundary.STATUS)
        self.assertFalse(held['pass'])


if __name__ == '__main__':
    unittest.main()
