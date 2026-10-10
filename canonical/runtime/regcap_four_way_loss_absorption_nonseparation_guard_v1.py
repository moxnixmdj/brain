"""Authenticated four-way regulatory-capital loss-absorption non-separation guard.

This guard proves one narrow negative classification fact:

    DISPOSITION::LOSS_ABSORPTION

is independently authenticated for CCoB, CCyB, TLAC, and MREL by the
already-bound necessary-property authorities. Therefore that property alone
cannot identify which of those four concepts a phrase denotes.

The guard grants no concept identity, equivalence, disjointness, candidate-
universe completeness, policy adequacy, execution, promotion, or terminal
authority. Its only purpose is to reject reverse classification from a shared
property and require an additional authenticated discriminator.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

SCHEMA = "PROJECT_BRAIN_REGCAP_FOUR_WAY_LOSS_ABSORPTION_NONSEPARATION_GUARD_V1"
SHARED_PROPERTY = "DISPOSITION::LOSS_ABSORPTION"
CONCEPTS = (
    regcap.CCOB,
    regcap.CCYB,
    regcap.TLAC,
    mrel.MREL,
)


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "candidate_universe_complete": False,
        "concept_identity_authority": False,
        "concept_equivalence_authority": False,
        "concept_disjointness_authority": False,
        "reverse_classification_authorized": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _request(authority, concept_id: str) -> dict[str, Any]:
    return {
        "schema": authority.REQUEST_SCHEMA,
        "scope_id": authority.SCOPE_ID,
        "concept_id": concept_id,
        "property_id": SHARED_PROPERTY,
    }


def verify_shared_loss_absorption(
    *,
    regcap_repo_root=None,
    mrel_repo_root=None,
) -> dict[str, Any]:
    """Authenticate the shared property and prove that it is non-separating."""
    try:
        results: dict[str, Any] = {}
        for concept in (regcap.CCOB, regcap.CCYB, regcap.TLAC):
            out = regcap.verify_property_request(
                _request(regcap, concept),
                repo_root=regcap_repo_root,
            )
            if out.get("pass") is not True:
                return _base(
                    "FAIL_CLOSED",
                    reason="REGCAP_PROPERTY_AUTHORITY_FAILED:" + concept,
                    failed_result=out,
                )
            results[concept] = out

        mrel_out = mrel.verify_property_request(
            _request(mrel, mrel.MREL),
            repo_root=mrel_repo_root,
        )
        if mrel_out.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="MREL_PROPERTY_AUTHORITY_FAILED:" + mrel.MREL,
                failed_result=mrel_out,
            )
        results[mrel.MREL] = mrel_out

        return _base(
            "PASS__FOUR_WAY_LOSS_ABSORPTION_PROPERTY_AUTHENTICATED_NONSEPARATING",
            passed=True,
            semantic_truth_authority=True,
            shared_property=SHARED_PROPERTY,
            candidate_concept_ids=list(CONCEPTS),
            property_entails_all_bound_candidates=True,
            property_separates_any_candidate=False,
            additional_authenticated_discriminator_required=True,
            authenticated_results=results,
            theorem_boundary=(
                "ONLY_PROVES_THAT_DISPOSITION_LOSS_ABSORPTION_IS_AUTHENTICATED_"
                "FOR_ALL_FOUR_DECLARED_BOUND_CANDIDATES_AND_THEREFORE_CANNOT_"
                "BY_ITSELF_SELECT_ONE_OF_THEM__NO_OPEN_WORLD_CANDIDATE_"
                "COMPLETENESS_IDENTITY_EQUIVALENCE_DISJOINTNESS_OR_TERMINAL_CLAIM"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
