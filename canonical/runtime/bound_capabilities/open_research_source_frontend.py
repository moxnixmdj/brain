#!/usr/bin/env python3
"""Model-independent source front-end for broad open research objectives.

This composes already-qualified decomposition, source-candidate discovery,
provenance verification, exact ROR organization identity binding, and a
fail-closed primary-publication/objective-relevance verifier. It deliberately
stops before evidence extraction, factual correctness, evidence sufficiency,
or answer synthesis.
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
    primary_relevance=_load_sibling("source_primary_relevance_verify")

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
    if not verified:
        return {
            "schema":SCHEMA,
            "status":"SOURCE_PROVENANCE_BLOCKED",
            "objective":objective,
            "decomposition":decomposition,
            "discovery":discovered,
            "provenance_verifications":verifications,
            "authority_identity_verifications":[],
            "primary_relevance_verifications":[],
            "next_required_capability":"MODEL_INDEPENDENT_SOURCE_CANDIDATE_PROVENANCE_VERIFICATION_V1",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

    authority_verifications=[]
    for item in verified:
        provenance=item["verification"]
        if provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
            continue
        candidate=dict(item["candidate"])
        if provenance.get("final_url"):
            candidate["final_url"]=provenance.get("final_url")
        if provenance.get("final_host"):
            candidate["final_host"]=provenance.get("final_host")
        bound=authority_identity.bind_candidate(candidate,timeout=timeout)
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

    primary_relevance_verifications=[]
    for item in authority_verified:
        checked=primary_relevance.verify(
            objective,
            item["candidate"],
            item["provenance"],
            item["authority_identity"],
            timeout=timeout,
        )
        primary_relevance_verifications.append({
            "candidate":item["candidate"],
            "provenance":item["provenance"],
            "authority_identity":item["authority_identity"],
            "primary_relevance":checked,
        })

    primary_verified=[
        x for x in primary_relevance_verifications
        if x["primary_relevance"].get("primary_source_status")=="VERIFIED"
    ]
    relevance_verified=[
        x for x in primary_relevance_verifications
        if x["primary_relevance"].get("relevance_status")=="VERIFIED"
    ]
    primary_relevance_verified=[
        x for x in primary_relevance_verifications
        if x["primary_relevance"].get("status")=="PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFIED"
    ]
    evidence_ready=bool(primary_relevance_verified)

    return {
        "schema":SCHEMA,
        "status":"SOURCE_FRONTEND_READY",
        "objective":objective,
        "question_shape":decomposition.get("question_shape"),
        "decomposition":decomposition,
        "discovery":discovered,
        "provenance_verifications":verifications,
        "provenance_verified_candidate_count":len(verified),
        "authority_identity_verifications":authority_verifications,
        "authority_identity_verified_candidate_count":len(authority_verified),
        "authority_identity_claim_scope":"HOST_TO_ROR_ORGANIZATION_DOMAIN_BINDING_ONLY",
        "primary_relevance_verifications":primary_relevance_verifications,
        "primary_source_verified_candidate_count":len(primary_verified),
        "relevance_verified_candidate_count":len(relevance_verified),
        "primary_relevance_verified_candidate_count":len(primary_relevance_verified),
        "primary_source_claim_scope":"EXACT_ROR_BOUND_ORGANIZATION_HOSTED_DOCUMENT_PUBLICATION_PROVENANCE_ONLY",
        "relevance_claim_scope":"EXACT_OBJECTIVE_ANCHOR_COVERAGE_ON_LIVE_DOCUMENT_METADATA_ONLY",
        "authority_verified_candidate_count":0,
        "role_progress":{
            "SOURCE_DISCOVERY":(
                "PRIMARY_RELEVANT_ORGANIZATION_PUBLICATIONS_AVAILABLE"
                if evidence_ready else
                "CANDIDATES_WITH_PROVENANCE_AND_ORGANIZATION_IDENTITY_AVAILABLE"
                if identity_ready else
                "CANDIDATES_WITH_PROVENANCE_IDENTITY_AVAILABLE"
            ),
            "EVIDENCE_ACQUISITION":(
                "PRIMARY_RELEVANT_SOURCE_AVAILABLE__EVIDENCE_EXTRACTION_REQUIRED"
                if evidence_ready else
                "BLOCKED_ON_PRIMARY_SOURCE_AND_RELEVANCE_VERIFICATION"
                if identity_ready else
                "BLOCKED_ON_AUTHORITY_IDENTITY_PRIMARY_SOURCE_AND_RELEVANCE_VERIFICATION"
            ),
            "EVIDENCE_EXTRACTION":(
                "REQUIRES_GROUNDING" if evidence_ready else "NOT_STARTED"
            ),
            "RELATION_EVALUATION":"NOT_STARTED",
            "DECISION_SYNTHESIS_AND_VERIFICATION":"NOT_STARTED",
        },
        "next_required_capability":(
            "MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_PRIMARY_RELEVANT_SOURCE"
            if evidence_ready else
            "MODEL_INDEPENDENT_PRIMARY_SOURCE_AND_OBJECTIVE_RELEVANCE_VERIFICATION"
            if identity_ready else
            "MODEL_INDEPENDENT_SOURCE_AUTHORITY_IDENTITY_PRIMARY_SOURCE_AND_RELEVANCE_VERIFICATION"
        ),
        "authority_identity_claims_made":identity_ready,
        "authority_claims_made":False,
        "primary_source_claims_made":bool(primary_verified),
        "relevance_claims_made":bool(relevance_verified),
        "factual_correctness_claims_made":False,
        "evidence_sufficiency_claims_made":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
