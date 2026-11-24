"""Mocked Harbor dispatch only. No Docker, live boundary or verifier is tested."""
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from canonical.runtime import harbor_epistemic_agent_v1 as agent
from canonical.runtime import harbor_experimental_vm_v1 as vm

CID = 'a' * 64
BASE = 'b' * 40
PATCH = b'diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n'
CHECK = {'static_filter_passed': True, 'compose_main_container_id': CID,
         'host_log_mount_destinations': []}


class MockEnvironment:
    def __init__(self, *, do_action=False):
        self.commands = []
        self.solver_calls = 0
        self.do_action = do_action

    async def exec(self, command, **kwargs):
        self.commands.append(command)
        if 'rev-parse' in command:
            out = BASE + '\n'
        elif 'harbor_process_cleanup_worker_v1.py snapshot' in command:
            out = vm._PROCESS_MARKER + json.dumps({'baseline': {'1': 7}, 'quiescence_verified': False})
        elif 'harbor_process_cleanup_worker_v1.py cleanup' in command:
            out = vm._PROCESS_MARKER + json.dumps({'status': 'NO_NEW_VISIBLE_PROCESSES',
                                                  'killed_pids': [], 'quiescence_verified': False})
        elif 'harbor_workspace_diff_v1.py snapshot' in command:
            out = agent._WORKSPACE_DIFF_MARKER + json.dumps({'status': 'SNAPSHOT', 'files': 3, 'bytes_hashed': 100, 'skipped': 0})
        elif 'harbor_workspace_diff_v1.py diff' in command:
            out = agent._WORKSPACE_DIFF_MARKER + json.dumps({'status': 'DIFF', 'added': 0, 'removed': 0, 'changed': 1,
                                                           'diff_bytes': 42, 'candidate_changed': True,
                                                           'changed_paths': ['app/sessions.py'], 'removed_paths': [], 'skipped': 0})
        elif 'harbor_container_solver_worker_v1.py' in command:
            self.solver_calls += 1
            if self.do_action and self.solver_calls == 1:
                response = {'pass': True, 'actions': [{'type': 'terminal_exec', 'args': {'command': 'printf x'}}]}
            else:
                response = {'pass': True, 'actions': [{'type': 'finish', 'args': {'summary': 'done'}}]}
            out = 'BRAIN_CONTAINER_SOLVE_V1:' + json.dumps(response)
        elif command == 'printf x':
            out = 'x'
        elif 'harbor_pro_git_capture_v1.py' in command:
            data = {'reported_base': BASE, 'sha256': hashlib.sha256(PATCH).hexdigest(),
                    'patch_base64': base64.b64encode(PATCH).decode(), 'worker_quiescence_verified': False,
                    'patch_completeness_verified': False, 'external_verifier_invoked': False}
            out = 'BRAIN_PRO_PATCH_CANDIDATE_V1:' + json.dumps(data)
        else:
            raise AssertionError('unexpected command ' + command)
        return SimpleNamespace(return_code=0, stdout=out + '\n', stderr='')


class ExperimentalDispatchTests(unittest.TestCase):
    def run_agent(self, suite, env, logs):
        inst = agent.HarborEpistemicAgent(suite=suite, brain_source='/host/brain')
        inst.logs_dir = logs
        asyncio.run(inst.run('task instruction', env, SimpleNamespace()))
        return json.loads((logs / agent.TRACE_FILENAME).read_text())

    def test_optin_unset_refuses_before_any_exec_or_inspection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), \
             patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock) as inspect:
            env = MockEnvironment()
            result = self.run_agent('pro-v2', env, Path(tmp))
            self.assertEqual(result['status'], 'ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK')
            self.assertEqual(env.commands, [])
            inspect.assert_not_awaited()
            self.assertFalse((Path(tmp) / 'model.patch').exists())

    def test_optin_pro_dispatches_container_worker_and_writes_candidate(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': '1'}, clear=True), \
             patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock, return_value=CHECK), \
             patch.object(agent, 'make_model', side_effect=AssertionError('host solver called')):
            env = MockEnvironment()
            result = self.run_agent('pro-v2', env, Path(tmp))
            self.assertEqual((Path(tmp) / 'model.patch').read_bytes(), PATCH)
            self.assertEqual(result['external_harbor_vm_eval_status'], 'EXPERIMENTAL_DISPATCH__UNVERIFIED')
            self.assertFalse(result['worker_quiescence_verified'])
            self.assertFalse(result['external_verifier_invoked'])
            self.assertTrue(result['patch_emitted'])
            self.assertEqual(len(env.commands), 5)
            self.assertIn('rev-parse', env.commands[0])
            self.assertIn('snapshot', env.commands[1])
            self.assertIn('harbor_container_solver_worker_v1.py', env.commands[2])
            self.assertIn('cleanup', env.commands[3])
            self.assertIn('harbor_pro_git_capture_v1.py', env.commands[4])
            traj = json.loads((Path(tmp) / 'trajectory.json').read_text())
            self.assertEqual(traj['schema_version'], 'ATIF-v1.8')
            self.assertEqual(traj['steps'][0]['message'], 'task instruction')

    def test_terminal_dispatch_leaves_effects_for_harbor_and_records_action(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': '1'}, clear=True), \
             patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock, return_value=CHECK):
            env = MockEnvironment(do_action=True)
            result = self.run_agent('terminal-bench-4', env, Path(tmp))
            self.assertEqual(result['status'], 'FINISHED__MODEL_PROPOSED__VERIFIER_DECIDES')
            self.assertIn('printf x', env.commands)
            self.assertFalse((Path(tmp) / 'model.patch').exists())
            trace = json.loads((Path(tmp) / agent.TRACE_FILENAME).read_text())
            self.assertEqual(trace['candidate_applied'], True)
            self.assertEqual(trace['diff_bytes'], 42)
            self.assertEqual(trace['apply']['status'], 'APPLIED__UNVERIFIED')
            self.assertEqual(trace['workspace_diff']['diff_bytes'], 42)
            diag = trace['trace'][-1]['imported_engine']
            self.assertEqual(diag['candidate_applied'], True)
            self.assertEqual(diag['workspace_diff']['changed_paths'], ['app/sessions.py'])
            self.assertTrue(any('harbor_workspace_diff_v1.py snapshot' in c for c in env.commands))
            self.assertTrue(any('harbor_workspace_diff_v1.py diff' in c for c in env.commands))
            traj = json.loads((Path(tmp) / 'trajectory.json').read_text())
            call = next(step for step in traj['steps'] if step.get('tool_calls'))
            self.assertEqual(call['tool_calls'][0]['arguments']['command'], 'printf x')
            self.assertIn('x', call['observation']['results'][0]['content'])
            self.assertFalse(result['task_completion_claimed'])

    def test_failed_check_or_changed_container_refuses_without_patch(self):
        for checks in ([CHECK | {'static_filter_passed': False}],
                       [CHECK, CHECK | {'compose_main_container_id': 'c' * 64}]):
            with self.subTest(checks=checks), tempfile.TemporaryDirectory() as tmp, \
                 patch.dict(os.environ, {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': '1'}, clear=True), \
                 patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock, side_effect=checks):
                env = MockEnvironment()
                with self.assertRaises(Exception):
                    self.run_agent('pro-v2', env, Path(tmp))
                self.assertFalse((Path(tmp) / 'model.patch').exists())
                self.assertEqual(env.commands, [])

    def test_uncertain_solver_dispatch_is_not_captured(self):
        class LostSolver(MockEnvironment):
            async def exec(self, command, **kwargs):
                if 'harbor_container_solver_worker_v1.py' in command:
                    self.commands.append(command)
                    raise TimeoutError('unknown outcome')
                return await super().exec(command, **kwargs)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': '1'}, clear=True), \
             patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock, return_value=CHECK):
            env = LostSolver()
            with self.assertRaisesRegex(vm.ExperimentalVMError, 'SOLVER_OR_ACTION_EXEC_UNCERTAIN'):
                self.run_agent('pro-v2', env, Path(tmp))
            self.assertEqual(sum('harbor_container_solver_worker_v1.py' in x for x in env.commands), 1)
            self.assertTrue(any('cleanup' in x for x in env.commands))
            self.assertFalse(any('harbor_pro_git_capture_v1.py' in x for x in env.commands))
            self.assertFalse((Path(tmp) / 'model.patch').exists())

    def test_unsupported_frontier_suite_remains_closed(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': '1'}, clear=True), \
             patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock) as inspect:
            env = MockEnvironment()
            result = self.run_agent('frontier-swe-v2', env, Path(tmp))
            self.assertFalse(result['execution_authorized'])
            self.assertEqual(env.commands, [])
            inspect.assert_not_awaited()

    def test_cleanup_failure_prevents_candidate_publication(self):
        class CleanupFailure(MockEnvironment):
            async def exec(self, command, **kwargs):
                if 'harbor_process_cleanup_worker_v1.py cleanup' in command:
                    self.commands.append(command)
                    return SimpleNamespace(return_code=2, stdout='', stderr='denied')
                return await super().exec(command, **kwargs)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': '1'}, clear=True), \
             patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock, return_value=CHECK):
            env = CleanupFailure()
            with self.assertRaisesRegex(vm.ExperimentalVMError, 'PROCESS_CLEANUP_FAILED'):
                self.run_agent('pro-v2', env, Path(tmp))
            self.assertFalse((Path(tmp) / 'model.patch').exists())
            self.assertFalse(any('harbor_pro_git_capture_v1.py' in x for x in env.commands))

    def test_writable_host_agent_logs_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': '1'}, clear=True), \
             patch.object(vm, 'inspect_compose_environment', new_callable=AsyncMock,
                          return_value=CHECK | {'host_log_mount_destinations': ['/logs/agent']}):
            env = MockEnvironment()
            with self.assertRaisesRegex(vm.ExperimentalVMError, 'AGENT_LOG_HOST_MOUNT_UNSAFE'):
                self.run_agent('pro-v2', env, Path(tmp))
            self.assertEqual(env.commands, [])
            self.assertFalse((Path(tmp) / 'model.patch').exists())


if __name__ == '__main__':
    unittest.main()
