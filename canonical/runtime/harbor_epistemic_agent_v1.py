"""Harbor external agent driven by Brain's open_model().solve(mode="EPISTEMIC").

The owner requested Harbor's container as the execution boundary, without a
nested namespace. The proposal helper dispatches the solver worker through
``environment.exec`` and never invokes solve on the host. The production entry
point remains disabled until read-only staging, container configuration,
network isolation, and benchmark-specific verifier handoff are checked. The
helper is for controlled transport tests only; its command policy is not an
isolation boundary.

`EPISTEMIC` is forwarded verbatim. Brain's solve() special-cases only RECALL and
SOLVE_OR_LEARN; every other mode string uses ordinary routing. This module does
not invent a new engine mode.

The Harbor entry point emits a refusal trace, not a benchmark result.
No environment variable or dataset label can override this refusal.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shlex
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.harbor_command_policy import validate_environment_command
from canonical.runtime.harbor_environment_transport_v2 import (
    ExecReceipt,
    HarborEnvironmentTransport,
    HarborTransportError,
)
from canonical.tools.pro_hard51_preflight_v1 import DISCLOSED_ID, DISCLOSURE

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
MAX_WORKER_REQUEST_BYTES = 64_000
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
    """A host-side model is never a valid Harbor solver."""
    raise AgentRejected("HOST_SOLVER_FORBIDDEN")


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


async def _call_container_model(
    transport: HarborEnvironmentTransport, goal: str, kwargs: Mapping[str, Any]
) -> dict[str, Any]:
    """Test-only transport seam; neither dispatch nor a response proves isolation."""
    request = {
        "goal": goal,
        "inputs": dict(kwargs.get("inputs") or {}),
        "mode": str(kwargs.get("mode") or DEFAULT_MODE),
    }
    raw = json.dumps(request, sort_keys=True, ensure_ascii=True).encode("utf-8")
    if len(raw) > MAX_WORKER_REQUEST_BYTES:
        raise AgentRejected("HARBOR_SOLVER_REQUEST_TOO_LARGE")
    payload = base64.b64encode(raw).decode("ascii")
    command = (
        "env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp "
        "python3 -I -B /opt/brain-ro/canonical/runtime/harbor_container_solver_worker_v1.py "
        + shlex.quote(payload)
    )
    receipt = await transport.exec(command, timeout_sec=180)
    if receipt.returncode != 0:
        raise AgentRejected("CONTAINER_SOLVER_NONZERO")
    marker = "BRAIN_CONTAINER_SOLVE_V1:"
    lines = [line[len(marker):] for line in receipt.stdout.splitlines()
             if line.startswith(marker)]
    if len(lines) != 1 or len(lines[0]) > 1_000_000:
        raise AgentRejected("CONTAINER_SOLVER_RESPONSE_INVALID")
    try:
        result = json.loads(lines[0])
    except (TypeError, ValueError) as exc:
        raise AgentRejected("CONTAINER_SOLVER_RESPONSE_INVALID") from exc
    if not isinstance(result, dict):
        raise AgentRejected("CONTAINER_SOLVER_RESPONSE_INVALID")
    return result


def _transport_contract() -> dict[str, Any]:
    return {
        "transport_only": True,
        "container_boundary_verified": False,
        "read_only_staging_verified": False,
        "network_egress_verified": False,
        "runtime_model_calls_verified": False,
        "parameters_stored_verified": False,
        "patch_emitted": False,
        "external_verifier_invoked": False,
        "verified_by_agent": False,
    }


async def run_epistemic_goal(
    instruction: str,
    environment: Any,
    *,
    model: Any = None,
    mode: str = DEFAULT_MODE,
    max_cycles: int = MAX_CYCLES,
) -> dict[str, Any]:
    """Test-only container transport loop; production admission remains closed.

    A supplied host model is explicitly rejected. This helper does not verify
    container isolation, collect patches, or invoke benchmark verifiers.
    """
    if model is not None:
        raise AgentRejected("HOST_SOLVER_FORBIDDEN")
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
        try:
            result = await _call_container_model(
                transport,
                goal,
                {
                    "inputs": {
                        "harbor_task": text,
                        "cycle": cycle,
                        "observations": list(observations),
                    },
                    "mode": mode,
                },
            )
        except (AgentRejected, HarborTransportError) as exc:
            trace.append({"cycle": cycle, "stop_reason": str(exc)[:200]})
            return {
                "schema": SCHEMA,
                **_transport_contract(),
                "status": "BLOCKED_CONTAINER_SOLVER_UNAVAILABLE",
                "task_completion_claimed": False,
                "mode_requested": mode,
                "mode_semantics": mode_note(mode),
                "instruction_sha256": instruction_sha256,
                "cycles": cycle,
                "trace": trace,
            }
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
                **_transport_contract(),
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
                **_transport_contract(),
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
                **_transport_contract(),
                "status": "FINISHED__MODEL_PROPOSED__VERIFIER_DECIDES",
                "task_completion_claimed": False,
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
                **_transport_contract(),
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
        **_transport_contract(),
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

    def __init__(self, *args: Any, allow_isolated_vm_eval: bool = False, **kwargs: Any) -> None:
        if type(allow_isolated_vm_eval) is not bool:
            raise AgentRejected("ISOLATED_VM_EVAL_FLAG_MUST_BE_BOOLEAN")
        super().__init__(*args, **kwargs)
        # This is only a request; it does not enable the unintegrated boundary.
        self.allow_isolated_vm_eval = allow_isolated_vm_eval

    @staticmethod
    def name() -> str:
        return "brain-epistemic"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        # Staging is intentionally disabled until a read-only mount and safe
        # container configuration can be established and independently checked.
        return None

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        # The transport exists, but no trusted runtime check has established
        # read-only staging, mounts, privileges, network isolation or a fresh
        # verifier. An opt-in flag is not proof. Refuse before any dispatch.
        result = {
            "schema": SCHEMA,
            "status": "ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK",
            "boundary_issue": "CONTAINER_CONFIGURATION_AND_VERIFIER_UNVERIFIED",
            "requested_isolated_vm_eval": self.allow_isolated_vm_eval,
            # Record the owner's requested opt-in without treating an env var
            # as proof of identity, mounts, network isolation or quiescence.
            "requested_external_harbor_vm_eval": os.environ.get("BRAIN_ALLOW_EXTERNAL_HARBOR_VM_EVAL") == "1",
            "external_harbor_vm_eval_status": "BLOCKED__INTEGRATION_INCOMPLETE",
            "execution_authorized": False,
            "task_completion_claimed": False,
            "verified_by_agent": False,
            "instruction_sha256": hashlib.sha256(instruction.encode("utf-8")).hexdigest(),
            # The entry point has no trusted benchmark task identity. Record the
            # known disclosure globally, not as an assertion about this task.
            "task_identity_verified": False,
            "benchmark_disclosure_notice": {"instance_id": DISCLOSED_ID, "note": DISCLOSURE},
        }
        try:
            logs = Path(self.logs_dir)
            logs.mkdir(parents=True, exist_ok=True)
            (logs / TRACE_FILENAME).write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        except Exception:
            pass
        # Do not overwrite accounting fields: their values are owned by Harbor.


# Requested import name; this is the same fail-closed class, not an admitted
# container implementation or an additional execution route.
HarborEpistemicAgent = EpistemicBrainAgent
