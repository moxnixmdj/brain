"""Independent verifier for combined cross-document source/residual frontier V1."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_source_coverage_gate_v1 as byte_gate
from canonical.runtime import cross_document_effect_source_coverage_gate_verify_v1 as byte_verify
from canonical.runtime import cross_document_residual_effect_frontier_v1 as residual
from canonical.runtime import cross_document_residual_effect_frontier_verify_v1 as residual_verify
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_VERIFY_V1"
PROBLEM_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_V1"


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _rows(rows:Any,name:str)->list[dict[str,Any]]:
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise ValueError(name+"_INVALID")
    out=[]; seen=set()
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError(name+"_ROW_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        text=row.get("source_text")
        if not isinstance(text,str):
            raise ValueError(name+"_SOURCE_TEXT_INVALID")
        if did in seen:
            raise ValueError(name+"_DOCUMENT_ID_DUPLICATE")
        seen.add(did)
        out.append(deepcopy(dict(row)))
    return sorted(out,key=lambda x:x["document_id"])


def _expected(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping) or problem.get("schema")!=PROBLEM_SCHEMA:
        raise ValueError("PROBLEM_SCHEMA_INVALID")
    if set(problem)!={
        "schema","case_id","byte_coverage_documents",
        "residual_source_documents","worldset_problem"
    }:
        raise ValueError("PROBLEM_FIELDS_INVALID")
    case_id=_token(problem.get("case_id"),"CASE_ID")
    ws=problem.get("worldset_problem")
    if not isinstance(ws,Mapping) or ws.get("case_id")!=case_id:
        raise ValueError("WORLDSET_INVALID")

    bdocs=_rows(problem.get("byte_coverage_documents"),"BYTE_DOCS")
    rdocs=_rows(problem.get("residual_source_documents"),"RESIDUAL_DOCS")
    bmap={x["document_id"]:x["source_text"] for x in bdocs}
    rmap={x["document_id"]:x["source_text"] for x in rdocs}
    if bmap!=rmap:
        raise ValueError("SOURCE_DOCUMENTS_NOT_IDENTICAL")

    bp={
        "schema":byte_gate.SCHEMA,
        "case_id":case_id,
        "documents":bdocs,
        "worldset_problem":deepcopy(dict(ws)),
    }
    br=byte_gate.evaluate(bp)
    if br.get("status")=="FAIL_CLOSED":
        return {"status":"FAIL_CLOSED__BYTE_COVERAGE","pass":False}
    bv=byte_verify.verify(bp,br)
    if bv.get("verified") is not True:
        raise ValueError("BYTE_VERIFY_FAILED")

    rp={
        "schema":residual.SCHEMA,
        "case_id":case_id,
        "source_documents":rdocs,
        "worldset_problem":deepcopy(dict(ws)),
    }
    rr=residual.evaluate(rp)
    if str(rr.get("status") or "").startswith("FAIL_CLOSED"):
        return {"status":"FAIL_CLOSED__RESIDUAL_FRONTIER","pass":False}
    rv=residual_verify.verify(rp,rr)
    if rv.get("verified") is not True:
        raise ValueError("RESIDUAL_VERIFY_FAILED")

    finite=worldset.evaluate(ws)
    fv=worldset_verify.verify(ws,finite)
    if fv.get("verified") is not True:
        raise ValueError("WORLDSET_VERIFY_FAILED")

    states={
        str(x.get("document_id")):str(x.get("state"))
        for x in rr.get("residuals") or []
        if isinstance(x,Mapping)
    }
    unknown={}
    for region in br.get("open_unknown_regions") or []:
        if isinstance(region,Mapping) and region.get("document_id"):
            unknown.setdefault(str(region["document_id"]),[]).append(deepcopy(dict(region)))

    discharged_byte=[]; discharged_scope=[]; unsafe=[]; obligations=[]
    residual_obligations={
        str(x.get("document_id")):deepcopy(dict(x))
        for x in rr.get("next_proof_obligations") or []
        if isinstance(x,Mapping) and x.get("document_id")
    }
    for did in sorted(bmap):
        rows=unknown.get(did,[])
        state=states.get(did,"TOP_EFFECT_MAY_AFFECT_QUERY")
        if not rows:
            discharged_byte.append(did)
        elif state=="PROVED_QUERY_IRRELEVANT":
            discharged_scope.append(did)
        else:
            unsafe.append(did)
            item={
                "kind":"CLOSE_QUERY_RELEVANT_UNKNOWN_SOURCE_REGIONS_OR_PROVE_QUERY_TARGET_EXCLUDED",
                "document_id":did,
                "open_unknown_region_ids":[str(x.get("region_id")) for x in rows],
                "residual_state":state,
            }
            if did in residual_obligations:
                item["residual_frontier_obligation"]=residual_obligations[did]
            if state=="PROVED_QUERY_EFFECT_ID_INVENTORY_EXHAUSTIVE":
                item["inventory_warning"]=(
                    "EFFECT_ID_INVENTORY_DOES_NOT_PROVE_VALUE_CLASS_CONDITION_OR_"
                    "PRECEDENCE_COMPLETENESS_FOR_UNKNOWN_BYTES"
                )
            obligations.append(item)

    common={
        "residual_states":dict(sorted(states.items())),
        "documents_discharged_by_exact_byte_semantics":discharged_byte,
        "documents_discharged_by_query_target_exclusion":discharged_scope,
    }
    if unsafe:
        regions=[x for did in unsafe for x in unknown.get(did,[])]
        return {
            "status":"OPEN__QUERY_RELEVANT_SOURCE_TOP_REMAINS",
            "pass":False,
            **common,
            "blocking_document_ids":unsafe,
            "blocking_unknown_regions":sorted(
                regions,key=lambda x:(x["document_id"],x["start"],x["end"])
            ),
            "next_proof_obligations":obligations,
            "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
            "minimum_discriminator_slots":deepcopy(
                finite.get("minimum_discriminator_slots") or []
            ),
            "world_count":finite.get("world_count"),
            "query_relative_source_completeness_proved":False,
        }
    if finite.get("pass") is not True:
        return {
            "status":"OPEN__SOURCE_TOP_CLOSED__FINITE_EFFECT_WORLDS_NOT_CLOSED",
            "pass":False,
            **common,
            "blocking_document_ids":[],
            "blocking_unknown_regions":[],
            "next_proof_obligations":[],
            "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
            "minimum_discriminator_slots":deepcopy(
                finite.get("minimum_discriminator_slots") or []
            ),
            "world_count":finite.get("world_count"),
            "query_relative_source_completeness_proved":True,
        }
    return {
        "status":"PASS__QUERY_RELATIVE_SOURCE_AND_EFFECT_COVERAGE_VERIFIED",
        "pass":True,
        **common,
        "blocking_document_ids":[],
        "blocking_unknown_regions":[],
        "next_proof_obligations":[],
        "effective_value":deepcopy(finite.get("effective_value")),
        "world_count":finite.get("world_count"),
        "minimum_discriminator_slots":[],
        "query_relative_source_completeness_proved":True,
    }


def verify(problem:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_expected(problem)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        keys=[
            "status","pass","residual_states",
            "documents_discharged_by_exact_byte_semantics",
            "documents_discharged_by_query_target_exclusion",
            "blocking_document_ids","blocking_unknown_regions",
            "next_proof_obligations","query_relative_source_completeness_proved",
        ]
        if expected.get("pass") is True:
            keys+=["effective_value","world_count","minimum_discriminator_slots"]
        elif expected.get("status") not in {
            "FAIL_CLOSED__BYTE_COVERAGE","FAIL_CLOSED__RESIDUAL_FRONTIER"
        }:
            keys+=["possible_outcomes","minimum_discriminator_slots","world_count"]
        for key in keys:
            if result.get(key)!=expected.get(key):
                errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_SOURCE_RESIDUAL_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"INDEPENDENT_COMPOSITION_OF_VERIFIED_BYTE_COVERAGE_RESIDUAL_TOP_AND_FINITE_WORLDSET",
    }
