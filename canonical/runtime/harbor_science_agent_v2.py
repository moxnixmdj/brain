"""Science Agent V2: typed actions, evidence grounding, failed-action memory."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from typing import Any

from canonical.runtime import harbor_science_agent_v1 as _v1
from canonical.runtime import harbor_science_planner_v2 as _planner_v2
from canonical.runtime.science_action_contract_v2 import (
    action_fingerprint,
    prompt_observation_state,
    render_source,
    required_schema_keys,
)

SCHEMA = "PROJECT_BRAIN_HARBOR_SCIENCE_AGENT_TRACE_V2"
_LOCK = asyncio.Lock()
_PASSIVE_OUTPUT_RE = re.compile(
    r"""(?is)\b(?:must|should|shall|needs?\s+to|is\s+to)\s+(?:be\s+)?"""
    r"""(?:written|saved|stored|exported|produced|delivered|emitted)\s+"""
    r"""(?:to|at|as|into)\s+[`'"\[]*(?P<path>/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)"""
)
_NAMED_OUTPUT_RE = re.compile(
    r"""(?is)\b(?:output|submission|deliverable|result)\s+(?:file|path|artifact)?\s*"""
    r"""(?:is|:|=|at|to)\s+[`'"\[]*(?P<path>/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)"""
)


def _brain_mandated_deliverables(goal: str) -> dict[str, str]:
    paths = list(_v1._brain_mandated_deliverables(goal).values())

    def add(path: str) -> None:
        if not _v1._valid_mandated_output_path(path):
            return
        if path not in paths and len(paths) < _v1.MAX_BRAIN_DELIVERABLES:
            paths.append(path)

    for pattern in (_PASSIVE_OUTPUT_RE, _NAMED_OUTPUT_RE):
        for match in pattern.finditer(str(goal or "")):
            add(match.group("path"))
    return {f"BRAIN_DELIVERABLE_{i + 1:02d}": path for i, path in enumerate(paths)}


def _local_rejection(
    sink: list[dict[str, Any]] | None,
    item: dict[str, Any],
    reason: str,
    **extra: Any,
) -> None:
    if sink is None:
        raise RuntimeError(reason)
    raw = json.dumps(
        item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    sink.append({
        "kind": "BRAIN_CANDIDATE_REJECTED",
        "reason": reason,
        "source_action_id": item.get("action_id"),
        "candidate_metadata_sha256": hashlib.sha256(raw).hexdigest(),
        "executed": False,
        "coverage_promoted": False,
        "requirement_set_rewritten": False,
        **extra,
    })


def _candidate_rows(
    raw: Any,
    requirements: set[str],
    *,
    rejected_candidates: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        return _v1._candidate_rows(
            raw, requirements, rejected_candidates=rejected_candidates
        )

    staged: list[tuple[dict[str, Any], str, str]] = []
    id_map: dict[str, str] = {}
    seen_fp: set[str] = set()

    for original in raw:
        if not isinstance(original, dict):
            return _v1._candidate_rows(
                raw, requirements, rejected_candidates=rejected_candidates
            )
        source_id = str(original.get("action_id") or "").strip()
        try:
            command_language, command = render_source(
                original.get("command_language"),
                original.get("command"),
                field="COMMAND",
            )
            _, verify = render_source(
                original.get("verify_language"),
                original.get("verify_command"),
                field="VERIFY_COMMAND",
            )
            fp = action_fingerprint(command_language, original.get("command"))
        except Exception as exc:
            _local_rejection(
                rejected_candidates,
                original,
                "EXECUTION_CONTRACT_INVALID",
                source_error=type(exc).__name__ + ":" + str(exc),
            )
            continue
        if fp in seen_fp:
            _local_rejection(
                rejected_candidates,
                original,
                "DUPLICATE_ACTION_BYTES_IN_PROPOSAL",
                action_fingerprint_sha256=fp,
            )
            continue
        if not source_id or source_id in id_map:
            _local_rejection(
                rejected_candidates,
                original,
                "SOURCE_ACTION_ID_INVALID_OR_DUPLICATE",
            )
            continue
        seen_fp.add(fp)
        id_map[source_id] = fp
        item = dict(original)
        item["action_id"] = fp
        item["command"] = command
        item["verify_command"] = verify
        item.pop("command_language", None)
        item.pop("verify_language", None)
        staged.append((item, source_id, fp))

    transformed: list[dict[str, Any]] = []
    for item, source_id, fp in staged:
        deps = item.get("depends_on") or []
        missing = [str(dep) for dep in deps if str(dep) not in id_map]
        if missing:
            _local_rejection(
                rejected_candidates,
                raw[[str(x.get("action_id") or "") for x in raw].index(source_id)],
                "DEPENDENCY_REJECTED",
                missing_dependencies=missing,
                action_fingerprint_sha256=fp,
            )
            continue
        item["depends_on"] = [id_map[str(dep)] for dep in deps]
        transformed.append(item)

    if not transformed:
        return []
    return _v1._candidate_rows(
        transformed,
        requirements,
        rejected_candidates=rejected_candidates,
    )


class _PlannerProxy:
    @staticmethod
    def extract_json_object(text: Any) -> dict[str, Any]:
        return _planner_v2.extract_json_object(text)

    @staticmethod
    def normalize_proposal_object(obj: dict[str, Any]) -> dict[str, Any]:
        return _planner_v2.normalize_proposal_object(obj)

    @staticmethod
    def plan(prompt: str, *, timeout_s: int = 180) -> dict[str, Any]:
        result = _planner_v2.plan(prompt, timeout_s=timeout_s)
        proposal = _planner_v2.normalize_proposal_object(
            _planner_v2.extract_json_object(result.get("text", ""))
        )
        candidates = proposal.get("candidates")
        if not isinstance(candidates, list):
            return result

        observed, failed = prompt_observation_state(prompt)
        kept: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in candidates:
            fp = action_fingerprint(row.get("command_language"), row.get("command"))
            if fp in failed or fp in seen:
                continue
            needed = required_schema_keys(
                row.get("command_language"), row.get("command")
            )
            if set(needed) - observed:
                continue
            seen.add(fp)
            kept.append(row)

        allowed = {str(x.get("action_id") or "") for x in kept}
        kept = [
            x for x in kept
            if all(str(dep) in allowed for dep in (x.get("depends_on") or []))
        ]
        proposal = dict(proposal)
        if kept:
            proposal["candidates"] = kept
        else:
            proposal.pop("candidates", None)
        out = dict(result)
        out["text"] = json.dumps(proposal, sort_keys=True, separators=(",", ":"))
        return out


async def run_science_goal(
    goal: str,
    environment: Any,
    *,
    max_cycles: int = 8,
) -> dict[str, Any]:
    async with _LOCK:
        prior_planner = _v1.science_planner
        prior_rows = _v1._candidate_rows
        prior_deliverables = _v1._brain_mandated_deliverables
        _v1.science_planner = _PlannerProxy
        _v1._candidate_rows = _candidate_rows
        _v1._brain_mandated_deliverables = _brain_mandated_deliverables
        try:
            result = await _v1.run_science_goal(
                goal, environment, max_cycles=max_cycles
            )
        finally:
            _v1.science_planner = prior_planner
            _v1._candidate_rows = prior_rows
            _v1._brain_mandated_deliverables = prior_deliverables
    out = dict(result)
    out["schema"] = SCHEMA
    out["typed_action_contract_v2"] = True
    out["failed_action_fingerprint_memory_v2"] = True
    out["external_schema_grounding_v2"] = True
    out["passive_deliverable_binding_v2"] = True
    return out


class HarborScienceAgent(_v1.HarborScienceAgent):
    def version(self) -> str:
        return "2.0.0"

    async def run(self, instruction: str, environment: Any, context: Any) -> None:
        result = await run_science_goal(instruction, environment)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "project_brain_science_trace.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if hasattr(context, "cost_usd"):
            context.cost_usd = 0.0
