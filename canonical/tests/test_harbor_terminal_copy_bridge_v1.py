"""Real temporary-filesystem effect tests; no Docker or benchmark verification."""
from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

from canonical.runtime import harbor_epistemic_agent_v1 as agent
from canonical.runtime import harbor_experimental_vm_v1 as vm
from canonical.runtime import harbor_terminal_copy_bridge_v1 as bridge

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'canonical/runtime/harbor_terminal_copy_bridge_v1.py'
SOLVER = ROOT / 'canonical/runtime/harbor_container_solver_worker_v1.py'
GOAL = 'Copy the contents of `src/source.txt` to a new file `out/destination.txt`.'


class LocalProcessEnvironment:
    """Runs real subprocesses in a temp directory; not a Docker simulation."""
    def __init__(self, cwd):
        self.cwd = cwd
        self.commands = []

    async def exec(self, command, **kwargs):
        self.commands.append(command)
        # In production these files are mounted at /opt/brain-ro. Test the same
        # checked-in scripts by substituting only that fixed deployment prefix.
        local = command.replace('/opt/brain-ro/', str(ROOT) + '/')
        result = subprocess.run(local, cwd=self.cwd, shell=True, text=True,
                                capture_output=True, timeout=kwargs['timeout_sec'])
        return SimpleNamespace(return_code=result.returncode, stdout=result.stdout, stderr=result.stderr)


class CopyBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'src').mkdir()
        (self.root / 'out').mkdir()
        (self.root / 'src/source.txt').write_bytes(b'hello\x00world\n')

    def tearDown(self):
        self.tmp.cleanup()

    def worker(self, instruction, suite='terminal-bench-4', observations=None):
        request = {'goal': 'not used by the copy route', 'mode': 'EPISTEMIC',
                   'inputs': {'harbor_task': instruction, 'harbor_suite': suite,
                              'observations': observations or []}}
        token = base64.b64encode(json.dumps(request).encode()).decode()
        result = subprocess.run(['python3', '-I', '-B', str(SOLVER), token], cwd=self.root,
                                text=True, capture_output=True, timeout=30, check=True)
        return json.loads(result.stdout.removeprefix('BRAIN_CONTAINER_SOLVE_V1:'))

    def perform(self, command):
        args = shlex.split(command)
        self.assertEqual(args[-3:-1], [bridge.WORKER, 'copy'])
        return subprocess.run(['python3', '-I', '-B', str(BRIDGE), 'copy', args[-1]],
                              cwd=self.root, text=True, capture_output=True, timeout=30)

    def test_real_loop_executes_copy_then_observes_contents(self):
        env = LocalProcessEnvironment(self.root)
        out = asyncio.run(agent.run_epistemic_goal(GOAL, env, suite='terminal-bench-4'))
        self.assertEqual(out['status'], 'FINISHED__DETERMINISTIC_PROPOSAL__VERIFIER_DECIDES')
        self.assertEqual((self.root / 'out/destination.txt').read_bytes(), b'hello\x00world\n')
        self.assertEqual([entry['proposed_actions'] for entry in out['trace']], [['terminal_exec'], ['finish']])
        self.assertEqual(out['trace'][0]['result']['returncode'], 0)
        self.assertFalse(out['external_verifier_invoked'])
        self.assertFalse(out['task_completion_claimed'])
        self.assertFalse(out['container_boundary_verified'])
        trajectory = vm.atif_trajectory(GOAL, out, 'local-test')
        self.assertEqual(trajectory['steps'][1]['tool_calls'][0]['function_name'], 'terminal_exec')
        self.assertEqual(len(env.commands), 3)

    def test_missing_source_existing_destination_and_symlink_fail_closed(self):
        (self.root / 'out/destination.txt').write_text('do not overwrite')
        self.assertFalse(self.worker(GOAL)['pass'])
        self.assertEqual((self.root / 'out/destination.txt').read_text(), 'do not overwrite')
        (self.root / 'out/destination.txt').unlink()
        (self.root / 'src/source.txt').unlink()
        self.assertFalse(self.worker(GOAL)['pass'])
        (self.root / 'src/source.txt').symlink_to(self.root / 'out')
        self.assertFalse(self.worker(GOAL)['pass'])
        (self.root / 'src/source.txt').unlink()
        (self.root / 'src/source.txt').write_text('source')
        (self.root / 'out').rmdir()
        (self.root / 'out').symlink_to(self.root / 'src', target_is_directory=True)
        self.assertFalse(self.worker(GOAL)['pass'])

    def test_source_changes_and_destination_races_are_rejected(self):
        command = self.worker(GOAL)['actions'][0]['args']['command']
        (self.root / 'src/source.txt').write_text('changed')
        self.assertNotEqual(self.perform(command).returncode, 0)
        self.assertFalse((self.root / 'out/destination.txt').exists())
        command = self.worker(GOAL)['actions'][0]['args']['command']
        (self.root / 'out/destination.txt').write_text('preexisting')
        self.assertNotEqual(self.perform(command).returncode, 0)
        self.assertEqual((self.root / 'out/destination.txt').read_text(), 'preexisting')

    def test_failed_or_tampered_observation_never_finishes(self):
        command = self.worker(GOAL)['actions'][0]['args']['command']
        self.assertEqual(self.perform(command).returncode, 0)
        obs = {'type': 'terminal_exec', 'command': command, 'returncode': 1}
        self.assertFalse(self.worker(GOAL, observations=[obs])['pass'])
        obs['returncode'] = 0
        obs['command'] += ' '
        self.assertFalse(self.worker(GOAL, observations=[obs])['pass'])
        obs['command'] = command
        (self.root / 'out/destination.txt').write_text('tampered')
        self.assertFalse(self.worker(GOAL, observations=[obs])['pass'])

    def test_unknown_grammar_cannot_be_interpreted_as_shell(self):
        for instruction in (
            'Copy the contents of `../source.txt` to a new file `out/x`.',
            'Copy the contents of `/etc/passwd` to a new file `out/x`.',
            'Copy the contents of `src/source.txt` to a new file `out/x`; touch /tmp/x.',
            'Implement this NodeBB JavaScript feature.',
        ):
            self.assertIsNone(bridge.propose(instruction, [], str(self.root)))
        self.assertFalse((self.root / 'out/x').exists())

    def test_bounded_source_size(self):
        (self.root / 'src/source.txt').write_bytes(b'x' * (bridge.MAX_BYTES + 1))
        self.assertFalse(self.worker(GOAL)['pass'])
        self.assertFalse((self.root / 'out/destination.txt').exists())


if __name__ == '__main__':
    unittest.main()
