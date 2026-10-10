"""Loss-absorbing cushion regulatory-capital grounding V4.

V4 preserves V3 source-local identity proofs, but replaces V1's three-concept
property candidate frontier with the four-concept V2 frontier that includes
MREL. Any V3 relative selection computed only over CCoB/CCyB/TLAC is retained as
historical evidence but loses current relative-selection authority whenever the
expanded inventory adds a previously unconsidered candidate.

This layer deliberately does not invent a four-concept discriminator matrix.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v3 as v3
from canonical.runtime import regcap_property_candidate_discovery_v2 as discovery
from canonical.runtime.bounded_participial_disposition_v1 import SEMANTIC_ATOM

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V4"


def _clear_relative_selection(out: dict[str, Any], base: Mapping[str, Any]) -> None:
    out["legacy_v3_relative_selection_authority"] = bool(
        base.get("relative_selection_authority")
    )
    out["legacy_v3_relative_selected_concept_id"] = base.get(
        "relative_selected_concept_id"
    )
    out["legacy_v3_bound_rival_surviving_concept_ids"] = list(
        base.get("bound_rival_surviving_concept_ids") or []
    )
    out["relative_selection_authority"] = False
    out["relative_selected_concept_id"] = None
    out["bound_rival_surviving_concept_ids"] = []
    out["semantic_identity_authority"] = False
    out["mapped_concept_id"] = None


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
) -> dict[str, Any]:
    base = v3.ground(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        repo_root=repo_root,
    )
    out = dict(base)
    out["schema"] = SCHEMA

    if base.get("status") == "FAIL_CLOSED":
        return out

    if (
        base.get("semantic_identity_authority") is True
        and base.get("mapped_concept_id")
    ):
        out.update({
            "expanded_candidate_discovery_attempted": False,
            "expanded_candidate_discovery_reason": (
                "STRONGER_SOURCE_LOCAL_IDENTITY_ALREADY_PROVED"
            ),
            "open_world_candidate_set_complete": False,
        })
        return out

    if base.get("source_constraint_proved") is not True:
        out.update({
            "expanded_candidate_discovery_attempted": False,
            "expanded_candidate_discovery_reason": (
                "LOSS_ABSORPTION_SOURCE_CONSTRAINT_NOT_PROVED"
            ),
            "open_world_candidate_set_complete": False,
        })
        return out

    expanded = discovery.discover(
        {
            "schema": discovery.REQUEST_SCHEMA,
            "scope_id": discovery.SCOPE_ID,
            "property_id": SEMANTIC_ATOM,
        },
        repo_root=repo_root,
    )
    out["expanded_candidate_discovery_attempted"] = True
    out["expanded_candidate_discovery"] = expanded

    if expanded.get("status") == "FAIL_CLOSED":
        _clear_relative_selection(out, base)
        out.update({
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "EXPANDED_CANDIDATE_DISCOVERY_FAIL_CLOSED",
            "candidate_concept_ids": [],
            "candidate_generation_authority": False,
            "candidate_set_complete_relative_to_bound_inventory": False,
            "open_world_candidate_set_complete": False,
            "opaque_remainder_required": True,
            "boundary": (
                "FOUR_CONCEPT_CANDIDATE_AUTHORITY_FAILED__STALE_THREE_RIVAL_"
                "FRONTIER_MUST_NOT_BE_USED_AS_IF_CURRENT"
            ),
        })
        return out

    expanded_ids = list(expanded.get("candidate_concept_ids") or [])
    old_ids = list(base.get("candidate_concept_ids") or [])
    out.update({
        "candidate_concept_ids": expanded_ids,
        "candidate_generation_authority": bool(
            expanded.get("candidate_generation_authority")
        ),
        "candidate_set_complete_relative_to_bound_inventory": bool(
            expanded.get("candidate_set_complete_relative_to_bound_inventory")
        ),
        "open_world_candidate_set_complete": False,
        "expanded_bound_concept_inventory": list(
            expanded.get("bound_concept_inventory") or []
        ),
        "next_positive_evidence_targets_by_candidate": {
            row["concept_id"]: list(row.get("positive_evidence_targets") or [])
            for row in expanded.get("candidates") or []
            if isinstance(row, Mapping) and row.get("concept_id")
        },
        "opaque_remainder_required": True,
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
    })

    added = sorted(set(expanded_ids) - set(old_ids))
    out["expanded_candidate_ids_added"] = added

    if base.get("relative_selection_authority") is True and added:
        _clear_relative_selection(out, base)
        out.update({
            "status": (
                "OPEN__LEGACY_THREE_RIVAL_SELECTION_INVALIDATED_BY_"
                "EXPANDED_BOUND_INVENTORY"
            ),
            "pass": True,
            "relative_selection_revalidation_required": True,
            "relative_selection_revalidation_reason": (
                "MREL_OR_OTHER_NEW_BOUND_CANDIDATE_WAS_NOT_IN_THE_V3_"
                "CONTRASTIVE_MATRIX"
            ),
        })
    else:
        out.update({
            "status": "OPEN__EXPANDED_REGCAP_CANDIDATE_FRONTIER",
            "pass": True,
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "relative_selection_revalidation_required": bool(added),
        })

    out["boundary"] = (
        "FOUR_CONCEPT_BOUND_CANDIDATE_FRONTIER_INCLUDES_MREL__"
        "LEGACY_THREE_RIVAL_RELATIVE_SELECTION_IS_NOT_REUSED_AFTER_EXPANSION__"
        "NO_FOUR_CONCEPT_IDENTITY_OR_OPEN_WORLD_CANDIDATE_COMPLETENESS"
    )
    return out
