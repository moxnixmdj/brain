"""Authenticated TLAC/MREL shared-signature guard V1.

This guard proves one narrow negative fact about discrimination:
the shared source-property bundle

  loss absorption + recapitalisation + resolution

cannot distinguish TLAC from MREL because both concepts independently entail
those properties in their separately authenticated source scopes.

It does NOT prove concept equivalence, coextension, disjointness, or candidate-
universe completeness. It prevents reverse-classification from a non-separating
property bundle.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

SCHEMA = "PROJECT_BRAIN_TLAC_MREL_SHARED_SIGNATURE_GUARD_V1"

SHARED_PROPERTIES = (
    "DISPOSITION::LOSS_ABSORPTION",
    "FUNCTION::LOSS_ABSORPTION",
    "FUNCTION::RECAPITALISATION",
    "REGIME::RESOLUTION",
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
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def verify_shared_signature(
    *,
    regcap_repo_root=None,
    mrel_repo_root=None,
    regcap_projection_verifier=regcap.verify_projection_pack,
    mrel_projection_verifier=mrel.verify_projection_pack,
) -> dict[str, Any]:
    try:
        tlac = {}
        mr = {}
        for prop in SHARED_PROPERTIES:
            tlac_out = regcap.verify_property_request(
                {
                    "schema": regcap.REQUEST_SCHEMA,
                    "scope_id": regcap.SCOPE_ID,
                    "concept_id": regcap.TLAC,
                    "property_id": prop,
                },
                repo_root=regcap_repo_root,
            )
            if regcap_projection_verifier is not regcap.verify_projection_pack:
                original = regcap.verify_projection_pack
                try:
                    regcap.verify_projection_pack = regcap_projection_verifier
                    tlac_out = regcap.verify_property_request(
                        {
                            "schema": regcap.REQUEST_SCHEMA,
                            "scope_id": regcap.SCOPE_ID,
                            "concept_id": regcap.TLAC,
                            "property_id": prop,
                        },
                        repo_root=regcap_repo_root,
                    )
                finally:
                    regcap.verify_projection_pack = original

            mrel_out = mrel.verify_property_request(
                {
                    "schema": mrel.REQUEST_SCHEMA,
                    "scope_id": mrel.SCOPE_ID,
                    "concept_id": mrel.MREL,
                    "property_id": prop,
                },
                repo_root=mrel_repo_root,
                projection_verifier=mrel_projection_verifier,
            )

            if tlac_out.get("pass") is not True:
                return _base(
                    "FAIL_CLOSED",
                    reason="TLAC_PROPERTY_AUTHORITY_FAILED:" + prop,
                    tlac_result=tlac_out,
                )
            if mrel_out.get("pass") is not True:
                return _base(
                    "FAIL_CLOSED",
                    reason="MREL_PROPERTY_AUTHORITY_FAILED:" + prop,
                    mrel_result=mrel_out,
                )
            tlac[prop] = tlac_out
            mr[prop] = mrel_out

        return _base(
            "PASS__TLAC_MREL_SHARED_SIGNATURE_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            tlac_concept_id=regcap.TLAC,
            mrel_concept_id=mrel.MREL,
            shared_properties=list(SHARED_PROPERTIES),
            property_bundle_separates_pair=False,
            reverse_classification_from_shared_bundle_authorized=False,
            identity_discriminator_required=True,
            tlac_results=tlac,
            mrel_results=mr,
            theorem_boundary=(
                "ONLY_PROVES_THAT_THE_DECLARED_SHARED_PROPERTY_BUNDLE_HAS_THE_SAME_"
                "PREDICTED_VALUE_FOR_TLAC_AND_MREL__NO_EQUIVALENCE_DISJOINTNESS_"
                "COEXTENSION_OR_COMPLETE_CANDIDATE_UNIVERSE_CLAIM"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
