"""Mock transport tests only: these do not demonstrate Docker isolation."""
from __future__ import annotations

import ast
import asyncio
import base64
import json
import shlex
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import harbor_epistemic_agent_v1 as agent


class Recorder:
    def __init__(self, stdout, return_code=0, error=None):
        self.calls = []
        self.stdout = stdout
        self.return_code = return_code
        self.error = error

    async def exec(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(return_code=self.return_code, stdout=self.stdout, stderr='')


def run(coro):
    return asyncio.run(coro)


class ContainerSolverTransportTests(unittest.TestCase):
    def test_model_request_is_encoded_and_dispatched_only_through_exec(self):
        reply = {'pass': False, 'status': 'FAIL_CLOSED'}
        env = Recorder('BRAIN_CONTAINER_SOLVE_V1:' + json.dumps(reply) + '\n')
        instruction = "$(touch /tmp/should-not-run); 'quoted' \n snowman: ☃"
        with patch.object(agent, 'make_model', side_effect=AssertionError('host solver')):
            result = run(agent.run_epistemic_goal(instruction, env))
        self.assertEqual(result['status'], 'BLOCKED_NO_MODEL_PROPOSAL')
        self.assertFalse(result['task_completion_claimed'])
        self.assertFalse(result['patch_emitted'])
        self.assertFalse(result['external_verifier_invoked'])
        self.assertFalse(result['container_boundary_verified'])
        self.assertFalse(result['network_egress_verified'])
        self.assertEqual(len(env.calls), 1)
        command, kwargs = env.calls[0]
        parts = shlex.split(command)
        self.assertEqual(parts[:3], ['env', '-i', 'PATH=/usr/local/bin:/usr/bin:/bin'])
        self.assertEqual(parts[4:7], ['python3', '-I', '-B'])
        self.assertEqual(parts[7], '/opt/brain-ro/canonical/runtime/harbor_container_solver_worker_v1.py')
        self.assertNotIn(instruction, command)
        request = json.loads(base64.b64decode(parts[8], validate=True))
        self.assertEqual(request['inputs']['harbor_task'], instruction)
        self.assertEqual(request['mode'], 'EPISTEMIC')
        self.assertEqual(kwargs, {'timeout_sec': 180})
        self.assertFalse(any('model.patch' in call[0] for call in env.calls))

    def test_host_module_has_no_solve_call(self):
        tree = ast.parse(Path(agent.__file__).read_text(encoding='utf-8'))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertFalse(any(isinstance(x.func, ast.Attribute) and x.func.attr == 'solve'
                             for x in calls))

    def test_worker_calls_open_model_and_solve_inside_worker_file(self):
        path = Path(agent.__file__).with_name('harbor_container_solver_worker_v1.py')
        tree = ast.parse(path.read_text(encoding='utf-8'))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertTrue(any(isinstance(x.func, ast.Attribute) and x.func.attr == 'solve'
                            and isinstance(x.func.value, ast.Call)
                            and isinstance(x.func.value.func, ast.Name)
                            and x.func.value.func.id == 'open_model' for x in calls))

    def test_untrusted_missing_duplicate_or_invalid_worker_reply_stops(self):
        for output in ('', 'noise', 'BRAIN_CONTAINER_SOLVE_V1:[]\n',
                       'BRAIN_CONTAINER_SOLVE_V1:{}\nBRAIN_CONTAINER_SOLVE_V1:{}\n'):
            with self.subTest(output=output):
                env = Recorder(output)
                out = run(agent.run_epistemic_goal('task', env))
                self.assertEqual(out['status'], 'BLOCKED_CONTAINER_SOLVER_UNAVAILABLE')
                self.assertFalse(out['patch_emitted'])
                self.assertEqual(len(env.calls), 1)

    def test_nonzero_and_uncertain_exec_are_not_replayed(self):
        for env in (Recorder('', return_code=1), Recorder('', error=TimeoutError('lost'))):
            with self.subTest(error=env.error):
                out = run(agent.run_epistemic_goal('task', env))
                self.assertEqual(out['status'], 'BLOCKED_CONTAINER_SOLVER_UNAVAILABLE')
                self.assertFalse(out['patch_emitted'])
                self.assertEqual(len(env.calls), 1)

    def test_oversized_request_is_rejected_before_exec(self):
        env = Recorder('')
        out = run(agent.run_epistemic_goal('x' * 64000, env))
        self.assertEqual(out['status'], 'BLOCKED_CONTAINER_SOLVER_UNAVAILABLE')
        self.assertEqual(out['trace'][0]['stop_reason'], 'HARBOR_SOLVER_REQUEST_TOO_LARGE')
        self.assertEqual(env.calls, [])

    def test_host_model_parameter_is_rejected_without_dispatch(self):
        env = Recorder('')
        class ForbiddenHostModel:
            def solve(self, *args, **kwargs):
                raise AssertionError('host solver was called')
        with self.assertRaisesRegex(agent.AgentRejected, 'HOST_SOLVER_FORBIDDEN'):
            run(agent.run_epistemic_goal('task', env, model=ForbiddenHostModel()))
        self.assertEqual(env.calls, [])


if __name__ == '__main__':
    unittest.main()
