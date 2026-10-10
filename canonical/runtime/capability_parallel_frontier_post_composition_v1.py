"""Post-composition live frontier planner.

The R1-R12 binding wave, same-subject composition, and whole-leaf scope layer
are already behind the current Professional frontier. This adapter bypasses
the obsolete sequential-root dynamic refresh and plans directly on the exact
content-addressed current frontier.

Professional phase identity is source-bound rather than work-id-bound: the
single candidate sourced from CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json and
mutating canonical:professional-quality must agree with the live Professional
property-truth counts. This prevents later phase renames from silently
regressing scheduling to the retired root-binding/composition phase.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA = "PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V2"
PROF_WORK = "PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION"
PROFESSIONAL_SOURCE_REL = (
    "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
)
PROFESSIONAL_MUTATION_KEY = "canonical:professional-quality"


class PostCompositionFrontierError(ValueError):
    pass


def _professional_row(frontier: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates = frontier.get("candidates")
    if not isinstance(candidates, list):
        raise PostCompositionFrontierError("CANDIDATES_INVALID")
    rows = []
    for row in candidates:
        if not isinstance(row, Mapping):
            continue
        mutation_keys = row.get("mutation_keys")
        if not isinstance(mutation_keys, list):
            mutation_keys = []
        if (
            row.get("source") == PROFESSIONAL_SOURCE_REL
            and PROFESSIONAL_MUTATION_KEY in mutation_keys
        ):
            rows.append(row)
    if len(rows) != 1:
        raise PostCompositionFrontierError(
            "POST_COMPOSITION_PROFESSIONAL_CANDIDATE_CARDINALITY"
        )
    return rows[0]


def _count(raw: Any, name: str, *, maximum: int = 24) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0 or raw > maximum:
        raise PostCompositionFrontierError(name + "_INVALID")
    return raw


def _assert_post_composition(frontier: Mapping[str, Any]) -> None:
    row = _professional_row(frontier)
    if row.get("evidence_acquisition_mode") != "READ_ONLY":
        raise PostCompositionFrontierError(
            "PROFESSIONAL_POST_COMPOSITION_NOT_READ_ONLY"
        )

    evidence = row.get("read_only_evidence")
    if not isinstance(evidence, Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_EVIDENCE_MISSING")

    source_set = frontier.get("scope", {}).get("source_set")
    if not isinstance(source_set, list):
        raise PostCompositionFrontierError("SOURCE_SET_INVALID")
    source_rows = [
        x
        for x in source_set
        if isinstance(x, Mapping) and x.get("path") == PROFESSIONAL_SOURCE_REL
    ]
    if len(source_rows) != 1:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_SOURCE_BINDING_CARDINALITY"
        )

    professional_path = core.ROOT / PROFESSIONAL_SOURCE_REL
    if not professional_path.is_file():
        raise PostCompositionFrontierError("PROFESSIONAL_SOURCE_UNAVAILABLE")
    actual_sha = core._git_blob_sha(professional_path)
    if source_rows[0].get("git_blob_sha") != actual_sha:
        raise PostCompositionFrontierError("PROFESSIONAL_SOURCE_SET_STALE")
    if evidence.get("source_git_blob_sha") != actual_sha:
        raise PostCompositionFrontierError("PROFESSIONAL_CANDIDATE_SOURCE_STALE")

    try:
        professional = json.loads(professional_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PostCompositionFrontierError("PROFESSIONAL_SOURCE_INVALID") from exc
    if not isinstance(professional, Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_SOURCE_INVALID")

    property_frontier = professional.get("property_truth_frontier")
    if not isinstance(property_frontier, Mapping):
        raise PostCompositionFrontierError(
            "PROFESSIONAL_PROPERTY_TRUTH_FRONTIER_MISSING"
        )

    total = _count(
        property_frontier.get("total_leaf_count"),
        "PROFESSIONAL_TOTAL_LEAF_COUNT",
    )
    if total != 24:
        raise PostCompositionFrontierError("PROFESSIONAL_TOTAL_LEAF_COUNT_NOT_24")
    verified = _count(
        property_frontier.get("verified_leaf_count"),
        "PROFESSIONAL_VERIFIED_LEAF_COUNT",
    )
    open_execution = _count(
        property_frontier.get("open_execution_leaf_count"),
        "PROFESSIONAL_OPEN_EXECUTION_LEAF_COUNT",
    )
    open_semantic = _count(
        property_frontier.get("open_semantic_leaf_count"),
        "PROFESSIONAL_OPEN_SEMANTIC_LEAF_COUNT",
    )
    if verified + open_execution + open_semantic != total:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_PROPERTY_TRUTH_PARTITION_INCOHERENT"
        )

    verified_ids = property_frontier.get("verified_leaf_ids")
    if not isinstance(verified_ids, list):
        raise PostCompositionFrontierError(
            "PROFESSIONAL_VERIFIED_LEAF_IDS_INVALID"
        )
    normalized_ids = [str(x) for x in verified_ids if isinstance(x, str) and x]
    if len(normalized_ids) != verified or len(set(normalized_ids)) != verified:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_VERIFIED_LEAF_IDS_COUNT_MISMATCH"
        )

    if evidence.get("whole_leaf_scope_complete_count") != 24:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_WHOLE_LEAF_SCOPE_NOT_24_OF_24"
        )
    if evidence.get("property_truth_closed_count") != verified:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_PROPERTY_TRUTH_COUNT_STALE"
        )
    if evidence.get("open_execution_leaf_count") != open_execution:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_OPEN_EXECUTION_COUNT_STALE"
        )
    if evidence.get("open_semantic_leaf_count") != open_semantic:
        raise PostCompositionFrontierError(
            "PROFESSIONAL_OPEN_SEMANTIC_COUNT_STALE"
        )

    candidate_ids = evidence.get("verified_property_truth_leaf_ids")
    if not isinstance(candidate_ids, list):
        raise PostCompositionFrontierError(
            "PROFESSIONAL_CANDIDATE_VERIFIED_IDS_INVALID"
        )
    if set(candidate_ids) != set(normalized_ids) or len(candidate_ids) != len(
        normalized_ids
    ):
        raise PostCompositionFrontierError(
            "PROFESSIONAL_CANDIDATE_VERIFIED_IDS_STALE"
        )


def plan_current_post_composition_frontier() -> dict[str, Any]:
    frontier = core.load_current_frontier()
    _assert_post_composition(frontier)
    out = core.plan_parallel_frontier(frontier)
    return {
        **out,
        "adapter_schema": SCHEMA,
        "post_composition_phase_verified": True,
        "professional_phase_identity": "SOURCE_BOUND_PROPERTY_TRUTH_FRONTIER",
        "sequential_root_dynamic_refresh_bypassed": True,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
