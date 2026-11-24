#!/usr/bin/env python3
"""Brain-owned, no-inference custom agent for Harbor v0.27.0.

The agent is an external ``BaseAgent`` integration. It makes zero model calls,
does not accept a model name, does not open the network at runtime, and never
reads hidden tests, solutions, verifier code or borrowed outputs. It executes
only command strings produced by ``brain_zero_model_policy_v1`` from the
instruction's own quoted operands and a read-only file-name scan.

Import path for Harbor::

    canonical.harbor.brain_zero_model_agent_v1:ZeroModelBrainAgent

This is a shipped harness adapter, not a claim of benchmark competence. A
runner-owned official Harbor verifier decides rewards; this agent only records
its own zero-model decision surface.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from canonical.harbor import brain_zero_model_policy_v1 as policy

SCHEMA = "BRAIN_NO_INFERENCE_HARBOR_AGENT_V1"


class ZeroModelBrainAgent(BaseAgent):
    """A deterministic, stdlib-policy custom agent with no inference substrate."""

    @staticmethod
    def name() -> str:
        return "brain-no-inference-v1"

    def __init__(self, logs_dir: pathlib.Path, **kwargs: Any) -> None:
        # Force model_name to None even if a caller supplies one. This adapter
        # must never acquire a model dependency through Harbor kwargs.
        kwargs.pop("model_name", None)
        super().__init__(logs_dir=logs_dir, model_name=None, **kwargs)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def version(self) -> str:
        return "1.0.0"

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
            "forbidden_path_markers": list(policy.FORBIDDEN_PATH_MARKERS),
            "note": "setup performs no environment command and no model call",
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
        scan_command = policy.scan_command()
        scan_rows: list[dict[str, Any]] = []

        async def exec_logged(command: str, phase: str) -> str:
            try:
                result = await environment.exec(command, timeout_sec=20)
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                return_code = int(result.return_code)
            except Exception as exc:  # fail closed without borrowing an output
                stdout = ""
                stderr = type(exc).__name__ + ": " + str(exc)[:200]
                return_code = -1
            scan_rows.append(
                {
                    "phase": phase,
                    "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
                    "command_is_safe": policy.command_is_safe(command) if phase == "action" else policy.scan_is_safe(command),
                    "return_code": return_code,
                    "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
                    "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
                    "stdout_tail": stdout[-200:],
                    "stderr_tail": stderr[-200:],
                }
            )
            return stdout

        scan_stdout = await exec_logged(scan_command, "scan")
        decision = policy.plan(instruction, scan_stdout)
        for command in decision["commands"]:
            await exec_logged(command, "action")
        # A second read-only scan is local state verification, never the
        # benchmark verifier and never a reward claim.
        verify_stdout = await exec_logged(scan_command, "verify_scan")

        payload = {
            "schema": SCHEMA,
            "decision": decision,
            "executed_commands": scan_rows,
            "verify_scan_sha256": hashlib.sha256(verify_stdout.encode("utf-8")).hexdigest(),
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
            "benchmark_reward_claimed": False,
        }
