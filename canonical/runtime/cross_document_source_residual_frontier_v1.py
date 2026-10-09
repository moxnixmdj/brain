"""Combined byte-coverage + residual-TOP frontier for cross-document effects V1.

This composes two independently verified safety abstractions:

1. byte coverage gate:
   every source byte is either closed structured semantics, whitespace, or
   OPEN_UNKNOWN_EFFECT;
2. source-backed residual frontier:
   each document retains TOP_EFFECT until source proof excludes the query target
   or proves a query-target effect-ID inventory.

Critical composition rule:
- no unknown bytes in a document => its residual TOP is discharged by exact
  source closure;
- unknown bytes MAY be ignored only when source proof excludes the query target;
- effect-ID inventory alone does NOT discharge unknown bytes because those bytes
  could still alter value/class/condition/precedence of a known effect.

Finite effect worlds are evaluated only after this combined query-relative
coverage condition is satisfied.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_source_coverage_gate_v1 as byte_gate
from canonical.runtime import cross_document_effect_source_coverage_gate_verify_v1 as byte_verify
from canonical.runtime import cross_document_residual_effect_frontier_v1 as residual
from canonical.runtime import cross_document_residual_effect_frontier_verify_v1 as residual_verify
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_V1"


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _byte_docs(rows:Any)->list[dict[str,Any]]:
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise ValueError("BYTE_COVERAGE_DOCUMENTS_INVALID")
    out=[]; seen=set()
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("BYTE_COVERAGE_DOCUMENT_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        text=row.get("source_text")
        if not isinstance(text,str):
            raise ValueError("BYTE_SOURCE_TEXT_INVALID:"+did)
        if did in seen:
            raise ValueError("BYTE_DOCUMENT_ID_DUPLICATE:"+did)
        seen.add(did)
        out.append(deepcopy(dict(row)))
    return sorted(out,key=lambda x:x["document_id"])


def _residual_docs(rows:Any)->list[dict[str,Any]]:
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        raise ValueError("RESIDUAL_SOURCE_DOCUMENTS_INVALID")
    out=[]; seen=set()
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("RESIDUAL_SOURCE_DOCUMENT_INVALID")
        did=_token(row.get("document_id"),"DOCUMENT_ID")
        text=row.get("source_text")
        if not isinstance(text,str):
            raise ValueError("RESIDUAL_SOURCE_TEXT_INVALID:"+did)
        if did in seen:
            raise ValueError("RESIDUAL_DOCUMENT_ID_DUPLICATE:"+did)
        seen.add(did)
        out.append(deepcopy(dict(row)))
    return sorted(out,key=lambda x:x["document_id"])


def evaluate(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
            raise ValueError("PROBLEM_SCHEMA_INVALID")
        if set(problem)!={
            "schema","case_id","byte_coverage_documents",
            "residual_source_documents","worldset_problem"
        }:
            raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")
        case_id=_token(problem.get("case_id"),"CASE_ID")
        ws=problem.get("worldset_problem")
        if not isinstance(ws,Mapping) or ws.get("case_id")!=case_id:
            raise ValueError("WORLDSET_PROBLEM_INVALID")

        bdocs=_byte_docs(problem.get("byte_coverage_documents"))
        rdocs=_residual_docs(problem.get("residual_source_documents"))
        bmap={x["document_id"]:x["source_text"] for x in bdocs}
        rmap={x["document_id"]:x["source_text"] for x in rdocs}
        if set(bmap)!=set(rmap):
            raise ValueError("BYTE_RESIDUAL_DOCUMENT_SET_MISMATCH")
        mismatched=[did for did in sorted(bmap) if bmap[did]!=rmap[did]]
        if mismatched:
            raise ValueError(
                "BYTE_RESIDUAL_SOURCE_TEXT_MISMATCH:"+",".join(mismatched)
            )

        byte_problem={
            "schema":byte_gate.SCHEMA,
            "case_id":case_id,
            "documents":bdocs,
            "worldset_problem":deepcopy(dict(ws)),
        }
        byte_result=byte_gate.evaluate(byte_problem)
        if byte_result.get("status")=="FAIL_CLOSED":
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__BYTE_COVERAGE",
                "pass":False,
                "case_id":case_id,
                "byte_coverage_result":byte_result,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }
        byte_check=byte_verify.verify(byte_problem,byte_result)
        if byte_check.get("verified") is not True:
            raise ValueError(
                "BYTE_COVERAGE_INDEPENDENT_VERIFICATION_FAILED:"
                + ",".join(byte_check.get("errors") or [])
            )

        residual_problem={
            "schema":residual.SCHEMA,
            "case_id":case_id,
            "source_documents":rdocs,
            "worldset_problem":deepcopy(dict(ws)),
        }
        residual_result=residual.evaluate(residual_problem)
        if str(residual_result.get("status") or "").startswith("FAIL_CLOSED"):
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__RESIDUAL_FRONTIER",
                "pass":False,
                "case_id":case_id,
                "byte_coverage_result":byte_result,
                "residual_result":residual_result,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }
        residual_check=residual_verify.verify(residual_problem,residual_result)
        if residual_check.get("verified") is not True:
            raise ValueError(
                "RESIDUAL_FRONTIER_INDEPENDENT_VERIFICATION_FAILED:"
                + ",".join(residual_check.get("errors") or [])
            )

        finite=worldset.evaluate(ws)
        finite_check=worldset_verify.verify(ws,finite)
        if finite_check.get("verified") is not True:
            raise ValueError(
                "FINITE_WORLDSET_INDEPENDENT_VERIFICATION_FAILED:"
                + ",".join(finite_check.get("errors") or [])
            )

        residual_states={
            str(x.get("document_id")):str(x.get("state"))
            for x in residual_result.get("residuals") or []
            if isinstance(x,Mapping)
        }
        unknown_by_doc={}
        for region in byte_result.get("open_unknown_regions") or []:
            if not isinstance(region,Mapping):
                continue
            did=str(region.get("document_id") or "")
            if did:
                unknown_by_doc.setdefault(did,[]).append(deepcopy(dict(region)))

        unsafe=[]
        discharged_by_scope=[]
        discharged_by_byte=[]
        next_obligations=[]
        residual_obligation_by_doc={
            str(x.get("document_id")):deepcopy(dict(x))
            for x in residual_result.get("next_proof_obligations") or []
            if isinstance(x,Mapping) and x.get("document_id")
        }

        for did in sorted(bmap):
            unknown=unknown_by_doc.get(did,[])
            state=residual_states.get(did,"TOP_EFFECT_MAY_AFFECT_QUERY")
            if not unknown:
                discharged_by_byte.append(did)
                continue
            if state=="PROVED_QUERY_IRRELEVANT":
                discharged_by_scope.append(did)
                continue

            unsafe.append(did)
            obligation={
                "kind":"CLOSE_QUERY_RELEVANT_UNKNOWN_SOURCE_REGIONS_OR_PROVE_QUERY_TARGET_EXCLUDED",
                "document_id":did,
                "open_unknown_region_ids":[
                    str(x.get("region_id")) for x in unknown
                ],
                "residual_state":state,
            }
            if did in residual_obligation_by_doc:
                obligation["residual_frontier_obligation"]=residual_obligation_by_doc[did]
            if state=="PROVED_QUERY_EFFECT_ID_INVENTORY_EXHAUSTIVE":
                obligation["inventory_warning"]=(
                    "EFFECT_ID_INVENTORY_DOES_NOT_PROVE_VALUE_CLASS_CONDITION_OR_"
                    "PRECEDENCE_COMPLETENESS_FOR_UNKNOWN_BYTES"
                )
            next_obligations.append(obligation)

        base={
            "schema":SCHEMA,
            "case_id":case_id,
            "byte_coverage_result":byte_result,
            "byte_coverage_verification":byte_check,
            "residual_result":residual_result,
            "residual_verification":residual_check,
            "finite_worldset_result":finite,
            "finite_worldset_verification":finite_check,
            "residual_states":dict(sorted(residual_states.items())),
            "documents_discharged_by_exact_byte_semantics":discharged_by_byte,
            "documents_discharged_by_query_target_exclusion":discharged_by_scope,
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }

        if unsafe:
            regions=[
                region
                for did in unsafe
                for region in unknown_by_doc.get(did,[])
            ]
            return {
                **base,
                "status":"OPEN__QUERY_RELEVANT_SOURCE_TOP_REMAINS",
                "pass":False,
                "blocking_document_ids":unsafe,
                "blocking_unknown_regions":sorted(
                    regions,key=lambda x:(x["document_id"],x["start"],x["end"])
                ),
                "next_proof_obligations":next_obligations,
                "possible_outcomes":deepcopy(finite.get("possible_outcomes") or []),
                "minimum_discriminator_slots":deepcopy(
                    finite.get("minimum_discriminator_slots") or []
                ),
                "world_count":finite.get("world_count"),
                "query_relative_source_completeness_proved":False,
                "soundness_rule":(
                    "UNKNOWN_SOURCE_BYTES_CANNOT_BE_DISCHARGED_BY_EFFECT_ID_"
                    "INVENTORY_ALONE__ONLY_EXACT_BYTE_SEMANTICS_OR_PROVED_QUERY_"
                    "TARGET_EXCLUSION_CAN_REMOVE_QUERY_RELEVANT_SOURCE_TOP"
                ),
            }

        if finite.get("pass") is not True:
            return {
                **base,
                "status":"OPEN__SOURCE_TOP_CLOSED__FINITE_EFFECT_WORLDS_NOT_CLOSED",
                "pass":False,
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
            **base,
            "status":"PASS__QUERY_RELATIVE_SOURCE_AND_EFFECT_COVERAGE_VERIFIED",
            "pass":True,
            "blocking_document_ids":[],
            "blocking_unknown_regions":[],
            "next_proof_obligations":[],
            "effective_value":deepcopy(finite.get("effective_value")),
            "world_count":finite.get("world_count"),
            "minimum_discriminator_slots":[],
            "query_relative_source_completeness_proved":True,
            "boundary":(
                "QUERY_CLOSURE_REQUIRES_EACH_DOCUMENT_TO_HAVE_EITHER_EXACT_"
                "BYTE_LEVEL_EFFECT_SEMANTICS_OR_SOURCE_PROVED_QUERY_TARGET_EXCLUSION;"
                "FINITE_WORLDSET_IS_INDEPENDENTLY_VERIFIED_AFTER_SOURCE_TOP_CLOSURE"
            ),
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }
