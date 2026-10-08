"""Bounded-source-grounded P3 router v1.

For task packages whose authoritative input explicitly declares a finite source set,
this adapter removes the caller-controlled evidence `verified` bit before invoking
the independently verified P3 V4 real-context front door.

Sound positive route, relative to the declared bounded task record:
- every declared source path is materialized exactly once;
- no undeclared source payload is present;
- every source is one normalized UTF-8 factual unit;
- every source is represented by exactly one evidence row;
- evidence text equals the exact declared source bytes;
- evidence provenance names that exact source path;
- this adapter, not the caller, mints `verified=True`;
- the grounded package must then pass one of V4's verified deterministic fast paths.

This proves exact grounding and no omission only relative to the declared bounded
source manifest. It does not prove that the manifest is globally authority-complete,
that an external publisher is authoritative, or any DB/U/terminal property.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.bounded_task_source_set_gate_v1 import compile_required_source_set
from canonical.runtime.p3_real_context_v3_admission_v4 import evaluate as evaluate_v4

SCHEMA="PROJECT_BRAIN_P3_BOUNDED_SOURCE_GROUNDED_ROUTER_V1"
_POSITIVE_ROUTES={
    "MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1":"GROUNDED_CLOSED_COMMON_POLICY_CELL",
    "EXPLICIT_WEIGHTED_SALIENCE_CELL_V1":"GROUNDED_EXPLICIT_WEIGHT_SALIENCE_CELL",
}


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "bounded_declared_source_set_verified":False,
        "evidence_exact_source_grounding_verified":False,
        "external_source_authority_verified":False,
        "v3_admission_authorized":False,"top_law_eligible":False,
        "policy_adequacy_authority":False,"db_admission_authority":False,
        "u_subtraction_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def _ground(payload:Mapping[str,Any])->tuple[dict[str,Any]|None,dict[str,Any]]:
    task_record=payload.get("task_record")
    materialized=payload.get("materialized_sources")
    v3_input=payload.get("v3_input")
    compiled=compile_required_source_set(task_record)
    if compiled.get("pass") is not True:
        return None,_fail("BOUNDED_SOURCE_SET_COMPILE_FAILED",source_set=compiled)
    if not isinstance(materialized,Mapping):
        return None,_fail("MATERIALIZED_SOURCES_REQUIRED")
    if not isinstance(v3_input,Mapping):
        return None,_fail("V3_INPUT_REQUIRED")
    task=v3_input.get("task")
    if not isinstance(task,Mapping):
        return None,_fail("V3_TASK_REQUIRED")
    evidence=task.get("evidence")
    if not isinstance(evidence,list) or not evidence:
        return None,_fail("EVIDENCE_REQUIRED")

    required={row["path"] for row in compiled["sources"]}
    supplied=set(materialized)
    if supplied != required:
        return None,_fail(
            "MATERIALIZED_SOURCE_SET_MISMATCH",
            missing_sources=sorted(required-supplied),
            undeclared_sources=sorted(supplied-required),
        )
    if len(evidence)!=len(required):
        return None,_fail(
            "EVIDENCE_COUNT_MUST_EQUAL_DECLARED_SOURCE_COUNT",
            evidence_count=len(evidence),source_count=len(required),
        )

    source_text:dict[str,str]={}
    source_sha:dict[str,str]={}
    for source_path in sorted(required):
        raw=materialized[source_path]
        if not isinstance(raw,str) or not raw:
            return None,_fail("DECLARED_SOURCE_MUST_BE_NONEMPTY_UTF8_TEXT",path=source_path)
        if raw!=raw.strip() or "\n" in raw or "\r" in raw:
            return None,_fail("DECLARED_SOURCE_MUST_BE_ONE_NORMALIZED_FACT_UNIT",path=source_path)
        source_text[source_path]=raw
        source_sha[source_path]=sha256(raw.encode("utf-8")).hexdigest()

    seen:set[str]=set()
    grounded_evidence=[]
    for i,row in enumerate(evidence):
        if not isinstance(row,Mapping):
            return None,_fail("EVIDENCE_ROW_INVALID",index=i)
        text=row.get("text")
        if not isinstance(text,str) or not text:
            return None,_fail("EVIDENCE_TEXT_REQUIRED",index=i)
        provenance=row.get("provenance")
        if not isinstance(provenance,list) or len(provenance)!=1 or not isinstance(provenance[0],Mapping):
            return None,_fail("EXACT_ONE_SOURCE_PROVENANCE_REQUIRED",index=i)
        sid=provenance[0].get("source_id")
        if not isinstance(sid,str) or sid not in required:
            return None,_fail("EVIDENCE_SOURCE_NOT_IN_DECLARED_SET",index=i,source_id=sid)
        if sid in seen:
            return None,_fail("DECLARED_SOURCE_EVIDENCED_MORE_THAN_ONCE",source_id=sid)
        if text!=source_text[sid]:
            return None,_fail(
                "EVIDENCE_TEXT_NOT_EXACT_SOURCE_BYTES",index=i,source_id=sid,
                expected_sha256=source_sha[sid],
                actual_sha256=sha256(text.encode("utf-8")).hexdigest(),
            )
        seen.add(sid)
        item=dict(row)
        item["verified"]=True
        item["provenance"]=[{"source_id":sid,"locator":"EXACT_WHOLE_SOURCE"}]
        grounded_evidence.append(item)

    if seen!=required:
        return None,_fail("DECLARED_SOURCE_NOT_EVIDENCED",missing_sources=sorted(required-seen))

    grounded=deepcopy(dict(v3_input))
    grounded["task"]["evidence"]=grounded_evidence
    receipt={
        "task_id":compiled["task_id"],
        "source_set_sha256":compiled["source_set_sha256"],
        "source_count":compiled["source_count"],
        "source_sha256":{k:source_sha[k] for k in sorted(source_sha)},
        "evidence_source_ids":sorted(seen),
    }
    return grounded,{
        "schema":SCHEMA,"pass":True,
        "status":"PASS__BOUNDED_DECLARED_SOURCE_SET_EXACTLY_GROUNDED",
        "bounded_declared_source_set_verified":True,
        "evidence_exact_source_grounding_verified":True,
        "external_source_authority_verified":False,
        "grounding_receipt":receipt,
        "terminal_authority":False,"terminal_credit_delta":0,
    }


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    context_id=payload.get("context_id")
    if not isinstance(context_id,str) or not context_id.strip():
        return _fail("CONTEXT_ID_REQUIRED")

    grounded,grounding=_ground(payload)
    if grounded is None:
        return grounding

    routed={"context_id":context_id,"v3_input":grounded}
    weights=payload.get("objective_weights")
    if isinstance(weights,Mapping):
        routed["objective_weights"]=dict(weights)
    result=evaluate_v4(routed)

    route=result.get("route")
    if result.get("pass") is True:
        if route not in _POSITIVE_ROUTES:
            return {
                **_fail("UNEXPECTED_POSITIVE_P3_ROUTE",route=route),
                "bounded_declared_source_set_verified":True,
                "evidence_exact_source_grounding_verified":True,
                "grounding_receipt":grounding["grounding_receipt"],
            }
        if (
            result.get("source_authorization_verified") is not False
            or result.get("policy_adequacy_authority") is not False
            or result.get("db_admission_authority") is not False
            or result.get("u_subtraction_authority") is not False
            or result.get("terminal_authority") is not False
            or result.get("terminal_credit_delta")!=0
        ):
            return {
                **_fail("P3_ROUTE_AUTHORITY_BOUNDARY_INVALID",route=route),
                "bounded_declared_source_set_verified":True,
                "evidence_exact_source_grounding_verified":True,
                "grounding_receipt":grounding["grounding_receipt"],
            }
        return {
            "schema":SCHEMA,"pass":True,
            "status":"PASS__BOUNDED_SOURCE_GROUNDED_P3_FAST_PATH",
            "route":_POSITIVE_ROUTES[route],
            "underlying_p3_route":route,
            "context_id":context_id,
            "bounded_declared_source_set_verified":True,
            "evidence_exact_source_grounding_verified":True,
            "external_source_authority_verified":False,
            "grounding_receipt":grounding["grounding_receipt"],
            "v3_admission_authorized":True,"top_law_eligible":True,
            "selected_claim_ids":result.get("selected_claim_ids"),
            "claim_order":result.get("claim_order"),
            "objective_value":result.get("objective_value"),
            "policy_adequacy_authority":False,"db_admission_authority":False,
            "u_subtraction_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,"p3_receipt":result,
            "boundary":"DECLARED_BOUNDED_SOURCE_UNIVERSE_ONLY__NO_EXTERNAL_AUTHORITY_OR_GLOBAL_COMPLETENESS",
        }

    return {
        **_fail(
            "NO_VERIFIED_P3_POSITIVE_CELL_FOR_GROUNDED_CONTEXT",
            p3_route=result.get("route"),
            p3_status=result.get("status"),
            p3_reason=result.get("reason"),
            closed_route_reason=result.get("closed_fast_path_reason"),
            weighted_route_reason=result.get("weighted_fast_path_reason"),
        ),
        "bounded_declared_source_set_verified":True,
        "evidence_exact_source_grounding_verified":True,
        "grounding_receipt":grounding["grounding_receipt"],
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
