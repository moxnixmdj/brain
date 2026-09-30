#!/usr/bin/env python3
"""Compose extracted open-research evidence into a bounded claim/relation result.

This layer is intentionally narrow. It reuses the already-qualified objective
binder and requires an independent verifier before exposing a consequential
Boolean decision. It does not upgrade retrieval provenance into factual truth,
primary-source status, causal evidence, or evidence sufficiency.
"""
from __future__ import annotations

import importlib.util
import pathlib

SCHEMA="PROJECT_BRAIN_OPEN_RESEARCH_CLAIM_RELATION_V1"

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

def evaluate(objective,source_frontend):
    objective=_canon(objective)
    base={
      "schema":SCHEMA,
      "objective":objective or None,
      "status":"BLOCKED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "output_verified":False,
    }
    if not objective:
        return {**base,"reason":"OBJECTIVE_REQUIRED"}
    if not isinstance(source_frontend,dict) or source_frontend.get("schema")!="PROJECT_BRAIN_OPEN_RESEARCH_SOURCE_FRONTEND_V1":
        return {**base,"reason":"SOURCE_FRONTEND_SCHEMA_INVALID"}
    if source_frontend.get("status")!="SOURCE_FRONTEND_READY":
        return {**base,"reason":"SOURCE_FRONTEND_NOT_READY"}
    if _canon(source_frontend.get("objective"))!=objective:
        return {**base,"reason":"SOURCE_FRONTEND_OBJECTIVE_MISMATCH"}

    binder=_load_sibling("objective_claim_operand_binding")
    verifier=_load_sibling("objective_claim_relation_verify")
    attempts=[]
    verified=[]
    for index,item in enumerate(source_frontend.get("evidence_extractions") or []):
        extraction=(item or {}).get("extraction") or {}
        if (
            extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
            or extraction.get("output_verified") is not True
        ):
            continue
        try:
            binding=binder.bind(objective,extraction,evaluate_relation=True)
        except Exception as exc:
            attempts.append({
              "index":index,"status":"BINDER_EXCEPTION",
              "error_class":type(exc).__name__,"error":str(exc)[:500],
            })
            continue
        if binding.get("status") not in {"CLAIM_SPEC_AND_OPERANDS_BOUND","CLAIM_SPEC_BOUND"}:
            attempts.append({
              "index":index,"status":"UNBOUND","reason":binding.get("reason"),
              "binding":binding,
            })
            continue
        check=verifier.verify(objective,extraction,binding)
        attempts.append({
          "index":index,
          "status":"VERIFIED" if check.get("verified") else "VERIFICATION_FAILED",
          "verification":check,
          "binding_status":binding.get("status"),
        })
        if check.get("verified") is True:
            verified.append((index,item,extraction,binding,check))

    if not verified:
        return {
          **base,
          "reason":"NO_INDEPENDENTLY_VERIFIED_CLAIM_RELATION",
          "attempts":attempts,
          "research_plan":source_frontend.get("decomposition"),
        }
    if len(verified)!=1:
        return {
          **base,
          "reason":"MULTIPLE_VERIFIED_CLAIM_RELATIONS_AMBIGUOUS",
          "verified_count":len(verified),
          "attempts":attempts,
          "research_plan":source_frontend.get("decomposition"),
        }

    index,item,extraction,binding,check=verified[0]
    relation=binding.get("relation_result") or {}
    mode=str((binding.get("relation_spec") or {}).get("mode") or "")
    if mode=="NUMERIC_RELATION":
        decision={
          "kind":"BOOLEAN_NUMERIC_RELATION",
          "predicate":bool(relation.get("predicate")),
          "operator":relation.get("operator"),
        }
    else:
        decision={
          "kind":"EXACT_TEXT_SUPPORT",
          "supported":relation.get("status")=="EXACT_TEXT_SUPPORT_VERIFIED",
        }

    candidate=(item or {}).get("candidate") or {}
    provenance=(item or {}).get("provenance") or {}
    relevance=(item or {}).get("relevance") or {}
    authority=(item or {}).get("authority_identity_metadata") or {}
    return {
      **base,
      "status":"OPEN_RESEARCH_CLAIM_RELATION_VERIFIED",
      "research_plan":source_frontend.get("decomposition"),
      "source_provenance":{
        "candidate":candidate,
        "retrieval":provenance,
        "relevance":relevance,
        "authority_identity_metadata":authority,
        "authority_identity_used_for_admission":False,
        "extraction_source_url":extraction.get("source_url"),
        "page_raw_sha256":extraction.get("page_raw_sha256"),
        "visible_text_sha256":extraction.get("visible_text_sha256"),
      },
      "tool_provenance":{
        "source_frontend_schema":source_frontend.get("schema"),
        "claim_binder_schema":binding.get("schema"),
        "relation_evaluator_schema":relation.get("schema"),
        "independent_verifier_schema":check.get("schema"),
        "execution_class":"DETERMINISTIC_MODEL_INDEPENDENT_PYTHON",
      },
      "experiment":{
        "method":"BIND_OBJECTIVE_ROLES_TO_INTEGRITY_CHECKED_EVIDENCE_AND_EVALUATE_TYPED_RELATION",
        "relation_spec":binding.get("relation_spec"),
        "binding_status":binding.get("status"),
      },
      "observations":{
        "left_binding":binding.get("left_binding"),
        "right_binding":binding.get("right_binding"),
        "operand_pair":binding.get("operand_pair"),
        "relation_result":relation,
      },
      "decision":decision,
      "limitations":[
        "Retrieval provenance and lexical relevance do not by themselves prove factual correctness.",
        "Primary-source status and evidence sufficiency are not promoted by this layer.",
        "No unit conversion, paraphrase entailment, causality inference, or latent semantic-role inference is performed.",
        "The independent verifier rechecks the consequential relation from the bound evidence without importing the binder or relation evaluator.",
      ],
      "independent_verification":check,
      "attempts":attempts,
      "selected_extraction_index":index,
      "semantic_entailment_status":binding.get("semantic_entailment_status"),
      "factual_correctness_status":binding.get("factual_correctness_status"),
      "evidence_sufficiency_status":binding.get("evidence_sufficiency_status"),
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "output_verified":True,
    }
