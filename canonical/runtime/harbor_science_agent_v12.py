"""Brain-owned Harbor research controller with durable causal journaling and exact-request planner transport recovery.

The cognition substrate may propose a bounded research contract and candidate shell
actions. Brain owns command admissibility, candidate selection, verification,
coverage state, and finish authority. No benchmark-specific task content lives here.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shlex
from typing import Any

from canonical.runtime import harbor_science_planner_v6 as science_planner
from canonical.runtime import science_typed_action_protocol_v2 as typed_action
from canonical.runtime.harbor_science_evidence_store_v1 import EvidenceStore
from canonical.runtime.harbor_command_policy import validate_environment_command
from canonical.runtime.harbor_environment_transport_v2 import (
    HarborEnvironmentTransport,
    HarborTransportUncertainError,
)
from execution_guard import terminal_agent_start_barrier_v1 as start_barrier
from execution_guard import terminal_causal_journal_filebridge_v2 as causal_bridge
from execution_guard.logical_attempt_identity_v1 import logical_attempt_id as canonical_logical_attempt_id
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

SCHEMA = "PROJECT_BRAIN_HARBOR_SCIENCE_AGENT_TRACE_V12"
MAX_CYCLES = 12
MAX_REQUIREMENTS = 16
MAX_CANDIDATES = 8
MAX_OUTPUT_CHARS = 16000
PLANNER_TIMEOUT_S = 300
DEFAULT_ACTION_TIMEOUT_S = 1800
MAX_ACTION_TIMEOUT_S = 3600
DEFAULT_VERIFY_TIMEOUT_S = 600
MAX_VERIFY_TIMEOUT_S = 3600
MAX_PLANNER_EVIDENCE_STRING_CHARS = 1024
MAX_PLANNER_EVIDENCE_OBSERVATIONS = 8
POST_FREEZE_STATE_RESERVE_TOKENS = 512
POST_FREEZE_STATE_RESERVE_DIGITS = "0" * POST_FREEZE_STATE_RESERVE_TOKENS
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_-]+$")

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
        (?:(?:a|the)\s+)?
        (?:(?:file|artifact|output|result)\s+)?
        (?:(?:named|called)\s+)?
        [`'"\[]*
        (?P<path>/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)
    """,
    re.VERBOSE,
)

def _valid_mandated_output_path(path: str) -> bool:
    if not path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")[1:]):
        return False
    return bool(re.fullmatch(r"/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+", path))

def _authoritative_artifacts_from_env() -> list[str]:
    raw = os.environ.get("BRAIN_TASK_ARTIFACTS_JSON")
    if raw is None or not raw.strip():
        return []
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise RuntimeError("SCIENCE_TASK_ARTIFACTS_JSON_INVALID") from exc
    rows = typed_action.normalize_authoritative_artifacts(value)
    return [row["path"] for row in rows]


def _brain_mandated_deliverables(
    goal: str,
    authoritative_artifacts: list[str] | None = None,
) -> dict[str, str]:
    text = str(goal or "")
    paths: list[str] = []

    def add(path: str) -> None:
        if not _valid_mandated_output_path(path):
            return
        if path not in paths and len(paths) < MAX_BRAIN_DELIVERABLES:
            paths.append(path)

    for row in typed_action.normalize_authoritative_artifacts(authoritative_artifacts or []):
        add(row["path"])

    for match in _EXPLICIT_SUBMISSION_PATH_RE.finditer(text):
        raw = match.group(1)
        add(raw if raw.startswith("/app/") else "/app/" + raw.lstrip("/"))

    # A task can require an artifact anywhere, not only under /app/submission.
    # Bind only absolute file paths that are syntactically attached to an
    # explicit output-producing directive; ordinary input references remain inputs.
    for match in _EXPLICIT_OUTPUT_DIRECTIVE_RE.finditer(text):
        add(match.group("path"))

    return {f"BD{i + 1:02d}": path for i, path in enumerate(paths)}

async def _validate_brain_deliverable(
    requirement_id: str,
    path: str,
    environment: BaseEnvironment,
) -> dict[str, Any]:
    transport = HarborEnvironmentTransport(environment)
    fmt = typed_action.inferred_format_from_path(path)
    command = typed_action.authoritative_deliverable_check_command({"path": path, "format": fmt})
    receipt = await transport.exec(command, timeout_sec=60)
    observed = [{
        "command": command,
        "format": fmt,
        "returncode": receipt.returncode,
        "stdout": receipt.stdout[-MAX_OUTPUT_CHARS:],
        "stderr": receipt.stderr[-MAX_OUTPUT_CHARS:],
    }]
    return {
        "requirement_id": requirement_id,
        "path": path,
        "format": fmt,
        "verified": receipt.returncode == 0,
        "checks": observed,
    }

MAX_DECLARED_INPUT_TOTAL_CHARS = 24000
MAX_DECLARED_INPUT_PER_FILE_CHARS = 8000
_EXPLICIT_SPEC_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])(/app/spec/[A-Za-z0-9_./-]+)"
)

def _declared_task_paths(
    goal: str,
    authoritative_artifacts: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Return explicit task-authoritative inputs and mandatory submission outputs."""
    inputs: list[str] = []
    for match in _EXPLICIT_SPEC_PATH_RE.finditer(str(goal or "")):
        path = match.group(1).rstrip(".,;:")
        if any(part in {".", ".."} for part in path.split("/")):
            continue
        if path not in inputs:
            inputs.append(path)
    outputs = list(_brain_mandated_deliverables(goal, authoritative_artifacts).values())
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

async def _discover_source_contract_catalog(
    environment: BaseEnvironment,
) -> list[dict[str, Any]]:
    """Read-only bounded local JSON schema discovery under /app.

    Only top-level key names/types and literal output-like scalar paths are
    surfaced. The catalog is evidence, never semantic or finish authority.
    """
    script = """from pathlib import Path
import json
rows=[]
for p in sorted(Path('/app').rglob('*.json'))[:64]:
    try:
        if not p.is_file() or p.stat().st_size > 1048576:
            continue
        d=json.load(open(p,'r',encoding='utf-8'))
        if not isinstance(d,dict):
            continue
        selected={}
        for k in ('output','output_path','result_path','submission_path'):
            v=d.get(k)
            if isinstance(v,str) and len(v)<=512:
                selected[k]=v
        rows.append({'path':str(p),'keys':sorted(str(k) for k in d.keys())[:128],
                     'types':{str(k):type(v).__name__ for k,v in sorted(d.items(),key=lambda kv:str(kv[0]))[:128]},
                     'selected_scalars':selected})
    except Exception:
        continue
print(json.dumps(rows,sort_keys=True,separators=(',',':')))
"""
    command = validate_environment_command("python -c " + shlex.quote(script))
    receipt = await HarborEnvironmentTransport(environment).exec(command, timeout_sec=60)
    if receipt.returncode != 0:
        return []
    try:
        value = json.loads(str(receipt.stdout or ""))
    except Exception:
        return []
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, dict)][:64]


async def _probe_schema_requirements(
    requirements: list[dict[str, Any]],
    environment: BaseEnvironment,
) -> tuple[bool, list[dict[str, Any]]]:
    transport = HarborEnvironmentTransport(environment)
    checks: list[dict[str, Any]] = []
    for row in requirements:
        command = typed_action.schema_probe_command(row)
        receipt = await transport.exec(command, timeout_sec=60)
        observed = {
            "path": row["path"],
            "format": row["format"],
            "keys": list(row["keys"]),
            "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
            "returncode": receipt.returncode,
            "stdout": str(receipt.stdout or "")[-2000:],
            "stderr": str(receipt.stderr or "")[-2000:],
        }
        checks.append(observed)
        if receipt.returncode != 0:
            return False, checks
    return True, checks


async def _validate_candidate_deliverables(
    deliverables: list[dict[str, str]],
    environment: BaseEnvironment,
) -> tuple[bool, list[dict[str, Any]]]:
    if not deliverables:
        return True, []
    transport = HarborEnvironmentTransport(environment)
    checks: list[dict[str, Any]] = []
    for row in deliverables:
        command = typed_action.deliverable_check_command(row)
        receipt = await transport.exec(command, timeout_sec=60)
        observed = {
            "path": row["path"],
            "format": row["format"],
            "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
            "returncode": receipt.returncode,
            "stdout": str(receipt.stdout or "")[-2000:],
            "stderr": str(receipt.stderr or "")[-2000:],
            "verified": receipt.returncode == 0,
        }
        checks.append(observed)
        if receipt.returncode != 0:
            return False, checks
    return True, checks


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
        fmt = typed_action.inferred_format_from_path(path)
        command = typed_action.authoritative_deliverable_check_command({"path": path, "format": fmt})
        receipt = await transport.exec(command, timeout_sec=60)
        if receipt.returncode != 0:
            failures.append({
                "path": path,
                "format": fmt,
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
        if (
            len(s) > science_planner.MAX_REQUIREMENT_ID_CHARS
            or _IDENTIFIER_RE.fullmatch(s) is None
        ):
            raise RuntimeError(f"SCIENCE_{field}_IDENTIFIER_INVALID")
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


def _candidate_rows(
    raw: Any,
    requirements: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse untrusted optional candidate metadata fail-closed, candidate by candidate.

    The frozen Brain requirement set is authoritative. A malformed candidate is
    evidence about the optional proposal substrate, not authority to mutate the
    contract and not a reason to abort otherwise admissible candidates.
    """
    if not isinstance(raw, list) or not raw or len(raw) > MAX_CANDIDATES:
        raise RuntimeError("SCIENCE_CANDIDATES_INVALID")

    rows: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def reject(
        *,
        index: int,
        action_id: str | None,
        reason: str,
        **details: Any,
    ) -> None:
        row: dict[str, Any] = {
            "kind": "PLANNER_CANDIDATE_REJECTED",
            "candidate_index": index,
            "action_id": action_id,
            "reason": reason,
            "executable": False,
            "promotable": False,
        }
        row.update(details)
        rejections.append(row)

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            reject(index=index, action_id=None, reason="CANDIDATE_NOT_OBJECT")
            continue

        aid = str(item.get("action_id") or "").strip()
        if (
            not aid
            or aid in seen_ids
            or len(aid) > science_planner.MAX_ACTION_ID_CHARS
            or _IDENTIFIER_RE.fullmatch(aid) is None
        ):
            reject(
                index=index,
                action_id=aid or None,
                reason="ACTION_ID_INVALID_OR_DUPLICATE",
            )
            continue
        seen_ids.add(aid)

        try:
            covers = _nonempty_strings(
                item.get("covers"),
                maximum=MAX_REQUIREMENTS,
                field="COVERS",
            )
        except (RuntimeError, ValueError) as exc:
            reject(
                index=index,
                action_id=aid,
                reason="COVERS_INVALID",
                error_type=type(exc).__name__,
                error_sha256=hashlib.sha256(
                    str(exc).encode("utf-8", "replace")
                ).hexdigest(),
            )
            continue

        unknown_covers = sorted(set(covers) - requirements)
        if unknown_covers:
            reject(
                index=index,
                action_id=aid,
                reason="COVERAGE_OUTSIDE_FROZEN_CONTRACT",
                covers=list(covers),
                unknown_covers=unknown_covers,
            )
            continue

        depends_on_raw = item.get("depends_on") or []
        if not isinstance(depends_on_raw, list) or len(depends_on_raw) > MAX_CANDIDATES:
            reject(
                index=index,
                action_id=aid,
                reason="DEPENDS_ON_INVALID",
            )
            continue

        depends_on: list[str] = []
        dependency_invalid = False
        for dep_raw in depends_on_raw:
            dep = str(dep_raw or "").strip()
            if (
                not dep
                or dep == aid
                or dep in depends_on
                or len(dep) > science_planner.MAX_ACTION_ID_CHARS
                or _IDENTIFIER_RE.fullmatch(dep) is None
            ):
                dependency_invalid = True
                break
            depends_on.append(dep)
        if dependency_invalid:
            reject(
                index=index,
                action_id=aid,
                reason="DEPENDS_ON_INVALID",
            )
            continue

        try:
            schema_requirements = typed_action.normalize_schema_requirements(
                item.get("schema_requirements")
            )
            deliverables = typed_action.normalize_deliverables(item.get("deliverables"))
            executor = str(item.get("executor") or "").strip().lower()
            verify_executor = str(item.get("verify_executor") or "").strip().lower()
            command_source = item.get("command")
            verify_source = item.get("verify_command")
            command, command_literal_keys = typed_action.compile_typed_source(
                executor,
                command_source,
                schema_requirements=schema_requirements,
            )
            verify_command, verify_literal_keys = typed_action.compile_typed_source(
                verify_executor,
                verify_source,
                schema_requirements=schema_requirements,
            )
            timeout_sec = _candidate_timeout(
                item.get("timeout_sec"),
                default=DEFAULT_ACTION_TIMEOUT_S,
                maximum=MAX_ACTION_TIMEOUT_S,
                field="ACTION_TIMEOUT",
            )
            verify_timeout_sec = _candidate_timeout(
                item.get("verify_timeout_sec"),
                default=DEFAULT_VERIFY_TIMEOUT_S,
                maximum=MAX_VERIFY_TIMEOUT_S,
                field="VERIFY_TIMEOUT",
            )
        except (RuntimeError, ValueError) as exc:
            reject(
                index=index,
                action_id=aid,
                reason="CANDIDATE_FIELD_OR_COMMAND_INVALID",
                error_type=type(exc).__name__,
                error_sha256=hashlib.sha256(
                    str(exc).encode("utf-8", "replace")
                ).hexdigest(),
            )
            continue

        normalized_row = {
            "action_id": aid,
            "covers": covers,
            "depends_on": depends_on,
            "timeout_sec": timeout_sec,
            "verify_timeout_sec": verify_timeout_sec,
            "executor": executor,
            "command_source": str(command_source),
            "command": command,
            "command_literal_schema_keys": sorted(command_literal_keys),
            "verify_executor": verify_executor,
            "verify_source": str(verify_source),
            "verify_command": verify_command,
            "verify_literal_schema_keys": sorted(verify_literal_keys),
            "schema_requirements": schema_requirements,
            "deliverables": deliverables,
            "_candidate_index": index,
        }
        normalized_row["action_fingerprint_sha256"] = typed_action.action_fingerprint(
            normalized_row
        )
        normalized_row["effect_fingerprint_sha256"] = typed_action.effect_fingerprint(
            executor, command
        )
        rows.append(normalized_row)

    # Dependency validity is defined over the candidates that survived all
    # candidate-local validation. Reject transitively instead of letting one
    # bad candidate recreate a proposal-wide fatal error through depends_on.
    while True:
        accepted_ids = {row["action_id"] for row in rows}
        invalid_rows = [
            row for row in rows
            if not set(row["depends_on"]).issubset(accepted_ids)
        ]
        if not invalid_rows:
            break
        invalid_ids = {row["action_id"] for row in invalid_rows}
        kept: list[dict[str, Any]] = []
        for row in rows:
            if row["action_id"] not in invalid_ids:
                kept.append(row)
                continue
            missing = sorted(set(row["depends_on"]) - accepted_ids)
            reject(
                index=int(row.pop("_candidate_index")),
                action_id=str(row["action_id"]),
                reason="DEPENDS_ON_REJECTED_OR_UNKNOWN_ACTION",
                depends_on=list(row["depends_on"]),
                unavailable_dependencies=missing,
            )
        rows = kept

    for row in rows:
        row.pop("_candidate_index", None)
    rejections.sort(key=lambda row: int(row["candidate_index"]))
    return rows, rejections

def _extract_contract(
    raw: dict[str, Any],
    prior_requirements: list[str] | None,
    mandatory_requirements: list[str] | None = None,
) -> tuple[list[str], list[dict[str, Any]], str | None, list[dict[str, Any]]]:
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
        # Brain owns the requirement set after the first successful freeze.
        # Later substrate material_requirements are non-authoritative metadata:
        # they cannot add, remove, reorder, or fatal-abort Brain requirements.
        requirements = list(prior_requirements)

    summary = raw.get("finish_summary")
    if summary is not None:
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("SCIENCE_FINISH_SUMMARY_INVALID")
        summary = summary.strip()

    candidates: list[dict[str, Any]] = []
    candidate_rejections: list[dict[str, Any]] = []
    primary_candidates = raw.get("candidates")
    alias_candidates = raw.get("candidate_actions")
    if (
        primary_candidates is not None
        and alias_candidates is not None
        and primary_candidates != alias_candidates
    ):
        raise RuntimeError("SCIENCE_CANDIDATE_ALIAS_CONFLICT")

    candidate_rows = (
        primary_candidates if primary_candidates is not None else alias_candidates
    )
    if candidate_rows is not None:
        candidates, candidate_rejections = _candidate_rows(
            candidate_rows,
            set(requirements),
        )
    return requirements, candidates, summary, candidate_rejections

def logical_attempt_id_for_goal(goal: str) -> str:
    """Return the one authorized attempt identity; goal text is never identity material."""
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("SCIENCE_GOAL_REQUIRED")
    slot_id = str(os.environ.get("BRAIN_SLOT_ID") or "").strip()
    task_digest = str(os.environ.get("BRAIN_TASK_DIGEST") or "").strip()
    carried = str(os.environ.get("BRAIN_LOGICAL_ATTEMPT_ID") or "").strip()
    if not slot_id:
        raise RuntimeError("BRAIN_SLOT_ID_REQUIRED")
    if not task_digest:
        raise RuntimeError("BRAIN_TASK_DIGEST_REQUIRED")
    if not carried:
        raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_REQUIRED")
    expected = canonical_logical_attempt_id(slot_id=slot_id, task_digest=task_digest)
    if carried != expected:
        raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH")
    return carried


def _compact_planner_value(value: Any) -> Any:
    """Bound planner-facing evidence while preserving full trace elsewhere."""
    if isinstance(value, str):
        if len(value) <= MAX_PLANNER_EVIDENCE_STRING_CHARS:
            return value
        raw = value.encode("utf-8", "replace")
        return {
            "kind": "BRAIN_TRUNCATED_EVIDENCE_TEXT",
            "original_chars": len(value),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "tail": value[-MAX_PLANNER_EVIDENCE_STRING_CHARS:],
        }
    if isinstance(value, list):
        return [_compact_planner_value(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _compact_planner_value(v) for k, v in value.items()}
    return value


def build_fitting_science_planner_prompt(
    *,
    goal: str,
    requirements: list[str] | None,
    unresolved: list[str],
    raw_task_prompt_summary: dict[str, Any],
    declared_inputs: list[str],
    brain_deliverables: dict[str, str],
    observations: list[dict[str, Any]],
    evidence_directory: list[dict[str, Any]],
    requested_evidence: list[dict[str, Any]],
    logical_attempt_id: str,
    cycle: int,
) -> tuple[str, dict[str, int]]:
    """Build an exact-token-fit prompt with lossless evidence virtualization."""
    directory_observation = {
        "kind": "BRAIN_EVIDENCE_DIRECTORY",
        "entry_count": len(evidence_directory),
        "entries": evidence_directory,
        "retrieval": (
            "Use evidence_requests with exact evidence_id and chunk_index. "
            "Omission from active context does not delete evidence."
        ),
    }
    fixed_evidence = [directory_observation] + list(requested_evidence)
    common = dict(
        goal=goal,
        requirements=requirements,
        unresolved=unresolved,
        raw_task_prompt_summary=raw_task_prompt_summary,
        declared_inputs=declared_inputs,
        brain_deliverables=brain_deliverables,
    )
    base_prompt = build_science_planner_prompt(**common, observations=fixed_evidence)
    base_payload, _ = science_planner.build_request_payload(
        base_prompt, logical_attempt_id=logical_attempt_id, cycle=cycle
    )
    base_tokens = science_planner.count_input_tokens(base_payload)
    if base_tokens + science_planner.MAX_TOOL_COMPLETION_TOKENS > science_planner.SERVER_CONTEXT_TOKENS:
        raise RuntimeError(
            "SCIENCE_PLANNER_BASE_CONTEXT_ENVELOPE_EXCEEDED:"
            f"{base_tokens}+{science_planner.MAX_TOOL_COMPLETION_TOKENS}>"
            f"{science_planner.SERVER_CONTEXT_TOKENS}"
        )

    recent_frontier: list[dict[str, Any]] = []
    considered = list(observations[-MAX_PLANNER_EVIDENCE_OBSERVATIONS:])
    for row in reversed(considered):
        candidate_recent = [_compact_planner_value(row)] + recent_frontier
        prompt = build_science_planner_prompt(
            **common,
            observations=fixed_evidence + candidate_recent,
        )
        payload, _ = science_planner.build_request_payload(
            prompt, logical_attempt_id=logical_attempt_id, cycle=cycle
        )
        tokens = science_planner.count_input_tokens(payload)
        if tokens + science_planner.MAX_TOOL_COMPLETION_TOKENS > science_planner.SERVER_CONTEXT_TOKENS:
            continue
        recent_frontier = candidate_recent

    active = fixed_evidence + recent_frontier
    prompt = build_science_planner_prompt(**common, observations=active)
    payload, _ = science_planner.build_request_payload(
        prompt, logical_attempt_id=logical_attempt_id, cycle=cycle
    )
    final_tokens = science_planner.count_input_tokens(payload)
    if final_tokens + science_planner.MAX_TOOL_COMPLETION_TOKENS > science_planner.SERVER_CONTEXT_TOKENS:
        raise RuntimeError("SCIENCE_PLANNER_FRONTIER_PACKER_INTERNAL_OVERFLOW")
    return prompt, {
        "base_input_tokens": base_tokens,
        "final_input_tokens": final_tokens,
        "included_observations": len(recent_frontier),
        "omitted_observations": max(0, len(observations) - len(recent_frontier)),
        "evidence_directory_entries": len(evidence_directory),
        "requested_evidence_chunks": len(requested_evidence),
    }

def build_science_planner_prompt(
    *,
    goal: str,
    requirements: list[str] | None,
    unresolved: list[str],
    raw_task_prompt_summary: dict[str, Any],
    declared_inputs: list[str],
    brain_deliverables: dict[str, str],
    observations: list[dict[str, Any]],
) -> str:
    """Single canonical planner prompt builder shared by runtime and prestart."""
    state_reserve = (
        "\nCycle-0 post-freeze state reserve (ignored; digits are tokenizer-isolated): "
        + POST_FREEZE_STATE_RESERVE_DIGITS
        if requirements is None
        else ""
    )
    return (
        "You are an OPTIONAL semantic proposal source inside Project Brain, not execution authority. "
        "Return one structured proposal object only. Project Brain owns action selection, command policy, verification, "
        "requirement-state updates, and finish authority. No network acquisition, package installation, "
        "git fetch/clone/pull, secrets, or host escape. "
        "On the first cycle provide material_requirements (1-16 stable short IDs). "
        "Provide 1-4 candidate actions as {action_id,covers,depends_on?,timeout_sec?,verify_timeout_sec?,executor,command,verify_executor,verify_command,schema_requirements?,deliverables?}. "
        "executor and verify_executor are explicit shell or python types. Python literal mapping-key reads must be declared in schema_requirements and are probed by Brain before effect. "
        "Declare exact artifact path/format postconditions in deliverables when an action creates an artifact. "
        "Use depends_on only for true within-proposal sequencing. covers must name only frozen material_requirements. "
        "Brain may execute multiple nonredundant candidates from one proposal, but promotes each claimed effect only "
        "after its independent verify_command succeeds. Brain alone decides completion after "
        "independent verification resolves every frozen material requirement. finish_summary is optional "
        "descriptive metadata only and never execution or finish authority. "
        f"Goal: {goal}\nFrozen requirements: {requirements!r}\nUnresolved: {unresolved!r}"
        + state_reserve
        + "\nBrain lossless raw-task acceptance manifest summary (non-droppable; exact task semantics are the Goal text above): "
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
        "Bounded evidence frontier: "
        + json.dumps(observations, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )


async def run_science_goal(
    goal: str,
    environment: BaseEnvironment,
    *,
    max_cycles: int = 8,
    journal_session: causal_bridge.JournalSession | None = None,
    authoritative_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("SCIENCE_GOAL_REQUIRED")
    logical_attempt_id = logical_attempt_id_for_goal(goal)
    max_cycles = max(1, min(int(max_cycles), MAX_CYCLES))
    raw_task_contract, raw_task_localization, raw_task_obligations = _compile_lossless_task_scope(goal)
    raw_task_prompt_summary = _planner_raw_task_manifest_summary(
        goal, raw_task_contract, raw_task_localization, raw_task_obligations
    )
    if authoritative_artifacts is None:
        authoritative_artifacts = _authoritative_artifacts_from_env()
    else:
        authoritative_artifacts = [
            row["path"] for row in typed_action.normalize_authoritative_artifacts(authoritative_artifacts)
        ]
    brain_deliverables = _brain_mandated_deliverables(goal, authoritative_artifacts)
    source_contract_catalog = await _discover_source_contract_catalog(environment)
    source_deliverables = typed_action.source_observed_deliverables(
        source_contract_catalog
    )
    existing_paths = set(brain_deliverables.values())
    for row in source_deliverables:
        if row["path"] not in existing_paths and len(brain_deliverables) < MAX_BRAIN_DELIVERABLES:
            rid = f"SD{len(brain_deliverables) + 1:02d}"
            brain_deliverables[rid] = row["path"]
            existing_paths.add(row["path"])
    mandatory_requirement_ids = list(brain_deliverables)
    requirements: list[str] | None = None
    resolved: set[str] = set()
    declared_inputs, _ = _declared_task_paths(goal, authoritative_artifacts)
    declared_outputs = list(brain_deliverables.values())
    for row in source_deliverables:
        if row["path"] not in declared_outputs:
            declared_outputs.append(row["path"])
    observations: list[dict[str, Any]] = await _snapshot_declared_inputs(
        environment, declared_inputs
    )
    observations.append({
        "kind": "BRAIN_LOCAL_SOURCE_SCHEMA_CATALOG",
        "rows": source_contract_catalog,
        "source_observed_deliverables": source_deliverables,
        "semantic_identity_authority": False,
        "finish_authority": False,
    })
    trace: list[dict[str, Any]] = []
    evidence_store = EvidenceStore.from_environment()
    evidence_directory: list[dict[str, Any]] = []
    evidence_ids: set[str] = set()
    requested_evidence_context: list[dict[str, Any]] = []
    failed_effect_fingerprints: dict[str, dict[str, Any]] = {}
    failed_precondition_fingerprints: dict[str, dict[str, Any]] = {}

    def record_observation(row: dict[str, Any]) -> None:
        observations.append(row)
        cycle_value = row.get("cycle") if isinstance(row, dict) else None
        descriptor = evidence_store.put(
            row,
            cycle=cycle_value if isinstance(cycle_value, int) and not isinstance(cycle_value, bool) else None,
        )
        evidence_id = str(descriptor["evidence_id"])
        if evidence_id not in evidence_ids:
            evidence_ids.add(evidence_id)
            evidence_directory.append(descriptor)

    for initial_observation in list(observations):
        descriptor = evidence_store.put(initial_observation)
        evidence_id = str(descriptor["evidence_id"])
        if evidence_id not in evidence_ids:
            evidence_ids.add(evidence_id)
            evidence_directory.append(descriptor)

    def blocked_result(status: str, summary: str, *, cycles: int) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "status": status,
            "controller_mode": "BRAIN_OWNED_RESEARCH_CONTROL__OPTIONAL_GENERAL_COGNITION_SUBSTRATE",
            "model_has_terminal_authority": False,
            "material_requirements": requirements or [],
            "brain_mandated_deliverables": brain_deliverables,
            "resolved_requirements": sorted(resolved),
            "cycles": cycles,
            "trace": trace,
            "task_completion_claimed": False,
            "finish_authority": "RAW_TASK_ACCEPTANCE_V1_REQUIRED",
            "raw_task_contract_sha256": raw_task_contract.get("task_contract_sha256"),
            "raw_task_required_obligation_count": len(raw_task_obligations),
            "raw_task_prompt_manifest_sha256": raw_task_prompt_summary["ordered_manifest_sha256"],
            "raw_task_acceptance_receipts_present": False,
            "effect_replay_authority": False,
            "verification_replay_authority": False,
            "summary": summary,
        }

    async def journal_fault(*, cycle: int, action_id: str, stage: str, exc: Exception) -> None:
        if journal_session is None:
            return
        payload = {
            "cycle": cycle,
            "action_id": action_id,
            "stage": stage,
            "error_type": type(exc).__name__,
            "error_sha256": hashlib.sha256(str(exc).encode("utf-8", "replace")).hexdigest(),
            "effect_replayed": False,
            "verification_replayed": False,
        }
        await asyncio.to_thread(journal_session.append, "FAULT", payload)

    for cycle in range(max_cycles):
        unresolved = [] if requirements is None else sorted(set(requirements) - resolved)
        output_gate_failures: list[dict[str, Any]] = []
        if requirements is not None and not unresolved and declared_outputs:
            output_gate_failures = await _declared_output_gate(
                environment, declared_outputs
            )
        prompt, prompt_fit = build_fitting_science_planner_prompt(
            goal=goal,
            requirements=requirements,
            unresolved=unresolved,
            raw_task_prompt_summary=raw_task_prompt_summary,
            declared_inputs=declared_inputs,
            brain_deliverables=brain_deliverables,
            observations=observations,
            evidence_directory=evidence_directory,
            requested_evidence=requested_evidence_context,
            logical_attempt_id=logical_attempt_id,
            cycle=cycle,
        )
        planned = science_planner.plan(
            prompt,
            logical_attempt_id=logical_attempt_id,
            cycle=cycle,
            timeout_s=PLANNER_TIMEOUT_S,
        )
        planned["evidence_frontier"] = prompt_fit
        raw = science_planner.normalize_proposal_object(
            science_planner.extract_json_object(planned.get("text", ""))
        )
        if not isinstance(raw, dict):
            raise RuntimeError("SCIENCE_PLANNER_OBJECT_REQUIRED")
        # Exact evidence chunks from the previous cognition turn have now been consumed.
        requested_evidence_context = []
        requirements, candidates, finish_summary, candidate_rejections = _extract_contract(
            raw,
            requirements,
            mandatory_requirement_ids,
        )
        evidence_requests = raw.get("evidence_requests") or []
        if evidence_requests:
            requested_evidence_context = evidence_store.resolve_requests(evidence_requests)
            fulfilled = {
                "cycle": cycle,
                "kind": "BRAIN_EVIDENCE_REQUEST_FULFILLED",
                "requests": [
                    {
                        "evidence_id": row["evidence_id"],
                        "chunk_index": row["chunk_index"],
                    }
                    for row in evidence_requests
                ],
                "fulfilled_chunk_count": len(requested_evidence_context),
                "effect_authority": False,
                "finish_authority": False,
            }
            record_observation(fulfilled)
            trace.append(fulfilled)
            if journal_session is not None:
                await asyncio.to_thread(
                    journal_session.append,
                    "PLANNER_EVIDENCE_REQUEST_FULFILLED",
                    fulfilled,
                )
            # Evidence acquisition is cognition-only. Do not execute actions from
            # the same proposal before the requested exact bytes are visible.
            continue
        unresolved_set = set(requirements) - resolved

        # Planner candidates are untrusted optional metadata. Preserve local
        # rejections as evidence, but never execute/promote them and never let
        # one malformed candidate abort valid siblings or later cycles.
        for candidate_rejection in candidate_rejections:
            rejected = {
                "cycle": cycle,
                **candidate_rejection,
            }
            trace.append(rejected)
            record_observation(rejected)
            if journal_session is not None:
                await asyncio.to_thread(
                    journal_session.append,
                    "PLANNER_CANDIDATE_REJECTED",
                    rejected,
                )

        if finish_summary is not None:
            if unresolved_set:
                rejected = {
                    "cycle": cycle,
                    "kind": "FINISH_REJECTED",
                    "reason": "UNRESOLVED_MATERIAL_REQUIREMENTS",
                    "unresolved": sorted(unresolved_set),
                }
                trace.append(rejected)
                record_observation(rejected)
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
                record_observation(rejected)
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
            record_observation(rejected)
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
            chosen_command_sha256 = hashlib.sha256(
                chosen["command"].encode("utf-8")
            ).hexdigest()
            action_fingerprint = chosen["action_fingerprint_sha256"]
            effect_fingerprint = chosen["effect_fingerprint_sha256"]

            prior_failure = failed_effect_fingerprints.get(effect_fingerprint)
            prior_precondition = failed_precondition_fingerprints.get(action_fingerprint)
            if prior_failure is not None or prior_precondition is not None:
                executed_action_ids.add(chosen["action_id"])
                prior = prior_failure if prior_failure is not None else prior_precondition
                rejected_repeat = {
                    "cycle": cycle,
                    "kind": (
                        "BRAIN_REJECTED_CONTENT_ADDRESSED_FAILED_EFFECT_REPEAT"
                        if prior_failure is not None
                        else "BRAIN_REJECTED_CONTENT_ADDRESSED_FAILED_PRECONDITION_REPEAT"
                    ),
                    "action_id": chosen["action_id"],
                    "action_fingerprint_sha256": action_fingerprint,
                    "effect_fingerprint_sha256": effect_fingerprint,
                    "command_sha256": chosen_command_sha256,
                    "executor": chosen["executor"],
                    "verify_executor": chosen["verify_executor"],
                    "schema_requirements": chosen["schema_requirements"],
                    "deliverables": chosen["deliverables"],
                    "prior_failure_cycle": prior.get("cycle"),
                    "prior_failure_action_id": prior.get("action_id"),
                    "reason": (
                        "EXACT_EFFECT_BYTES_ALREADY_EXECUTED_WITHOUT_VERIFIED_PROMOTION__COMMAND_BYTES_MUST_CHANGE"
                        if prior_failure is not None
                        else "EXACT_TYPED_PRECONDITION_ALREADY_FAILED__DECLARATION_BYTES_MUST_CHANGE"
                    ),
                    "effect_executed": False,
                    "coverage_promoted": False,
                }
                trace.append(rejected_repeat)
                record_observation(rejected_repeat)
                if journal_session is not None:
                    await asyncio.to_thread(
                        journal_session.append,
                        "PLANNER_CANDIDATE_REJECTED",
                        rejected_repeat,
                    )
                continue

            schema_ok, schema_checks = await _probe_schema_requirements(
                chosen["schema_requirements"], environment
            )
            if not schema_ok:
                failed_precondition_fingerprints[action_fingerprint] = {
                    "cycle": cycle,
                    "action_id": chosen["action_id"],
                    "reason": "SCHEMA_PRECONDITION_FAILED",
                }
                executed_action_ids.add(chosen["action_id"])
                rejected_schema = {
                    "cycle": cycle,
                    "kind": "BRAIN_REJECTED_UNAUTHENTICATED_SCHEMA_DEREFERENCE",
                    "action_id": chosen["action_id"],
                    "action_fingerprint_sha256": action_fingerprint,
                    "schema_checks": schema_checks,
                    "effect_executed": False,
                    "coverage_promoted": False,
                }
                trace.append(rejected_schema)
                record_observation(rejected_schema)
                if journal_session is not None:
                    await asyncio.to_thread(
                        journal_session.append,
                        "PLANNER_CANDIDATE_REJECTED",
                        rejected_schema,
                    )
                continue

            if journal_session is not None:
                proposal_bytes = json.dumps(
                    raw,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
                intent_payload = {
                    "cycle": cycle,
                    "planner_payload_sha256": planned.get("payload_sha256"),
                    "planner_request_identity_sha256": planned.get("request_identity_sha256"),
                    "proposal_sha256": hashlib.sha256(proposal_bytes).hexdigest(),
                    "action_id": chosen["action_id"],
                    "command_sha256": chosen_command_sha256,
                    "verify_command_sha256": hashlib.sha256(chosen["verify_command"].encode("utf-8")).hexdigest(),
                    "covers": list(chosen["covers"]),
                    "depends_on": list(chosen["depends_on"]),
                    "action_timeout_sec": chosen["timeout_sec"],
                    "verify_timeout_sec": chosen["verify_timeout_sec"],
                }
                await asyncio.to_thread(
                    journal_session.append,
                    "PLANNER_PROPOSAL_ACTION_INTENT",
                    intent_payload,
                )

            executed_action_ids.add(chosen["action_id"])
            executed_any = True

            try:
                action_receipt = await transport.exec(
                    chosen["command"], timeout_sec=chosen["timeout_sec"]
                )
            except HarborTransportUncertainError as exc:
                await journal_fault(
                    cycle=cycle,
                    action_id=chosen["action_id"],
                    stage="ACTION_EFFECT",
                    exc=exc,
                )
                record = {
                    "cycle": cycle,
                    "kind": "BRAIN_SELECTED_RESEARCH_ACTION",
                    "action_id": chosen["action_id"],
                    "covers": chosen["covers"],
                    "depends_on": chosen["depends_on"],
                    "action_timeout_sec": chosen["timeout_sec"],
                    "verify_timeout_sec": chosen["verify_timeout_sec"],
                    "selection_reason": "MAX_DECLARED_UNRESOLVED_COVERAGE_THEN_ACTION_ID__DEPENDENCY_GATED__STRUCTURAL_CONTROL_ONLY",
                    "action_result": {
                        "returncode": None,
                        "stdout": "",
                        "stderr": "",
                        "transport_uncertain": True,
                    },
                    "action_transport_clean": False,
                    "verify_result": None,
                    "verified_covers": [],
                    "brain_deliverable_checks": [],
                    "coverage_promoted": False,
                    "effect_replayed": False,
                    "verification_replayed": False,
                }
                trace.append(record)
                record_observation(record)
                return blocked_result(
                    "BLOCKED_ACTION_EFFECT_OUTCOME_UNCERTAIN",
                    "The action was dispatched but no trustworthy execution receipt exists. "
                    "The action was not replayed and no planner-provided verifier was used to infer success; "
                    "Harbor's independent benchmark verifier remains the scoring authority over the actual environment.",
                    cycles=cycle + 1,
                )

            full_action_evidence = {
                "cycle": cycle,
                "kind": "BRAIN_FULL_ACTION_RECEIPT_EVIDENCE",
                "action_id": chosen["action_id"],
                "returncode": action_receipt.returncode,
                "stdout": str(action_receipt.stdout or ""),
                "stderr": str(action_receipt.stderr or ""),
                "transport_uncertain": False,
            }
            record_observation(full_action_evidence)
            action_observed = {
                "returncode": action_receipt.returncode,
                "stdout": action_receipt.stdout[-MAX_OUTPUT_CHARS:],
                "stderr": action_receipt.stderr[-MAX_OUTPUT_CHARS:],
                "transport_uncertain": False,
            }
            verify_observed = None
            verify_receipt = None
            verified = False
            verified_covers: list[str] = []
            deliverable_checks: list[dict[str, Any]] = []
            action_transport_clean = _action_transport_clean(
                action_receipt.returncode, action_receipt.stdout, action_receipt.stderr
            )
            if action_transport_clean:
                try:
                    verify_receipt = await transport.exec(
                        chosen["verify_command"],
                        timeout_sec=chosen["verify_timeout_sec"],
                    )
                except HarborTransportUncertainError as exc:
                    await journal_fault(
                        cycle=cycle,
                        action_id=chosen["action_id"],
                        stage="VERIFY_COMMAND",
                        exc=exc,
                    )
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
                        "action_transport_clean": True,
                        "verify_result": {
                            "returncode": None,
                            "stdout": "",
                            "stderr": "",
                            "transport_uncertain": True,
                        },
                        "verified_covers": [],
                        "brain_deliverable_checks": [],
                        "coverage_promoted": False,
                        "effect_replayed": False,
                        "verification_replayed": False,
                    }
                    trace.append(record)
                    record_observation(record)
                    return blocked_result(
                        "BLOCKED_VERIFICATION_OUTCOME_UNCERTAIN",
                        "The action has a trustworthy successful receipt but its verification transport outcome is uncertain. "
                        "Verification was not replayed; Harbor's independent benchmark verifier remains live.",
                        cycles=cycle + 1,
                    )

                full_verify_evidence = {
                    "cycle": cycle,
                    "kind": "BRAIN_FULL_VERIFY_RECEIPT_EVIDENCE",
                    "action_id": chosen["action_id"],
                    "returncode": verify_receipt.returncode,
                    "stdout": str(verify_receipt.stdout or ""),
                    "stderr": str(verify_receipt.stderr or ""),
                    "transport_uncertain": False,
                }
                record_observation(full_verify_evidence)
                verify_observed = {
                    "returncode": verify_receipt.returncode,
                    "stdout": verify_receipt.stdout[-MAX_OUTPUT_CHARS:],
                    "stderr": verify_receipt.stderr[-MAX_OUTPUT_CHARS:],
                    "transport_uncertain": False,
                }
                if verify_receipt.returncode == 0:
                    candidate_deliverables_ok, candidate_deliverable_checks = (
                        await _validate_candidate_deliverables(
                            chosen["deliverables"], environment
                        )
                    )
                    deliverable_checks.extend(candidate_deliverable_checks)
                    if candidate_deliverables_ok:
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
                    verified = (
                        candidate_deliverables_ok
                        and len(verified_covers) == len(chosen["covers"])
                    )
                    if verified:
                        verified_action_ids.add(chosen["action_id"])

            if not verified:
                failed_effect_fingerprints[effect_fingerprint] = {
                    "cycle": cycle,
                    "action_id": chosen["action_id"],
                    "effect_fingerprint_sha256": effect_fingerprint,
                    "command_sha256": chosen_command_sha256,
                    "returncode": action_receipt.returncode,
                    "verification_performed": verify_observed is not None,
                    "verification_returncode": (
                        verify_observed.get("returncode")
                        if isinstance(verify_observed, dict)
                        else None
                    ),
                }

            record = {
                "cycle": cycle,
                "kind": "BRAIN_SELECTED_RESEARCH_ACTION",
                "action_id": chosen["action_id"],
                "action_fingerprint_sha256": action_fingerprint,
                "executor": chosen["executor"],
                "verify_executor": chosen["verify_executor"],
                "schema_requirements": chosen["schema_requirements"],
                "candidate_deliverables": chosen["deliverables"],
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
            if journal_session is not None:
                action_stdout = str(action_receipt.stdout or "")
                action_stderr = str(action_receipt.stderr or "")
                verify_stdout = (
                    str(verify_receipt.stdout or "")
                    if verify_receipt is not None
                    else ""
                )
                verify_stderr = (
                    str(verify_receipt.stderr or "")
                    if verify_receipt is not None
                    else ""
                )
                state_payload = {
                    "cycle": cycle,
                    "action_id": chosen["action_id"],
                    "action_returncode": action_receipt.returncode,
                    "action_stdout_sha256": hashlib.sha256(
                        action_stdout.encode("utf-8", "replace")
                    ).hexdigest(),
                    "action_stderr_sha256": hashlib.sha256(
                        action_stderr.encode("utf-8", "replace")
                    ).hexdigest(),
                    "verification_performed": verify_observed is not None,
                    "verification_returncode": (
                        verify_observed.get("returncode")
                        if isinstance(verify_observed, dict)
                        else None
                    ),
                    "verification_stdout_sha256": hashlib.sha256(
                        verify_stdout.encode("utf-8", "replace")
                    ).hexdigest(),
                    "verification_stderr_sha256": hashlib.sha256(
                        verify_stderr.encode("utf-8", "replace")
                    ).hexdigest(),
                    "verified_covers": list(verified_covers),
                    "resolved_requirement_ids": sorted(resolved),
                    "coverage_promoted": bool(verified),
                }
                await asyncio.to_thread(
                    journal_session.append,
                    "ACTION_VERIFY_STATE_COMMIT",
                    state_payload,
                )

            trace.append(record)
            record_observation(record)

        if not executed_any:
            blocked = {
                "cycle": cycle,
                "kind": "BRAIN_RESEARCH_SELECTION_BLOCKED",
                "reason": "NO_DEPENDENCY_SATISFIED_NONREDUNDANT_PROPOSAL_COVERS_CURRENT_RESIDUAL",
                "unresolved": sorted(set(requirements) - resolved),
            }
            trace.append(blocked)
            record_observation(blocked)
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
                record_observation(rejected)
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
        return "1.12.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        logical_attempt_id = logical_attempt_id_for_goal(instruction)
        await start_barrier.await_start_commit(logical_attempt_id)
        journal_dir = os.environ.get("BRAIN_CAUSAL_JOURNAL_DIR")
        if not isinstance(journal_dir, str) or not journal_dir.strip():
            raise RuntimeError("BRAIN_CAUSAL_JOURNAL_DIR_REQUIRED")
        journal_session = causal_bridge.JournalSession(
            journal_dir,
            logical_attempt_id,
        )
        try:
            result = await run_science_goal(
                instruction,
                environment,
                journal_session=journal_session,
            )
        except Exception as exc:
            # Keep internal controller/provider failures inside this one Harbor
            # trial so the independent benchmark verifier can still score the
            # actual task environment. BaseException subclasses such as
            # cancellation remain outside this containment boundary.
            result = {
                "schema": SCHEMA,
                "status": "BLOCKED_INTERNAL_CONTROLLER_OR_TRANSPORT_EXCEPTION",
                "internal_unsolved": True,
                "externality_proved": False,
                "task_completion_claimed": False,
                "model_has_terminal_authority": False,
                "effect_replay_authority": False,
                "verification_replay_authority": False,
                "exception_type": type(exc).__name__,
                "exception_sha256": hashlib.sha256(
                    str(exc).encode("utf-8", "replace")
                ).hexdigest(),
                "summary": (
                    "Internal controller/provider failure was contained inside "
                    "the single Harbor trial. No retry, replacement trial, "
                    "effect replay, or terminal claim was created."
                ),
            }
            try:
                await asyncio.to_thread(
                    journal_session.append,
                    "FAULT",
                    {
                        "cycle": -1,
                        "action_id": "CONTROLLER",
                        "stage": "CONTROLLER_EXCEPTION",
                        "error_type": type(exc).__name__,
                        "error_sha256": result["exception_sha256"],
                        "effect_replayed": False,
                        "verification_replayed": False,
                    },
                )
            except Exception:
                pass

        # Evidence logging must not turn a verifiable environment into an agent
        # crash. The Harbor verifier, not this host log, owns benchmark scoring.
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            (self.logs_dir / "project_brain_science_trace.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        if hasattr(context, "cost_usd"):
            try:
                context.cost_usd = 0.0
            except Exception:
                pass
