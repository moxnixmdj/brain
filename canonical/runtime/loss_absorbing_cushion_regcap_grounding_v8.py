"""Loss-absorbing cushion grounding V8.

V8 preserves V7 unless a checker-owned authority-domain candidate is supplied
for the already-bound four-way minimum-information request. The candidate never
replaces the original source or predicate identity. It contributes only one
additional authenticated governing-requirement observation.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v7 as v7
from canonical.runtime import regcap_four_way_authority_candidate_observation_v1 as candidate_observation
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

SCHEMA = "PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V8"
FOUR = tuple(sorted((regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL)))


def _exact_four(base: Mapping[str, Any]) -> bool:
    return (
        sorted(str(x) for x in base.get("candidate_concept_ids") or []) == list(FOUR)
        and base.get("candidate_set_complete_relative_to_bound_inventory") is True
    )


def ground(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
    governing_requirement_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base = v7.ground(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        repo_root=repo_root,
    )
    out = dict(base)
    out["schema"] = SCHEMA

    if governing_requirement_candidate is None:
        out["authority_candidate_observation_attempted"] = False
        return out
    if base.get("status") == "FAIL_CLOSED":
        return out
    if (
        base.get("relative_selection_authority") is True
        and base.get("relative_selected_concept_id")
    ) or (
        base.get("semantic_identity_authority") is True
        and base.get("mapped_concept_id")
    ):
        out["authority_candidate_observation_attempted"] = False
        out["authority_candidate_observation_reason"] = (
            "V7_ALREADY_HAS_STRONGER_OR_EQUAL_SELECTION"
        )
        return out
    if not _exact_four(base):
        out["authority_candidate_observation_attempted"] = False
        out["authority_candidate_observation_reason"] = (
            "EXACT_FOUR_CONCEPT_BOUND_INVENTORY_REQUIRED"
        )
        return out

    observed = candidate_observation.observe(
        governing_requirement_candidate,
        repo_root=repo_root,
    )
    out["authority_candidate_observation_attempted"] = True
    out["authority_candidate_observation_result"] = observed

    if observed.get("status") == "FAIL_CLOSED":
        out.update({
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "AUTHORITY_CANDIDATE_OBSERVATION_FAIL_CLOSED:"
            + str(observed.get("reason") or "UNKNOWN"),
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "semantic_identity_authority": False,
            "mapped_concept_id": None,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        })
        return out
    if observed.get("pass") is not True:
        out["authority_candidate_observation_reason"] = observed.get("status")
        return out
    if observed.get("semantic_truth_authority") is not True:
        out.update({
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "AUTHORITY_CANDIDATE_OBSERVATION_WITHOUT_SEMANTIC_AUTHORITY",
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        })
        return out

    selected = str(observed.get("selected_concept_id") or "")
    if selected not in FOUR:
        out.update({
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "AUTHORITY_CANDIDATE_SELECTED_OUTSIDE_FOUR_WAY_DOMAIN",
            "relative_selection_authority": False,
            "relative_selected_concept_id": None,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        })
        return out

    out.pop("minimum_policy_changing_information_request", None)
    out.update({
        "minimum_policy_changing_information_request_available": False,
        "minimum_policy_changing_information_request_superseded_by": (
            "AUTHORITY_CANDIDATE_GOVERNING_REQUIREMENT_OBSERVATION"
        ),
        "status": (
            "OPEN__UNIQUE_REGCAP_SELECTION_RELATIVE_TO_FOUR_CONCEPT_BOUND_INVENTORY"
        ),
        "pass": True,
        "semantic_truth_authority": True,
        "relative_selection_authority": True,
        "relative_selected_concept_id": selected,
        "bound_rival_surviving_concept_ids": [selected],
        "four_concept_relative_selection_reproved": True,
        "four_concept_relative_selection_basis": {
            "method": "CHECKER_OWNED_AUTHORITY_CANDIDATE_OBSERVATION",
            "scope_id": observed.get("scope_id"),
            "observation_id": observed.get("observation_id"),
            "observed_outcome": observed.get("observed_outcome"),
            "authority_sha256": observed.get("authority_sha256"),
            "raw_sha256": observed.get("raw_sha256"),
            "final_url": observed.get("final_url"),
            "selected_concept_id": selected,
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
            "ORIGINAL_SOURCE_AND_PREDICATE_IDENTITY_PRESERVED__"
            "ONE_ADDITIONAL_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION__"
            "UNIQUE_ONLY_RELATIVE_TO_DECLARED_FOUR_CONCEPT_BOUND_INVENTORY__"
            "NO_OPEN_WORLD_OR_GLOBAL_CONCEPT_IDENTITY"
        ),
    })
    return out
