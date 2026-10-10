"""Loss-absorbing cushion regulatory-capital grounding V6.

V6 preserves V5, including its authenticated TLAC/MREL recomposition, and adds
the two remaining bounded pair revalidations:
    {CCoB, MREL}
    {CCyB, MREL}

The historical three-rival result is used only as a partition over
{CCoB, CCyB, TLAC}. MREL remains alive until an independently authenticated
pair discriminator resolves the exact surviving pair.

No pair result becomes global concept identity or open-world completeness.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v5 as v5
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as pair

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V6"
FOUR = tuple(sorted((regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL)))


def _eligible_anchor_pair(base: Mapping[str, Any]) -> tuple[str | None, str]:
    if sorted(str(x) for x in base.get("candidate_concept_ids") or []) != list(FOUR):
        return None, "EXPANDED_FRONTIER_NOT_EXACT_FOUR_CONCEPT_INVENTORY"
    if base.get("candidate_set_complete_relative_to_bound_inventory") is not True:
        return None, "FOUR_CONCEPT_BOUND_INVENTORY_COMPLETENESS_NOT_PROVED"
    if sorted(str(x) for x in base.get("expanded_candidate_ids_added") or []) != [mrel.MREL]:
        return None, "EXPANSION_IS_NOT_EXACTLY_MREL"
    if base.get("legacy_v3_relative_selection_authority") is not True:
        return None, "LEGACY_THREE_RIVAL_SELECTION_NOT_AUTHENTICATED"

    selected = str(base.get("legacy_v3_relative_selected_concept_id") or "")
    if selected not in {regcap.CCOB, regcap.CCYB}:
        return None, "LEGACY_SELECTION_NOT_CCOB_OR_CCYB"

    survivors = sorted(
        str(x)
        for x in base.get("legacy_v3_bound_rival_surviving_concept_ids") or []
    )
    if survivors != [selected]:
        return None, "LEGACY_SURVIVOR_SET_NOT_EXACT_SELECTED_ANCHOR"

    context = base.get("context_signature_result")
    if not isinstance(context, Mapping) or context.get("semantic_truth_authority") is not True:
        return None, "LEGACY_CONTEXT_SEMANTIC_TRUTH_NOT_AUTHENTICATED"

    return selected, "ELIGIBLE_EXACT_ANCHOR_MREL_SURVIVOR_PAIR"


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
    pair_projection_verifier=pair.verify_projection_pack,
) -> dict[str, Any]:
    base = v5.ground(
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
            "anchor_mrel_revalidation_attempted": False,
            "anchor_mrel_revalidation_reason": "STRONGER_SOURCE_LOCAL_IDENTITY_ALREADY_PROVED",
        })
        return out

    if (
        base.get("relative_selection_authority") is True
        and base.get("relative_selected_concept_id")
    ):
        out.update({
            "anchor_mrel_revalidation_attempted": False,
            "anchor_mrel_revalidation_reason": "V5_CURRENT_FOUR_RIVAL_SELECTION_ALREADY_REPROVED",
        })
        return out

    anchor, reason = _eligible_anchor_pair(base)
    if anchor is None:
        out.update({
            "anchor_mrel_revalidation_attempted": False,
            "anchor_mrel_revalidation_reason": reason,
        })
        return out

    pair_id = pair.CCOB_MREL if anchor == regcap.CCOB else pair.CCYB_MREL
    resolved = pair.resolve_relative(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        pair_id=pair_id,
        candidate_concept_ids=[anchor, mrel.MREL],
        repo_root=repo_root,
        projection_verifier=pair_projection_verifier,
    )
    out["anchor_mrel_revalidation_attempted"] = True
    out["anchor_mrel_pair_id"] = pair_id
    out["anchor_mrel_pair_result"] = resolved

    if resolved.get("status") == "FAIL_CLOSED":
        out.update({
            "anchor_mrel_revalidation_preserved_safe_v5_open_state": True,
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "bound_rival_surviving_concept_ids": [],
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
        })
        return out

    if resolved.get("relative_selection_authority") is not True:
        out.update({
            "status": "OPEN__ANCHOR_MREL_PAIR_REMAINS_UNRESOLVED",
            "pass": True,
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "bound_rival_surviving_concept_ids": [anchor, mrel.MREL],
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
            "fully_semantically_bound": False,
            "opaque_remainder_required": True,
            "candidate_universe_complete": False,
            "open_world_candidate_set_complete": False,
            "anchor_mrel_revalidation_reason": "NO_AUTHENTICATED_PAIR_SPECIFIC_MARKER",
            "boundary": (
                "LEGACY_THREE_RIVAL_CONTEXT_REDUCED_THE_OLD_SUBSET_TO_ONE_ANCHOR__"
                "MREL_REMAINS_ALIVE__NO_PAIR_SPECIFIC_MARKER_MEANS_NO_UNIQUE_SELECTION"
            ),
        })
        return out

    selected = str(resolved.get("selected_concept_id") or "")
    if selected not in {anchor, mrel.MREL}:
        out.update({
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "PAIR_DISCRIMINATOR_SELECTED_OUTSIDE_DECLARED_PAIR",
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
        })
        return out

    out.update({
        "status": "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
        "pass": True,
        "semantic_truth_authority": True,
        "relative_selection_authority": True,
        "relative_selected_concept_id": selected,
        "bound_rival_surviving_concept_ids": [selected],
        "four_concept_relative_selection_reproved": True,
        "four_concept_relative_selection_basis": {
            "legacy_three_rival_survivor": anchor,
            "expanded_candidate_added": mrel.MREL,
            "pair_id": pair_id,
            "pair_scope_id": pair.PAIR_SCOPE[pair_id],
            "pair_observation_id": pair.OBSERVATION_ID,
            "pair_selected_concept_id": selected,
        },
        "candidate_set_complete_relative_to_bound_inventory": True,
        "candidate_universe_complete": False,
        "open_world_candidate_set_complete": False,
        "semantic_identity_authority": False,
        "global_phrase_identity_authority": False,
        "mapped_concept_id": None,
        "fully_semantically_bound": False,
        "opaque_remainder_required": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "UNIQUE_ONLY_RELATIVE_TO_DECLARED_FOUR_CONCEPT_BOUND_INVENTORY__"
            "OLD_THREE_RIVAL_CONTEXT_PARTITIONS_ONLY_ITS_OWN_SUBSET__"
            "MREL_IS_RETAINED_UNTIL_AUTHENTICATED_CCOB_MREL_OR_CCYB_MREL_PAIR_REPLAY__"
            "NO_OPEN_WORLD_OR_GLOBAL_CONCEPT_IDENTITY"
        ),
    })
    return out
