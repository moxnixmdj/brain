"""Post-composition live frontier planner with bounded dynamic currentness.

The static frontier is a durable scheduling snapshot, not eternal truth. This
adapter may refresh only explicitly supported current-pointer families whose
moving state has a strict machine-checkable contract. Unsupported source drift
continues to fail closed in the core frontier verifier.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping
from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA = "PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V2"
PROF_SOURCE = "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
PROF_SCHEMA = "PROJECT_BRAIN_CURRENT_PROFESSIONAL_QUALITY_EXECUTION_POINTER_V1"
PROF_MUTATION_KEY = "canonical:professional-quality"
PROF_AUTHORITY_KEY = "authority:professional-v7-subject"
BYTES_SOURCE = "canonical/research/bytes/BYTES_ACTIVE_STATE_20261010_V1.json"
BYTES_SCHEMA = "PROJECT_BRAIN_BYTES_ACTIVE_STATE_V1"
BYTES_MUTATION_KEY = "canonical:bytes"
TOTAL_LEAVES = 24


class PostCompositionFrontierError(ValueError):
    pass


def _contains(values: Any, target: str) -> bool:
    return isinstance(values, list) and target in values


def _count(value: Any, reason: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PostCompositionFrontierError(reason)
    return value


def _load_current(rel: str, schema: str) -> tuple[dict[str, Any], str]:
    path = core.ROOT / rel
    if not path.is_file() or path.is_symlink():
        raise PostCompositionFrontierError("CURRENT_SOURCE_MISSING:" + rel)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PostCompositionFrontierError(
            "CURRENT_SOURCE_INVALID:" + rel + ":" + type(exc).__name__
        ) from exc
    if not isinstance(doc, dict) or doc.get("schema") != schema:
        raise PostCompositionFrontierError("CURRENT_SOURCE_SCHEMA_INVALID:" + rel)
    return doc, core._git_blob_sha(path)


def _source_row(frontier: dict[str, Any], rel: str) -> dict[str, Any]:
    rows = frontier.get("scope", {}).get("source_set")
    if not isinstance(rows, list):
        raise PostCompositionFrontierError("SOURCE_SET_MISSING")
    matches = [x for x in rows if isinstance(x, dict) and x.get("path") == rel]
    if len(matches) != 1:
        raise PostCompositionFrontierError("SOURCE_ROW_CARDINALITY:" + rel)
    return matches[0]


def _professional_rows(frontier: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = frontier.get("candidates")
    if not isinstance(candidates, list):
        raise PostCompositionFrontierError("CANDIDATES_INVALID")
    return [
        row for row in candidates
        if isinstance(row, Mapping)
        and row.get("source") == PROF_SOURCE
        and _contains(row.get("mutation_keys"), PROF_MUTATION_KEY)
        and _contains(row.get("authority_keys"), PROF_AUTHORITY_KEY)
    ]


def _professional_live(doc: Mapping[str, Any]) -> dict[str, Any]:
    if doc.get("live_default") is not False or doc.get("terminal_authority") is not False:
        raise PostCompositionFrontierError("PROFESSIONAL_AUTHORITY_BOUNDARY_CHANGED")
    live = doc.get("property_truth_frontier")
    if not isinstance(live, Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_CURRENT_FRONTIER_MISSING")
    closed = _count(live.get("verified_leaf_count"), "PROFESSIONAL_CLOSED_INVALID")
    total = _count(live.get("total_leaf_count"), "PROFESSIONAL_TOTAL_INVALID")
    open_exec = _count(live.get("open_execution_leaf_count"), "PROFESSIONAL_OPEN_EXEC_INVALID")
    open_sem = _count(live.get("open_semantic_leaf_count"), "PROFESSIONAL_OPEN_SEM_INVALID")
    ids = live.get("verified_leaf_ids")
    if total != TOTAL_LEAVES:
        raise PostCompositionFrontierError("PROFESSIONAL_TOTAL_NOT_24")
    if not isinstance(ids, list) or any(not isinstance(x, str) or not x for x in ids):
        raise PostCompositionFrontierError("PROFESSIONAL_VERIFIED_IDS_INVALID")
    if len(ids) != len(set(ids)) or len(ids) != closed:
        raise PostCompositionFrontierError("PROFESSIONAL_VERIFIED_IDS_COUNT_MISMATCH")
    if closed + open_exec + open_sem != total:
        raise PostCompositionFrontierError("PROFESSIONAL_ACCOUNTING_NOT_TOTAL")
    shared = live.get("shared_semantic_blocker")
    if not isinstance(shared, Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_SHARED_SEMANTIC_BLOCKER_MISSING")
    if shared.get("independently_verified") is not True:
        raise PostCompositionFrontierError("PROFESSIONAL_SHARED_SEMANTIC_BLOCKER_UNVERIFIED")
    if shared.get("catalog_alone_can_authorize_semantic_property_truth") is not False:
        raise PostCompositionFrontierError("PROFESSIONAL_SEMANTIC_CATALOG_BOUNDARY_DRIFT")
    return {
        "closed": closed,
        "open_exec": open_exec,
        "open_sem": open_sem,
        "ids": list(ids),
    }


def _refresh_professional(frontier: dict[str, Any]) -> dict[str, Any]:
    doc, sha = _load_current(PROF_SOURCE, PROF_SCHEMA)
    live = _professional_live(doc)
    rows = _professional_rows(frontier)
    if len(rows) != 1:
        raise PostCompositionFrontierError("POST_COMPOSITION_PROFESSIONAL_CANDIDATE_CARDINALITY")
    candidates = frontier["candidates"]
    index = next(i for i, row in enumerate(candidates) if row is rows[0])
    row = dict(rows[0])
    if row.get("evidence_acquisition_mode") != "READ_ONLY":
        raise PostCompositionFrontierError("PROFESSIONAL_POST_COMPOSITION_NOT_READ_ONLY")
    ev = dict(row.get("read_only_evidence") or {})
    ev.update({
        "source": PROF_SOURCE,
        "source_git_blob_sha": sha,
        "whole_leaf_scope_complete_count": TOTAL_LEAVES,
        "property_truth_closed_count": live["closed"],
        "verified_property_truth_leaf_ids": live["ids"],
        "open_execution_leaf_count": live["open_exec"],
        "open_semantic_leaf_count": live["open_sem"],
        "semantic_shared_blocker_independently_verified": True,
        "semantic_catalog_alone_can_close": False,
        "vector_bounds_complete": False,
        "dynamic_current_pointer_follow": True,
    })
    row["read_only_evidence"] = ev
    row["causal_role"] = (
        str(live["closed"]) + "_EXECUTION_LEAVES_CLOSED__DEPLET_"
        + str(live["open_exec"])
        + "_REMAINING_EXECUTION_LEAVES__PARALLEL_SEMANTIC_TOTALITY_REUSE"
    )
    row["readiness"] = (
        "PROPERTY_TRUTH_" + str(live["closed"]) + "_OF_24__"
        + str(live["open_exec"]) + "_EXECUTION_LEAVES_OPEN__"
        + str(live["open_sem"]) + "_SEMANTIC_LEAVES_OPEN"
    )
    candidates[index] = row
    _source_row(frontier, PROF_SOURCE)["git_blob_sha"] = sha
    return live


def _parse_qualification(value: Any) -> int:
    match = re.fullmatch(r"([0-9]+)/([0-9]+)", str(value or ""))
    if not match or match.group(1) != match.group(2):
        raise PostCompositionFrontierError("BYTES_QUALIFICATION_NOT_FULL_PASS")
    return int(match.group(1))


def _refresh_bytes(frontier: dict[str, Any]) -> dict[str, Any]:
    doc, sha = _load_current(BYTES_SOURCE, BYTES_SCHEMA)
    exact = doc.get("exact_symbolic_state")
    bottleneck = doc.get("current_bottleneck")
    frozen = doc.get("next_frozen_qualification")
    if not all(isinstance(x, Mapping) for x in (exact, bottleneck, frozen)):
        raise PostCompositionFrontierError("BYTES_CURRENT_STRUCTURE_INVALID")
    if exact.get("promotion_credit_from_this_record") != 0:
        raise PostCompositionFrontierError("BYTES_CURRENT_PROMOTION_BOUNDARY_CHANGED")
    q = str(exact.get("final_untouched_qualification") or "")
    qn = _parse_qualification(q)
    if str(exact.get("clean_room_execution") or "") != q:
        raise PostCompositionFrontierError("BYTES_CLEAN_ROOM_NOT_EQUAL_QUALIFICATION")
    if str(exact.get("archive_replay") or "") != q:
        raise PostCompositionFrontierError("BYTES_ARCHIVE_NOT_EQUAL_QUALIFICATION")
    raw = _count(exact.get("raw_python_source_bytes"), "BYTES_RAW_COUNT_INVALID")
    bexec = _count(exact.get("B_exec_raw_python_source_bytes"), "BYTES_EXEC_COUNT_INVALID")
    next_id = str(frozen.get("id") or "").strip()
    if frozen.get("spent") is not False or not next_id:
        raise PostCompositionFrontierError("BYTES_NEXT_FROZEN_BOUNDARY_INVALID")
    status = str(doc.get("status") or "")
    match = re.search(r"_V([0-9]+)_FRONTIER", status)
    if not match:
        raise PostCompositionFrontierError("BYTES_FRONTIER_VERSION_MISSING")
    version = int(match.group(1))
    if version < 1:
        raise PostCompositionFrontierError("BYTES_FRONTIER_VERSION_INVALID")

    candidates = frontier.get("candidates")
    if not isinstance(candidates, list):
        raise PostCompositionFrontierError("CANDIDATES_INVALID")
    positions = [
        i for i, row in enumerate(candidates)
        if isinstance(row, Mapping)
        and row.get("source") == BYTES_SOURCE
        and _contains(row.get("mutation_keys"), BYTES_MUTATION_KEY)
    ]
    if len(positions) != 1:
        raise PostCompositionFrontierError("BYTES_CANDIDATE_CARDINALITY")
    row = dict(candidates[positions[0]])
    if row.get("evidence_acquisition_mode") != "READ_ONLY":
        raise PostCompositionFrontierError("BYTES_POST_COMPOSITION_NOT_READ_ONLY")
    row["work_id"] = "BYTES_EXACT_SYMBOLIC_V" + str(version) + "_NEXT_PHYSICAL_CUT"
    row["causal_role"] = (
        "CONTINUE_VERIFIED_RESOURCE_REDUCTION_FROM_"
        + str(raw)
        + "_RAW_PYTHON_BYTES__RERANK_BEFORE_NEXT_PHYSICAL_CUT"
    )
    row["readiness"] = "ACTIONABLE_VERIFIED_BYTES_V" + str(version) + "_CURRENT"
    row["ready"] = "V" + str(version) + "_CURRENT_AT_" + str(raw) + "_BYTES"
    row["source_git_blob_sha"] = sha
    ev = dict(row.get("read_only_evidence") or {})
    ev.update({
        "source": BYTES_SOURCE,
        "source_git_blob_sha": sha,
        "raw_python_source_bytes": raw,
        "B_exec_raw_python_source_bytes": bexec,
        "qualification": q,
        "qualification_case_count": qn,
        "next_action": str(bottleneck.get("next_action") or ""),
        "next_frozen_qualification": next_id,
        "next_frozen_spent": False,
        "vector_bounds_complete": False,
        "dynamic_current_pointer_follow": True,
    })
    row["read_only_evidence"] = ev
    candidates[positions[0]] = row
    _source_row(frontier, BYTES_SOURCE)["git_blob_sha"] = sha
    return {"version": version, "raw": raw, "qualification": q, "sha": sha}


def _refresh_supported_sources(frontier: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    out = json.loads(json.dumps(frontier))
    professional = _refresh_professional(out)
    bytes_state = _refresh_bytes(out)
    dynamic = out.setdefault("dynamic_currentness", {})
    if not isinstance(dynamic, dict):
        raise PostCompositionFrontierError("DYNAMIC_CURRENTNESS_NOT_OBJECT")
    dynamic.update({
        "post_composition_professional_follow": True,
        "professional_property_truth_closed_count": professional["closed"],
        "professional_open_execution_leaf_count": professional["open_exec"],
        "post_composition_bytes_follow": True,
        "bytes_frontier_version": bytes_state["version"],
        "bytes_raw_python_source_bytes": bytes_state["raw"],
        "unsupported_source_drift_fails_closed": True,
    })
    return out, professional, bytes_state


def _assert_post_composition(frontier: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = _professional_rows(frontier)
    if len(rows) != 1:
        raise PostCompositionFrontierError("POST_COMPOSITION_PROFESSIONAL_CANDIDATE_CARDINALITY")
    row = rows[0]
    ev = row.get("read_only_evidence")
    if not isinstance(ev, Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_EVIDENCE_MISSING")
    live = _professional_live(_load_current(PROF_SOURCE, PROF_SCHEMA)[0])
    comparisons = {
        "property_truth_closed_count": live["closed"],
        "open_execution_leaf_count": live["open_exec"],
        "open_semantic_leaf_count": live["open_sem"],
    }
    for key, expected in comparisons.items():
        if ev.get(key) != expected:
            raise PostCompositionFrontierError("PROFESSIONAL_CURRENT_EVIDENCE_DRIFT:" + key)
    if ev.get("verified_property_truth_leaf_ids") != live["ids"]:
        raise PostCompositionFrontierError("PROFESSIONAL_CURRENT_EVIDENCE_DRIFT:verified_leaf_ids")
    return live


def plan_current_post_composition_frontier() -> dict[str, Any]:
    frontier, professional, bytes_state = _refresh_supported_sources(
        core.load_current_frontier()
    )
    _assert_post_composition(frontier)
    out = core.plan_parallel_frontier(frontier)
    return {
        **out,
        "adapter_schema": SCHEMA,
        "post_composition_phase_verified": True,
        "dynamic_professional_currentness_verified": True,
        "professional_property_truth_closed_count": professional["closed"],
        "professional_open_execution_leaf_count": professional["open_exec"],
        "professional_open_semantic_leaf_count": professional["open_sem"],
        "dynamic_bytes_currentness_verified": True,
        "bytes_frontier_version": bytes_state["version"],
        "bytes_raw_python_source_bytes": bytes_state["raw"],
        "unsupported_source_drift_fails_closed": True,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
