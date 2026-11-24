"""Regression checks for the host-solver hazard; no Docker or benchmark run."""
from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import harbor_epistemic_agent_v1 as agent


class HostWritingProposalSource:
    def __init__(self, sentinel: Path):
        self.sentinel = sentinel

    def solve(self, goal, **kwargs):
        # This fake demonstrates the placement of solve(), not a Docker escape.
        self.sentinel.write_text('host-side solve was called')
        return {'pass': False, 'status': 'FAIL_CLOSED'}


class EnvironmentRecorder:
    def __init__(self):
        self.commands = []

    async def exec(self, command, **kwargs):
        self.commands.append(command)
        return SimpleNamespace(return_code=0, stdout='', stderr='')


class HarborContainerBoundaryTests(unittest.TestCase):
    def test_proposal_helper_rejects_host_solver_before_any_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / 'sentinel'
            env = EnvironmentRecorder()
            with self.assertRaisesRegex(agent.AgentRejected, 'HOST_SOLVER_FORBIDDEN'):
                asyncio.run(agent.run_epistemic_goal('task', env, model=HostWritingProposalSource(sentinel)))
            self.assertFalse(sentinel.exists())
            self.assertEqual(env.commands, [])

    def test_external_vm_opt_in_is_recorded_but_does_not_bypass_missing_boundary(self):
        for value, requested in ((None, False), ('', False), ('true', False), ('1', True)):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                inst = agent.HarborEpistemicAgent()
                inst.logs_dir = Path(tmp)
                env = EnvironmentRecorder()
                variables = {} if value is None else {'BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL': value}
                with patch.dict('os.environ', variables, clear=True):
                    asyncio.run(inst.run('task', env, SimpleNamespace()))
                trace = json.loads((Path(tmp) / agent.TRACE_FILENAME).read_text())
                self.assertIs(trace['requested_external_harbor_vm_eval'], requested)
                self.assertEqual(trace['external_harbor_vm_eval_status'], 'BLOCKED__INTEGRATION_INCOMPLETE')
                self.assertFalse(trace['execution_authorized'])
                self.assertEqual(env.commands, [])

    def test_opt_in_must_be_a_boolean(self):
        with self.assertRaisesRegex(agent.AgentRejected, 'ISOLATED_VM_EVAL_FLAG_MUST_BE_BOOLEAN'):
            agent.HarborEpistemicAgent(allow_isolated_vm_eval='true')

    def test_production_entry_refuses_before_solver_despite_vm_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            inst = agent.HarborEpistemicAgent(allow_isolated_vm_eval=True)
            inst.logs_dir = Path(tmp)
            env = EnvironmentRecorder()
            with patch.dict('os.environ', {'BRAIN_CARRIER_QUALIFIED': 'true',
                                           'BRAIN_ALLOW_ISOLATED_VM_EVAL': 'true'}), \
                 patch.object(agent, 'make_model', side_effect=AssertionError('host solver invoked')):
                asyncio.run(inst.run('task', env, SimpleNamespace()))
            trace = json.loads((Path(tmp) / agent.TRACE_FILENAME).read_text())
            self.assertEqual(trace['status'], 'ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK')
            self.assertEqual(trace['boundary_issue'], 'CONTAINER_CONFIGURATION_AND_VERIFIER_UNVERIFIED')
            self.assertTrue(trace['requested_isolated_vm_eval'])
            self.assertFalse(trace['execution_authorized'])
            self.assertIs(agent.HarborEpistemicAgent, agent.EpistemicBrainAgent)
            self.assertEqual(trace['benchmark_disclosure_notice']['instance_id'], agent.DISCLOSED_ID)
            self.assertFalse(trace['task_completion_claimed'])
            self.assertEqual(env.commands, [])


if __name__ == '__main__':
    unittest.main()
