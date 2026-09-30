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

_PROVENANCE_RELEVANCE_STATUSES={
    "RETRIEVAL_PROVENANCE_VERIFIED",
    "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
}

def _rankable_item(item):
    candidate=dict((item or {}).get("candidate") or {})
    verification=dict((item or {}).get("verification") or {})
    record_title=_canon(verification.get("record_title"))
    page_title=_canon(verification.get("page_title"))
    if record_title:
        candidate["record_title"]=record_title
    elif page_title and not _canon(candidate.get("title")):
        candidate["record_title"]=page_title
    return {"candidate":candidate,"verification":verification}

def _selected_ranked_item(relevance,items):
    if not isinstance(relevance,dict):
        return None
    if relevance.get("status")!="LEXICAL_RELEVANCE_RANKED" or relevance.get("output_verified") is not True:
        return None
    index=relevance.get("top_candidate_original_index")
    if not isinstance(index,int) or index<0 or index>=len(items):
        return None
    rows=relevance.get("ranked_candidates") or []
    selected_row=next(
        (row for row in rows if isinstance(row,dict) and row.get("original_index")==index),
        None,
    )
    if not selected_row or selected_row.get("lexical_admission_status")!="ADMITTED":
        return None
    return items[index]

def _metadata_anchor_query(objective,item):
    item=dict(item or {})
    verification=dict(item.get("verification") or {})
    candidate=dict(item.get("candidate") or {})
    if verification.get("status")!="BIBLIOGRAPHIC_PROVENANCE_VERIFIED":
        return None
    title=_canon(verification.get("record_title") or candidate.get("record_title") or candidate.get("title"))
    doi=_canon(verification.get("doi") or candidate.get("doi"))
    if not title and not doi:
        return None
    focus=_load_sibling("research_query_focus")
    objective_focus=focus.focus(objective,max_tokens=32)
    if objective_focus.get("status")!="FOCUSED":
        return None
    title_tokens=[]
    if title:
        title_focus=focus.focus(title,max_tokens=32)
        if title_focus.get("status")=="FOCUSED":
            title_tokens=list(title_focus.get("tokens") or [])
    objective_tokens=list(objective_focus.get("tokens") or [])
    combined=list(objective_tokens)
    for token in title_tokens:
        if token not in combined:
            combined.append(token)
    combined=combined[:48]
    parts=([doi] if doi else [])+combined
    query=_canon(" ".join(parts))
    if not query:
        return None
    return {
        "status":"METADATA_ANCHOR_READY",
        "query":query,
        "doi":doi or None,
        "record_title":title or None,
        "objective_query":objective_focus.get("query"),
        "objective_tokens":objective_tokens,
        "metadata_title_tokens":title_tokens,
        "new_metadata_tokens":[x for x in title_tokens if x not in objective_tokens],
        "refinement_pass_limit":1,
        "factual_evidence_status":"NOT_EVIDENCE__QUERY_ANCHOR_ONLY",
    }

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

    verifications=[]
    for candidate in discovered.get("candidates") or []:
        verification=verifier.verify(candidate,timeout=timeout)
        verifications.append({"candidate":candidate,"verification":verification})

    provenance_verified=[
        _rankable_item(x) for x in verifications
        if (x.get("verification") or {}).get("status") in _PROVENANCE_RELEVANCE_STATUSES
    ]
    retrieval_verified_initial=[
        x for x in provenance_verified
        if x["verification"].get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
    ]
    bibliographic_verified=[
        x for x in provenance_verified
        if x["verification"].get("status")=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED"
    ]
    if not provenance_verified:
        return {
            "schema":SCHEMA,
            "status":"SOURCE_RETRIEVAL_PROVENANCE_BLOCKED",
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

    initial_relevance=relevance_ranker.rank(
        objective,[x["candidate"] for x in provenance_verified]
    )
    initial_selected=_selected_ranked_item(initial_relevance,provenance_verified)
    selected_item=None
    relevance=initial_relevance
    relevance_ready=False
    refined_discovery=None
    refined_verifications=[]
    refined_retrieval_verified=[]
    refined_relevance=None
    metadata_refinement={
        "status":"NOT_REQUIRED",
        "attempt_count":0,
        "pass_limit":1,
        "bibliographic_metadata_used_as_evidence":False,
    }

    if initial_selected is not None:
        selected_status=initial_selected["verification"].get("status")
        if selected_status=="RETRIEVAL_PROVENANCE_VERIFIED":
            selected_item=initial_selected
            relevance_ready=True
        elif selected_status=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED":
            anchor=_metadata_anchor_query(objective,initial_selected)
            if anchor is None:
                metadata_refinement={
                    **metadata_refinement,
                    "status":"METADATA_ANCHOR_UNAVAILABLE",
                    "attempt_count":0,
                }
            else:
                refined_discovery=discovery.discover(
                    objective,limit=limit,timeout=timeout,
                    query_override=anchor["query"],
                )
                if refined_discovery.get("status")=="CANDIDATES_DISCOVERED":
                    for candidate in refined_discovery.get("candidates") or []:
                        verification=verifier.verify(candidate,timeout=timeout)
                        refined_verifications.append({
                            "candidate":candidate,
                            "verification":verification,
                        })
                    refined_retrieval_verified=[
                        _rankable_item(x) for x in refined_verifications
                        if (x.get("verification") or {}).get("status")
                        =="RETRIEVAL_PROVENANCE_VERIFIED"
                    ]
                    if refined_retrieval_verified:
                        refined_relevance=relevance_ranker.rank(
                            objective,[x["candidate"] for x in refined_retrieval_verified]
                        )
                        refined_selected=_selected_ranked_item(
                            refined_relevance,refined_retrieval_verified
                        )
                        if refined_selected is not None:
                            selected_item=refined_selected
                            relevance=refined_relevance
                            relevance_ready=True
                metadata_refinement={
                    "status":(
                        "LIVE_RETRIEVAL_REFINED_AND_SELECTED"
                        if relevance_ready
                        else "LIVE_RETRIEVAL_REFINEMENT_UNRESOLVED"
                    ),
                    "attempt_count":1,
                    "pass_limit":1,
                    "anchor":anchor,
                    "discovery":refined_discovery,
                    "provenance_verifications":refined_verifications,
                    "relevance":refined_relevance,
                    "bibliographic_metadata_used_as_evidence":False,
                }

    authority_verifications=[]
    evidence_extractions=[]

    if selected_item is not None:
        candidate=dict(selected_item["candidate"])
        provenance=selected_item["verification"]
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
                bound=claim_binder.bind(
                    objective,extraction,evaluate_relation=True
                )
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
        "refined_provenance_verifications":refined_verifications,
        "provenance_verified_candidate_count":len(provenance_verified),
        "live_retrieval_provenance_verified_candidate_count":(
            len(retrieval_verified_initial)+len(refined_retrieval_verified)
        ),
        "bibliographic_provenance_verified_candidate_count":len(bibliographic_verified),
        "relevance_pool_candidate_count":len(provenance_verified),
        "metadata_anchored_retrieval_refinement":metadata_refinement,
        "authority_identity_verifications":authority_verifications,
        "authority_identity_verified_candidate_count":len(authority_verified),
        "authority_identity_claim_scope":"OPTIONAL_HOST_TO_ROR_ORGANIZATION_METADATA_ONLY__NOT_ADMISSION_GATE",
        "authority_identity_required_for_admission":False,
        "objective_relevance_verifications":[
            {
                "phase":"INITIAL_ALL_PROVENANCE_VERIFIED_CANDIDATES",
                "relevance":initial_relevance,
                "candidate":initial_selected["candidate"] if initial_selected else None,
                "candidate_provenance_status":(
                    initial_selected["verification"].get("status")
                    if initial_selected else None
                ),
            },
            *([{
                "phase":"METADATA_ANCHORED_LIVE_RETRIEVAL",
                "relevance":refined_relevance,
                "candidate":selected_item["candidate"] if selected_item else None,
                "candidate_provenance_status":(
                    selected_item["verification"].get("status")
                    if selected_item else None
                ),
            }] if metadata_refinement.get("attempt_count") else []),
        ],
        "relevance_verified_candidate_count":1 if relevance_ready else 0,
        "relevance_claim_scope":"QUALIFIED_DETERMINISTIC_BM25_WITH_QUERY_COMPLEXITY_SCALED_TERM_COVERAGE__BIBLIOGRAPHIC_METADATA_MAY_REFINE_QUERY_BUT_IS_NEVER_EVIDENCE",
        "evidence_extractions":evidence_extractions,
        "evidence_extracted_candidate_count":len(evidence_extracted),
        "claim_relation_evaluations":claim_relation_evaluations,
        "claim_relation_evaluated_count":len(relation_evaluated),
        "claim_relation_claim_scope":"OBJECTIVE_BOUND_BOUNDED_EXPLICIT_RELATION_OR_EXACT_QUOTED_SUPPORT_ONLY__FACTUAL_CORRECTNESS_UNVERIFIED",
        "authority_verified_candidate_count":0,
        "primary_source_verified_candidate_count":0,
        "role_progress":{
            "SOURCE_DISCOVERY":(
                "OBJECTIVE_RELEVANCE_SELECTED_LIVE_RETRIEVAL_SOURCE_AVAILABLE"
                if relevance_ready else
                "BIBLIOGRAPHICALLY_RELEVANT_METADATA_AVAILABLE__LIVE_RETRIEVAL_REFINEMENT_UNRESOLVED"
                if initial_selected is not None
                and initial_selected["verification"].get("status")=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED"
                else "CANDIDATES_WITH_VERIFIED_PROVENANCE_AVAILABLE"
            ),
            "EVIDENCE_ACQUISITION":(
                "GENERIC_PROVENANCE_BEARING_OBJECTIVE_GROUNDED_EVIDENCE_AVAILABLE"
                if evidence_ready else
                "RELEVANCE_SELECTED_SOURCE_AVAILABLE__GENERIC_EVIDENCE_EXTRACTION_REQUIRED"
                if relevance_ready else
                "BLOCKED_ON_OBJECTIVE_RELEVANCE_VERIFICATION"
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
            "MODEL_INDEPENDENT_METADATA_ANCHORED_LIVE_RETRIEVAL_FOR_SELECTED_PROVENANCE_RECORD"
            if metadata_refinement.get("attempt_count")
            and metadata_refinement.get("status")!="LIVE_RETRIEVAL_REFINED_AND_SELECTED"
            else "MODEL_INDEPENDENT_OBJECTIVE_RELEVANCE_VERIFICATION_V1"
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
