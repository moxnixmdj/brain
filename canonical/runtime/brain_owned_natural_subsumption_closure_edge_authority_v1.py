"""Brain-owned controlled-natural subsumption-closure edge authority V1.

Proof class: NATURAL_SUBSUMPTION_CLOSURE

It proves a requested ENTAILS relation only when:
- every load-bearing local edge is parsed from an exact controlled-natural
  "every X is a Y" source sentence,
- the requested source->target relation is not itself directly declared, and
- a path of at least two independently source-aligned subsumption edges connects
  source to target.

No NOT_ENTAILS conclusion is derived from a missing path.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.certified_natural_semantic_subsumption_source_v1 import parse
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_EVIDENCE_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_NATURAL_SUBSUMPTION_CLOSURE_EDGE_AUTHORITY_V1"
PROOF_CLASS="NATURAL_SUBSUMPTION_CLOSURE"


def _canon(v:Any)->bytes:
    return json.dumps(
        v,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    ).encode("utf-8")


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "pass":False,
        "schema":AUTHORITY_SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        **extra,
    }


def supports(raw:Any)->bool:
    return (
        isinstance(raw,Mapping)
        and raw.get("schema")==SCHEMA
        and raw.get("proof_class")==PROOF_CLASS
    )


def _path(adj:Mapping[str,set[str]],start:str,target:str)->list[str]|None:
    q=deque([start])
    prior={start:None}
    while q:
        cur=q.popleft()
        for nxt in sorted(adj.get(cur,set())):
            if nxt in prior:
                continue
            prior[nxt]=cur
            if nxt==target:
                rev=[target]
                node=target
                while prior[node] is not None:
                    node=prior[node]
                    rev.append(node)
                return list(reversed(rev))
            q.append(nxt)
    return None


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")
    allowed={
        "schema","proof_class","scope_id","source_id","target_id",
        "relation","natural_subsumption_source",
    }
    if set(raw)!=allowed:
        return _fail(
            "EVIDENCE_FIELD_SET_INVALID",
            extra_fields=sorted(set(raw)-allowed),
            missing_fields=sorted(allowed-set(raw)),
        )
    if raw.get("schema")!=SCHEMA:
        return _fail("EVIDENCE_SCHEMA_INVALID")
    if raw.get("proof_class")!=PROOF_CLASS:
        return _fail("PROOF_CLASS_UNSUPPORTED")

    scope=str(raw.get("scope_id") or "").strip()
    source=str(raw.get("source_id") or "").strip()
    target=str(raw.get("target_id") or "").strip()
    relation=str(raw.get("relation") or "").strip().upper()
    if not scope:
        return _fail("SCOPE_ID_REQUIRED")
    if not source or not target or source==target:
        return _fail("DISTINCT_SOURCE_TARGET_IDS_REQUIRED")
    if relation!="ENTAILS":
        return _fail("ONLY_POSITIVE_ENTAILS_SUPPORTED")

    src=raw.get("natural_subsumption_source")
    if not isinstance(src,Mapping) or set(src)!={"source_id","source_text"}:
        return _fail("NATURAL_SUBSUMPTION_SOURCE_INVALID")
    declaration_source_id=str(src.get("source_id") or "").strip()
    source_text=src.get("source_text")
    if (
        not declaration_source_id
        or not isinstance(source_text,str)
        or not source_text
    ):
        return _fail("NATURAL_SUBSUMPTION_SOURCE_BINDING_INVALID")

    parsed=parse(source_text,source_id=declaration_source_id)
    if parsed.get("status")!="PARSED":
        return _fail(
            "NATURAL_SUBSUMPTION_SOURCE_NOT_CERTIFIED",
            parse_status=parsed.get("status"),
            parse_reason=parsed.get("reason"),
        )

    rows=[
        row for row in parsed.get("edges") or []
        if isinstance(row,Mapping) and row.get("scope_id")==scope
    ]
    direct=any(
        row.get("source_id")==source and row.get("target_id")==target
        for row in rows
    )
    if direct:
        return _fail("REQUESTED_RELATION_IS_EXPLICIT_NOT_NONEXPLICIT")

    adj={}
    by_pair={}
    for row in rows:
        a=str(row.get("source_id") or "")
        b=str(row.get("target_id") or "")
        if not a or not b:
            return _fail("PARSED_EDGE_BINDING_INVALID")
        adj.setdefault(a,set()).add(b)
        by_pair[(a,b)]=row

    path=_path(adj,source,target)
    if path is None:
        return _fail("NONEXPLICIT_ENTAILMENT_PATH_NOT_PROVED")
    if len(path)<3:
        return _fail("NONEXPLICIT_PATH_MUST_USE_AT_LEAST_TWO_EDGES")

    path_receipts=[]
    for a,b in zip(path,path[1:]):
        row=by_pair[(a,b)]
        path_receipts.append({
            "source_id":a,
            "target_id":b,
            "source_span_bytes":deepcopy(row.get("source_span_bytes")),
            "source_text_sha256":row.get("source_text_sha256"),
            "semantic_relation":"SUBSET_ENTAILS",
        })

    evidence_sha=sha256(_canon(dict(raw))).hexdigest()
    body={
        "pass":True,
        "schema":RECEIPT_SCHEMA,
        "scope_id":scope,
        "source_id":source,
        "target_id":target,
        "relation":"ENTAILS",
        "source_semantics_authenticated":True,
        "target_semantics_authenticated":True,
        "relation_semantics_authenticated":True,
        "verification_authority_mutated":False,
        "evidence_sha256":evidence_sha,
    }
    receipt_sha=sha256(_canon(body)).hexdigest()
    return {
        **body,
        "receipt_sha256":receipt_sha,
        "authority_schema":AUTHORITY_SCHEMA,
        "proof_class":PROOF_CLASS,
        "nonexplicit_entailment_path":path,
        "path_edge_receipts":path_receipts,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":(
            "POSITIVE_TRANSITIVE_CLOSURE_OVER_EXACT_SOURCE_ALIGNED_CONTROLLED_"
            "NATURAL_SUBSUMPTION_SENTENCES_ONLY__NO_NOT_ENTAILS_OPEN_WORLD_"
            "COMPLETENESS_GENERAL_PARSING_OR_LEXICAL_INFERENCE"
        ),
    }
