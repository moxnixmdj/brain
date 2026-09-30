#!/usr/bin/env python3
"""Parent-effective open research claim pipeline.

Consumes a SOURCE_FRONTEND_READY result with generic V2 evidence, invokes the
already-verified bounded objective claim-spec/operand binder, then requires a
producer-independent deterministic verifier before emitting a completed
bounded research result.

This is intentionally narrow. It does not claim source truth, causality,
evidence sufficiency, source independence, or general semantic entailment.
"""
from __future__ import annotations

import importlib.util
import pathlib

SCHEMA="PROJECT_BRAIN_OPEN_RESEARCH_CLAIM_PIPELINE_V1"

def _load(name):
    path=pathlib.Path(__file__).resolve().with_name(name+".py")
    spec=importlib.util.spec_from_file_location("project_brain_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _canon(value):
    return " ".join(str(value or "").split())

def run(objective,source_frontend):
    objective=_canon(objective)
    base={
      "schema":SCHEMA,
      "objective":objective or None,
      "status":"OPEN_RESEARCH_CLAIM_PIPELINE_BLOCKED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "semantic_entailment_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "causality_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "source_independence_status":"UNVERIFIED",
    }
    if not objective:
        return {**base,"reason":"OBJECTIVE_REQUIRED"}
    if not isinstance(source_frontend,dict) or source_frontend.get("status")!="SOURCE_FRONTEND_READY":
        return {**base,"reason":"SOURCE_FRONTEND_READY_REQUIRED"}

    rows=[]
    for item in source_frontend.get("evidence_extractions") or []:
        extraction=(item or {}).get("extraction") or {}
        if (
            extraction.get("status")=="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
            and extraction.get("output_verified") is True
            and int(extraction.get("evidence_unit_count") or 0)>0
        ):
            rows.append(item)
    if len(rows)!=1:
        return {
          **base,
          "reason":"EXACTLY_ONE_ADMITTED_EVIDENCE_EXTRACTION_REQUIRED",
          "admitted_evidence_extraction_count":len(rows),
        }

    selected=rows[0]
    extraction=selected["extraction"]
    binder=_load("objective_claim_operand_binding")
    binding=binder.bind(objective,extraction,evaluate_relation=True)
    if binding.get("status") not in {"CLAIM_SPEC_BOUND","CLAIM_SPEC_AND_OPERANDS_BOUND"} or binding.get("output_verified") is not True:
        return {
          **base,
          "reason":"CLAIM_SPEC_OPERAND_BINDING_BLOCKED",
          "binding_reason":binding.get("reason"),
          "binding":binding,
        }

    independent=_load("open_research_claim_verify")
    verification=independent.verify(extraction,binding)
    if verification.get("verified") is not True:
        return {
          **base,
          "reason":"INDEPENDENT_RELATION_VERIFICATION_FAILED",
          "binding":binding,
          "independent_verification":verification,
        }

    relation=binding.get("relation_result") or {}
    mode=str((binding.get("relation_spec") or {}).get("mode") or "").upper()
    if mode=="NUMERIC_RELATION":
        decision={
          "kind":"BOUNDED_NUMERIC_RELATION",
          "operator":relation.get("operator"),
          "predicate":bool(relation.get("predicate")),
          "answer":"YES" if bool(relation.get("predicate")) else "NO",
        }
    else:
        supported=relation.get("status")=="EXACT_TEXT_SUPPORT_VERIFIED"
        decision={
          "kind":"EXACT_TEXT_SUPPORT",
          "predicate":bool(supported),
          "answer":"SUPPORTED_EXACTLY" if supported else "NOT_SUPPORTED_EXACTLY",
        }

    provenance={
      "candidate":selected.get("candidate"),
      "retrieval_provenance":selected.get("provenance"),
      "objective_relevance":selected.get("relevance"),
      "authority_identity_metadata":selected.get("authority_identity_metadata"),
      "authority_identity_used_for_admission":bool(selected.get("authority_identity_used_for_admission")),
    }
    limitations=[
      "The source text is provenance-bound and objective-grounded, but factual correctness is not inferred by this pipeline.",
      "Primary-source/authority status is preserved only if independently established upstream; optional authority metadata is not an admission gate.",
      "The binder covers only its verified bounded comparison/exact-quoted grammar and fails closed outside that scope.",
      "No unit conversion, paraphrase entailment, causal inference, evidence-sufficiency inference, or source-independence inference is performed.",
    ]
    return {
      **base,
      "status":"OPEN_RESEARCH_CLAIM_RESULT_VERIFIED",
      "research_plan":source_frontend.get("decomposition"),
      "source_provenance":provenance,
      "tool_provenance":[
        "open_research_source_frontend",
        "evidence.claim_spec.bind.explicit_comparison.stdlib",
        "evidence.claim_relation.generic_units.stdlib",
        "open_research_claim_verify",
      ],
      "experiment":{
        "kind":"DETERMINISTIC_EXECUTABLE_BOUNDED_CLAIM_CHECK",
        "relation_spec":binding.get("relation_spec"),
        "operand_pair":binding.get("operand_pair"),
      },
      "observations":{
        "evidence_unit_count":extraction.get("evidence_unit_count"),
        "evidence_units":extraction.get("evidence_units"),
        "relation_result":relation,
      },
      "decision":decision,
      "limitations":limitations,
      "independent_verification":verification,
      "binding":binding,
      "source_frontend_status":"SOURCE_FRONTEND_READY",
      "output_verified":True,
      "returncode":0,
      "stdout":"COMPOUND_GOAL_COMPLETE",
    }
