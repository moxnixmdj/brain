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
import re

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

def _metadata_refined_query(relevance,candidate,verification):
    focus=_canon(((relevance.get("query_focus") or {}).get("query")))
    title=_canon(
        verification.get("record_title")
        or candidate.get("record_title")
        or candidate.get("title")
    )
    if not focus or not title:
        return None
    query=_canon(focus+" "+title)
    if len(query)>1200:
        query=query[:1200].rsplit(" ",1)[0] or query[:1200]
    return query


def _comparative_operand_queries(objective,claim_binder):
    parser=getattr(claim_binder,"_parse_objective",None)
    if not callable(parser):
        return None
    parsed,reason=parser(objective)
    if reason or not isinstance(parsed,dict) or parsed.get("mode")!="NUMERIC_RELATION":
        return None
    left=_canon(parsed.get("left_entity"))
    right=_canon(parsed.get("right_entity"))
    if not left or not right:
        return None

    left_query=left
    right_query=right
    left_of=re.match(r"^(?:the\s+)?(.+?)\s+of\s+(.+)$",left,re.IGNORECASE)
    right_that=re.match(r"^(?:that|those)\s+of\s+(.+)$",right,re.IGNORECASE)
    if left_of and right_that:
        property_phrase=_canon(left_of.group(1))
        left_subject=_canon(left_of.group(2))
        right_subject=_canon(right_that.group(1))
        if property_phrase and left_subject and right_subject:
            left_query=_canon(property_phrase+" "+left_subject)
            right_query=_canon(property_phrase+" "+right_subject)

    if left_query.casefold()==right_query.casefold():
        return None
    return [
        {"role":"left","entity":left,"query":left_query},
        {"role":"right","entity":right,"query":right_query},
    ]

def _candidate_rows_for_query(query,discovery,verifier,limit,timeout):
    discovered=discovery.discover(
        query,limit=limit,timeout=timeout,query_override=query
    )
    verifications=[]
    if discovered.get("status")=="CANDIDATES_DISCOVERED":
        for candidate in discovered.get("candidates") or []:
            verifications.append({
                "candidate":candidate,
                "verification":verifier.verify(candidate,timeout=timeout),
            })
    verified=[
        x for x in verifications
        if (x.get("verification") or {}).get("status") in {
            "RETRIEVAL_PROVENANCE_VERIFIED",
            "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
        }
    ]
    return discovered,verifications,verified

def _select_extract_for_query(
    query,discovery,verifier,relevance_ranker,evidence_extractor,
    authority_identity,limit,timeout
):
    discovered,verifications,verified=_candidate_rows_for_query(
        query,discovery,verifier,limit,timeout
    )
    if not verified:
        return {
            "status":"OPERAND_SOURCE_PROVENANCE_BLOCKED",
            "query":query,
            "discovery":discovered,
            "provenance_verifications":verifications,
        }

    candidates=[]
    for item in verified:
        candidate=dict(item["candidate"])
        verification=item["verification"]
        if verification.get("record_title"):
            candidate["record_title"]=verification["record_title"]
        if verification.get("publisher") and not candidate.get("publisher"):
            candidate["publisher"]=verification["publisher"]
        candidates.append(candidate)

    relevance=relevance_ranker.rank(query,candidates)
    relevance_ready=(
        relevance.get("status")=="LEXICAL_RELEVANCE_RANKED"
        and relevance.get("output_verified") is True
        and relevance.get("top_candidate_original_index") is not None
        and isinstance(relevance.get("top_candidate_admission"),dict)
        and relevance["top_candidate_admission"].get("verified") is True
    )
    if not relevance_ready:
        return {
            "status":"OPERAND_SOURCE_RELEVANCE_BLOCKED",
            "query":query,
            "discovery":discovered,
            "provenance_verifications":verifications,
            "relevance":relevance,
        }

    index=int(relevance["top_candidate_original_index"])
    if not (0<=index<len(verified)):
        raise RuntimeError("OPERAND_RELEVANCE_INDEX_OUT_OF_RANGE")
    selected=verified[index]
    candidate=dict(selected["candidate"])
    provenance=selected["verification"]
    selected_materialization=None
    metadata_anchored_refinement=None
    selected_source_origin="INITIAL_LIVE_RETRIEVAL"

    if provenance.get("status")=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED":
        selected_materialization=verifier.materialize(
            candidate,provenance,timeout=timeout
        )
        if selected_materialization.get("status")=="RETRIEVAL_PROVENANCE_VERIFIED":
            provenance=selected_materialization
            selected_source_origin="BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION"
        else:
            refined_query=_metadata_refined_query(relevance,candidate,provenance)
            refined_discovery,refined_verifications,refined_verified=(
                _candidate_rows_for_query(
                    refined_query,discovery,verifier,limit,timeout
                )
                if refined_query else
                (
                    {"status":"DISCOVERY_UNAVAILABLE","reason":"METADATA_REFINED_QUERY_UNAVAILABLE","candidates":[]},
                    [],[],
                )
            )
            refined_retrieval=[
                x for x in refined_verified
                if (x.get("verification") or {}).get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
            ]
            refined_candidates=[dict(x["candidate"]) for x in refined_retrieval]
            refined_relevance=(
                relevance_ranker.rank(query,refined_candidates)
                if refined_candidates else
                {"status":"RELEVANCE_UNRESOLVED","reason":"REFINED_LIVE_CANDIDATES_REQUIRED","output_verified":False}
            )
            refined_ready=(
                refined_relevance.get("status")=="LEXICAL_RELEVANCE_RANKED"
                and refined_relevance.get("output_verified") is True
                and refined_relevance.get("top_candidate_original_index") is not None
                and isinstance(refined_relevance.get("top_candidate_admission"),dict)
                and refined_relevance["top_candidate_admission"].get("verified") is True
            )
            metadata_anchored_refinement={
                "query":refined_query,
                "discovery":refined_discovery,
                "provenance_verifications":refined_verifications,
                "relevance":refined_relevance,
                "selected":bool(refined_ready),
            }
            if not refined_ready:
                return {
                    "status":"OPERAND_SOURCE_MATERIALIZATION_BLOCKED",
                    "query":query,
                    "discovery":discovered,
                    "provenance_verifications":verifications,
                    "relevance":relevance,
                    "selected_source_materialization":selected_materialization,
                    "metadata_anchored_refinement":metadata_anchored_refinement,
                }
            refined_index=int(refined_relevance["top_candidate_original_index"])
            if not (0<=refined_index<len(refined_retrieval)):
                raise RuntimeError("OPERAND_REFINED_RELEVANCE_INDEX_OUT_OF_RANGE")
            selected=refined_retrieval[refined_index]
            candidate=dict(selected["candidate"])
            provenance=selected["verification"]
            relevance=refined_relevance
            selected_source_origin="BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL"

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

    extraction=evidence_extractor.extract(
        query,candidate,provenance,relevance,timeout=timeout
    )
    if (
        extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
        or int(extraction.get("evidence_unit_count") or 0)<=0
    ):
        return {
            "status":"OPERAND_EVIDENCE_EXTRACTION_BLOCKED",
            "query":query,
            "discovery":discovered,
            "provenance_verifications":verifications,
            "relevance":relevance,
            "candidate":candidate,
            "provenance":provenance,
            "extraction":extraction,
            "selected_source_materialization":selected_materialization,
            "metadata_anchored_refinement":metadata_anchored_refinement,
        }

    return {
        "status":"OPERAND_EVIDENCE_READY",
        "query":query,
        "discovery":discovered,
        "provenance_verifications":verifications,
        "relevance":relevance,
        "candidate":candidate,
        "provenance":provenance,
        "authority_identity_metadata":optional_authority,
        "extraction":extraction,
        "selected_source_materialization":selected_materialization,
        "metadata_anchored_refinement":metadata_anchored_refinement,
        "selected_source_origin":selected_source_origin,
    }

def _merge_operand_extractions(role_results):
    rows=[]
    seen=set()
    sources=[]
    for item in role_results:
        extraction=item.get("extraction") or {}
        source=extraction.get("source_url")
        if source and source not in sources:
            sources.append(source)
        for row in extraction.get("evidence_units") or []:
            uid=str(row.get("evidence_unit_id") or "")
            if not uid or uid in seen:
                continue
            seen.add(uid)
            rows.append(dict(row))
    return {
        "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
        "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
        "evidence_extraction_status":"VERIFIED",
        "verification_method":"COMPARATIVE_OPERAND_AWARE_MULTI_SOURCE_MERGE_OF_VERIFIED_EXTRACTIONS",
        "source_url":"MULTI_SOURCE",
        "source_urls":sources,
        "multi_source":True,
        "evidence_unit_count":len(rows),
        "evidence_units":rows,
        "output_verified":bool(rows),
    }

def _run_comparative_operand_multisource(
    objective,decomposition,discovery,verifier,relevance_ranker,
    evidence_extractor,claim_binder,authority_identity,limit,timeout
):
    query_plan=_comparative_operand_queries(objective,claim_binder)
    if not query_plan:
        return None

    role_results=[]
    for spec in query_plan:
        result=_select_extract_for_query(
            spec["query"],discovery,verifier,relevance_ranker,
            evidence_extractor,authority_identity,limit,timeout
        )
        result["role"]=spec["role"]
        result["entity"]=spec["entity"]
        role_results.append(result)

    blocked=[x for x in role_results if x.get("status")!="OPERAND_EVIDENCE_READY"]
    if blocked:
        return {
            "schema":SCHEMA,
            "status":"COMPARATIVE_OPERAND_SOURCE_BLOCKED",
            "objective":objective,
            "question_shape":decomposition.get("question_shape"),
            "decomposition":decomposition,
            "comparative_operand_queries":query_plan,
            "comparative_operand_retrievals":role_results,
            "provenance_verified_candidate_count":sum(
                sum(
                    1 for row in item.get("provenance_verifications") or []
                    if (row.get("verification") or {}).get("status") in {
                        "RETRIEVAL_PROVENANCE_VERIFIED",
                        "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                    }
                )
                for item in role_results
            ),
            "relevance_verified_candidate_count":sum(
                1 for item in role_results
                if item.get("status")=="OPERAND_EVIDENCE_READY"
            ),
            "authority_identity_verified_candidate_count":0,
            "evidence_extractions":[
                {"role":item.get("role"),"extraction":item.get("extraction")}
                for item in role_results if item.get("extraction")
            ],
            "claim_relation_evaluations":[],
            "next_required_capability":"MODEL_INDEPENDENT_COMPARATIVE_OPERAND_AWARE_MULTI_SOURCE_RETRIEVAL_V1",
            "authority_claims_made":False,
            "primary_source_claims_made":False,
            "factual_correctness_claims_made":False,
            "evidence_sufficiency_claims_made":False,
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

    merged=_merge_operand_extractions(role_results)
    bound=claim_binder.bind(objective,merged,evaluate_relation=True)
    relation_result=bound.get("relation_result") if isinstance(bound,dict) else None
    relation_ready=(
        bound.get("status")=="CLAIM_SPEC_AND_OPERANDS_BOUND"
        and isinstance(relation_result,dict)
        and relation_result.get("output_verified") is True
        and relation_result.get("status")=="NUMERIC_RELATION_VERIFIED"
    )
    relation_rows=[{
        "source_url":"MULTI_SOURCE",
        "extraction":merged,
        "binding":bound,
    }]
    return {
        "schema":SCHEMA,
        "status":"SOURCE_FRONTEND_READY",
        "objective":objective,
        "question_shape":decomposition.get("question_shape"),
        "decomposition":decomposition,
        "discovery":{
            "mode":"COMPARATIVE_OPERAND_AWARE_MULTI_SOURCE",
            "operand_queries":query_plan,
        },
        "comparative_operand_queries":query_plan,
        "comparative_operand_retrievals":role_results,
        "provenance_verifications":[
            row
            for item in role_results
            for row in (item.get("provenance_verifications") or [])
        ],
        "provenance_verified_candidate_count":sum(
            sum(
                1 for row in item.get("provenance_verifications") or []
                if (row.get("verification") or {}).get("status") in {
                    "RETRIEVAL_PROVENANCE_VERIFIED",
                    "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                }
            )
            for item in role_results
        ),
        "retrieval_provenance_verified_candidate_count":sum(
            sum(
                1 for row in item.get("provenance_verifications") or []
                if (row.get("verification") or {}).get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
            )
            for item in role_results
        ),
        "bibliographic_provenance_verified_candidate_count":sum(
            sum(
                1 for row in item.get("provenance_verifications") or []
                if (row.get("verification") or {}).get("status")=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED"
            )
            for item in role_results
        ),
        "selected_source_materialization":[
            item.get("selected_source_materialization") for item in role_results
        ],
        "metadata_anchored_refinement":[
            item.get("metadata_anchored_refinement") for item in role_results
        ],
        "selected_source_origin":[
            item.get("selected_source_origin") for item in role_results
        ],
        "authority_identity_verifications":[
            {
                "candidate":item.get("candidate"),
                "provenance":item.get("provenance"),
                "authority_identity":item.get("authority_identity_metadata"),
                "used_for_admission":False,
            }
            for item in role_results
        ],
        "authority_identity_verified_candidate_count":sum(
            1 for item in role_results
            if (item.get("authority_identity_metadata") or {}).get("status")=="AUTHORITY_IDENTITY_VERIFIED"
        ),
        "authority_identity_claim_scope":"OPTIONAL_HOST_TO_ROR_ORGANIZATION_METADATA_ONLY__NOT_ADMISSION_GATE",
        "authority_identity_required_for_admission":False,
        "objective_relevance_verifications":[
            {
                "role":item.get("role"),
                "relevance":item.get("relevance"),
                "candidate":item.get("candidate"),
            }
            for item in role_results
        ],
        "relevance_verified_candidate_count":len(role_results),
        "relevance_claim_scope":"PER_OPERAND_QUALIFIED_DETERMINISTIC_BM25_PLUS_FOCUSED_QUERY_TOKEN_COVERAGE_ADMISSION_ONLY",
        "evidence_extractions":[
            {
                "role":item.get("role"),
                "candidate":item.get("candidate"),
                "provenance":item.get("provenance"),
                "relevance":item.get("relevance"),
                "extraction":item.get("extraction"),
            }
            for item in role_results
        ],
        "evidence_extracted_candidate_count":len(role_results),
        "merged_evidence_extraction":merged,
        "claim_relation_evaluations":relation_rows,
        "claim_relation_evaluated_count":1 if relation_ready else 0,
        "claim_relation_claim_scope":"OBJECTIVE_BOUND_BOUNDED_EXPLICIT_RELATION_OVER_MERGED_MULTI_SOURCE_EVIDENCE__FACTUAL_CORRECTNESS_UNVERIFIED",
        "authority_verified_candidate_count":0,
        "primary_source_verified_candidate_count":0,
        "role_progress":{
            "SOURCE_DISCOVERY":"OPERAND_AWARE_PROVENANCE_VERIFIED_SOURCES_AVAILABLE",
            "EVIDENCE_ACQUISITION":"MULTI_SOURCE_OPERAND_EVIDENCE_AVAILABLE",
            "EVIDENCE_EXTRACTION":"MERGED_AUDITABLE_EVIDENCE_UNITS_AVAILABLE__FACTUAL_CORRECTNESS_UNVERIFIED",
            "RELATION_EVALUATION":(
                "OBJECTIVE_BOUND_EXPLICIT_RELATION_EVALUATED__FACTUAL_CORRECTNESS_UNVERIFIED"
                if relation_ready else "CLAIM_SPEC_AND_OPERAND_BINDING_REQUIRED"
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
        ),
        "authority_identity_claims_made":False,
        "authority_claims_made":False,
        "primary_source_gate_required":False,
        "primary_source_status_role":"OPTIONAL_METADATA_NOT_UNIVERSAL_RESEARCH_ADMISSION_GATE",
        "primary_source_claims_made":False,
        "relevance_claims_made":True,
        "factual_correctness_claims_made":False,
        "evidence_sufficiency_claims_made":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
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

    comparative=_run_comparative_operand_multisource(
        objective,decomposition,discovery,verifier,relevance_ranker,
        evidence_extractor,claim_binder,authority_identity,limit,timeout
    )
    if comparative is not None:
        return comparative

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
        x for x in verifications
        if x["verification"].get("status") in {
            "RETRIEVAL_PROVENANCE_VERIFIED",
            "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
        }
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

    candidates=[]
    for item in provenance_verified:
        candidate=dict(item["candidate"])
        verification=item["verification"]
        if verification.get("record_title"):
            candidate["record_title"]=verification["record_title"]
        if verification.get("publisher") and not candidate.get("publisher"):
            candidate["publisher"]=verification["publisher"]
        candidates.append(candidate)
    relevance=relevance_ranker.rank(objective,candidates)
    relevance_ready=(
        relevance.get("status")=="LEXICAL_RELEVANCE_RANKED"
        and relevance.get("output_verified") is True
        and relevance.get("top_candidate_original_index") is not None
        and isinstance(relevance.get("top_candidate_admission"),dict)
        and relevance["top_candidate_admission"].get("verified") is True
    )

    authority_verifications=[]
    evidence_extractions=[]
    selected_item=None
    if relevance_ready:
        index=int(relevance["top_candidate_original_index"])
        if 0<=index<len(provenance_verified):
            selected_item=provenance_verified[index]

    selected_materialization=None
    metadata_anchored_refinement=None
    selected_source_origin=None
    if selected_item is not None:
        candidate=dict(selected_item["candidate"])
        provenance=selected_item["verification"]
        if provenance.get("status")=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED":
            selected_materialization=verifier.materialize(
                candidate,provenance,timeout=timeout
            )
            if selected_materialization.get("status")=="RETRIEVAL_PROVENANCE_VERIFIED":
                provenance=selected_materialization
                selected_source_origin="BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION"
            else:
                refined_query=_metadata_refined_query(relevance,candidate,provenance)
                refined_discovery=(
                    discovery.discover(
                        objective,limit=limit,timeout=timeout,
                        query_override=refined_query,
                    )
                    if refined_query else
                    {"status":"DISCOVERY_UNAVAILABLE","reason":"METADATA_REFINED_QUERY_UNAVAILABLE","candidates":[]}
                )
                refined_verifications=[]
                if refined_discovery.get("status")=="CANDIDATES_DISCOVERED":
                    for refined_candidate in refined_discovery.get("candidates") or []:
                        refined_verifications.append({
                            "candidate":refined_candidate,
                            "verification":verifier.verify(refined_candidate,timeout=timeout),
                        })
                refined_retrieval=[
                    x for x in refined_verifications
                    if x["verification"].get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
                ]
                refined_candidates=[dict(x["candidate"]) for x in refined_retrieval]
                refined_relevance=(
                    relevance_ranker.rank(objective,refined_candidates)
                    if refined_candidates else
                    {"status":"RELEVANCE_UNRESOLVED","reason":"REFINED_LIVE_CANDIDATES_REQUIRED","output_verified":False}
                )
                refined_ready=(
                    refined_relevance.get("status")=="LEXICAL_RELEVANCE_RANKED"
                    and refined_relevance.get("output_verified") is True
                    and refined_relevance.get("top_candidate_original_index") is not None
                    and isinstance(refined_relevance.get("top_candidate_admission"),dict)
                    and refined_relevance["top_candidate_admission"].get("verified") is True
                )
                metadata_anchored_refinement={
                    "query":refined_query,
                    "discovery":refined_discovery,
                    "provenance_verifications":refined_verifications,
                    "relevance":refined_relevance,
                    "selected":bool(refined_ready),
                }
                if not refined_ready:
                    return {
                        "schema":SCHEMA,
                        "status":"SELECTED_SOURCE_MATERIALIZATION_BLOCKED",
                        "objective":objective,
                        "decomposition":decomposition,
                        "discovery":discovered,
                        "provenance_verifications":verifications,
                        "provenance_verified_candidate_count":len(provenance_verified),
                        "objective_relevance_verifications":[{
                            "relevance":relevance,
                            "candidate":candidate,
                        }],
                        "selected_source_materialization":selected_materialization,
                        "metadata_anchored_refinement":metadata_anchored_refinement,
                        "authority_identity_verifications":[],
                        "evidence_extractions":[],
                        "claim_relation_evaluations":[],
                        "next_required_capability":"MODEL_INDEPENDENT_SELECTED_SOURCE_LIVE_MATERIALIZATION_OR_METADATA_REFINED_RETRIEVAL_V1",
                        "model_dependency_count":0,
                        "incremental_spend_usd":0,
                    }
                refined_index=int(refined_relevance["top_candidate_original_index"])
                if not (0<=refined_index<len(refined_retrieval)):
                    raise RuntimeError("REFINED_RELEVANCE_INDEX_OUT_OF_RANGE")
                selected_item=refined_retrieval[refined_index]
                candidate=dict(selected_item["candidate"])
                provenance=selected_item["verification"]
                relevance=refined_relevance
                selected_source_origin="BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL"
        else:
            selected_source_origin="INITIAL_LIVE_RETRIEVAL"
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
        "provenance_verified_candidate_count":len(provenance_verified),
        "retrieval_provenance_verified_candidate_count":sum(
            1 for x in verifications
            if x["verification"].get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
        ),
        "bibliographic_provenance_verified_candidate_count":sum(
            1 for x in verifications
            if x["verification"].get("status")=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED"
        ),
        "selected_source_materialization":selected_materialization,
        "metadata_anchored_refinement":metadata_anchored_refinement,
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
        "relevance_claim_scope":"QUALIFIED_DETERMINISTIC_BM25_PLUS_FOCUSED_QUERY_TOKEN_COVERAGE_ADMISSION_ONLY",
        "evidence_extractions":evidence_extractions,
        "evidence_extracted_candidate_count":len(evidence_extracted),
        "claim_relation_evaluations":claim_relation_evaluations,
        "claim_relation_evaluated_count":len(relation_evaluated),
        "claim_relation_claim_scope":"OBJECTIVE_BOUND_BOUNDED_EXPLICIT_RELATION_OR_EXACT_QUOTED_SUPPORT_ONLY__FACTUAL_CORRECTNESS_UNVERIFIED",
        "authority_verified_candidate_count":0,
        "primary_source_verified_candidate_count":0,
        "role_progress":{
            "SOURCE_DISCOVERY":(
                "OBJECTIVE_RELEVANCE_SELECTED_PROVENANCE_VERIFIED_SOURCE_AVAILABLE"
                if relevance_ready else "CANDIDATES_WITH_LIVE_RETRIEVAL_PROVENANCE_AVAILABLE"
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
            "MODEL_INDEPENDENT_OBJECTIVE_RELEVANCE_VERIFICATION_V1"
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
