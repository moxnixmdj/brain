"""Loss-absorbing cushion regulatory-capital grounding V7.

V7 preserves V6 and closes one composition gap for the declared four-concept
bound inventory {CCoB, CCyB, TLAC, MREL}.

If V6 remains unresolved but the exact four-way inventory is authenticated, V7
replays all three independently authenticated MREL pair discriminators against
the same source context:
    {CCoB, MREL}
    {CCyB, MREL}
    {TLAC, MREL}

Only unanimous MREL selection across all three exact pair scopes is lifted to a
four-way relative selection. A conflicting positive selection fails closed. Any
missing pair discriminator leaves the four-way state open.

This is bounded relative selection only. It grants no global concept identity,
open-world ontology completeness, policy adequacy, execution, acceptance,
promotion, or terminal authority.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v6 as v6
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as regpair
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlacpair

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V7"
FOUR = tuple(sorted((regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL)))


def _exact_four(base: Mapping[str, Any]) -> bool:
    return (
        sorted(str(x) for x in base.get("candidate_concept_ids") or []) == list(FOUR)
        and base.get("candidate_set_complete_relative_to_bound_inventory") is True
    )


def _fail(out: dict[str, Any], reason: str, **extra: Any) -> dict[str, Any]:
    out.pop("minimum_policy_changing_information_request", None)
    out.update({
        "minimum_policy_changing_information_request_available": False,
        "minimum_policy_changing_information_request_suppressed_by": "V7_FAIL_CLOSED",
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "relative_selection_authority": False,
        "relative_selected_concept_id": None,
        "bound_rival_surviving_concept_ids": [],
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    })
    return out


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
    regcap_pair_projection_verifier=regpair.verify_projection_pack,
    tlac_pair_projection_verifier=tlacpair.verify_projection_pack,
) -> dict[str, Any]:
    base = v6.ground(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        repo_root=repo_root,
        pair_projection_verifier=regcap_pair_projection_verifier,
    )
    out = dict(base)
    out["schema"] = SCHEMA

    if base.get("status") == "FAIL_CLOSED":
        return out

    if (
        base.get("semantic_identity_authority") is True
        and base.get("mapped_concept_id")
    ) or (
        base.get("relative_selection_authority") is True
        and base.get("relative_selected_concept_id")
    ):
        out.update({
            "all_pairs_mrel_lift_attempted": False,
            "all_pairs_mrel_lift_reason": "V6_ALREADY_HAS_STRONGER_OR_EQUAL_SELECTION",
        })
        return out

    if not _exact_four(base):
        out.update({
            "all_pairs_mrel_lift_attempted": False,
            "all_pairs_mrel_lift_reason": "EXACT_FOUR_CONCEPT_BOUND_INVENTORY_REQUIRED",
        })
        return out

    pair_results = {
        regpair.CCOB_MREL: regpair.resolve_relative(
            source_text,
            source_id=source_id,
            start=start,
            end=end,
            pair_id=regpair.CCOB_MREL,
            candidate_concept_ids=[regcap.CCOB, mrel.MREL],
            repo_root=repo_root,
            projection_verifier=regcap_pair_projection_verifier,
        ),
        regpair.CCYB_MREL: regpair.resolve_relative(
            source_text,
            source_id=source_id,
            start=start,
            end=end,
            pair_id=regpair.CCYB_MREL,
            candidate_concept_ids=[regcap.CCYB, mrel.MREL],
            repo_root=repo_root,
            projection_verifier=regcap_pair_projection_verifier,
        ),
        "TLAC_MREL": tlacpair.resolve_relative(
            source_text,
            source_id=source_id,
            candidate_concept_ids=[regcap.TLAC, mrel.MREL],
            repo_root=repo_root,
            projection_verifier=tlac_pair_projection_verifier,
        ),
    }
    out["all_pairs_mrel_lift_attempted"] = True
    out["all_pairs_mrel_results"] = pair_results

    for pair_id, result in pair_results.items():
        if result.get("status") == "FAIL_CLOSED":
            return _fail(
                out,
                "PAIR_REPLAY_FAIL_CLOSED:" + pair_id,
                failed_pair_id=pair_id,
                failed_pair_result=result,
            )

    selections = {
        pair_id: str(result.get("selected_concept_id") or "")
        for pair_id, result in pair_results.items()
        if result.get("relative_selection_authority") is True
    }
    non_mrel = {pid: cid for pid, cid in selections.items() if cid != mrel.MREL}
    if non_mrel and any(cid == mrel.MREL for cid in selections.values()):
        return _fail(
            out,
            "CONFLICTING_ALL_PAIR_CONTEXT_SELECTIONS",
            pair_selections=selections,
        )

    if len(selections) == 3 and set(selections.values()) == {mrel.MREL}:
        out.pop("minimum_policy_changing_information_request", None)
        out.update({
            "minimum_policy_changing_information_request_available": False,
            "minimum_policy_changing_information_request_superseded_by": (
                "UNANIMOUS_THREE_PAIR_MREL_LIFT"
            ),
            "status": "OPEN__UNIQUE_MREL_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY",
            "pass": True,
            "semantic_truth_authority": True,
            "relative_selection_authority": True,
            "relative_selected_concept_id": mrel.MREL,
            "bound_rival_surviving_concept_ids": [mrel.MREL],
            "four_concept_relative_selection_reproved": True,
            "four_concept_relative_selection_basis": {
                "method": "UNANIMOUS_THREE_PAIR_MREL_LIFT",
                "pair_ids": [regpair.CCOB_MREL, regpair.CCYB_MREL, "TLAC_MREL"],
                "selected_concept_id": mrel.MREL,
                "same_source_id": source_id,
            },
            "candidate_set_complete_relative_to_bound_inventory": True,
            "candidate_universe_complete": False,
            "open_world_candidate_set_complete": False,
            "semantic_identity_authority": False,
            "global_phrase_identity_authority": False,
            "mapped_concept_id": None,
            "fully_semantically_bound": False,
            "opaque_remainder_required": True,
            "all_pairs_mrel_lift_reason": "ALL_THREE_EXACT_PAIR_SCOPES_SELECT_MREL",
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "UNIQUE_ONLY_RELATIVE_TO_DECLARED_FOUR_CONCEPT_BOUND_INVENTORY__"
                "MREL_SELECTED_IN_EACH_EXACT_CCOB_MREL_CCYB_MREL_AND_TLAC_MREL_PAIR_SCOPE__"
                "NO_OPEN_WORLD_OR_GLOBAL_CONCEPT_IDENTITY"
            ),
        })
        return out

    out.update({
        "status": "OPEN__FOUR_WAY_CONTEXT_REMAINS_UNRESOLVED_AFTER_ALL_PAIR_REPLAY",
        "pass": True,
        "relative_selection_authority": False,
        "relative_selected_concept_id": None,
        "bound_rival_surviving_concept_ids": list(FOUR),
        "semantic_identity_authority": False,
        "mapped_concept_id": None,
        "fully_semantically_bound": False,
        "opaque_remainder_required": True,
        "all_pairs_mrel_lift_reason": "UNANIMOUS_MREL_SELECTION_NOT_PROVED",
        "pair_selections": selections,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "PAIR_EVIDENCE_INCOMPLETE_OR_NONUNANIMOUS__PRESERVE_FOUR_WAY_AMBIGUITY__"
            "ACQUIRE_ONLY_MINIMUM_ADDITIONAL_AUTHENTICATED_DISCRIMINATOR"
        ),
    })
    return out
