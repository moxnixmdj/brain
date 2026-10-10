"""Claim-scoped R12 material-defeater generator closure adapter V1.

This is the exact reuse bridge from the already-proved four-root architecture to
R12's remaining stronger CC_R3 obligation. It never treats a finite defeater
catalog or 8/8 contract clauses as totality. Positive CC_R3 requires a
claim-bound universal or lossless generator-closure certificate whose coverage
is itself independently verified.

This module grants CC_R3 only. R4, semantic property truth, quality,
acceptance, promotion, and terminal authority remain separate.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_MATERIAL_DEFEATER_GENERATOR_CLOSURE_V1"
CERT_SCHEMA="PROJECT_BRAIN_R12_MATERIAL_DEFEATER_GENERATOR_CERTIFICATE_V1"
PROPERTY_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
OBLIGATION="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION"
ALLOWED_BASES=frozenset({"UNIVERSAL_FORMAL_SCOPE_PROOF","LOSSLESS_DECOMPOSITION_OR_GENERATOR_CLOSURE"})

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "material_defeater_totality_proved":False,
        "cc_r3_terminal_closure_proved":False,
        "semantic_property_truth_authority":False,
        "r4_proof_realization_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def evaluate(r12:Mapping[str,Any], cert:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(r12,Mapping) or not isinstance(cert,Mapping):
        return _fail("INPUT_NOT_MAPPING")
    if r12.get("property_claim_id")!=PROPERTY_CLAIM_ID or r12.get("scope_claim_id")!=SCOPE_CLAIM_ID:
        return _fail("R12_CLAIM_IDENTITY_DRIFT")
    if r12.get("leaf_id")!=LEAF_ID:
        return _fail("R12_LEAF_ID_DRIFT")
    d=r12.get("derived") or {}
    if d.get("all_eight_root_contract_clauses_verified") is not True or d.get("verified_clause_count")!=8:
        return _fail("R12_ROOT_CONTRACT_NOT_CLOSED")
    residual=r12.get("stronger_target_residual") or {}
    if residual.get("obligation")!=OBLIGATION or residual.get("state")!="OPEN":
        return _fail("R12_STRONGER_RESIDUAL_IDENTITY_DRIFT")
    if r12.get("cc_r3_terminal_closure_proved") is not False:
        return _fail("R12_CC_R3_PRESTATE_INVALID")

    if cert.get("schema")!=CERT_SCHEMA:
        return _fail("CERT_SCHEMA_INVALID")
    required={
        "property_claim_id":PROPERTY_CLAIM_ID,
        "scope_claim_id":SCOPE_CLAIM_ID,
        "leaf_id":LEAF_ID,
        "obligation":OBLIGATION,
    }
    for k,v in required.items():
        if cert.get(k)!=v:
            return _fail("CERT_BINDING_MISMATCH:"+k)
    if cert.get("proof_basis") not in ALLOWED_BASES:
        return _fail("CERT_PROOF_BASIS_NOT_SOUND_ROUTE")
    for k in (
        "scope_complete",
        "generator_or_universal_cover_complete",
        "all_material_defeaters_in_scope_covered",
        "uncovered_material_defeater_complement_empty",
        "decision_null_or_resolved_for_every_covered_defeater",
        "independent_verified",
        "content_addressed",
        "fail_closed_on_unknown",
    ):
        if cert.get(k) is not True:
            return _fail("CERT_PREMISE_UNPROVED:"+k)
    if cert.get("finite_catalog_only") is not False:
        return _fail("FINITE_CATALOG_CANNOT_AUTHORIZE_TOTALITY")
    if cert.get("eight_clause_count_only") is not False:
        return _fail("CLAUSE_COUNT_CANNOT_AUTHORIZE_TOTALITY")
    if cert.get("unknown_remainder") not in (None,[],{},"NONE"):
        return _fail("UNKNOWN_REMAINDER_NONEMPTY")
    verifier=cert.get("independent_verifier_id")
    if not isinstance(verifier,str) or not verifier.strip():
        return _fail("INDEPENDENT_VERIFIER_ID_REQUIRED")

    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__R12_MATERIAL_DEFEATER_TOTALITY_FROM_CLAIM_SCOPED_UNIVERSAL_OR_GENERATOR_CLOSURE__CC_R3_ONLY",
        "property_claim_id":PROPERTY_CLAIM_ID,"scope_claim_id":SCOPE_CLAIM_ID,
        "leaf_id":LEAF_ID,"obligation":OBLIGATION,
        "proof_basis":cert.get("proof_basis"),
        "material_defeater_totality_proved":True,
        "cc_r3_terminal_closure_proved":True,
        "semantic_property_truth_authority":False,
        "r4_proof_realization_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,
    }
