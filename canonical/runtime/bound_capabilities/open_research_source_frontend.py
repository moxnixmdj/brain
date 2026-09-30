#!/usr/bin/env python3
"""Model-independent source front-end for broad open research objectives.

This composes qualified decomposition, open-web discovery, live retrieval
provenance, generic deterministic BM25 objective relevance, fresh exact
same-source evidence extraction, and the independently verified bounded
objective-to-claim-spec/relation evaluator. ROR organization identity is
optional metadata, not an admission gate.

The frontend deliberately keeps factual correctness, evidence sufficiency,
source independence, causal inference, and decision-quality synthesis
unverified.
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

def _verification_status(item):
    return str(((item or {}).get("verification") or {}).get("status") or "")

def _provenance_verified(item):
    return _verification_status(item) in {
        "RETRIEVAL_PROVENANCE_VERIFIED",
        "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
    }

def _ranking_candidate(item):
    candidate=dict((item or {}).get("candidate") or {})
    verification=dict((item or {}).get("verification") or {})
    record_title=_canon(verification.get("record_title"))
    if record_title:
        candidate["record_title"]=record_title
    return candidate

def _rank_verified_pool(objective,items,relevance_ranker):
    items=[x for x in items if _provenance_verified(x)]
    if not items:
        return {
          "status":"RELEVANCE_UNRESOLVED",
          "reason":"PROVENANCE_VERIFIED_CANDIDATES_REQUIRED",
          "ranked_candidates":[],
          "output_verified":False,
        },None
    candidates=[_ranking_candidate(x) for x in items]
    relevance=relevance_ranker.rank(objective,candidates)
    ready=(
        relevance.get("status")=="LEXICAL_RELEVANCE_RANKED"
        and relevance.get("output_verified") is True
        and relevance.get("top_candidate_original_index") is not None
        and ((relevance.get("top_candidate_admission") or {}).get("verified") is True)
    )
    if not ready:
        return relevance,None
    index=int(relevance["top_candidate_original_index"])
    if not (0<=index<len(items)):
        return relevance,None
    selected=dict(items[index])
    selected["ranking_candidate"]=candidates[index]
    return relevance,selected

def _metadata_refined_query(relevance,selected):
    verification=dict((selected or {}).get("verification") or {})
    candidate=dict((selected or {}).get("candidate") or {})
    focus=_canon(((relevance.get("query_focus") or {}).get("query")))
    title=_canon(verification.get("record_title") or candidate.get("record_title") or candidate.get("title"))
    if not focus or not title:
        return None
    # Preserve the frozen subject query and append only provenance-verified
    # bibliographic title metadata. No source/domain/value is invented here.
    query=_canon(focus+" "+title)
    return query[:1200].rsplit(" ",1)[0] if len(query)>1200 else query

def _verify_discovery(discovered,verifier,timeout):
    out=[]
    for candidate in discovered.get("candidates") or []:
        verification=verifier.verify(candidate,timeout=timeout)
        out.append({"candidate":candidate,"verification":verification})
    return out

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
    relevance_ranker=_load_sibling("objective_relevance_bm25")
    evidence_extractor=_load_sibling("objective_evidence_unit_extract")
    claim_binder=_load_sibling("objective_claim_operand_binding")
    authority_identity=_load_sibling("source_authority_binding_ror")

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

    verifications=_verify_discovery(discovered,verifier,timeout)
    provenance_verified=[x for x in verifications if _provenance_verified(x)]
    retrieval_verified=[
        x for x in verifications if _verification_status(x)=="RETRIEVAL_PROVENANCE_VERIFIED"
    ]
    bibliographic_verified=[
        x for x in verifications if _verification_status(x)=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED"
    ]
    if not provenance_verified:
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
            "next_required_capability":"MODEL_INDEPENDENT_PROVENANCE_VERIFICATION_FOR_DISCOVERED_SOURCE",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

    initial_relevance,selected=_rank_verified_pool(
        objective,provenance_verified,relevance_ranker
    )
    relevance=initial_relevance
    selected_item=None
    selected_source_origin=None
    bibliographic_materialization=None
    refinement=None

    if selected is not None:
        selected_status=_verification_status(selected)
        if selected_status=="RETRIEVAL_PROVENANCE_VERIFIED":
            selected_item=selected
            selected_source_origin="INITIAL_LIVE_RETRIEVAL"
        elif selected_status=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED":
            materialized=verifier.materialize_retrieval(
                selected.get("candidate") or {},
                selected.get("verification") or {},
                timeout=timeout,
            )
            bibliographic_materialization={
                "candidate":selected.get("candidate"),
                "bibliographic_verification":selected.get("verification"),
                "materialization":materialized,
            }
            if materialized.get("status")=="RETRIEVAL_PROVENANCE_VERIFIED":
                selected_item={
                    "candidate":selected.get("candidate"),
                    "verification":materialized,
                    "ranking_candidate":selected.get("ranking_candidate"),
                }
                selected_source_origin="BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION"
            else:
                refined_query=_metadata_refined_query(initial_relevance,selected)
                if refined_query:
                    refined_discovery=discovery.discover(
                        objective,limit=limit,timeout=timeout,
                        query_override=refined_query,
                    )
                    refined_verifications=(
                        _verify_discovery(refined_discovery,verifier,timeout)
                        if refined_discovery.get("status")=="CANDIDATES_DISCOVERED"
                        else []
                    )
                    refined_retrieval=[
                        x for x in refined_verifications
                        if _verification_status(x)=="RETRIEVAL_PROVENANCE_VERIFIED"
                    ]
                    refined_relevance,refined_selected=_rank_verified_pool(
                        objective,refined_retrieval,relevance_ranker
                    )
                    refinement={
                        "query":refined_query,
                        "discovery":refined_discovery,
                        "provenance_verifications":refined_verifications,
                        "relevance":refined_relevance,
                    }
                    if refined_selected is not None:
                        selected_item=refined_selected
                        selected_source_origin="BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL"
                        relevance=refined_relevance

    relevance_ready=selected_item is not None
    authority_verifications=[]
    evidence_extractions=[]

    if selected_item is not None:
        candidate=dict(selected_item["candidate"])
        provenance=dict(selected_item["verification"])
        enriched=dict(candidate)
        if provenance.get("final_url"):
            enriched["final_url"]=provenance["final_url"]
        if provenance.get("final_host"):
            enriched["final_host"]=provenance["final_host"]
        try:
            optional_authority=authority_identity.bind_candidate(enriched,timeout=timeout)
        except Exception as exc:
            optional_authority={
                "status":"UNVERIFIED",
                "reason":"OPTIONAL_AUTHORITY_IDENTITY_LOOKUP_FAILED",
                "error_class":type(exc).__name__,
            }
        authority_verifications.append({
            "candidate":candidate,
            "provenance":provenance,
            "authority_identity":optional_authority,
            "used_for_admission":False,
        })
        extracted=evidence_extractor.extract(
            objective,candidate,provenance,relevance,timeout=timeout
        )
        evidence_extractions.append({
            "candidate":candidate,
            "provenance":provenance,
            "relevance":relevance,
            "selected_source_origin":selected_source_origin,
            "authority_identity_metadata":optional_authority,
            "authority_identity_used_for_admission":False,
            "extraction":extracted,
        })

    authority_verified=[
        x for x in authority_verifications
        if x["authority_identity"].get("status")=="AUTHORITY_IDENTITY_VERIFIED"
    ]
    evidence_extracted=[
        x for x in evidence_extractions
        if (x.get("extraction") or {}).get("status")=="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
        and int((x.get("extraction") or {}).get("evidence_unit_count") or 0)>0
    ]
    evidence_ready=bool(evidence_extracted)

    claim_relation_evaluations=[]
    if evidence_ready:
        for item in evidence_extracted:
            extraction=item.get("extraction") or {}
            try:
                bound=claim_binder.bind(objective,extraction,evaluate_relation=True)
            except Exception as exc:
                bound={
                    "status":"UNBOUND",
                    "reason":"CLAIM_SPEC_OR_RELATION_EVALUATION_FAILED",
                    "error_class":type(exc).__name__,
                    "error":str(exc)[:1000],
                    "model_dependency_count":0,
                    "incremental_spend_usd":0,
                }
            claim_relation_evaluations.append({
                "source_url":extraction.get("source_url"),
                "extraction":extraction,
                "binding":bound,
            })

    relation_evaluated=[
        item for item in claim_relation_evaluations
        if (item.get("binding") or {}).get("status") in {
            "CLAIM_SPEC_AND_OPERANDS_BOUND","CLAIM_SPEC_BOUND"
        }
        and isinstance((item.get("binding") or {}).get("relation_result"),dict)
        and ((item.get("binding") or {}).get("relation_result") or {}).get("output_verified") is True
        and ((item.get("binding") or {}).get("relation_result") or {}).get("status") in {
            "NUMERIC_RELATION_VERIFIED",
            "EXACT_TEXT_SUPPORT_VERIFIED",
            "EXACT_TEXT_SUPPORT_NOT_VERIFIED",
        }
    ]
    relation_ready=bool(relation_evaluated)

    return {
        "schema":SCHEMA,
        "status":"SOURCE_FRONTEND_READY",
        "objective":objective,
        "question_shape":decomposition.get("question_shape"),
        "decomposition":decomposition,
        "discovery":discovered,
        "provenance_verifications":verifications,
        "provenance_verified_candidate_count":len(provenance_verified),
        "retrieval_provenance_verified_candidate_count":len(retrieval_verified),
        "bibliographic_provenance_verified_candidate_count":len(bibliographic_verified),
        "bibliographic_materialization":bibliographic_materialization,
        "metadata_anchored_refinement":refinement,
        "selected_source_origin":selected_source_origin,
        "authority_identity_verifications":authority_verifications,
        "authority_identity_verified_candidate_count":len(authority_verified),
        "authority_identity_claim_scope":"OPTIONAL_HOST_TO_ROR_ORGANIZATION_METADATA_ONLY__NOT_ADMISSION_GATE",
        "authority_identity_required_for_admission":False,
        "objective_relevance_verifications":[{
            "relevance":relevance,
            "candidate":selected_item["candidate"] if selected_item else None,
        }],
        "relevance_verified_candidate_count":1 if relevance_ready else 0,
        "relevance_claim_scope":"DETERMINISTIC_BM25_PLUS_FOCUSED_QUERY_TOKEN_COVERAGE_ADMISSION_ONLY",
        "evidence_extractions":evidence_extractions,
        "evidence_extracted_candidate_count":len(evidence_extracted),
        "claim_relation_evaluations":claim_relation_evaluations,
        "claim_relation_evaluated_count":len(relation_evaluated),
        "claim_relation_claim_scope":"OBJECTIVE_BOUND_BOUNDED_EXPLICIT_RELATION_OR_EXACT_QUOTED_SUPPORT_ONLY__FACTUAL_CORRECTNESS_UNVERIFIED",
        "authority_verified_candidate_count":0,
        "primary_source_verified_candidate_count":0,
        "role_progress":{
            "SOURCE_DISCOVERY":(
                "OBJECTIVE_RELEVANCE_SELECTED_LIVE_MATERIALIZED_SOURCE_AVAILABLE"
                if relevance_ready else "PROVENANCE_VERIFIED_CANDIDATES_AVAILABLE__NO_ADMISSIBLE_SUBJECT_COVERAGE"
            ),
            "EVIDENCE_ACQUISITION":(
                "GENERIC_PROVENANCE_BEARING_OBJECTIVE_GROUNDED_EVIDENCE_AVAILABLE"
                if evidence_ready else
                "RELEVANCE_SELECTED_LIVE_SOURCE_AVAILABLE__GENERIC_EVIDENCE_EXTRACTION_REQUIRED"
                if relevance_ready else
                "BLOCKED_ON_OBJECTIVE_RELEVANCE_ADMISSION"
            ),
            "EVIDENCE_EXTRACTION":(
                "OBJECTIVE_GROUNDED_AUDITABLE_EVIDENCE_UNITS_AVAILABLE__FACTUAL_CORRECTNESS_UNVERIFIED"
                if evidence_ready else
                "REQUIRES_GROUNDING" if relevance_ready else "NOT_STARTED"
            ),
            "RELATION_EVALUATION":(
                "OBJECTIVE_BOUND_EXPLICIT_RELATION_EVALUATED__FACTUAL_CORRECTNESS_UNVERIFIED"
                if relation_ready else
                "CLAIM_SPEC_AND_OPERAND_BINDING_REQUIRED"
                if evidence_ready else
                "NOT_STARTED"
            ),
            "DECISION_SYNTHESIS_AND_VERIFICATION":(
                "REQUIRED__NO_CONFIDENCE_SUFFICIENCY_OR_SOURCE_INDEPENDENCE_INFERRED"
                if relation_ready else "NOT_STARTED"
            ),
        },
        "next_required_capability":(
            "MODEL_INDEPENDENT_DECISION_QUALITY_SYNTHESIS_AND_VERIFICATION_FROM_OBJECTIVE_BOUND_RELATION_V1"
            if relation_ready else
            "MODEL_INDEPENDENT_CLAIM_SPEC_AND_OPERAND_BINDING_FROM_OBJECTIVE_AND_GENERIC_EVIDENCE_V1"
            if evidence_ready else
            "MODEL_INDEPENDENT_EVIDENCE_EXTRACTION_FROM_VERIFIED_RELEVANT_SOURCE"
            if relevance_ready else
            "MODEL_INDEPENDENT_OBJECTIVE_RELEVANCE_AND_LIVE_SOURCE_ADMISSION_V1"
        ),
        "authority_identity_claims_made":bool(authority_verified),
        "authority_claims_made":False,
        "primary_source_gate_required":False,
        "primary_source_status_role":"OPTIONAL_METADATA_NOT_UNIVERSAL_RESEARCH_ADMISSION_GATE",
        "primary_source_claims_made":False,
        "relevance_claims_made":relevance_ready,
        "factual_correctness_claims_made":False,
        "evidence_sufficiency_claims_made":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
