"""Source-aligned semantic proof registry base for V15.

V11 preserves V10 and adds one pluggable proof path:
    CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE

The caller identifies an exact source character span and supplies a scoped
semantic-entailment DAG. The claim receives zero authority unless
certified_document_effect_field_edge_v1 recomputes the DAG through an explicit
relation_verifier and proves that the exact source mention entails the
deterministic effect-field concept.

Accepted edge proofs are normalized to the existing
CERTIFIED_DOCUMENT_EFFECT_FIELD shape so the field lattice can consume them.
No relation verifier means the claim stays rejected/TOP.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v10 import (
    verify_proof as verify_v10,
)
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    prove_field,
)
from canonical.runtime.brain_owned_semantic_relation_edge_registry_v3 import (
    can_prove as brain_edge_can_prove,
    verify as brain_edge_verify,
)

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V15_REGISTRY_BASE"
EDGE_KIND="CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE"


def _fail(errors:list[str],base:Mapping[str,Any]|None=None)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "terminal_authority":False,
    }
    if isinstance(base,Mapping):
        out["base_proof"]=dict(base)
    return out


def _span(
    source_text:str,
    raw:Any,
)->tuple[int,int,str,list[int]]:
    if (
        not isinstance(raw,Sequence)
        or isinstance(raw,(str,bytes))
        or len(raw)!=2
    ):
        raise ValueError("SOURCE_SPAN_CHARS_INVALID")
    start,end=raw
    if (
        isinstance(start,bool) or not isinstance(start,int)
        or isinstance(end,bool) or not isinstance(end,int)
        or start<0 or end<=start or end>len(source_text)
    ):
        raise ValueError("SOURCE_SPAN_CHARS_INVALID")
    raw_span=source_text[start:end]
    if not raw_span.strip():
        raise ValueError("SOURCE_SPAN_EMPTY")
    byte_start=len(source_text[:start].encode("utf-8"))
    byte_end=byte_start+len(raw_span.encode("utf-8"))
    return start,end,raw_span,[byte_start,byte_end]


def verify_proof(
    source_text:str,
    *,
    source_id:str,
    claims:Sequence[Mapping[str,Any]],
    typed_context:Mapping[str,Any]|None=None,
    expected_typed_context_sha256:str|None=None,
    fact_source:str|bytes|None=None,
    fact_source_id:str|None=None,
    relation_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
    if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
        return _fail(["CLAIMS_INVALID"])

    base_claims=[]
    edge_claims=[]
    seen=set()
    errors=[]
    for i,claim in enumerate(claims):
        if not isinstance(claim,Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        cid=str(claim.get("claim_id") or "").strip()
        if not cid:
            errors.append(f"CLAIM_ID_MISSING:{i}")
            continue
        if cid in seen:
            errors.append("CLAIM_ID_DUPLICATE:"+cid)
            continue
        seen.add(cid)
        if claim.get("kind")==EDGE_KIND:
            edge_claims.append(claim)
        else:
            base_claims.append(claim)
    if errors:
        return _fail(errors)

    base=verify_v10(
        source_text,
        source_id=source_id,
        claims=base_claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,
        fact_source_id=fact_source_id,
    )
    if base.get("status")=="FAIL_CLOSED":
        return _fail(["V10_PRIMITIVE_CHECK_FAIL_CLOSED"],base)

    accepted=list(base.get("accepted_claims") or [])
    rejected=list(base.get("rejected_claims") or [])
    proved=list(base.get("proved_constraints") or [])
    edge_receipts=[]

    accepted_fields={}
    for row in accepted:
        if not isinstance(row,Mapping):
            continue
        if row.get("kind")!="CERTIFIED_DOCUMENT_EFFECT_FIELD":
            continue
        key=(str(row.get("effect_id") or ""),str(row.get("field") or ""))
        if key[0] and key[1]:
            accepted_fields[key]=row

    edge_values={}
    for claim in edge_claims:
        cid=str(claim["claim_id"])
        allowed={
            "claim_id","kind","scope_id","effect_id","field","value",
            "source_span_chars","dag_evidence","expected_dag_sha256",
        }
        if set(claim)!=allowed:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_FIELD_EDGE_CLAIM_FIELD_SET_INVALID",
            })
            continue
        try:
            start,end,raw_span,byte_span=_span(
                source_text,claim.get("source_span_chars")
            )
        except Exception as exc:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_FIELD_EDGE_SOURCE_SPAN_INVALID:"
                +type(exc).__name__+":"+str(exc),
            })
            continue

        effective_relation_verifier=relation_verifier
        if not callable(effective_relation_verifier):
            dag_evidence=claim.get("dag_evidence")
            rows=[]
            if isinstance(dag_evidence,Mapping):
                ent=dag_evidence.get("entailment_receipts")
                cnt=dag_evidence.get("counterexample_receipts")
                if (
                    isinstance(ent,Sequence)
                    and not isinstance(ent,(str,bytes))
                    and isinstance(cnt,Sequence)
                    and not isinstance(cnt,(str,bytes))
                ):
                    rows=list(ent)+list(cnt)
            if rows and all(brain_edge_can_prove(row) for row in rows):
                effective_relation_verifier=brain_edge_verify

        out=prove_field(
            source_id=source_id,
            raw_span=raw_span,
            scope_id=claim.get("scope_id"),
            effect_id=claim.get("effect_id"),
            field=claim.get("field"),
            value=claim.get("value"),
            dag_evidence=claim.get("dag_evidence"),
            expected_dag_sha256=str(
                claim.get("expected_dag_sha256") or ""
            ),
            relation_verifier=effective_relation_verifier,
        )
        if out.get("status")=="FAIL_CLOSED":
            return _fail(
                [
                    "DOCUMENT_EFFECT_FIELD_EDGE_FAIL_CLOSED:"
                    +cid+":"+str(out.get("reason") or "UNKNOWN")
                ],
                base,
            )
        if out.get("pass") is not True:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_FIELD_EDGE_NOT_PROVED:"
                +str(out.get("reason") or out.get("status") or "UNKNOWN"),
            })
            continue

        receipt=out.get("field_receipt")
        if not isinstance(receipt,Mapping):
            return _fail(
                ["DOCUMENT_EFFECT_FIELD_EDGE_RECEIPT_MISSING:"+cid],
                base,
            )
        eid=str(receipt.get("effect_id") or "")
        field=str(receipt.get("field") or "")
        value=receipt.get("value")
        key=(eid,field)

        prior=accepted_fields.get(key)
        if prior is not None:
            if prior.get("value")!=value:
                return _fail(
                    ["DIRECT_AND_EDGE_FIELD_CONFLICT:"+eid+":"+field],
                    base,
                )
            edge_receipts.append({
                "claim_id":cid,
                "status":"REDUNDANT_WITH_EXISTING_FIELD_PROOF",
                "field_receipt":dict(receipt),
            })
            continue

        if key in edge_values:
            if edge_values[key]!=value:
                return _fail(
                    ["MULTIPLE_EDGE_FIELD_VALUES_CONFLICT:"+eid+":"+field],
                    base,
                )
            edge_receipts.append({
                "claim_id":cid,
                "status":"REDUNDANT_WITH_PRIOR_EDGE_FIELD_PROOF",
                "field_receipt":dict(receipt),
            })
            continue
        edge_values[key]=value

        receipt_sha=str(receipt.get("receipt_sha256") or "")
        constraint={
            "op":"ATOM",
            "id":"DOCUMENT_EFFECT_FIELD_EDGE::"
            +source_id+"::"+receipt_sha,
        }
        raw_hash=sha256(raw_span.encode("utf-8")).hexdigest()
        row={
            "claim_id":cid,
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "field_id":"EDGE-FIELD-"+receipt_sha[:24],
            "effect_id":eid,
            "field":field,
            "value":value,
            "source_span_chars":[start,end],
            "source_span_bytes":byte_span,
            "source_text_sha256":raw_hash,
            "constraint":constraint,
            "proof_primitive":"SEMANTIC_ENTAILMENT_DAG_FIELD_EDGE_V1",
            "semantic_edge_receipt_sha256":receipt_sha,
        }
        accepted.append(row)
        accepted_fields[key]=row
        proved.append(constraint)
        edge_receipts.append({
            "claim_id":cid,
            "status":"ACCEPTED",
            "field_receipt":dict(receipt),
        })

    return {
        "schema":SCHEMA,
        "status":"PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id":source_id,
        "accepted_claims":accepted,
        "rejected_claims":rejected,
        "proved_constraints":proved,
        "edge_field_receipts":edge_receipts,
        "terminal_authority":False,
        "soundness_boundary":(
            "V15_REGISTRY_BASE_PRESERVES_V14_FIELD_EDGE_SEMANTICS_WITH_REGISTRY_V3_"
            "INDEPENDENTLY_RECOMPUTED_SCOPED_SEMANTIC_ENTAILMENT_DAG;"
            "MISSING_RELATION_VERIFIER_OR_UNPROVED_EDGE_LEAVES_THE_FIELD_UNPROVED;"
            "BRAIN_OWNED_SEMANTIC_RELATION_EDGE_REGISTRY_V3_IS_USED_ONLY_WHEN_EVERY_DAG_"
            "RECEIPT_IS_A_SUPPORTED_INTERNAL_PROOF_CLASS;"
            "UNSUPPORTED_EVIDENCE_WITHOUT_CALLER_VERIFIER_REMAINS_TOP;"
            "NO_GENERAL_RAW_LANGUAGE_EXTRACTION_CLOSURE"
        ),
    }
