"""Post-composition live frontier planner.

The R1-R12 binding wave and same-subject composition are already verified.
This adapter reuses interval-robust frontier V2 on the current live frontier and
validates the professional lane by current semantic invariants, not by one
historical work-id or stale immutable snapshot.
"""
from __future__ import annotations
import json
from typing import Any, Mapping
from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA = "PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V1"
PROF_SOURCE = "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
PROF_MUTATION_KEY = "canonical:professional-quality"
PROF_AUTHORITY_KEY = "authority:professional-v7-subject"
TOTAL_LEAVES = 24


class PostCompositionFrontierError(ValueError):
    pass


def _contains(values: Any, target: str) -> bool:
    return isinstance(values, list) and target in values


def _professional_rows(frontier: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = frontier.get("candidates")
    if not isinstance(candidates, list):
        raise PostCompositionFrontierError("CANDIDATES_INVALID")
    rows = []
    for row in candidates:
        if not isinstance(row, Mapping):
            continue
        if row.get("source") != PROF_SOURCE:
            continue
        if not _contains(row.get("mutation_keys"), PROF_MUTATION_KEY):
            continue
        if not _contains(row.get("authority_keys"), PROF_AUTHORITY_KEY):
            continue
        rows.append(row)
    return rows


def _count(value: Any, reason: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PostCompositionFrontierError(reason)
    return value


def _assert_post_composition(frontier: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = _professional_rows(frontier)
    if len(rows) != 1:
        raise PostCompositionFrontierError(
            "POST_COMPOSITION_PROFESSIONAL_CANDIDATE_CARDINALITY"
        )
    row = rows[0]
    if row.get("evidence_acquisition_mode") != "READ_ONLY":
        raise PostCompositionFrontierError("PROFESSIONAL_POST_COMPOSITION_NOT_READ_ONLY")
    ev = row.get("read_only_evidence")
    if not isinstance(ev, Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_EVIDENCE_MISSING")

    scope = _count(
        ev.get("whole_leaf_scope_complete_count"),
        "PROFESSIONAL_SCOPE_COUNT_INVALID",
    )
    closed = _count(
        ev.get("property_truth_closed_count"),
        "PROFESSIONAL_PROPERTY_TRUTH_COUNT_INVALID",
    )
    open_exec = _count(
        ev.get("open_execution_leaf_count"),
        "PROFESSIONAL_OPEN_EXECUTION_COUNT_INVALID",
    )
    open_sem = _count(
        ev.get("open_semantic_leaf_count"),
        "PROFESSIONAL_OPEN_SEMANTIC_COUNT_INVALID",
    )
    ids = ev.get("verified_property_truth_leaf_ids")
    if not isinstance(ids, list) or any(not isinstance(x, str) or not x for x in ids):
        raise PostCompositionFrontierError("PROFESSIONAL_VERIFIED_LEAF_IDS_INVALID")
    if len(ids) != len(set(ids)) or len(ids) != closed:
        raise PostCompositionFrontierError("PROFESSIONAL_VERIFIED_LEAF_COUNT_MISMATCH")
    if scope != TOTAL_LEAVES:
        raise PostCompositionFrontierError("PROFESSIONAL_SCOPE_NOT_24_OF_24")
    if closed + open_exec + open_sem != TOTAL_LEAVES:
        raise PostCompositionFrontierError("PROFESSIONAL_LEAF_ACCOUNTING_NOT_TOTAL")
    if ev.get("semantic_shared_blocker_independently_verified") is not True:
        raise PostCompositionFrontierError("PROFESSIONAL_SEMANTIC_BLOCKER_NOT_VERIFIED")
    if ev.get("semantic_catalog_alone_can_close") is not False:
        raise PostCompositionFrontierError("PROFESSIONAL_SEMANTIC_CATALOG_BOUNDARY_DRIFT")

    professional_path = core.ROOT / PROF_SOURCE
    if not professional_path.is_file() or professional_path.is_symlink():
        raise PostCompositionFrontierError("PROFESSIONAL_CURRENT_SOURCE_MISSING")
    try:
        professional_doc = json.loads(professional_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_CURRENT_SOURCE_INVALID:" + type(exc).__name__
        ) from exc
    live = professional_doc.get("property_truth_frontier")
    if not isinstance(live, Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_CURRENT_FRONTIER_MISSING")
    comparisons = {
        "verified_leaf_count": closed,
        "open_execution_leaf_count": open_exec,
        "open_semantic_leaf_count": open_sem,
    }
    for key, expected in comparisons.items():
        if live.get(key) != expected:
            raise PostCompositionFrontierError(
                "PROFESSIONAL_CURRENT_EVIDENCE_DRIFT:" + key
            )
    live_ids = live.get("verified_leaf_ids")
    if not isinstance(live_ids, list) or live_ids != ids:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_CURRENT_EVIDENCE_DRIFT:verified_leaf_ids"
        )

    return {
        "property_truth_closed_count": closed,
        "open_execution_leaf_count": open_exec,
        "open_semantic_leaf_count": open_sem,
    }


def plan_current_post_composition_frontier() -> dict[str, Any]:
    frontier = core.load_current_frontier()
    professional = _assert_post_composition(frontier)
    out = core.plan_parallel_frontier(frontier)
    return {
        **out,
        "adapter_schema": SCHEMA,
        "post_composition_phase_verified": True,
        "professional_current_invariant_verified": True,
        "professional_property_truth_closed_count": professional[
            "property_truth_closed_count"
        ],
        "professional_open_execution_leaf_count": professional[
            "open_execution_leaf_count"
        ],
        "professional_open_semantic_leaf_count": professional[
            "open_semantic_leaf_count"
        ],
        "sequential_root_dynamic_refresh_bypassed": True,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
