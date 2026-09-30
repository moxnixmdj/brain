#!/usr/bin/env python3
"""Model-independent source front-end for broad open research objectives.

Composes qualified decomposition, source-candidate discovery, retrieval
provenance, optional ROR organization identity metadata, and generic
provenance-bound fresh-page relevance/evidence extraction.

Organization identity and primary-source status are NOT universal admission
gates. Extracted units do not imply support, entailment, correctness, quality,
sufficiency, independence, or answer validity.
"""
from __future__ import annotations

import importlib.util
import pathlib

SCHEMA="PROJECT_BRAIN_OPEN_RESEARCH_SOURCE_FRONTEND_V1"

def _load_sibling(name):
    path=pathlib.Path(__file__).resolve().with_name(name+".py")
    spec=importlib.util.spec_from_file_location("project_brain_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _canon(value):
    return " ".join(str(value or "").strip().split())

def run(objective,decomposition,limit=12,timeout=15):
    objective=_canon(objective)
    if not objective:
        raise ValueError("OBJECTIVE_REQUIRED")
    if not isinstance(decomposition,dict) or decomposition.get("status")!="DECOMPOSED":
        raise ValueError("QUALIFIED_DECOMPOSITION_REQUIRED")
    if _canon(decomposition.get("objective"))!=objective:
        raise ValueError("DECOMPOSITION_OBJECTIVE_MISMATCH")
    roles=decomposition.get("roles")
    if not isinstance(roles,list) or not any(
        isinstance(x,dict) and x.get("role")=="SOURCE_DISCOVERY" for x in roles
    ):
        raise ValueError("SOURCE_DISCOVERY_ROLE_REQUIRED")

    discovery=_load_sibling("open_web_source_candidate_discovery")
    verifier=_load_sibling("source_candidate_provenance_verify")
    authority_identity=_load_sibling("source_authority_binding_ror")
    evidence_extractor=_load_sibling("provenance_relevant_evidence_extract")

    discovered=discovery.discover(objective,limit=limit,timeout=timeout)
    if discovered.get("status")!="CANDIDATES_DISCOVERED":
        return {
            "schema":SCHEMA,
            "status":"SOURCE_DISCOVERY_BLOCKED",
            "objective":objective,
            "decomposition":decomposition,
            "discovery":discovered,
            "provenance_verifications":[],
            "next_required_capability":"MODEL_INDEPENDENT_OPEN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

    verifications=[]
    for candidate in discovered.get("candidates") or []:
        verification=verifier.verify(candidate,timeout=timeout)
        verifications.append({
            "candidate":candidate,
            "verification":verification,
        })

    verified=[
        x for x in verifications
        if x["verification"].get("status") in {
            "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
            "RETRIEVAL_PROVENANCE_VERIFIED",
        }
    ]
    retrieval_verified=[
        x for x in verified
        if x["verification"].get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
    ]
    if not verified:
        return {
            "schema":SCHEMA,
            "status":"SOURCE_PROVENANCE_BLOCKED",
            "objective":objective,
            "decomposition":decomposition,
            "discovery":discovered,
            "provenance_verifications":verifications,
            "authority_identity_verifications":[],
            "objective_relevance_verifications":[],
            "evidence_extractions":[],
            "next_required_capability":"MODEL_INDEPENDENT_SOURCE_CANDIDATE_PROVENANCE_VERIFICATION_V1",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

    # Optional organization identity metadata. Failure here must not block generic
    # relevance or evidence extraction.
    authority_verifications=[]
    for item in retrieval_verified:
        candidate=dict(item["candidate"])
        provenance=item["verification"]
        if provenance.get("final_url"):
            candidate["final_url"]=provenance.get("final_url")
        if provenance.get("final_host"):
            candidate["final_host"]=provenance.get("final_host")
        try:
            bound=authority_identity.bind_candidate(candidate,timeout=timeout)
        except Exception as exc:
            bound={
                "status":"UNVERIFIED",
                "reason":"OPTIONAL_AUTHORITY_IDENTITY_LOOKUP_FAILED",
                "error_class":type(exc).__name__,
            }
        authority_verifications.append({
            "candidate":item["candidate"],
            "provenance":provenance,
            "authority_identity":bound,
        })
    authority_verified=[
        x for x in authority_verifications
        if x["authority_identity"].get("status")=="AUTHORITY_IDENTITY_VERIFIED"
    ]
    identity_ready=bool(authority_verified)

    evidence_extractions=[]
    for item in retrieval_verified:
        extracted=evidence_extractor.extract(
            objective,
            item["candidate"],
            item["verification"],
            timeout=timeout,
        )
        evidence_extractions.append({
            "candidate":item["candidate"],
            "provenance":item["verification"],
            "extraction":extracted,
        })

    relevance_verified=[
        x for x in evidence_extractions
        if x["extraction"].get("objective_relevance_status")=="VERIFIED"
        and (x["extraction"].get("relevance_verification") or {}).get("status")
            =="PROVENANCE_RELEVANT_SOURCE_VERIFIED"
    ]
    evidence_extracted=[
        x for x in evidence_extractions
        if x["extraction"].get("status")=="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
        and x["extraction"].get("evidence_extraction_status")=="VERIFIED"
        and int(x["extraction"].get("evidence_unit_count") or 0)>0
    ]
    relevance_ready=bool(relevance_verified)
    extraction_ready=bool(evidence_extracted)

    objective_relevance_verifications=[
        {
            "candidate":x["candidate"],
            "provenance":x["provenance"],
            "relevance":x["extraction"].get("relevance_verification") or {},
        }
        for x in evidence_extractions
        if x["extraction"].get("relevance_verification")
    ]

    return {
        "schema":SCHEMA,
        "status":"SOURCE_FRONTEND_READY",
        "objective":objective,
        "question_shape":decomposition.get("question_shape"),
        "decomposition":decomposition,
        "discovery":discovered,
        "provenance_verifications":verifications,
        "provenance_verified_candidate_count":len(verified),
        "retrieval_provenance_verified_candidate_count":len(retrieval_verified),
        "authority_identity_verifications":authority_verifications,
        "authority_identity_verified_candidate_count":len(authority_verified),
        "authority_identity_claim_scope":"OPTIONAL_HOST_TO_ROR_ORGANIZATION_DOMAIN_BINDING_METADATA_ONLY",
        "objective_relevance_verifications":objective_relevance_verifications,
        "relevance_verified_candidate_count":len(relevance_verified),
        "relevance_claim_scope":"FRESH_SAME_PROVENANCE_HOST_STRICT_BOUNDED_LEXICAL_OBJECTIVE_COVERAGE_ONLY",
        "evidence_extractions":evidence_extractions,
        "evidence_extracted_candidate_count":len(evidence_extracted),
        "evidence_extraction_claim_scope":"NORMALIZED_VISIBLE_TEXT_UNITS_WITH_OBJECTIVE_LEXICAL_BINDING_AND_HASHED_PROVENANCE_ONLY",
        "authority_verified_candidate_count":0,
        "primary_source_verified_candidate_count":0,
        "role_progress":{
            "SOURCE_DISCOVERY":(
                "PROVENANCE_VERIFIED_OBJECTIVE_RELEVANT_SOURCE_AVAILABLE"
                if relevance_ready else
                "RETRIEVAL_PROVENANCE_CANDIDATES_AVAILABLE"
                if retrieval_verified else
                "BIBLIOGRAPHIC_PROVENANCE_ONLY"
            ),
            "EVIDENCE_ACQUISITION":(
                "OBJECTIVE_GROUNDED_EVIDENCE_UNITS_AVAILABLE"
                if extraction_ready else
                "RELEVANT_SOURCE_AVAILABLE__EVIDENCE_EXTRACTION_REQUIRED"
                if relevance_ready else
                "BLOCKED_ON_OBJECTIVE_RELEVANCE_OR_RELEVANT_SOURCE_COVERAGE"
            ),
            "EVIDENCE_EXTRACTION":(
                "VERIFIED_NARROW_OBJECTIVE_GROUNDED_VISIBLE_TEXT_UNITS"
                if extraction_ready else
                "REQUIRES_GROUNDING" if relevance_ready else "NOT_STARTED"
            ),
            "RELATION_EVALUATION":(
                "REQUIRED_FROM_GROUNDED_UNITS" if extraction_ready else "NOT_STARTED"
            ),
            "DECISION_SYNTHESIS_AND_VERIFICATION":"NOT_STARTED",
        },
        "next_required_capability":(
            "MODEL_INDEPENDENT_EVIDENCE_RELATION_EVALUATION"
            if extraction_ready else
            "MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_RELEVANT_SOURCE"
            if relevance_ready else
            "MODEL_INDEPENDENT_OBJECTIVE_RELEVANCE_VERIFICATION_OR_RELEVANT_SOURCE_DISCOVERY"
            if retrieval_verified else
            "MODEL_INDEPENDENT_LIVE_RETRIEVAL_PROVENANCE"
        ),
        "authority_identity_claims_made":identity_ready,
        "authority_claims_made":False,
        "authority_identity_gate_required":False,
        "primary_source_gate_required":False,
        "primary_source_status_role":"OPTIONAL_METADATA_NOT_UNIVERSAL_RESEARCH_ADMISSION_GATE",
        "primary_source_claims_made":False,
        "relevance_claims_made":relevance_ready,
        "evidence_extraction_claims_made":extraction_ready,
        "evidence_relation_claims_made":False,
        "factual_correctness_claims_made":False,
        "evidence_quality_claims_made":False,
        "evidence_sufficiency_claims_made":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
