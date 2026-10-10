"""Fail-closed R12 semantic coverage-root frontier classifier.

This module does not grant semantic property truth or root-certificate authority.
It compresses the current R12 semantic residual after verified whole-domain scope
and lossless identity-carrier factorization.

Current intended interpretation:
- CC_R1 reality containment has sufficient verified material to construct a
  claim-scoped certificate, but no certificate is minted by this classifier.
- CC_R2 mission soundness still needs an explicit claim-to-authorized-mission
  semantic reduction.
- CC_R3 terminal closure is the substantive universal R12 semantic property and
  remains open.
- CC_R4 proof authority remains blocked until the same exact claim has valid
  content-addressed CC_R1/CC_R2/CC_R3 certificates and independent receipts.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_ROOT_CUT_V1"
R12_LEAF = "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
R12_CLAIM_ID = "05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"

EXPECTED = {
    "domain_status_prefix": "PASS__PYCOMPILE__8_OF_8_ADVERSARIAL_TESTS__24_OF_24_REAL_MANIFEST_LEAVES",
    "scope_status_prefix": "PASS__",
    "identity_status_prefix": "PASS__INDEPENDENT_SPRITE__PYCOMPILE__8_OF_8__12_OF_12_SEMANTIC_CLAIMS_UNIVERSAL_IDENTITY_FACTORIZATION",
    "bounded_status_prefix": "PASS__PINNED_EXACT_BYTES__25_OF_25__TWELVE_SCOPED_CAPABILITIES__R12_BOUNDED_SEMANTIC_AND_EXECUTION",
}

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "leaf_id": R12_LEAF,
        "claim_id": R12_CLAIM_ID,
        "root_states": {},
        "semantic_property_truth_authority": False,
        "root_certificate_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }

def _starts(doc: Mapping[str, Any], prefix: str) -> bool:
    return str(doc.get("status") or "").startswith(prefix)

def evaluate(
    *,
    domain_verification: Mapping[str, Any],
    scope_batch_verification: Mapping[str, Any],
    identity_verification: Mapping[str, Any],
    bounded_r12_verification: Mapping[str, Any],
) -> dict[str, Any]:
    if not all(isinstance(x, Mapping) for x in (
        domain_verification,
        scope_batch_verification,
        identity_verification,
        bounded_r12_verification,
    )):
        return _fail("INPUT_NOT_MAPPING")

    if not _starts(domain_verification, EXPECTED["domain_status_prefix"]):
        return _fail("WHOLE_DOMAIN_EQUIVALENCE_NOT_VERIFIED")
    replay = domain_verification.get("independent_replay") or {}
    if replay.get("real_manifest_passed") != 24 or replay.get("unique_claim_id_count") != 24:
        return _fail("WHOLE_DOMAIN_EQUIVALENCE_COUNT_DRIFT")

    if not _starts(scope_batch_verification, EXPECTED["scope_status_prefix"]):
        return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_VERIFIED")
    srep = scope_batch_verification.get("independent_replay") or {}
    if srep.get("domain_equivalence_pass_count") != 24:
        return _fail("SCOPE_BATCH_DOMAIN_COUNT_DRIFT")
    if srep.get("scope_complete_count") != 24:
        return _fail("SCOPE_BATCH_COVER_COUNT_DRIFT")
    if srep.get("property_truth_count") != 0:
        return _fail("SCOPE_BATCH_PROPERTY_SELF_PROMOTION")

    if not _starts(identity_verification, EXPECTED["identity_status_prefix"]):
        return _fail("IDENTITY_CARRIER_NOT_VERIFIED")
    if identity_verification.get("semantic_leaf_count") != 12:
        return _fail("IDENTITY_CARRIER_LEAF_COUNT_DRIFT")
    if identity_verification.get("universal_factorization_proved_count") != 12:
        return _fail("IDENTITY_CARRIER_FACTORIZATION_COUNT_DRIFT")
    irep = identity_verification.get("independent_replay") or {}
    if irep.get("r12_claim_id") != R12_CLAIM_ID:
        return _fail("R12_CLAIM_ID_DRIFT")
    theorem = identity_verification.get("theorem") or {}
    if theorem.get("finite_witness_set_used") is not False:
        return _fail("IDENTITY_CARRIER_FINITE_SAMPLE_FORBIDDEN")
    if theorem.get("semantic_information_loss") is not False:
        return _fail("IDENTITY_CARRIER_INFORMATION_LOSS")

    if not _starts(bounded_r12_verification, EXPECTED["bounded_status_prefix"]):
        return _fail("R12_BOUNDED_SEMANTIC_EVIDENCE_NOT_VERIFIED")
    projection = bounded_r12_verification.get("r12_projection") or {}
    if R12_LEAF not in (projection.get("contributes_to_leaf_ids") or []):
        return _fail("R12_BOUNDED_PROJECTION_LEAF_MISSING")
    if projection.get("bounded_subset_only") is not True:
        return _fail("R12_BOUNDED_EVIDENCE_SCOPE_DRIFT")
    if projection.get("semantic_leaf_credit") is not False:
        return _fail("R12_BOUNDED_EVIDENCE_SELF_PROMOTION")

    roots = {
        "CC_R1_REALITY_CONTAINMENT_V1": {
            "state": "MATERIALIZABLE_FROM_VERIFIED_EXISTING_PROOFS",
            "basis": [
                "WHOLE_ADMISSIBLE_R12_SEMANTIC_DOMAIN_EQUIVALENCE",
                "WHOLE_LEAF_SCOPE_COMPLETE",
                "LOSSLESS_IDENTITY_CARRIER_UNIVERSAL_FACTORIZATION",
            ],
            "remaining": "MINT_EXACT_CLAIM_SCOPED_CONTENT_ADDRESSED_CC_R1_CERTIFICATE_AND_INDEPENDENT_RECEIPT",
            "semantic_research_open": False,
        },
        "CC_R2_MISSION_SOUNDNESS_V1": {
            "state": "OPEN_SEMANTIC_PROOF",
            "basis": [
                "AUTHORIZED_MISSION_EXISTS",
                "R12_SEMANTIC_CLAIM_IS_FROZEN_AND_CONTENT_ADDRESSED",
            ],
            "remaining": "PROVE_EXPLICIT_CLAIM_SCOPED_REDUCTION_FROM_R12_SEMANTIC_GOOD_SET_TO_AUTHORIZED_MISSION_ACCEPTANCE",
            "semantic_research_open": True,
        },
        "CC_R3_TERMINAL_CLOSURE_V1": {
            "state": "OPEN_SEMANTIC_PROOF",
            "basis": [
                "R12_BOUNDED_SEMANTIC_EVIDENCE_EXISTS",
                "R12_WHOLE_DOMAIN_SCOPE_IS_FROZEN",
            ],
            "remaining": "PROVE_FOR_ALL_ADMISSIBLE_R12_SEMANTIC_WORLD_STATES_THAT_STILL_POSSIBLE_BEHAVIOR_SATISFIES_THE_R12_SEMANTIC_ACCEPTANCE_PROPERTY",
            "semantic_research_open": True,
            "bounded_evidence_is_not_totality": True,
        },
        "CC_R4_PROOF_AUTHORITY_V1": {
            "state": "DEPENDENCY_BLOCKED",
            "remaining": "AFTER_EXACT_SAME_CLAIM_CC_R1_CC_R2_CC_R3_CERTIFICATES_EXIST__BIND_CONTENT_ADDRESSED_VERIFIERS_INDEPENDENT_RECEIPTS_AND_CURRENTNESS",
            "semantic_research_open": False,
        },
    }
    open_semantic = [
        root for root, row in roots.items()
        if row.get("state") == "OPEN_SEMANTIC_PROOF"
    ]
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__R12_SEMANTIC_ROOT_CUT_COMPRESSED_TO_CC_R2_AND_CC_R3_SEMANTIC_PROOFS__CC_R1_MATERIALIZABLE__CC_R4_DEPENDENCY_BLOCKED__ZERO_PROPERTY_CREDIT",
        "leaf_id": R12_LEAF,
        "claim_id": R12_CLAIM_ID,
        "root_states": roots,
        "open_semantic_root_ids": open_semantic,
        "open_semantic_root_count": len(open_semantic),
        "certificate_materialization_root_ids": ["CC_R1_REALITY_CONTAINMENT_V1"],
        "dependency_blocked_root_ids": ["CC_R4_PROOF_AUTHORITY_V1"],
        "carrier_factorization_open": False,
        "whole_domain_scope_open": False,
        "bounded_r12_evidence_present": True,
        "semantic_property_truth_authority": False,
        "root_certificate_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        "next": "PROVE_CC_R2_CLAIM_TO_MISSION_REDUCTION_AND_CC_R3_UNIVERSAL_R12_SEMANTIC_PROPERTY_IN_PARALLEL__MATERIALIZE_CC_R1_CERTIFICATE_AS_NONRESEARCH_PLUMBING",
    }
