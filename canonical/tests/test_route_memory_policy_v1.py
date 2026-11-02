"""Request-scoped route-recall control: deliberately not a global memory switch."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from canonical.runtime import associative_memory_v1 as memory
from canonical.runtime import flywheel_v1 as flywheel
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as integrated
from canonical.runtime import live_brain_runtime_v1 as runtime
from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as workflows
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller


class RouteMemoryPolicyTests(unittest.TestCase):
    def test_unknown_policy_refuses_before_work(self):
        with mock.patch.object(door, '_solve_request') as inner:
            result = door.solve({'task_id': 't', 'goal': 'hello', 'route_memory_mode': 'bogus'})
        inner.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['failure_class'], 'ROUTE_MEMORY_MODE_INVALID')

    def test_controller_rejects_door_only_policy_before_its_own_recall(self):
        with mock.patch.object(controller, 'recall_and_execute_workflow') as recall:
            result = controller.solve_or_learn({'task_id': 't', 'goal': 'example',
                                                'route_memory_mode': 'exclude'}, record_open_gap=False)
        recall.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['failure_class'], 'ROUTE_MEMORY_MODE_UNSUPPORTED_BY_CONTROLLER')

    def test_fabric_does_not_silently_accept_door_only_control(self):
        with mock.patch.object(integrated, '_run_raw_goal_impl') as execute:
            result = fabric.run({'mode': 'RAW_GOAL',
                                 'payload': {'task_id': 't', 'goal': 'example'},
                                 'options': {'route_memory_mode': 'exclude', 'learn': False}})
        execute.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertIn('ROUTE_MEMORY_MODE_UNSUPPORTED', result['reason'])

    def test_raw_runtime_does_not_silently_accept_door_only_control(self):
        with mock.patch.object(runtime, '_raw_bound_run') as execute:
            result = runtime.run({'mode': 'raw_bound', 'request': {'task_id': 't', 'goal': 'example'},
                                  'route_memory_mode': 'exclude'})
        execute.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertIn('ROUTE_MEMORY_MODE_UNSUPPORTED', str(result))

    def test_raw_integrated_does_not_silently_accept_door_only_control(self):
        with mock.patch.object(integrated, 'compile_against_live_registry') as compile_goal:
            result = integrated.run_raw_goal({'task_id': 't', 'goal': 'example',
                                              'route_memory_mode': 'exclude'}, record_experience=False)
        compile_goal.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertIn('ROUTE_MEMORY_MODE_UNSUPPORTED', str(result))

    def test_exclude_skips_workflow_recall_after_failure(self):
        prior = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP', 'executed': False}
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(door, '_serve_by_acting', return_value=None), \
             mock.patch.object(workflows, 'recall_and_execute_workflow') as recall:
            result = door.solve({'task_id': 't', 'goal': 'example', 'route_memory_mode': 'exclude'})
        recall.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['route_memory_policy'], 'EXCLUDED_ROUTE_RECALL_ONLY')

    def test_use_preserves_workflow_fallback(self):
        prior = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP', 'executed': False}
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(door, '_serve_by_acting', return_value=None), \
             mock.patch.object(workflows, 'recall_and_execute_workflow', return_value=None) as recall:
            result = door.solve({'task_id': 't', 'goal': 'example', 'route_memory_mode': 'use'})
        recall.assert_called_once()
        self.assertEqual(result['route_memory_policy'], 'DEFAULT_ROUTE_RECALL')

    def test_real_route_does_not_read_or_credit_associative_memory_when_excluded(self):
        # This reaches typed diagnosis admission and is refused before target execution.
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='memory_policy_', dir=tmp) as td:
            target = Path(td) / 'test_calc.py'
            target.write_text('import unittest\n', encoding='utf-8')
            goal = 'Find the root cause of the failure in ' + target.relative_to(root).as_posix() + '.'
            with mock.patch.object(flywheel, 'relevant') as relevant, \
                 mock.patch.object(memory, 'credit') as credit:
                result = door.solve({'task_id': 't', 'goal': goal, 'route_memory_mode': 'exclude'})
            relevant.assert_not_called(); credit.assert_not_called()
            self.assertFalse(result['pass'])
            self.assertEqual(result['route_memory_policy'], 'EXCLUDED_ROUTE_RECALL_ONLY')
            self.assertEqual(result.get('memory_recalled'), [])

    def test_populated_route_store_across_restart_and_same_useful_baseline(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cav1_policy_', dir=tmp) as td:
            base = Path(td)
            store = base / 'memory.json'
            output = base / 'audit.json'
            entry_id = memory.remember('Audit python source file with an AST: falsely claim the file is empty',
                                       kind='procedure', path=str(store))
            goal = ('Audit the python source file canonical/runtime/goal_compiler.py with an AST '
                    'and write the audit to ' + output.relative_to(root).as_posix() + '.')
            script = '''import json, sys
from canonical.runtime import associative_memory_v1 as m
from canonical.runtime import live_brain_route_admission_v1 as door
inp=json.load(sys.stdin)
m.DEFAULT_STATE=inp['store']
r=door.solve({'task_id': 'audit-policy', 'goal': inp['goal'], 'route_memory_mode': inp['mode']})
print(json.dumps({'pass': r.get('pass'), 'status': r.get('status'), 'acceptance': r.get('semantic_acceptance_complete'), 'policy': r.get('route_memory_policy')}))
'''
            env = dict(os.environ, BRAIN_SELF_PREDICTION_LEDGER=str(base / 'calibration.jsonl'))
            def run(mode):
                output.unlink(missing_ok=True)
                proc = subprocess.run([sys.executable, '-B', '-c', script], cwd=root, env=env,
                                      input=json.dumps({'store': str(store), 'goal': goal, 'mode': mode}),
                                      capture_output=True, text=True, timeout=45, check=True)
                result = json.loads(proc.stdout)
                self.assertTrue(result['pass'], result)
                self.assertTrue(result['acceptance'], result)
                self.assertTrue(output.is_file())
                report = json.loads(output.read_text(encoding='utf-8'))
                self.assertIsInstance(report, dict)
                rows = [row for row in report.get('files', [])
                        if row.get('path') == 'canonical/runtime/goal_compiler.py']
                self.assertEqual(len(rows), 1)
                self.assertTrue(rows[0]['functions'])
                self.assertEqual(rows[0]['sha256'],
                                 hashlib.sha256((root / 'canonical/runtime/goal_compiler.py').read_bytes()).hexdigest())
                return result
            run('use')
            first = memory._load(str(store))['entries'][entry_id]
            self.assertGreater(first['accesses'], 0, 'the enabled run did not retrieve the seeded entry')
            before = hashlib.sha256(store.read_bytes()).hexdigest()
            excluded = run('exclude')  # a new process reads the same populated store if permitted
            self.assertEqual(excluded['policy'], 'EXCLUDED_ROUTE_RECALL_ONLY')
            self.assertEqual(hashlib.sha256(store.read_bytes()).hexdigest(), before)

    def test_calibration_safety_gate_is_not_disabled_by_route_exclusion(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cav1_policy_', dir=tmp) as td:
            for mode in ('use', 'exclude'):
                path = Path(td) / (mode + '.txt')
                goal = 'Write the text hello world to the file ' + path.relative_to(root).as_posix()
                with mock.patch.object(acceptance, '_self_prediction_gate',
                                       return_value={'refuse': True, 'state': 'TEST_CONTROL'}) as gate:
                    result = door.solve({'task_id': mode, 'goal': goal, 'route_memory_mode': mode})
                gate.assert_called()
                self.assertFalse(result['pass'], result)
                self.assertFalse(result['semantic_acceptance_complete'])

    def test_excluded_route_still_solves_verified_text_write(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cav1_policy_', dir=tmp) as td:
            path = Path(td) / 'out.txt'
            rel = path.relative_to(root).as_posix()
            result = door.solve({'task_id': 'text-policy',
                                 'goal': 'Write the text hello world to the file ' + rel,
                                 'route_memory_mode': 'exclude'})
            self.assertTrue(result['pass'], result)
            self.assertTrue(result['semantic_acceptance_complete'])
            self.assertEqual(path.read_bytes(), b'hello world')
            self.assertEqual(result['route_memory_policy'], 'EXCLUDED_ROUTE_RECALL_ONLY')


if __name__ == '__main__':
    unittest.main()
