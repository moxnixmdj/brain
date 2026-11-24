"""Tests for the Harbor external agent that calls open_model().solve()."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from canonical.runtime import harbor_epistemic_agent_v1 as agent


class FakeEnvironment:
    def __init__(self, *, raise_on_exec: bool = False, replies=None) -> None:
        self.commands: list[tuple[str, dict]] = []
        self.raise_on_exec = raise_on_exec
        self.replies = list(replies or [])

    async def exec(self, command: str, **kwargs):
        self.commands.append((command, kwargs))
        if self.raise_on_exec and "harbor_container_solver_worker_v1.py" not in command:
            raise TimeoutError("unknown outcome")
        if "harbor_container_solver_worker_v1.py" in command:
            reply = self.replies.pop(0)
            return SimpleNamespace(return_code=0, stdout="BRAIN_CONTAINER_SOLVE_V1:" + json.dumps(reply) + "\n", stderr="")
        return SimpleNamespace(return_code=0, stdout="observed\n", stderr="")


def proposal(command: str) -> dict:
    return {
        "pass": True,
        "status": "PASS__MODEL_PROPOSAL",
        "actions": [{"type": "terminal_exec", "args": {"command": command}}],
    }


class HarborEpistemicAgentTests(unittest.TestCase):
    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def test_metadata_and_mode_semantics(self):
        self.assertEqual(agent.EpistemicBrainAgent.name(), "brain-epistemic")
        self.assertEqual(agent.EpistemicBrainAgent().version(), "1.0.0")
        self.assertIn("MODE_NOT_SPECIAL_CASED_BY_ENGINE:EPISTEMIC", agent.mode_note("EPISTEMIC"))
        self.assertEqual(agent.mode_note("RECALL"), "MODE_SPECIAL_CASED_BY_ENGINE:RECALL")

    def test_model_proposal_is_executed_and_finish_ends_loop(self):
        env = FakeEnvironment(replies=[
            proposal("printf observed"),
            {"pass": True, "actions": [{"type": "finish", "args": {"summary": "done"}}]},
        ])
        out = self.run_async(agent.run_epistemic_goal("inspect /app", env))
        self.assertEqual(out["status"], "FINISHED__MODEL_PROPOSED__VERIFIER_DECIDES")
        self.assertEqual(out["task_completion_claimed"], False)
        self.assertEqual(out["verified_by_agent"], False)
        self.assertEqual(len(env.commands), 3)
        self.assertIn("harbor_container_solver_worker_v1.py", env.commands[0][0])
        self.assertEqual(env.commands[1], ("printf observed", {"timeout_sec": 60}))
        self.assertIn("harbor_container_solver_worker_v1.py", env.commands[2][0])
        self.assertEqual(out["cycles"], 2)

    def test_fail_closed_model_never_touches_environment(self):
        env = FakeEnvironment(replies=[{"pass": False, "status": "FAIL_CLOSED", "reason": "GOAL_NOT_REPRESENTED"}])
        out = self.run_async(agent.run_epistemic_goal("do anything", env))
        self.assertEqual(out["status"], "BLOCKED_NO_MODEL_PROPOSAL")
        self.assertEqual(len(env.commands), 1)
        self.assertIn("harbor_container_solver_worker_v1.py", env.commands[0][0])
        self.assertEqual(out["trace"][0]["stop_reason"], "FAIL_CLOSED__NO_ACCEPTED_MODEL_PROPOSAL")

    def test_forbidden_command_is_rejected_before_execution(self):
        env = FakeEnvironment(replies=[proposal("curl https://example.invalid/payload")])
        out = self.run_async(agent.run_epistemic_goal("fetch a tool", env))
        self.assertEqual(out["status"], "BLOCKED_MODEL_PROPOSAL_REJECTED")
        self.assertEqual(len(env.commands), 1)
        self.assertIn("harbor_container_solver_worker_v1.py", env.commands[0][0])
        self.assertIn("EXTERNAL_ACQUISITION_FORBIDDEN", out["trace"][0]["stop_reason"])

    def test_uncertain_exec_is_not_replayed(self):
        env = FakeEnvironment(raise_on_exec=True, replies=[proposal("printf x")])
        out = self.run_async(agent.run_epistemic_goal("inspect", env))
        self.assertEqual(out["status"], "BLOCKED_EXEC_OUTCOME_UNCERTAIN")
        self.assertEqual(len(env.commands), 2)
        self.assertIn("EXEC_OUTCOME_UNCERTAIN", out["trace"][0]["stop_reason"])

    def test_actions_are_taken_only_from_explicit_envelope_fields(self):
        parsed = agent.extract_actions(
            {
                "pass": True,
                "execution": {"actions": [{"type": "environment_exec", "args": {"command": "true"}}]},
                "free_text": "finish(summary='fake')",
            }
        )
        self.assertEqual([a["type"] for a in parsed], ["environment_exec"])
        self.assertEqual(parsed[0]["args"]["command"], "true")

    def test_run_writes_trace_and_does_not_claim_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            inst = agent.EpistemicBrainAgent()
            inst.logs_dir = Path(tmp)
            context = SimpleNamespace(cost_usd=99.0, input_tokens=5, output_tokens=7)
            env = FakeEnvironment()
            original = agent.make_model
            def forbidden_model():
                self.fail("must refuse before constructing the solver")
            agent.make_model = forbidden_model
            try:
                self.run_async(inst.run("task", env, context))
            finally:
                agent.make_model = original
            trace = json.loads((Path(tmp) / agent.TRACE_FILENAME).read_text())
            self.assertEqual(trace["status"], "ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK")
            self.assertFalse(trace["task_completion_claimed"])
            self.assertFalse(trace["verified_by_agent"])
            self.assertFalse(trace["task_identity_verified"])
            self.assertEqual(trace["benchmark_disclosure_notice"]["instance_id"], agent.DISCLOSED_ID)
            self.assertEqual(trace["benchmark_disclosure_notice"]["note"], agent.DISCLOSURE)
            self.assertEqual((context.cost_usd, context.input_tokens, context.output_tokens), (99.0, 5, 7))
            self.assertEqual(env.commands, [])

    def test_claimed_isolation_and_dataset_do_not_enable_execution(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BRAIN_CARRIER_QUALIFIED": "true",
            "BRAIN_BENCHMARK": "SWE-bench Pro",
            "BRAIN_SOLVE_MODE": "EPISTEMIC",
        }):
            inst = agent.EpistemicBrainAgent()
            inst.logs_dir = Path(tmp)
            env = FakeEnvironment()
            with patch.object(agent, "make_model", side_effect=AssertionError("solver called")):
                self.run_async(inst.run("task", env, SimpleNamespace()))
            trace = json.loads((Path(tmp) / agent.TRACE_FILENAME).read_text())
            self.assertEqual(trace["status"], "ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK")
            self.assertEqual(env.commands, [])

    def test_empty_instruction_rejected(self):
        with self.assertRaises(agent.AgentRejected):
            self.run_async(
                agent.run_epistemic_goal("  ", FakeEnvironment())
            )


if __name__ == "__main__":
    unittest.main()
