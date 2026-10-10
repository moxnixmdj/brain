"""Bounded minimum proof discovery for one document-effect field V1.

Inputs are proposals only:
- candidate source spans,
- candidate normalized field values,
- candidate semantic relation evidence rows.

None has authority. Every evidence row must independently pass the Brain-owned
semantic relation registry and then re-pass the exact field-edge adapter binding
for the candidate source span and field concept.

If no candidate proves the field, the field remains TOP.
If more than one distinct field value is independently proved, discovery fails
closed rather than choosing.
If several proofs establish the same value, the smallest deterministic proof is
selected by source span bytes, evidence bytes, then lexical tie-breakers.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.brain_owned_semantic_relation_edge_registry_v4 import (
    verify as verify_relation,
)
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
    prove_field,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)

SCHEMA="PROJECT_BRAIN_DOCUMENT_EFFECT_FIELD_PROOF_DISCOVERY_V1"
MAX_SPANS=128
MAX_VALUES=64
MAX_EVIDENCE_ROWS=256
MAX_PROVED_CANDIDATES=256


def _canon(v:Any)->str:
    return json.dumps(
        v,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    cleaned=v.strip()
    if cleaned!=v:
        raise ValueError(name+"_NOT_CANONICAL")
    return cleaned


def _mention_id(source_id:str,scope_id:str,raw_span:str)->str:
    return "MENTION:"+sha256(
        (source_id+"\n"+scope_id+"\n"+raw_span).encode("utf-8")
    ).hexdigest()


def _spans(source_text:str,rows:Any)->list[dict[str,Any]]:
    if (
        not isinstance(rows,Sequence)
        or isinstance(rows,(str,bytes))
        or not rows
        or len(rows)>MAX_SPANS
    ):
        raise ValueError("CANDIDATE_SPANS_INVALID_OR_TOO_LARGE")
    out=[]; seen=set()
    for i,row in enumerate(rows):
        if (
            not isinstance(row,Sequence)
            or isinstance(row,(str,bytes))
            or len(row)!=2
        ):
            raise ValueError("CANDIDATE_SPAN_INVALID:"+str(i))
        start,end=row
        if (
            isinstance(start,bool) or not isinstance(start,int)
            or isinstance(end,bool) or not isinstance(end,int)
            or start<0 or end<=start or end>len(source_text)
        ):
            raise ValueError("CANDIDATE_SPAN_INVALID:"+str(i))
        key=(start,end)
        if key in seen:
            continue
        seen.add(key)
        raw=source_text[start:end]
        if not raw.strip():
            continue
        out.append({
            "start":start,
            "end":end,
            "raw_span":raw,
            "byte_length":len(raw.encode("utf-8")),
        })
    if not out:
        raise ValueError("NO_NONEMPTY_CANDIDATE_SPANS")
    out.sort(key=lambda x:(x["byte_length"],x["start"],x["end"]))
    return out


def _values(
    *,
    scope_id:str,
    effect_id:str,
    field:str,
    rows:Any,
)->list[dict[str,Any]]:
    if (
        not isinstance(rows,Sequence)
        or isinstance(rows,(str,bytes))
        or not rows
        or len(rows)>MAX_VALUES
    ):
        raise ValueError("CANDIDATE_VALUES_INVALID_OR_TOO_LARGE")
    out=[]; seen=set()
    for i,value in enumerate(rows):
        try:
            concept=field_concept_id(
                scope_id=scope_id,
                effect_id=effect_id,
                field=field,
                value=value,
            )
        except Exception:
            continue
        key=_canon(value)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "value":value,
            "value_key":key,
            "field_concept_id":concept,
        })
    if not out:
        raise ValueError("NO_VALID_CANDIDATE_VALUES")
    out.sort(key=lambda x:x["value_key"])
    return out


def _evidence_rows(rows:Any)->list[dict[str,Any]]:
    if (
        not isinstance(rows,Sequence)
        or isinstance(rows,(str,bytes))
        or len(rows)>MAX_EVIDENCE_ROWS
    ):
        raise ValueError("RELATION_EVIDENCE_CANDIDATES_INVALID_OR_TOO_LARGE")
    out=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            continue
        raw=dict(row)
        checked=verify_relation(raw)
        if not isinstance(checked,Mapping) or checked.get("pass") is not True:
            continue
        if checked.get("relation")!="ENTAILS":
            continue
        out.append({
            "candidate_index":i,
            "raw":raw,
            "receipt":dict(checked),
            "raw_size":len(_canon(raw).encode("utf-8")),
        })
    out.sort(key=lambda x:(x["raw_size"],x["candidate_index"]))
    return out


def discover(problem:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(problem,Mapping) or problem.get("schema")!=SCHEMA:
            raise ValueError("PROBLEM_SCHEMA_INVALID")
        if set(problem)!={
            "schema","source_id","source_text","scope_id","effect_id","field",
            "candidate_spans","candidate_values","relation_evidence_candidates",
        }:
            raise ValueError("PROBLEM_FIELD_SET_NOT_EXACT")

        source_id=_token(problem.get("source_id"),"SOURCE_ID")
        source_text=problem.get("source_text")
        if not isinstance(source_text,str) or not source_text:
            raise ValueError("SOURCE_TEXT_INVALID")
        scope_id=_token(problem.get("scope_id"),"SCOPE_ID")
        effect_id=_token(problem.get("effect_id"),"EFFECT_ID")
        field=_token(problem.get("field"),"FIELD")

        spans=_spans(source_text,problem.get("candidate_spans"))
        values=_values(
            scope_id=scope_id,
            effect_id=effect_id,
            field=field,
            rows=problem.get("candidate_values"),
        )
        evidence=_evidence_rows(problem.get("relation_evidence_candidates"))

        evidence_index={}
        for row in evidence:
            receipt=row["receipt"]
            key=(
                str(receipt.get("scope_id") or ""),
                str(receipt.get("source_id") or ""),
                str(receipt.get("target_id") or ""),
            )
            evidence_index.setdefault(key,[]).append(row)

        proved=[]
        attempted_bindings=0
        for span in spans:
            mention=_mention_id(source_id,scope_id,span["raw_span"])
            for value in values:
                key=(scope_id,mention,value["field_concept_id"])
                candidates=evidence_index.get(key,[])
                for ev in candidates:
                    attempted_bindings+=1
                    dag={
                        "schema":EVIDENCE_SCHEMA,
                        "scope_id":scope_id,
                        "left_id":mention,
                        "right_id":value["field_concept_id"],
                        "entailment_receipts":[ev["raw"]],
                        "counterexample_receipts":[],
                    }
                    out=prove_field(
                        source_id=source_id,
                        raw_span=span["raw_span"],
                        scope_id=scope_id,
                        effect_id=effect_id,
                        field=field,
                        value=value["value"],
                        dag_evidence=dag,
                        expected_dag_sha256=evidence_sha256(dag),
                        relation_verifier=verify_relation,
                    )
                    if out.get("pass") is not True:
                        continue
                    receipt=out.get("field_receipt")
                    if not isinstance(receipt,Mapping):
                        continue
                    candidate={
                        "value":value["value"],
                        "value_key":value["value_key"],
                        "source_span_chars":[span["start"],span["end"]],
                        "source_span_byte_length":span["byte_length"],
                        "evidence_candidate_index":ev["candidate_index"],
                        "evidence_raw_size":ev["raw_size"],
                        "dag_evidence":dag,
                        "expected_dag_sha256":evidence_sha256(dag),
                        "field_receipt":dict(receipt),
                    }
                    proved.append(candidate)
                    if len(proved)>MAX_PROVED_CANDIDATES:
                        raise ValueError("PROVED_CANDIDATE_BOUND_EXCEEDED")

        distinct={row["value_key"] for row in proved}
        if len(distinct)>1:
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED__MULTIPLE_PROVED_FIELD_VALUES",
                "pass":False,
                "effect_id":effect_id,
                "field":field,
                "proved_values":[
                    json.loads(key) for key in sorted(distinct)
                ],
                "proved_candidate_count":len(proved),
                "semantic_truth_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }

        if not proved:
            return {
                "schema":SCHEMA,
                "status":"OPEN__NO_AUTHENTICATED_FIELD_PROOF_DISCOVERED",
                "pass":False,
                "effect_id":effect_id,
                "field":field,
                "candidate_span_count":len(spans),
                "candidate_value_count":len(values),
                "authenticated_relation_evidence_count":len(evidence),
                "attempted_bindings":attempted_bindings,
                "claim":None,
                "semantic_truth_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }

        proved.sort(key=lambda row:(
            row["source_span_byte_length"],
            row["evidence_raw_size"],
            row["source_span_chars"][0],
            row["source_span_chars"][1],
            row["value_key"],
            row["evidence_candidate_index"],
        ))
        best=proved[0]
        claim={
            "claim_id":"DISCOVERED_FIELD_EDGE::"+sha256(
                _canon({
                    "source_id":source_id,
                    "scope_id":scope_id,
                    "effect_id":effect_id,
                    "field":field,
                    "value":best["value"],
                    "source_span_chars":best["source_span_chars"],
                    "dag_evidence":best["dag_evidence"],
                }).encode("utf-8")
            ).hexdigest(),
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
            "scope_id":scope_id,
            "effect_id":effect_id,
            "field":field,
            "value":best["value"],
            "source_span_chars":best["source_span_chars"],
            "dag_evidence":best["dag_evidence"],
            "expected_dag_sha256":best["expected_dag_sha256"],
        }
        return {
            "schema":SCHEMA,
            "status":"PASS__MINIMUM_AUTHENTICATED_FIELD_PROOF_DISCOVERED",
            "pass":True,
            "effect_id":effect_id,
            "field":field,
            "value":best["value"],
            "claim":claim,
            "field_receipt":best["field_receipt"],
            "proved_candidate_count":len(proved),
            "candidate_span_count":len(spans),
            "candidate_value_count":len(values),
            "authenticated_relation_evidence_count":len(evidence),
            "attempted_bindings":attempted_bindings,
            "selection_objective":[
                "MIN_SOURCE_SPAN_BYTES",
                "MIN_EVIDENCE_BYTES",
                "EARLIEST_SOURCE_SPAN",
                "CANONICAL_VALUE",
                "EARLIEST_EVIDENCE_CANDIDATE",
            ],
            "search_authority":False,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
            "boundary":(
                "DISCOVERY_IS_COMPLETE_ONLY_RELATIVE_TO_THE_SUPPLIED_FINITE_"
                "SPAN_VALUE_AND_EVIDENCE_CANDIDATE_UNIVERSE__EVERY_SELECTED_"
                "PROOF_IS_INDEPENDENTLY_RECOMPUTED_BY_THE_BRAIN_OWNED_RELATION_"
                "REGISTRY_AND_FIELD_EDGE_ADAPTER"
            ),
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "search_authority":False,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }
