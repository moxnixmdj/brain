"""Loss-absorbing cushion regulatory-capital grounding V5.

V5 composes two already-authenticated bounded refinements without inventing a
four-concept discriminator matrix:

1. V3 may reduce the legacy {CCoB, CCyB, TLAC} rival set to TLAC.
2. V4 expands the loss-absorption candidate inventory with MREL and correctly
   revokes that legacy three-rival selection.
3. Only when those facts make the remaining declared four-concept alternatives
   exactly {TLAC, MREL}, V5 replays the independently authenticated TLAC/MREL
   governing-requirement discriminator.

The result is selection only relative to the declared four-concept bound
inventory.  It never creates open-world identity.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v4 as v4
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as pair

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V5"
FOUR = tuple(sorted((regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL)))
PAIR = tuple(sorted((regcap.TLAC, mrel.MREL)))


def _eligible_pair_recomposition(base: Mapping[str, Any]) -> tuple[bool, str]:
    expanded = sorted(str(x) for x in base.get("candidate_concept_ids") or [])
    added = sorted(str(x) for x in base.get("expanded_candidate_ids_added") or [])
    legacy_survivors = sorted(
        str(x) for x in base.get("legacy_v3_bound_rival_surviving_concept_ids") or []
    )
    inferred_legacy = sorted(set(expanded) - set(added))

    checks = [
        (expanded == list(FOUR), "EXPANDED_FRONTIER_NOT_EXACT_FOUR_CONCEPT_INVENTORY"),
        (
            base.get("candidate_set_complete_relative_to_bound_inventory") is True,
            "FOUR_CONCEPT_BOUND_INVENTORY_COMPLETENESS_NOT_PROVED",
        ),
        (added == [mrel.MREL], "EXPANSION_IS_NOT_EXACTLY_MREL"),
        (
            inferred_legacy == sorted((regcap.CCOB, regcap.CCYB, regcap.TLAC)),
            "LEGACY_FRONTIER_NOT_EXACT_THREE_RIVAL_SET",
        ),
        (
            base.get("legacy_v3_relative_selection_authority") is True,
            "LEGACY_THREE_RIVAL_SELECTION_NOT_AUTHENTICATED",
        ),
        (
            base.get("legacy_v3_relative_selected_concept_id") == regcap.TLAC,
            "LEGACY_SELECTION_NOT_TLAC",
        ),
        (legacy_survivors == [regcap.TLAC], "LEGACY_SURVIVOR_SET_NOT_EXACT_TLAC"),
        (
            isinstance(base.get("context_signature_result"), Mapping)
            and base["context_signature_result"].get("semantic_truth_authority") is True,
            "LEGACY_CONTEXT_SEMANTIC_TRUTH_NOT_AUTHENTICATED",
        ),
    ]
    for ok, reason in checks:
        if not ok:
            return False, reason
    return True, "ELIGIBLE_EXACT_TLAC_MREL_SURVIVOR_PAIR"


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
    pair_projection_verifier=pair.verify_projection_pack,
) -> dict[str, Any]:
    base = v4.ground(
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
            "pair_recomposition_attempted": False,
            "pair_recomposition_reason": "STRONGER_SOURCE_LOCAL_IDENTITY_ALREADY_PROVED",
        })
        return out

    eligible, reason = _eligible_pair_recomposition(base)
    if not eligible:
        out.update({
            "pair_recomposition_attempted": False,
            "pair_recomposition_reason": reason,
        })
        return out

    resolved = pair.resolve_relative(
        source_text,
        source_id=source_id,
        candidate_concept_ids=list(PAIR),
        repo_root=repo_root,
        projection_verifier=pair_projection_verifier,
    )
    out["pair_recomposition_attempted"] = True
    out["tlac_mrel_pair_result"] = resolved

    if resolved.get("status") == "FAIL_CLOSED":
        out.update({
            "pair_recomposition_preserved_safe_v4_open_state": True,
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "bound_rival_surviving_concept_ids": [],
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
        })
        return out

    if resolved.get("relative_selection_authority") is not True:
        out.update({
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "bound_rival_surviving_concept_ids": [],
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
            "pair_recomposition_reason": "NO_AUTHENTICATED_TLAC_MREL_GOVERNING_REQUIREMENT_MARKER",
        })
        return out

    selected = str(resolved.get("selected_concept_id") or "")
    if selected not in PAIR:
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
            "legacy_three_rival_survivor": regcap.TLAC,
            "expanded_candidate_added": mrel.MREL,
            "pair_scope_id": pair.SCOPE_ID,
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
            "COMPOSED_FROM_AUTHENTICATED_THREE_RIVAL_TLAC_SURVIVOR_PLUS_"
            "AUTHENTICATED_TLAC_MREL_PAIR_DISCRIMINATOR__"
            "NO_OPEN_WORLD_OR_GLOBAL_CONCEPT_IDENTITY"
        ),
    })
    return out
