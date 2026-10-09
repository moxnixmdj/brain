"""Brain-owned Harbor research controller for zero-case science-route qualification.

The cognition substrate may propose a bounded research contract and candidate shell
actions. Brain owns command admissibility, candidate selection, verification,
coverage state, and finish authority. No benchmark-specific task content lives here.
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
from typing import Any

from canonical.runtime import harbor_science_planner_v1 as science_planner
from canonical.runtime.harbor_command_policy import validate_environment_command
from canonical.runtime.harbor_environment_transport import HarborEnvironmentTransport
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract as compile_raw_task_contract
from canonical.runtime.raw_task_acceptance_residual_localizer_v1 import localize as localize_raw_task_acceptance

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:
    BaseAgent = object
    BaseEnvironment = Any
    AgentContext = Any
    class AgentCapabilities:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

SCHEMA = "PROJECT_BRAIN_HARBOR_SCIENCE_AGENT_TRACE_V1"
MAX_CYCLES = 12
MAX_REQUIREMENTS = 16
MAX_CANDIDATES = 8
MAX_OUTPUT_CHARS = 16000
PLANNER_TIMEOUT_S = 300
DEFAULT_ACTION_TIMEOUT_S = 1800
MAX_ACTION_TIMEOUT_S = 7200
DEFAULT_VERIFY_TIMEOUT_S = 600
MAX_VERIFY_TIMEOUT_S = 3600

_FATAL_ACTION_STDERR_MARKERS = (
    "here-document at line",
    "unexpected eof",
    "syntax error near unexpected token",
)

def _action_transport_clean(returncode: int, stdout: Any, stderr: Any) -> bool:
    if int(returncode) != 0:
        return False
    text = (str(stdout or "") + "\n" + str(stderr or "")).lower()
    return not any(marker in text for marker in _FATAL_ACTION_STDERR_MARKERS)
MAX_BRAIN_DELIVERABLES = 16
_EXPLICIT_SUBMISSION_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:/app/)?submission/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)"
)
_EXPLICIT_OUTPUT_DIRECTIVE_RE = re.compile(
    r"""(?is)\b(?:write|create|save|store|export|produce|deliver|emit)\b
        [^.\n]{0,240}?
        \b(?:to|at|as|into)\s+
        [`'"\[]*
        (?P<path>/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)
    """,
    re.VERBOSE,
)

def _valid_mandated_output_path(path: str) -> bool:
    if not path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")[1:]):
        return False
    return bool(re.fullmatch(r"/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+", path))

def _brain_mandated_deliverables(goal: str) -> dict[str, str]:
    text = str(goal or "")
    paths: list[str] = []

    def add(path: str) -> None:
        if not _valid_mandated_output_path(path):
            return
        if path not in paths and len(paths) < MAX_BRAIN_DELIVERABLES:
            paths.append(path)

    for match in _EXPLICIT_SUBMISSION_PATH_RE.finditer(text):
        raw = match.group(1)
        add(raw if raw.startswith("/app/") else "/app/" + raw.lstrip("/"))

    # A task can require an artifact anywhere, not only under /app/submission.
    # Bind only absolute file paths that are syntactically attached to an
    # explicit output-producing directive; ordinary input references remain inputs.
    for match in _EXPLICIT_OUTPUT_DIRECTIVE_RE.finditer(text):
        add(match.group("path"))

    return {f"BRAIN_DELIVERABLE_{i + 1:02d}": path for i, path in enumerate(paths)}

async def _validate_brain_deliverable(
    requirement_id: str,
    path: str,
    environment: BaseEnvironment,
) -> dict[str, Any]:
    transport = HarborEnvironmentTransport(environment)
    quoted = shlex.quote(path)
    checks = [f"test -s {quoted}"]
    if path.lower().endswith(".json"):
        checks.append(f"python -m json.tool {quoted} >/dev/null")
    elif path.lower().endswith(".py"):
        checks.append(f"python -m py_compile {quoted}")
    observed: list[dict[str, Any]] = []
    for command in checks:
        receipt = await transport.exec(command, timeout_sec=60)
        row = {
            "command": command,
            "returncode": receipt.returncode,
            "stdout": receipt.stdout[-MAX_OUTPUT_CHARS:],
            "stderr": receipt.stderr[-MAX_OUTPUT_CHARS:],
        }
        observed.append(row)
        if receipt.returncode != 0:
            return {
                "requirement_id": requirement_id,
                "path": path,
                "verified": False,
                "checks": observed,
            }
    return {
        "requirement_id": requirement_id,
        "path": path,
        "verified": True,
        "checks": observed,
    }

MAX_DECLARED_INPUT_TOTAL_CHARS = 24000
MAX_DECLARED_INPUT_PER_FILE_CHARS = 8000
_EXPLICIT_SPEC_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])(/app/spec/[A-Za-z0-9_./-]+)"
)

def _declared_task_paths(goal: str) -> tuple[list[str], list[str]]:
    """Return explicit task-authoritative inputs and mandatory submission outputs."""
    inputs: list[str] = []
    for match in _EXPLICIT_SPEC_PATH_RE.finditer(str(goal or "")):
        path = match.group(1).rstrip(".,;:")
        if any(part in {".", ".."} for part in path.split("/")):
            continue
        if path not in inputs:
            inputs.append(path)
    outputs = list(_brain_mandated_deliverables(goal).values())
    return inputs, outputs

async def _snapshot_declared_inputs(
    environment: BaseEnvironment,
    paths: list[str],
) -> list[dict[str, Any]]:
    """Brain-owned read of exact declared local source bytes before planning."""
    if not paths:
        return []
    transport = HarborEnvironmentTransport(environment)
    remaining = MAX_DECLARED_INPUT_TOTAL_CHARS
    snapshots: list[dict[str, Any]] = []
    for path in paths:
        q = shlex.quote(path)
        take = min(MAX_DECLARED_INPUT_PER_FILE_CHARS, max(0, remaining))
        command = validate_environment_command(
            f"test -f {q} && sha256sum {q} && printf '\\n---CONTENT---\\n' && head -c {take} {q}"
        )
        receipt = await transport.exec(command, timeout_sec=60)
        if receipt.returncode != 0:
            raise RuntimeError("SCIENCE_DECLARED_INPUT_UNREADABLE:" + path)
        snapshots.append({
            "kind": "BRAIN_DECLARED_INPUT_SNAPSHOT",
            "path": path,
            "returncode": receipt.returncode,
            "stdout": receipt.stdout[-MAX_OUTPUT_CHARS:],
            "stderr": receipt.stderr[-2000:],
        })
        remaining = max(0, remaining - take)
    return snapshots

async def _declared_output_gate(
    environment: BaseEnvironment,
    paths: list[str],
) -> list[dict[str, Any]]:
    """Revalidate exact declared outputs immediately before Brain finish."""
    if not paths:
        return []
    transport = HarborEnvironmentTransport(environment)
    failures: list[dict[str, Any]] = []
    for path in paths:
        q = shlex.quote(path)
        checks = [f"test -s {q}"]
        if path.lower().endswith(".json"):
            checks.append(f"python -m json.tool {q} >/dev/null")
        elif path.lower().endswith(".py"):
            checks.append(f"python -m py_compile {q}")
        command = validate_environment_command(" && ".join(checks))
        receipt = await transport.exec(command, timeout_sec=60)
        if receipt.returncode != 0:
            failures.append({
                "path": path,
                "returncode": receipt.returncode,
                "stdout": receipt.stdout[-2000:],
                "stderr": receipt.stderr[-2000:],
            })
    return failures

def _compile_lossless_task_scope(goal: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Compile the exact raw goal into non-droppable Brain-owned acceptance scope."""
    contract = compile_raw_task_contract(
        goal,
        source_id="HARBOR_SCIENCE_GOAL",
        routing_target_effects=["SCIENCE_CANDIDATE_READY"],
    )
    if contract.get("pass") is not True:
        raise RuntimeError("SCIENCE_RAW_TASK_CONTRACT_FAILED:" + ";".join(contract.get("errors") or []))
    acceptance = contract.get("acceptance_contract") or {}
    obligations = acceptance.get("obligations") or []
    if not obligations:
        raise RuntimeError("SCIENCE_RAW_TASK_OBLIGATION_COUNT_INVALID")
    # Do not impose a second semantic/cardinality ceiling above the lossless
    # source contract. Resource admissibility belongs to the exact planner
    # token-budget guard, which can fail closed without dropping obligations.
    localization = localize_raw_task_acceptance(contract)
    if localization.get("pass") is not True:
        raise RuntimeError("SCIENCE_RAW_TASK_LOCALIZATION_FAILED:" + str(localization.get("reason") or "UNKNOWN"))
    localized = {row.get("obligation_id"): row for row in localization.get("obligations") or []}
    prompt_rows: list[dict[str, Any]] = []
    for row in obligations:
        oid = row.get("obligation_id")
        if oid not in localized:
            raise RuntimeError("SCIENCE_RAW_TASK_LOCALIZATION_INCOMPLETE")
        prompt_rows.append({
            "obligation_id": oid,
            "segment_sha256": row.get("segment_sha256"),
            "segment_index": row.get("segment_index"),
            "span": row.get("span"),
            "acceptance_route_status": localized[oid].get("status"),
            "acceptance_receipt_required": True,
        })
    return contract, localization, prompt_rows

def _planner_raw_task_manifest_summary(
    goal: str,
    contract: dict[str, Any],
    localization: dict[str, Any],
    prompt_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compress planner-only metadata without weakening Brain-owned acceptance.

    The exact Goal text remains in the planner prompt. The full per-segment
    acceptance contract remains in Brain state and still requires an independent
    receipt for every original obligation. The optional cognition substrate gets
    only a content-addressed summary because individual RAWREQ IDs/hashes are
    routing/accounting metadata, not task semantics or finish authority.
    """
    acceptance = contract.get("acceptance_contract") or {}
    required = acceptance.get("required_obligation_ids") or []
    obligations = acceptance.get("obligations") or []
    localized_rows = localization.get("obligations") or []
    if (
        not isinstance(required, list)
        or not required
        or not isinstance(obligations, list)
        or len(obligations) != len(required)
        or not isinstance(prompt_rows, list)
        or len(prompt_rows) != len(required)
        or not isinstance(localized_rows, list)
        or len(localized_rows) != len(required)
    ):
        raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_CARDINALITY_INVALID")

    ordered_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    previous_end = -1
    for index, row in enumerate(prompt_rows):
        if not isinstance(row, dict):
            raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_ROW_INVALID")
        oid = row.get("obligation_id")
        span = row.get("span")
        segment_sha = row.get("segment_sha256")
        if oid != required[index] or not isinstance(oid, str) or not oid or oid in seen:
            raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_IDENTITY_INVALID")
        seen.add(oid)
        if (
            not isinstance(span, list)
            or len(span) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in span)
        ):
            raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_SPAN_INVALID")
        start, end = span
        if start < 0 or end <= start or end > len(goal) or start < previous_end:
            raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_SPAN_ORDER_INVALID")
        if not isinstance(segment_sha, str) or len(segment_sha) != 64:
            raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_HASH_INVALID")
        if hashlib.sha256(goal[start:end].encode("utf-8")).hexdigest() != segment_sha:
            raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_SOURCE_HASH_MISMATCH")
        if row.get("acceptance_receipt_required") is not True:
            raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_RECEIPT_DISABLED")
        previous_end = end
        ordered_rows.append({
            "obligation_id": oid,
            "segment_sha256": segment_sha,
            "segment_index": row.get("segment_index"),
            "span": span,
            "acceptance_route_status": row.get("acceptance_route_status"),
            "acceptance_receipt_required": True,
        })

    manifest_bytes = json.dumps(
        ordered_rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    objective_count = int(localization.get("objective_route_obligation_count") or 0)
    residual_count = int(localization.get("semantic_residual_obligation_count") or 0)
    if objective_count + residual_count != len(required):
        raise RuntimeError("SCIENCE_RAW_TASK_PROMPT_SUMMARY_PARTITION_INVALID")

    return {
        "schema": "PROJECT_BRAIN_SCIENCE_RAW_TASK_PLANNER_MANIFEST_SUMMARY_V1",
        "task_contract_sha256": contract.get("task_contract_sha256"),
        "required_obligation_count": len(required),
        "objective_route_obligation_count": objective_count,
        "semantic_residual_obligation_count": residual_count,
        "ordered_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_task_sha256": contract.get("task_sha256"),
        "raw_goal_is_authoritative_planner_semantic_source": True,
        "brain_retains_full_per_obligation_acceptance_contract": True,
        "every_original_obligation_still_requires_independent_acceptance": True,
        "planner_acceptance_or_finish_authority": False,
        "individual_content_address_rows_omitted_from_prompt_metadata_only": True,
    }

def _nonempty_strings(value: Any, *, maximum: int, field: str) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > maximum:
        raise RuntimeError(f"SCIENCE_{field}_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RuntimeError(f"SCIENCE_{field}_INVALID")
        s = item.strip()
        if s in out:
            raise RuntimeError(f"SCIENCE_{field}_DUPLICATE")
        out.append(s)
    return out

def _candidate_timeout(value: Any, *, default: int, maximum: int, field: str) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise RuntimeError(f"SCIENCE_{field}_INVALID")
    return value


def _candidate_rows(raw: Any, requirements: set[str]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw or len(raw) > MAX_CANDIDATES:
        raise RuntimeError("SCIENCE_CANDIDATES_INVALID")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise RuntimeError("SCIENCE_CANDIDATE_INVALID")
        aid = str(item.get("action_id") or "").strip()
        if not aid or aid in ids:
            raise RuntimeError("SCIENCE_ACTION_ID_INVALID_OR_DUPLICATE")
        ids.add(aid)
        covers = _nonempty_strings(item.get("covers"), maximum=MAX_REQUIREMENTS, field="COVERS")
        if not set(covers).issubset(requirements):
            raise RuntimeError("SCIENCE_COVERAGE_OUTSIDE_CONTRACT")
        depends_on_raw = item.get("depends_on") or []
        if not isinstance(depends_on_raw, list) or len(depends_on_raw) > MAX_CANDIDATES:
            raise RuntimeError("SCIENCE_DEPENDS_ON_INVALID")
        depends_on: list[str] = []
        for dep in depends_on_raw:
            dep = str(dep or "").strip()
            if not dep or dep == aid or dep in depends_on:
                raise RuntimeError("SCIENCE_DEPENDS_ON_INVALID")
            depends_on.append(dep)
        command = validate_environment_command(item.get("command"))
        verify_command = validate_environment_command(item.get("verify_command"))
        rows.append({
            "action_id": aid,
            "covers": covers,
            "depends_on": depends_on,
            "timeout_sec": _candidate_timeout(
                item.get("timeout_sec"),
                default=DEFAULT_ACTION_TIMEOUT_S,
                maximum=MAX_ACTION_TIMEOUT_S,
                field="ACTION_TIMEOUT",
            ),
            "verify_timeout_sec": _candidate_timeout(
                item.get("verify_timeout_sec"),
                default=DEFAULT_VERIFY_TIMEOUT_S,
                maximum=MAX_VERIFY_TIMEOUT_S,
                field="VERIFY_TIMEOUT",
            ),
            "command": command,
            "verify_command": verify_command,
        })
    for row in rows:
        if not set(row["depends_on"]).issubset(ids):
            raise RuntimeError("SCIENCE_DEPENDS_ON_UNKNOWN_ACTION")
    return rows

def _extract_contract(raw: dict[str, Any], prior_requirements: list[str] | None, mandatory_requirements: list[str] | None = None) -> tuple[list[str], list[dict[str, Any]], str | None]:
    mandatory = list(mandatory_requirements or [])
    if len(mandatory) > MAX_REQUIREMENTS:
        raise RuntimeError("SCIENCE_MANDATORY_REQUIREMENTS_OVERFLOW")
    if prior_requirements is None:
        requirements = _nonempty_strings(
            raw.get("material_requirements"),
            maximum=MAX_REQUIREMENTS,
            field="MATERIAL_REQUIREMENTS",
        )
        for requirement_id in mandatory:
            if requirement_id not in requirements:
                requirements.append(requirement_id)
        if len(requirements) > MAX_REQUIREMENTS:
            raise RuntimeError("SCIENCE_REQUIREMENTS_WITH_MANDATORY_OVERFLOW")
    else:
        requirements = list(prior_requirements)
        if "material_requirements" in raw:
            repeated = _nonempty_strings(
                raw.get("material_requirements"),
                maximum=MAX_REQUIREMENTS,
                field="MATERIAL_REQUIREMENTS",
            )
            for requirement_id in mandatory:
                if requirement_id not in repeated:
                    repeated.append(requirement_id)
            if repeated != requirements:
                raise RuntimeError("SCIENCE_REQUIREMENTS_MUTATED_AFTER_FREEZE")
    summary = raw.get("finish_summary")
    if summary is not None:
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("SCIENCE_FINISH_SUMMARY_INVALID")
        summary = summary.strip()
    candidates = []
    primary_candidates = raw.get("candidates")
    alias_candidates = raw.get("candidate_actions")
    if primary_candidates is not None and alias_candidates is not None and primary_candidates != alias_candidates:
        raise RuntimeError("SCIENCE_CANDIDATE_ALIAS_CONFLICT")
    candidate_rows = primary_candidates if primary_candidates is not None else alias_candidates
    if candidate_rows is not None:
        candidates = _candidate_rows(candidate_rows, set(requirements))
    return requirements, candidates, summary

async def run_science_goal(goal: str, environment: BaseEnvironment, *, max_cycles: int = 8) -> dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("SCIENCE_GOAL_REQUIRED")
    max_cycles = max(1, min(int(max_cycles), MAX_CYCLES))
    raw_task_contract, raw_task_localization, raw_task_obligations = _compile_lossless_task_scope(goal)
    raw_task_prompt_summary = _planner_raw_task_manifest_summary(
        goal, raw_task_contract, raw_task_localization, raw_task_obligations
    )
    brain_deliverables = _brain_mandated_deliverables(goal)
    mandatory_requirement_ids = list(brain_deliverables)
    requirements: list[str] | None = None
    resolved: set[str] = set()
    declared_inputs, declared_outputs = _declared_task_paths(goal)
    observations: list[dict[str, Any]] = await _snapshot_declared_inputs(
        environment, declared_inputs
    )
    trace: list[dict[str, Any]] = []

    for cycle in range(max_cycles):
        unresolved = [] if requirements is None else sorted(set(requirements) - resolved)
        output_gate_failures: list[dict[str, Any]] = []
        if requirements is not None and not unresolved and declared_outputs:
            output_gate_failures = await _declared_output_gate(
                environment, declared_outputs
            )
        prompt = (
            "You are an OPTIONAL semantic proposal source inside Project Brain, not execution authority. "
            "Return one structured proposal object only. Project Brain owns action selection, command policy, verification, "
            "requirement-state updates, and finish authority. No network acquisition, package installation, "
            "git fetch/clone/pull, secrets, or host escape. "
            "On the first cycle provide material_requirements (1-16 stable short IDs). "
            "Provide 1-4 candidate actions as {action_id,covers,depends_on?,timeout_sec?,verify_timeout_sec?,command,verify_command}. "
            "Use depends_on only for true within-proposal sequencing. covers must name only frozen material_requirements. "
            "Brain may execute multiple nonredundant candidates from one proposal, but promotes each claimed effect only "
            "after its independent verify_command succeeds. Brain alone decides completion after "
            "independent verification resolves every frozen material requirement. finish_summary is optional "
            "descriptive metadata only and never execution or finish authority. "
            f"Goal: {goal}\nFrozen requirements: {requirements!r}\nUnresolved: {unresolved!r}\n"
            "Brain lossless raw-task acceptance manifest summary (non-droppable; exact task semantics are the Goal text above): "
            + json.dumps(raw_task_prompt_summary, sort_keys=True)
            + "\nEvery original raw obligation remains separately acceptance-pending in Brain state until exact candidate-bound independent acceptance exists. "
            "The optional planner has no acceptance or finish authority; omitted per-obligation IDs/hashes are metadata only.\n"
            "Brain-declared authoritative local inputs: "
            + json.dumps(declared_inputs, sort_keys=True)
            + "\nBrain-mandated explicit deliverables (requirement ID -> path): "
            + json.dumps(brain_deliverables, sort_keys=True)
            + "\nThe BRAIN_DECLARED_INPUT_SNAPSHOT observations below are exact local task-source reads. "
            "Use those bytes instead of guessing plant parameters, interfaces, scenarios, or other declared source facts. "
            "These Brain-mandated requirement IDs are part of the frozen contract and may not be omitted. "
            "A candidate claiming one of them must actually create that exact nonempty file; Brain validates it independently.\n"
            "Recent observations: " + json.dumps(observations[-8:], sort_keys=True)[:30000]
        )
        planned = science_planner.plan(prompt, timeout_s=PLANNER_TIMEOUT_S)
        raw = science_planner.normalize_proposal_object(
            science_planner.extract_json_object(planned.get("text", ""))
        )
        if not isinstance(raw, dict):
            raise RuntimeError("SCIENCE_PLANNER_OBJECT_REQUIRED")
        requirements, candidates, finish_summary = _extract_contract(raw, requirements, mandatory_requirement_ids)
        unresolved_set = set(requirements) - resolved

        if finish_summary is not None:
            if unresolved_set:
                rejected = {
                    "cycle": cycle,
                    "kind": "FINISH_REJECTED",
                    "reason": "UNRESOLVED_MATERIAL_REQUIREMENTS",
                    "unresolved": sorted(unresolved_set),
                }
                trace.append(rejected)
                observations.append(rejected)
                # A premature finish request is metadata only. It must not suppress
                # otherwise admissible candidate actions in the same proposal.
            elif output_gate_failures:
                rejected = {
                    "cycle": cycle,
                    "kind": "FINISH_REJECTED",
                    "reason": "BRAIN_DECLARED_OUTPUT_GATE_FAILED",
                    "failures": output_gate_failures,
                }
                trace.append(rejected)
                observations.append(rejected)
            else:
                return {
                    "schema": SCHEMA,
                    "status": "SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER",
                    "controller_mode": "BRAIN_OWNED_RESEARCH_CONTROL__OPTIONAL_GENERAL_COGNITION_SUBSTRATE",
                    "model_has_terminal_authority": False,
                    "task_completion_claimed": False,
                    "finish_authority": "RAW_TASK_ACCEPTANCE_V1_REQUIRED",
                    "raw_task_contract_sha256": raw_task_contract.get("task_contract_sha256"),
                    "raw_task_required_obligation_count": len(raw_task_obligations),
                    "raw_task_prompt_manifest_sha256": raw_task_prompt_summary["ordered_manifest_sha256"],
                    "raw_task_objective_route_obligation_count": raw_task_localization.get("objective_route_obligation_count"),
                    "raw_task_semantic_residual_obligation_count": raw_task_localization.get("semantic_residual_obligation_count"),
                    "raw_task_acceptance_receipts_present": False,
                    "material_requirements": requirements,
                    "brain_mandated_deliverables": brain_deliverables,
                    "resolved_requirements": sorted(resolved),
                    "cycles": cycle + 1,
                    "trace": trace,
                    "summary": finish_summary,
                    "planner_model_last": planned.get("model"),
                }

        if not candidates:
            rejected = {"cycle": cycle, "kind": "NO_CANDIDATES", "unresolved": sorted(unresolved_set)}
            trace.append(rejected)
            observations.append(rejected)
            continue

        # Candidate coverage is substrate-proposed metadata, not a verified semantic fact.
        # Brain may execute several nonredundant candidates from one proposal, but
        # every promotion remains independently verified and dependency-gated.
        transport = HarborEnvironmentTransport(environment)
        executed_action_ids: set[str] = set()
        verified_action_ids: set[str] = set()
        executed_any = False

        while True:
            unresolved_set = set(requirements) - resolved
            current_output_failures: list[dict[str, Any]] = []
            if not unresolved_set and declared_outputs:
                current_output_failures = await _declared_output_gate(
                    environment, declared_outputs
                )
                if not current_output_failures:
                    break

            scored = []
            for row in candidates:
                if row["action_id"] in executed_action_ids:
                    continue
                if not set(row["depends_on"]).issubset(verified_action_ids):
                    continue
                new = len(set(row["covers"]) & unresolved_set)
                if new or (not unresolved_set and bool(current_output_failures)):
                    scored.append((-new, row["action_id"], row))
            if not scored:
                break

            scored.sort(key=lambda x:(x[0],x[1]))
            chosen = scored[0][2]
            executed_action_ids.add(chosen["action_id"])
            executed_any = True

            action_receipt = await transport.exec(
                chosen["command"], timeout_sec=chosen["timeout_sec"]
            )
            action_observed = {
                "returncode": action_receipt.returncode,
                "stdout": action_receipt.stdout[-MAX_OUTPUT_CHARS:],
                "stderr": action_receipt.stderr[-MAX_OUTPUT_CHARS:],
            }
            verify_observed = None
            verified = False
            verified_covers: list[str] = []
            deliverable_checks: list[dict[str, Any]] = []
            action_transport_clean = _action_transport_clean(
                action_receipt.returncode, action_receipt.stdout, action_receipt.stderr
            )
            if action_transport_clean:
                verify_receipt = await transport.exec(
                    chosen["verify_command"],
                    timeout_sec=chosen["verify_timeout_sec"],
                )
                verify_observed = {
                    "returncode": verify_receipt.returncode,
                    "stdout": verify_receipt.stdout[-MAX_OUTPUT_CHARS:],
                    "stderr": verify_receipt.stderr[-MAX_OUTPUT_CHARS:],
                }
                if verify_receipt.returncode == 0:
                    for requirement_id in chosen["covers"]:
                        path = brain_deliverables.get(requirement_id)
                        if path is None:
                            verified_covers.append(requirement_id)
                            continue
                        check = await _validate_brain_deliverable(requirement_id, path, environment)
                        deliverable_checks.append(check)
                        if check["verified"] is True:
                            verified_covers.append(requirement_id)
                    resolved.update(verified_covers)
                    verified = len(verified_covers) == len(chosen["covers"])
                    if verified:
                        verified_action_ids.add(chosen["action_id"])

            record = {
                "cycle": cycle,
                "kind": "BRAIN_SELECTED_RESEARCH_ACTION",
                "action_id": chosen["action_id"],
                "covers": chosen["covers"],
                "depends_on": chosen["depends_on"],
                "action_timeout_sec": chosen["timeout_sec"],
                "verify_timeout_sec": chosen["verify_timeout_sec"],
                "selection_reason": "MAX_DECLARED_UNRESOLVED_COVERAGE_THEN_ACTION_ID__DEPENDENCY_GATED__STRUCTURAL_CONTROL_ONLY",
                "action_result": action_observed,
                "action_transport_clean": action_transport_clean,
                "verify_result": verify_observed,
                "verified_covers": verified_covers,
                "brain_deliverable_checks": deliverable_checks,
                "coverage_promoted": verified,
            }
            trace.append(record)
            observations.append(record)

        if not executed_any:
            blocked = {
                "cycle": cycle,
                "kind": "BRAIN_RESEARCH_SELECTION_BLOCKED",
                "reason": "NO_DEPENDENCY_SATISFIED_NONREDUNDANT_PROPOSAL_COVERS_CURRENT_RESIDUAL",
                "unresolved": sorted(set(requirements) - resolved),
            }
            trace.append(blocked)
            observations.append(blocked)
            continue

        # Completion is a deterministic consequence of Brain-owned verified state.
        # Do not spend another cognition turn asking the substrate to notice that
        # all requirements are already resolved.
        if requirements is not None and not (set(requirements) - resolved):
            post_gate_failures = await _declared_output_gate(
                environment, declared_outputs
            )
            if post_gate_failures:
                rejected = {
                    "cycle": cycle,
                    "kind": "BRAIN_DECLARED_OUTPUT_GATE_FAILED",
                    "reason": "MANDATORY_TASK_OUTPUT_MISSING_OR_INVALID",
                    "failures": post_gate_failures,
                }
                trace.append(rejected)
                observations.append(rejected)
                continue
            return {
                "schema": SCHEMA,
                "status": "SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER",
                "controller_mode": "BRAIN_OWNED_RESEARCH_CONTROL__OPTIONAL_GENERAL_COGNITION_SUBSTRATE",
                "model_has_terminal_authority": False,
                "task_completion_claimed": False,
                "finish_authority": "RAW_TASK_ACCEPTANCE_V1_REQUIRED",
                "raw_task_contract_sha256": raw_task_contract.get("task_contract_sha256"),
                "raw_task_required_obligation_count": len(raw_task_obligations),
                "raw_task_prompt_manifest_sha256": raw_task_prompt_summary["ordered_manifest_sha256"],
                "raw_task_objective_route_obligation_count": raw_task_localization.get("objective_route_obligation_count"),
                "raw_task_semantic_residual_obligation_count": raw_task_localization.get("semantic_residual_obligation_count"),
                "raw_task_acceptance_receipts_present": False,
                "material_requirements": requirements,
                "brain_mandated_deliverables": brain_deliverables,
                "resolved_requirements": sorted(resolved),
                "cycles": cycle + 1,
                "trace": trace,
                "summary": "Brain verified routing state and declared outputs; exact raw-task acceptance remains external-verifier pending.",
                "planner_model_last": planned.get("model"),
            }

    return {
        "schema": SCHEMA,
        "status": "BLOCKED_MAX_CYCLES_NO_BRAIN_AUTHORIZED_FINISH",
        "controller_mode": "BRAIN_OWNED_RESEARCH_CONTROL__OPTIONAL_GENERAL_COGNITION_SUBSTRATE",
        "model_has_terminal_authority": False,
        "material_requirements": requirements or [],
        "brain_mandated_deliverables": brain_deliverables,
        "resolved_requirements": sorted(resolved),
        "cycles": max_cycles,
        "trace": trace,
        "task_completion_claimed": False,
        "finish_authority": "RAW_TASK_ACCEPTANCE_V1_REQUIRED",
        "raw_task_contract_sha256": raw_task_contract.get("task_contract_sha256"),
        "raw_task_required_obligation_count": len(raw_task_obligations),
        "raw_task_prompt_manifest_sha256": raw_task_prompt_summary["ordered_manifest_sha256"],
        "raw_task_acceptance_receipts_present": False,
        "summary": "",
    }

class HarborScienceAgent(BaseAgent):
    capabilities = AgentCapabilities()

    @staticmethod
    def name() -> str:
        return "project-brain-science"

    def version(self) -> str:
        return "1.2.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        result = await run_science_goal(instruction, environment)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "project_brain_science_trace.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if hasattr(context, "cost_usd"):
            context.cost_usd = 0.0
