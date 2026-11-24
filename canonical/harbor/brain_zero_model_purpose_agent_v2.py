#!/usr/bin/env python3
"""Brain-owned zero-model purpose-compiler agent for Harbor v0.27.0.

This external BaseAgent adapter makes zero model calls, forces model_name to
None, opens no runtime network, and never reads hidden tests, solutions,
verifier code or borrowed outputs. It executes only command strings produced by
brain_zero_model_purpose_policy_v2 from instruction-supplied operands and a
bounded read-only file-name scan. It captures a visible-repository git diff as
model.patch for the official SWE-bench Pro V2 fresh-sandbox re-grader.

Import path for Harbor:

    canonical.harbor.brain_zero_model_purpose_agent_v2:ZeroModelBrainPurposeAgentV2
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from canonical.harbor import brain_zero_model_purpose_policy_v2 as policy

SCHEMA = "BRAIN_ZERO_MODEL_PURPOSE_AGENT_V2"


class ZeroModelBrainPurposeAgentV2(BaseAgent):
    """Deterministic zero-inference custom agent with patch capture."""

    @staticmethod
    def name() -> str:
        return "brain-no-inference-purpose-v2"

    def __init__(self, logs_dir: pathlib.Path, **kwargs: Any) -> None:
        kwargs.pop("model_name", None)
        super().__init__(logs_dir=logs_dir, model_name=None, **kwargs)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def version(self) -> str:
        return "2.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEMA,
            "policy_schema": policy.SCHEMA,
            "agent_name": self.name(),
            "agent_version": self.version(),
            "model_name": self.model_name,
            "model_calls": 0,
            "runtime_network_calls": 0,
            "hidden_test_reading": False,
            "borrowed_outputs": False,
            "patch_capture": "visible_repository_git_diff_only",
        }
        (self.logs_dir / "setup.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = []

        async def exec_logged(command: str, phase: str) -> str:
            try:
                result = await environment.exec(command, timeout_sec=60)
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                return_code = int(result.return_code)
            except Exception as exc:
                stdout = ""
                stderr = type(exc).__name__ + ": " + str(exc)[:200]
                return_code = -1
            rows.append(
                {
                    "phase": phase,
                    "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
                    "command_is_safe": (
                        policy.command_is_safe(command)
                        if phase in {"action", "patch_capture"}
                        else policy.scan_is_safe(command)
                    ),
                    "return_code": return_code,
                    "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
                    "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
                    "stdout_tail": stdout[-200:],
                    "stderr_tail": stderr[-200:],
                }
            )
            return stdout

        scan_stdout = await exec_logged(policy.scan_command(), "scan")
        decision = policy.plan(instruction, scan_stdout)
        for command in decision["commands"]:
            if policy.command_is_safe(command):
                await exec_logged(command, "action")
        patch_stdout = await exec_logged(policy.patch_capture_command(), "patch_capture")
        patch_bytes = patch_stdout.encode("utf-8", errors="replace")[:2_000_000]
        (self.logs_dir / "model.patch").write_bytes(patch_bytes)

        payload = {
            "schema": SCHEMA,
            "decision": decision,
            "executed_commands": rows,
            "patch_sha256": hashlib.sha256(patch_bytes).hexdigest(),
            "patch_bytes": len(patch_bytes),
            "model_calls": 0,
            "runtime_network_calls": 0,
            "hidden_test_reading": False,
            "borrowed_outputs": False,
            "benchmark_reward_claimed": False,
        }
        (self.logs_dir / "agent_decision.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        context.n_input_tokens = 0
        context.n_cache_tokens = 0
        context.n_output_tokens = 0
        context.cost_usd = 0.0
        context.model_usage = None
        context.rollout_details = None
        context.metadata = {
            "schema": SCHEMA,
            "model_calls": 0,
            "runtime_network_calls": 0,
            "hidden_test_reading": False,
            "borrowed_outputs": False,
            "benchmark_reward_claimed": False,
            "patch_bytes": len(patch_bytes),
        }
