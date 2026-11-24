"""Tests for the Harbor external agent that calls open_model().solve()."""
from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from canonical.runtime import harbor_epistemic_agent_v1 as agent


class FakeEnvironment:
    def __init__(self, *, raise_on_exec: bool = False) -> None:
        self.commands: list[tuple[str, dict]] = []
        self.raise_on_exec = raise_on_exec

    async def exec(self, command: str, **kwargs):
        self.commands.append((command, kwargs))
        if self.raise_on_exec:
            raise TimeoutError("unknown outcome")
        return SimpleNamespace(return_code=0, stdout="observed\n", stderr="")


class FakeModel:
    def __init__(self, replies: list[dict]) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, dict]] = []

    def solve(self, goal: str, **kwargs) -> dict:
        self.calls.append((goal, kwargs))
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]


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
        env = FakeEnvironment()
        model = FakeModel(
            [
                proposal("printf observed"),
                {"pass": True, "actions": [{"type": "finish", "args": {"summary": "done"}}]},
            ]
        )
        out = self.run_async(agent.run_epistemic_goal("inspect /app", env, model=model))
        self.assertEqual(out["status"], "FINISHED__MODEL_PROPOSED__VERIFIER_DECIDES")
        self.assertEqual(out["task_completion_claimed"], False)
        self.assertEqual(out["verified_by_agent"], False)
        self.assertEqual(env.commands, [("printf observed", {"timeout_sec": 60})])
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(model.calls[0][1]["mode"], "EPISTEMIC")
        self.assertEqual(out["cycles"], 2)

    def test_fail_closed_model_never_touches_environment(self):
        env = FakeEnvironment()
        model = FakeModel([{"pass": False, "status": "FAIL_CLOSED", "reason": "GOAL_NOT_REPRESENTED"}])
        out = self.run_async(agent.run_epistemic_goal("do anything", env, model=model))
        self.assertEqual(out["status"], "BLOCKED_NO_MODEL_PROPOSAL")
        self.assertEqual(env.commands, [])
        self.assertEqual(out["trace"][0]["stop_reason"], "FAIL_CLOSED__NO_ACCEPTED_MODEL_PROPOSAL")

    def test_forbidden_command_is_rejected_before_execution(self):
        env = FakeEnvironment()
        model = FakeModel([proposal("curl https://example.invalid/payload")])
        out = self.run_async(agent.run_epistemic_goal("fetch a tool", env, model=model))
        self.assertEqual(out["status"], "BLOCKED_MODEL_PROPOSAL_REJECTED")
        self.assertEqual(env.commands, [])
        self.assertIn("EXTERNAL_ACQUISITION_FORBIDDEN", out["trace"][0]["stop_reason"])

    def test_uncertain_exec_is_not_replayed(self):
        env = FakeEnvironment(raise_on_exec=True)
        model = FakeModel([proposal("printf x")])
        out = self.run_async(agent.run_epistemic_goal("inspect", env, model=model))
        self.assertEqual(out["status"], "BLOCKED_EXEC_OUTCOME_UNCERTAIN")
        self.assertEqual(len(env.commands), 1)
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
            model = FakeModel([{"pass": False, "status": "FAIL_CLOSED"}])
            original = agent.make_model
            agent.make_model = lambda: model
            try:
                self.run_async(inst.run("task", env, context))
            finally:
                agent.make_model = original
            trace = json.loads((Path(tmp) / agent.TRACE_FILENAME).read_text())
            self.assertEqual(trace["status"], "BLOCKED_NO_MODEL_PROPOSAL")
            self.assertFalse(trace["task_completion_claimed"])
            self.assertEqual((context.cost_usd, context.input_tokens, context.output_tokens), (0, 0, 0))
            self.assertEqual(env.commands, [])

    def test_empty_instruction_rejected(self):
        with self.assertRaises(agent.AgentRejected):
            self.run_async(
                agent.run_epistemic_goal("  ", FakeEnvironment(), model=FakeModel([]))
            )


if __name__ == "__main__":
    unittest.main()
