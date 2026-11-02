"""Known test-running diagnostic adapter must not run with host authority."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from canonical.runtime import capability_composer_v1 as graph
from canonical.runtime import composer_route_v1 as composer
from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as integrated
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


CID = 'software.analysis.diagnose_and_architect.v1'


class DiagnosisExecutionConfinementTests(unittest.TestCase):
    def test_real_public_diagnosis_does_not_run_target_tests(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='diagnosis_boundary_', dir=tmp) as td:
            target = Path(td) / 'test_arithmetic.py'
            marker = Path(td) / 'ran.txt'
            target.write_text("from pathlib import Path\nPath(%r).write_text('executed')\n" % str(marker)
                              + "import unittest\nclass TestCase(unittest.TestCase):\n"
                              + "    def test_failure(self): self.assertEqual(1, 2)\n", encoding='utf-8')
            relative = target.relative_to(root).as_posix()
            result = door.solve({'task_id': 'diagnosis-boundary',
                                 'goal': 'Find the root cause of the failure in ' + relative + '.'})
            self.assertFalse(result['pass'], result)
            self.assertEqual(result['status'], boundary.STATUS)
            self.assertFalse(marker.exists(), 'target test ran outside an admitted carrier')

    def test_raw_fabric_preflights_dispatched_diagnostic(self):
        entry = graph.load_registry()[CID]
        compiled = {'selected_capability': CID, 'controller_actions': [{'type': 'invoke_capability',
                    'args': {'capability_id': CID}}], 'target_effects': ['diagnosis']}
        with mock.patch.object(integrated, 'compile_against_live_registry', return_value=({}, {CID: entry}, compiled)), \
             mock.patch.object(integrated, 'drive_controller') as drive:
            result = fabric.run({'mode': 'RAW_GOAL',
                                 'payload': {'task_id': 't', 'goal': 'diagnose a failure'},
                                 'options': {'learn': False, 'auto_repair': False}})
        drive.assert_not_called()
        self.assertEqual(result['result']['status'], boundary.STATUS)
        self.assertFalse(result['result']['executed'])

    def test_raw_refusal_does_not_trigger_learning_repair_or_queue_drain(self):
        entry = graph.load_registry()[CID]
        compiled = {'selected_capability': CID, 'controller_actions': [{'type': 'invoke_capability',
                    'args': {'capability_id': CID}}], 'target_effects': ['diagnosis']}
        from canonical.runtime import live_brain_runtime_v1 as runtime
        with mock.patch.object(integrated, 'compile_against_live_registry', return_value=({}, {CID: entry}, compiled)), \
             mock.patch.object(integrated, 'drive_controller') as drive, \
             mock.patch.object(runtime, '_observe_runtime_outcome') as observe, \
             mock.patch.object(runtime, 'execute_failure_repair_cycle') as repair, \
             mock.patch.object(integrated, '_advance_learning_queue') as raw_queue, \
             mock.patch.object(fabric.improvement_driver, 'drain') as drain:
            result = fabric.run({'mode': 'RAW_GOAL',
                                 'payload': {'task_id': 't', 'goal': 'diagnose a failure'},
                                 'options': {'learn': True}})
        drive.assert_not_called(); observe.assert_not_called(); repair.assert_not_called()
        raw_queue.assert_not_called(); drain.assert_not_called()
        self.assertEqual(result['result']['status'], boundary.STATUS)
        self.assertFalse(result['result']['pass'])

    def test_raw_fabric_preflights_later_action_before_earlier_one(self):
        entry = graph.load_registry()[CID]
        actions = [{'type': 'invoke_capability', 'args': {'capability_id': 'first'}},
                   {'type': 'invoke_capability', 'args': {'capability_id': CID}}]
        compiled = {'controller_actions': actions, 'target_effects': ['diagnosis']}
        with mock.patch.object(integrated, 'compile_against_live_registry', return_value=({}, {CID: entry}, compiled)), \
             mock.patch.object(integrated, 'drive_controller') as drive:
            result = integrated.run_raw_goal({'task_id': 't', 'goal': 'diagnose a failure'}, record_experience=False)
        drive.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])

    def test_raw_fabric_preflights_dag_before_dispatch(self):
        entry = graph.load_registry()[CID]
        compiled = {'capability_dag': {'steps': [{'capability_id': 'first'}, {'capability_id': CID}]},
                    'target_effects': ['diagnosis']}
        with mock.patch.object(integrated, 'compile_against_live_registry', return_value=({}, {CID: entry}, compiled)), \
             mock.patch.object(integrated, 'drive_controller') as drive:
            result = integrated.run_raw_goal({'task_id': 't', 'goal': 'diagnose a failure'}, record_experience=False)
        drive.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])

    def test_direct_local_dispatch_refuses_before_adapter_import(self):
        entry = graph.load_registry()[CID]
        with mock.patch.object(door.importlib.util, 'spec_from_file_location') as loader:
            with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
                door.run_adapter_locally(entry, {'args': {'operation': 'find_root_cause'}})
        loader.assert_not_called()

    def test_composer_preflights_whole_chain(self):
        entry = graph.load_registry()[CID]
        registry = {'first': {'adapter_module': 'text_file_write'}, CID: entry}
        with mock.patch.object(door, 'run_adapter_locally') as dispatch:
            result = composer.execute_chain(['first', CID], 'diagnose', registry=registry)
        dispatch.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])
        self.assertEqual(result['steps'], [])

    def test_known_path_alias_is_also_refused(self):
        entry = {'adapter_module': 'alternate_name', 'source': {'adapter_path':
                 './canonical/runtime/bound_capabilities/../bound_capabilities/software_analysis_diagnose_and_architect_v1.py'}}
        with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
            door.run_adapter_locally(entry, {'args': {'operation': 'find_root_cause'}})

    def test_known_kernel_id_is_refused_even_if_entry_is_missing(self):
        compiled = {'selected_capability': CID, 'target_effects': ['diagnosis']}
        with mock.patch.object(door.live_integrated_brain_v1, 'drive_controller') as kernel:
            result = door._execute('t', 'diagnose a test', compiled, {}, time.perf_counter_ns())
        kernel.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])

    def test_kernel_path_preflight_does_not_dispatch(self):
        entry = graph.load_registry()[CID]
        compiled = {'selected_capability': CID, 'target_effects': ['diagnosis']}
        with mock.patch.object(door.live_integrated_brain_v1, 'drive_controller') as kernel:
            result = door._execute('t', 'diagnose a test', compiled, {CID: entry}, time.perf_counter_ns())
        kernel.assert_not_called()
        self.assertEqual(result['status'], boundary.STATUS)
        self.assertFalse(result['executed'])


if __name__ == '__main__':
    unittest.main()
