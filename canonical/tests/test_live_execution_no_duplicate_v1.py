"""A failed, already-executed local action must not be dispatched twice."""
from __future__ import annotations

import pathlib
import tempfile
import time
import unittest
from unittest.mock import patch

from canonical.runtime import live_brain_route_admission_v1 as door

ROOT = pathlib.Path(__file__).resolve().parents[2]


class FailedExecutionRetryTests(unittest.TestCase):
    def test_adapter_side_effect_is_not_repeated_after_failure(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='once_effect_', dir=work) as temp:
            scratch = pathlib.Path(temp)
            adapter = scratch / 'adapter.py'
            marker = scratch / 'writes.txt'
            adapter.write_text(
                'from pathlib import Path\n'
                'def run(args, root):\n'
                '    with (Path(root) / args["marker"]).open("a") as f:\n'
                '        f.write("executed\\n")\n'
                '    raise RuntimeError("failure after an effect")\n',
                encoding='utf-8',
            )
            cid = 'test.action.one_shot.v1'
            entry = {
                'capability_id': cid,
                'adapter_module': 'one_shot_fixture',
                'source': {'type': 'python_stdlib', 'adapter_path': adapter.relative_to(ROOT).as_posix()},
                'action_template': {'type': 'invoke_capability', 'args': {
                    'capability_id': cid, 'marker': marker.relative_to(ROOT).as_posix()}},
            }
            compiled = {'selected_capability': cid, 'inputs': {}, 'target_effects': ['software.task.completed']}

            # The fallback controller is a local seam: if invoked, it records a
            # second effect. The first effect is the real adapter's filesystem write.
            def retry_controller(*args):
                with marker.open('a', encoding='utf-8') as f:
                    f.write('retried\n')
                return None, 'CONTROL_PLAN_INVALID'

            with patch.object(door.live_integrated_brain_v1, 'drive_controller', retry_controller):
                result = door._execute('ONCE', 'Execute the described one shot task.',
                                       compiled, {cid: entry}, time.perf_counter_ns())
            self.assertFalse(result['pass'])
            self.assertEqual(marker.read_text(encoding='utf-8').splitlines(), ['executed'])
            self.assertTrue(result['executed'], result)

    def test_invalid_result_and_loaded_module_are_not_pre_execution_refusals(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        cases = (
            ('invalid_result', 'def run(args, root):\n    mark()\n    return None\n'),
            ('typed_failure', 'from canonical.runtime.live_brain_route_admission_v1 import LocalExecutionFailure\n'
                              'def run(args, root):\n    mark()\n    raise LocalExecutionFailure("adapter refused after effect")\n'),
            ('missing_entrypoint', 'mark()\n'),
        )
        with tempfile.TemporaryDirectory(prefix='once_shapes_', dir=work) as temp:
            scratch = pathlib.Path(temp)
            for name, body in cases:
                with self.subTest(name=name):
                    marker = scratch / (name + '.txt')
                    adapter = scratch / (name + '.py')
                    adapter.write_text(
                        'from pathlib import Path\n'
                        f'p = Path({str(marker)!r})\n'
                        'def mark():\n    with p.open("a") as f: f.write("executed\\n")\n'
                        + body, encoding='utf-8')
                    cid = 'test.action.' + name + '.v1'
                    entry = {
                        'capability_id': cid, 'adapter_module': 'fixture_' + name,
                        'source': {'type': 'python_stdlib', 'adapter_path': adapter.relative_to(ROOT).as_posix()},
                        'action_template': {'type': 'invoke_capability', 'args': {'capability_id': cid}},
                    }
                    compiled = {'selected_capability': cid, 'inputs': {}, 'target_effects': ['software.task.completed']}

                    def retry_controller(*args):
                        with marker.open('a', encoding='utf-8') as f:
                            f.write('retried\n')
                        return None, 'CONTROL_PLAN_INVALID'

                    with patch.object(door.live_integrated_brain_v1, 'drive_controller', retry_controller):
                        result = door._execute('ONCE_' + name, 'Execute the described one shot task.',
                                               compiled, {cid: entry}, time.perf_counter_ns())
                    self.assertFalse(result['pass'])
                    self.assertEqual(marker.read_text(encoding='utf-8').splitlines(), ['executed'])
                    self.assertTrue(result['executed'], result)

    def test_dag_failure_after_effect_is_not_retried_by_kernel(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='dag_once_', dir=work) as temp:
            scratch = pathlib.Path(temp)
            marker = scratch / 'effects.txt'
            adapter = scratch / 'adapter.py'
            adapter.write_text('from pathlib import Path\n'
                               'def run(args, root):\n'
                               f'    Path({str(marker)!r}).write_text("executed\\n")\n'
                               '    raise RuntimeError("after effect")\n')
            cid = 'test.dag.one_shot.v1'
            entry = {'capability_id': cid, 'adapter_module': 'dag_fixture',
                     'source': {'type': 'python_stdlib', 'adapter_path': adapter.relative_to(ROOT).as_posix()}}
            action = {'args': {'capability_id': cid}}
            compiled = {'capability_dag': {'steps': [{'capability_id': cid, 'action': action}]},
                        'controller_actions': [action]}
            raw = {'task_sha256': 'test', 'task_contract_sha256': 'test',
                   'acceptance_contract': {'obligations': []}}
            def kernel(*args):
                with marker.open('a') as f: f.write('retried\n')
                return {}
            with patch.object(door.astra_runtime, 'run_goal', kernel):
                result = door._execute_capability_dag('DAG_ONCE', 'one task', compiled, {cid: entry},
                                                      raw, time.perf_counter_ns())
            self.assertFalse(result['pass'])
            self.assertTrue(result['executed'])
            self.assertEqual(marker.read_text().splitlines(), ['executed'])

    def test_dag_later_preflight_failure_does_not_repeat_an_earlier_step(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='dag_partial_', dir=work) as temp:
            scratch = pathlib.Path(temp)
            marker = scratch / 'effects.txt'
            adapter = scratch / 'adapter.py'
            adapter.write_text('from pathlib import Path\n'
                               'def run(args, root):\n'
                               f'    Path({str(marker)!r}).write_text("first\\n")\n'
                               '    return {"ok": True}\n')
            first, second = 'test.dag.first.v1', 'test.dag.second.v1'
            entries = {
                first: {'capability_id': first, 'adapter_module': 'dag_first',
                        'source': {'type': 'python_stdlib', 'adapter_path': adapter.relative_to(ROOT).as_posix()}},
                second: {'capability_id': second, 'adapter_module': 'unused',
                         'source': {'type': 'python_stdlib', 'modules': ['module_that_does_not_exist_brain_test']}},
            }
            steps = [{'capability_id': cid, 'action': {'args': {'capability_id': cid}}}
                     for cid in (first, second)]
            compiled = {'capability_dag': {'steps': steps}, 'controller_actions': [x['action'] for x in steps]}
            raw = {'task_sha256': 'test', 'task_contract_sha256': 'test',
                   'acceptance_contract': {'obligations': []}}
            def kernel(*args):
                with marker.open('a') as f: f.write('retried\n')
                return {}
            with patch.object(door.astra_runtime, 'run_goal', kernel):
                result = door._execute_capability_dag('DAG_PARTIAL', 'two tasks', compiled, entries,
                                                      raw, time.perf_counter_ns())
            self.assertFalse(result['pass'])
            self.assertTrue(result['executed'])
            self.assertEqual(marker.read_text().splitlines(), ['first'])

    def test_dag_pre_execution_refusal_can_try_kernel(self):
        cid = 'test.dag.preflight.v1'
        entry = {'capability_id': cid, 'adapter_module': 'unused',
                 'source': {'type': 'python_stdlib', 'modules': ['module_that_does_not_exist_brain_test']}}
        action = {'args': {'capability_id': cid}}
        compiled = {'capability_dag': {'steps': [{'capability_id': cid, 'action': action}]},
                    'controller_actions': [action]}
        raw = {'task_sha256': 'test', 'task_contract_sha256': 'test',
               'acceptance_contract': {'obligations': []}}
        called = []
        def kernel(*args):
            called.append(True)
            return {}
        with patch.object(door.astra_runtime, 'run_goal', kernel):
            result = door._execute_capability_dag('DAG_PREFLIGHT', 'one task', compiled, {cid: entry},
                                                  raw, time.perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertEqual(called, [True])

    def test_pre_execution_refusal_can_still_try_controller(self):
        cid = 'test.action.preflight.v1'
        entry = {
            'capability_id': cid,
            'adapter_module': 'unused',
            'source': {'type': 'python_stdlib', 'modules': ['module_that_does_not_exist_brain_test']},
            'action_template': {'type': 'invoke_capability', 'args': {'capability_id': cid}},
        }
        compiled = {'selected_capability': cid, 'inputs': {}, 'target_effects': ['software.task.completed']}
        called = []

        def retry_controller(*args):
            called.append(True)
            return None, 'CONTROL_PLAN_INVALID'

        with patch.object(door.live_integrated_brain_v1, 'drive_controller', retry_controller):
            result = door._execute('PREFLIGHT', 'Execute the described one shot task.',
                                   compiled, {cid: entry}, time.perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertEqual(called, [True])


if __name__ == '__main__':
    unittest.main()
