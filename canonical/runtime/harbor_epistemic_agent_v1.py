"""Harbor external agent driven by Brain's open_model().solve(mode="EPISTEMIC").

The model is an *optional proposal source*, never the authority. This agent only
runs commands that the model explicitly proposes, passes each command through
the repository's deterministic command policy, and executes it through the
existing Harbor environment transport. There is no implicit retry, no network
acquisition, no guessed action, and no completion claim by the agent: the
Harbor verifier decides whether the task is solved.

`EPISTEMIC` is forwarded verbatim. Brain's solve() special-cases only RECALL and
SOLVE_OR_LEARN; every other mode string uses ordinary routing. This module does
not invent a new engine mode.

Run from the Harbor process (the module must be importable there):

    harbor run -d terminal-bench/terminal-bench@4.0.0 -e docker \
      -a canonical.runtime.harbor_epistemic_agent_v1:EpistemicBrainAgent -n 4
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.harbor_command_policy import validate_environment_command
from canonical.runtime.harbor_environment_transport_v2 import (
    ExecReceipt,
    HarborEnvironmentTransport,
    HarborTransportError,
)

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:  # allow import, tests and dry inspection without Harbor installed
    BaseAgent = object
    BaseEnvironment = Any
    AgentContext = Any

    class AgentCapabilities:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs


SCHEMA = "PROJECT_BRAIN_HARBOR_EPISTEMIC_AGENT_V1"
DEFAULT_MODE = "EPISTEMIC"
MAX_CYCLES = 8
MAX_COMMAND_CHARS = 12000
MAX_OUTPUT_CHARS = 16000
TRACE_FILENAME = "brain_epistemic_trace.json"
EXEC_TYPES = frozenset({"terminal_exec", "environment_exec", "exec"})


class AgentRejected(Exception):
    """A proposal was malformed or forbidden; stop without further execution."""


def mode_note(mode: str) -> str:
    requested = str(mode or DEFAULT_MODE).strip().upper()
    if requested in {"RECALL", "SOLVE_OR_LEARN"}:
        return "MODE_SPECIAL_CASED_BY_ENGINE:" + requested
    return "MODE_NOT_SPECIAL_CASED_BY_ENGINE:" + requested


def make_model() -> Any:
    from canonical.runtime.brain_unified_model_v1 import open_model

    artifact = str(os.environ.get("BRAIN_MODEL_ARTIFACT") or "").strip()
    return open_model(artifact) if artifact else open_model()


def build_goal(instruction: str, cycle: int, observations: Sequence[Mapping[str, Any]]) -> str:
    """Ask for one bounded action at a time; include only observed facts."""
    text = str(instruction or "").strip()
    if not text:
        raise AgentRejected("HARBOR_INSTRUCTION_REQUIRED")
    compact = []
    for obs in observations[-4:]:
        compact.append(
            {
                "type": obs.get("type"),
                "returncode": obs.get("returncode"),
                "stdout": str(obs.get("stdout") or "")[-2000:],
                "stderr": str(obs.get("stderr") or "")[-2000:],
            }
        )
    return (
        "You are an optional proposal source inside Project Brain, not the authority. "
        "Return an action object for this isolated Harbor task environment.\n"
        "Allowed actions: terminal_exec(command, timeout_sec) | finish(summary).\n"
        "Only inspect or modify the supplied task environment. No network acquisition, "
        "no package installation, no git fetch/clone/pull, no secrets, no external solutions.\n"
        f"Action schema: {{\"actions\":[{{\"type\":\"terminal_exec\",\"args\":{{\"command\":\"...\"}}}}]}}\n"
        f"Cycle: {cycle}\nObservations: {json.dumps(compact, sort_keys=True)}\n"
        "Task instruction:\n" + text
    )


def extract_actions(result: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Read only explicitly declared actions from a solve() envelope."""
    if not isinstance(result, Mapping):
        return []
    candidates: list[Any] = []
    for key in ("actions", "proposed_actions", "next_action", "action"):
        value = result.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, Mapping):
            candidates.append(value)
    execution = result.get("execution")
    if isinstance(execution, Mapping):
        for value in execution.get("actions", []) if isinstance(execution.get("actions"), list) else []:
            candidates.append(value)
    out: list[dict[str, Any]] = []
    for raw in candidates:
        if not isinstance(raw, Mapping):
            continue
        action = dict(raw)
        typ = str(action.get("type") or "").strip()
        if "." in typ:
            typ = typ.rsplit(".", 1)[-1]
        action["type"] = typ
        args = action.get("args")
        if not isinstance(args, Mapping):
            continue
        action["args"] = dict(args)
        out.append(action)
    return out


def validate_action(action: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    typ = str(action.get("type") or "")
    args = dict(action.get("args") or {})
    if typ in EXEC_TYPES:
        try:
            command = validate_environment_command(args.get("command"))
        except ValueError as exc:
            raise AgentRejected(str(exc)) from exc
        if len(command) > MAX_COMMAND_CHARS:
            raise AgentRejected("HARBOR_COMMAND_TOO_LONG")
        timeout = args.get("timeout_sec", args.get("timeout_s", 60))
        try:
            timeout_sec = int(timeout)
        except (TypeError, ValueError) as exc:
            raise AgentRejected("HARBOR_TIMEOUT_INVALID") from exc
        if not 1 <= timeout_sec <= 180:
            raise AgentRejected("HARBOR_TIMEOUT_OUT_OF_RANGE")
        return "exec", {"command": command, "timeout_sec": timeout_sec}
    if typ == "finish":
        summary = str(args.get("summary") or "").strip()
        if not summary:
            raise AgentRejected("HARBOR_FINISH_SUMMARY_REQUIRED")
        return "finish", {"summary": summary[:MAX_COMMAND_CHARS]}
    raise AgentRejected("HARBOR_ACTION_TYPE_REJECTED:" + typ[:80])


async def _call_model(model: Any, goal: str, kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """Call the synchronous engine without blocking Harbor's event loop."""
    return await asyncio.to_thread(model.solve, goal, **dict(kwargs))


async def run_epistemic_goal(
    instruction: str,
    environment: Any,
    *,
    model: Any,
    mode: str = DEFAULT_MODE,
    max_cycles: int = MAX_CYCLES,
) -> dict[str, Any]:
    """Run a bounded propose-act loop. No proposal means no action."""
    text = str(instruction or "").strip()
    if not text:
        raise AgentRejected("HARBOR_INSTRUCTION_REQUIRED")
    if not 1 <= int(max_cycles) <= MAX_CYCLES:
        raise AgentRejected("HARBOR_MAX_CYCLES_INVALID")
    transport = HarborEnvironmentTransport(environment)
    trace: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    instruction_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for cycle in range(1, int(max_cycles) + 1):
        goal = build_goal(text, cycle, observations)
        result = await _call_model(
            model,
            goal,
            {
                "inputs": {
                    "harbor_task": text,
                    "cycle": cycle,
                    "observations": list(observations),
                },
                "mode": mode,
                "context_paths": [],
            },
        )
        envelope = {
            "cycle": cycle,
            "model_status": str(result.get("status") or "") if isinstance(result, Mapping) else "",
            "model_reason": str(result.get("reason") or "") if isinstance(result, Mapping) else "",
            "model_pass": bool(isinstance(result, Mapping) and result.get("pass") is True),
            "model_capability_id": (
                str(result.get("capability_id") or "") if isinstance(result, Mapping) else ""
            ),
        }
        actions = extract_actions(result)
        envelope["proposed_actions"] = [str(a.get("type") or "") for a in actions]
        if not envelope["model_pass"] or not actions:
            envelope["stop_reason"] = "FAIL_CLOSED__NO_ACCEPTED_MODEL_PROPOSAL"
            trace.append(envelope)
            return {
                "schema": SCHEMA,
                "status": "BLOCKED_NO_MODEL_PROPOSAL",
                "task_completion_claimed": False,
                "mode_requested": mode,
                "mode_semantics": mode_note(mode),
                "instruction_sha256": instruction_sha256,
                "cycles": cycle,
                "trace": trace,
            }
        action = actions[0]
        try:
            kind, args = validate_action(action)
        except AgentRejected as exc:
            envelope["stop_reason"] = str(exc)
            trace.append(envelope)
            return {
                "schema": SCHEMA,
                "status": "BLOCKED_MODEL_PROPOSAL_REJECTED",
                "task_completion_claimed": False,
                "mode_requested": mode,
                "mode_semantics": mode_note(mode),
                "instruction_sha256": instruction_sha256,
                "cycles": cycle,
                "trace": trace,
            }
        envelope["action"] = {"type": kind, **args}
        if kind == "finish":
            trace.append(envelope)
            return {
                "schema": SCHEMA,
                "status": "FINISHED__MODEL_PROPOSED__VERIFIER_DECIDES",
                "task_completion_claimed": False,
                "verified_by_agent": False,
                "summary": args["summary"],
                "mode_requested": mode,
                "mode_semantics": mode_note(mode),
                "instruction_sha256": instruction_sha256,
                "cycles": cycle,
                "trace": trace,
            }
        receipt: ExecReceipt | None
        try:
            receipt = await transport.exec(args["command"], timeout_sec=args["timeout_sec"])
        except HarborTransportError as exc:
            envelope["stop_reason"] = "EXEC_OUTCOME_UNCERTAIN__NO_IMPLICIT_REPLAY:" + str(exc)[:200]
            receipt = None
        if receipt is None:
            trace.append(envelope)
            return {
                "schema": SCHEMA,
                "status": "BLOCKED_EXEC_OUTCOME_UNCERTAIN",
                "task_completion_claimed": False,
                "mode_requested": mode,
                "mode_semantics": mode_note(mode),
                "instruction_sha256": instruction_sha256,
                "cycles": cycle,
                "trace": trace,
            }
        observed = {
            "type": "terminal_exec",
            "command": receipt.command,
            "returncode": receipt.returncode,
            "stdout": receipt.stdout[-MAX_OUTPUT_CHARS:],
            "stderr": receipt.stderr[-MAX_OUTPUT_CHARS:],
        }
        envelope["result"] = {
            "returncode": receipt.returncode,
            "stdout": observed["stdout"],
            "stderr": observed["stderr"],
        }
        trace.append(envelope)
        observations.append(observed)
    return {
        "schema": SCHEMA,
        "status": "BLOCKED_MAX_CYCLES_WITHOUT_MODEL_FINISH",
        "task_completion_claimed": False,
        "mode_requested": mode,
        "mode_semantics": mode_note(mode),
        "instruction_sha256": instruction_sha256,
        "cycles": int(max_cycles),
        "trace": trace,
    }


class EpistemicBrainAgent(BaseAgent):
    capabilities = AgentCapabilities()

    @staticmethod
    def name() -> str:
        return "brain-epistemic"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        # The engine runs in the Harbor process; nothing is installed in the
        # task container, so there is no setup side effect to perform.
        return None

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        try:
            mode = str(os.environ.get("BRAIN_SOLVE_MODE") or DEFAULT_MODE).strip().upper() or DEFAULT_MODE
            result = await run_epistemic_goal(
                instruction,
                environment,
                model=make_model(),
                mode=mode,
            )
        except Exception as exc:
            result = {
                "schema": SCHEMA,
                "status": "BLOCKED_AGENT_EXCEPTION",
                "exception_type": type(exc).__name__,
                "exception_sha256": hashlib.sha256(str(exc).encode("utf-8", "replace")).hexdigest(),
                "task_completion_claimed": False,
            }
        try:
            logs = Path(self.logs_dir)
            logs.mkdir(parents=True, exist_ok=True)
            (logs / TRACE_FILENAME).write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        except Exception:
            pass
        for attr in ("cost_usd", "input_tokens", "output_tokens"):
            if hasattr(context, attr):
                try:
                    setattr(context, attr, 0)
                except Exception:
                    pass
