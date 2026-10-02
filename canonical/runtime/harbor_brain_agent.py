"""Harbor adapter for the canonical Project Brain controller.

This module is transport glue, not a new controller. It reuses the bounded
proposal/finalization helpers in canonical.runtime.astra_runtime and exposes only
the Harbor task environment as an action surface.

Terminal capability credit MUST NOT come from this adapter itself. Every run
records whether the controller was model-assisted; donor/dependency accounting
remains authoritative.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from canonical.runtime import astra_runtime

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:  # lets Brain unit tests import without Harbor installed
    BaseAgent = object  # type: ignore[assignment,misc]
    BaseEnvironment = Any  # type: ignore[assignment,misc]
    AgentContext = Any  # type: ignore[assignment,misc]

    class AgentCapabilities:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs


SCHEMA = "PROJECT_BRAIN_HARBOR_AGENT_TRACE_V1"
MAX_CYCLES = 12
MAX_COMMAND_CHARS = 12000
MAX_OUTPUT_CHARS = 16000

_FORBIDDEN_COMMAND_PATTERNS = (
    r"(?i)\b(curl|wget)\b",
    r"(?i)\bgit\s+(clone|fetch|pull)\b",
    r"(?i)\b(pip|pip3|uv|poetry)\s+install\b",
    r"(?i)\b(apt|apt-get|dnf|yum|apk)\s+.*\binstall\b",
    r"(?i)\bssh\b",
    r"(?i)\bscp\b",
)


def validate_environment_command(command: Any) -> str:
    if not isinstance(command, str) or not command.strip():
        raise ValueError("HARBOR_COMMAND_REQUIRED")
    command = command.strip()
    if len(command) > MAX_COMMAND_CHARS:
        raise ValueError("HARBOR_COMMAND_TOO_LONG")
    if "\x00" in command:
        raise ValueError("HARBOR_COMMAND_NUL")
    for pattern in _FORBIDDEN_COMMAND_PATTERNS:
        if re.search(pattern, command):
            raise ValueError("HARBOR_COMMAND_EXTERNAL_ACQUISITION_FORBIDDEN")
    return command


def _planner_action(raw: dict[str, Any]) -> dict[str, Any]:
    action = raw.get("action")
    if not isinstance(action, dict):
        actions = raw.get("actions")
        if isinstance(actions, list) and actions and isinstance(actions[0], dict):
            action = actions[0]
    if not isinstance(action, dict) and isinstance(raw.get("next_action"), dict):
        action = raw["next_action"]
    if not isinstance(action, dict):
        raise RuntimeError("HARBOR_PLANNER_ACTION_MISSING")
    typ = action.get("type")
    if isinstance(typ, str) and "." in typ:
        typ = typ.rsplit(".", 1)[-1]
        action = dict(action)
        action["type"] = typ
    if typ not in {"environment_exec", "finish"}:
        raise RuntimeError("HARBOR_PLANNER_ACTION_REJECTED:" + str(typ))
    if not isinstance(action.get("args"), dict):
        raise RuntimeError("HARBOR_PLANNER_ARGS_INVALID")
    return action


async def run_bounded_harbor_goal(
    goal: str,
    environment: BaseEnvironment,
    *,
    max_cycles: int = 8,
) -> dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("HARBOR_GOAL_REQUIRED")
    max_cycles = max(1, min(int(max_cycles), MAX_CYCLES))
    observations: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []

    for cycle in range(max_cycles):
        obs = astra_runtime._pack_observations_for_model(observations, max_chars=12000)
        prompt = (
            "You are an OPTIONAL proposal source inside Project Brain, not the authority. "
            "Return JSON text only. The task environment is isolated and terminal evidence "
            "must not be used to discover new external solutions. "
            "Goal: " + goal + "\n"
            "Allowed actions: environment_exec(command, timeout_s), finish(summary). "
            "environment_exec may inspect or modify ONLY the supplied task environment. "
            "No network acquisition, no package installation, no git fetch/clone/pull, "
            "no secrets. Prefer the smallest falsifiable action. "
            "Schema: {\"actions\":[{\"type\":\"...\",\"args\":{},\"why\":\"...\"}]}. "
            "Observations envelope: " + obs
        )
        planned = astra_runtime._planner_post(prompt, timeout_s=20)
        raw = astra_runtime._extract_json_object(planned.get("text", ""))
        action = _planner_action(raw)
        typ = action["type"]

        if typ == "finish":
            summary = str(action["args"].get("summary") or "").strip()
            if not summary:
                raise RuntimeError("HARBOR_EMPTY_FINISH")
            return {
                "schema": SCHEMA,
                "status": "FINISHED",
                "controller_mode": "OPTIONAL_MODEL_ADVISORY",
                "model_dependency_count": 1,
                "planner_model_last": planned.get("model"),
                "cycles": cycle + 1,
                "trace": trace,
                "summary": summary,
            }

        command = validate_environment_command(action["args"].get("command"))
        raw_timeout = action["args"].get("timeout_s", 60)
        try:
            timeout_s = max(1, min(int(raw_timeout), 180))
        except (TypeError, ValueError):
            raise RuntimeError("HARBOR_TIMEOUT_INVALID")
        result = await environment.exec(command=command, timeout_sec=timeout_s)
        stdout = str(getattr(result, "stdout", "") or "")[-MAX_OUTPUT_CHARS:]
        stderr = str(getattr(result, "stderr", "") or "")[-MAX_OUTPUT_CHARS:]
        returncode = int(getattr(result, "return_code", getattr(result, "returncode", 0)) or 0)
        observed = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
        trace.append({
            "cycle": cycle,
            "action": {"type": typ, "args": {"command": command, "timeout_s": timeout_s}},
            "result": observed,
        })
        observations.append({"action": action, "result": observed})

    final_obs = astra_runtime._pack_observations_for_model(observations, max_chars=12000)
    final_prompt = (
        "FINALIZATION ONLY. Do not request tools. Return JSON text only with "
        "{\"summary\":\"...\"}. Goal: " + goal +
        "\nAdmitted observations: " + final_obs
    )
    finalized = astra_runtime._planner_post(final_prompt, timeout_s=20)
    obj = astra_runtime._extract_json_object(finalized.get("text", ""))
    summary = obj.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise RuntimeError("HARBOR_FINALIZATION_INVALID")
    return {
        "schema": SCHEMA,
        "status": "FINISHED_AFTER_BOUNDED_ACTIONS",
        "controller_mode": "OPTIONAL_MODEL_ADVISORY_FORCED_FINALIZATION",
        "model_dependency_count": 1,
        "planner_model_last": finalized.get("model"),
        "cycles": max_cycles,
        "trace": trace,
        "summary": summary.strip(),
    }


class HarborBrainAgent(BaseAgent):  # type: ignore[misc]
    """Harbor custom agent that binds a task environment to Project Brain."""

    capabilities = AgentCapabilities()

    @staticmethod
    def name() -> str:
        return "project-brain"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        result = await run_bounded_harbor_goal(instruction, environment)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        trace_path = self.logs_dir / "project_brain_harbor_trace.json"
        trace_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if hasattr(context, "cost_usd"):
            context.cost_usd = 0.0
