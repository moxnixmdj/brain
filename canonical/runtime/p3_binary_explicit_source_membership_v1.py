"""Strict explicit-source membership for the bounded P3 binary decision cell.

This compiler proves membership only when the authoritative raw source is itself
an exact JSON encoding of the complete bounded cell contract. It rejects duplicate
JSON keys, unknown semantic fields, extra claims/evidence, non-explicit audience
profiles, and objectives that are only partially matched by the existing binary
objective parser.

It then executes the already verified grounded binary decision expression cell.
A pass proves semantic scope membership for this explicit raw-source subregion
only. It does not authenticate that an upstream caller chose the authoritative
source, does not map free-form tasks into the schema, and grants no policy/DB/U/
terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import objective_claim_operand_binding as binder
from canonical.runtime.p3_binary_decision_grounded_expression_v1 import evaluate as expression
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA

SCHEMA="PROJECT_BRAIN_P3_BINARY_EXPLICIT_SOURCE_MEMBERSHIP_V1"
CONTRACT="P3_BOUND_BINARY_OBJECTIVE_DECISION_EXPRESSION_V1"
MAX_BYTES=2_000_000

_TOP_KEYS={"contract","objective","v2_input"}
_V2_KEYS={"schema","task"}
_TASK_KEYS={"claims","evidence","audience_profile"}
_CLAIM_KEYS={"claim_id","text","required"}
_EVIDENCE_KEYS={"evidence_id","text","verified","provenance"}
_PROFILE_KEYS={"profile_id","constraints"}
_CONSTRAINT_KEYS={
  "output_format","citation_mode","style","required_sections","allowed_sections",
  "max_items","max_chars","heading_level","require_title",
}
_PROVENANCE_KEYS={"source_id","locator"}


class MembershipError(ValueError):
    pass


def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out:
            raise MembershipError("DUPLICATE_JSON_KEY:"+str(k))
        out[k]=v
    return out


def _token(v:Any,label:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise MembershipError(label+"_INVALID")
    return v.strip()


def _strict_binary_objective(objective:str)->dict[str,Any]:
    raw=_token(objective,"OBJECTIVE")
    if "\n" in raw or "\r" in raw:
        raise MembershipError("OBJECTIVE_MULTILINE_FORBIDDEN")

    parsed,reason=binder._parse_objective(raw)
    if reason or not isinstance(parsed,Mapping) or parsed.get("mode")!="NUMERIC_RELATION":
        raise MembershipError("OBJECTIVE_NOT_BOUND_BINARY_NUMERIC_RELATION")

    matches=[]
    for rx,op,threshold_group in binder._RELATION_PATTERNS:
        m=rx.fullmatch(raw)
        if not m:
            continue
        left=binder._clean_entity(m.group(1))
        right=binder._clean_entity(m.group(2))
        threshold=(
          binder._canon(m.group(threshold_group)).rstrip(".,;:")
          if threshold_group else None
        )
        row={"operator":op,"left_entity":left,"right_entity":right,"threshold":threshold}
        if row not in matches:
            matches.append(row)
    if len(matches)!=1:
        raise MembershipError("OBJECTIVE_NOT_EXACTLY_FULLY_CONSUMED_BY_ONE_BINARY_GRAMMAR")

    exact=matches[0]
    if (
      exact["operator"]!=parsed.get("operator")
      or exact["left_entity"]!=parsed.get("left_entity")
      or exact["right_entity"]!=parsed.get("right_entity")
      or exact["threshold"]!=parsed.get("threshold")
    ):
        raise MembershipError("OBJECTIVE_FULLMATCH_PARSE_DRIFT")
    return {
      "operator":exact["operator"],
      "left_entity":exact["left_entity"],
      "right_entity":exact["right_entity"],
      "threshold":exact["threshold"],
    }


def _validate_provenance(value:Any,label:str)->None:
    if not isinstance(value,list) or not value:
        raise MembershipError(label+"_REQUIRED")
    for i,row in enumerate(value):
        if not isinstance(row,Mapping) or set(row)-_PROVENANCE_KEYS:
            raise MembershipError(f"{label}_ROW_FIELDS_INVALID:{i}")
        _token(row.get("source_id"),f"{label}_SOURCE_ID:{i}")
        if "locator" in row and row.get("locator") is not None:
            _token(row.get("locator"),f"{label}_LOCATOR:{i}")


def _validate_doc(doc:Mapping[str,Any])->dict[str,Any]:
    if set(doc)!=_TOP_KEYS:
        raise MembershipError("TOP_LEVEL_KEYS_NOT_EXACT_BOUND_CELL")
    if doc.get("contract")!=CONTRACT:
        raise MembershipError("BOUND_BINARY_CONTRACT_ID_REQUIRED")
    objective_info=_strict_binary_objective(doc.get("objective"))

    public=doc.get("v2_input")
    if not isinstance(public,Mapping) or set(public)!=_V2_KEYS:
        raise MembershipError("V2_INPUT_KEYS_NOT_EXACT")
    if public.get("schema")!=INPUT_SCHEMA:
        raise MembershipError("V2_INPUT_SCHEMA_INVALID")
    task=public.get("task")
    if not isinstance(task,Mapping) or set(task)!=_TASK_KEYS:
        raise MembershipError("TASK_KEYS_NOT_EXACT_BOUND_CELL")

    claims=task.get("claims")
    if not isinstance(claims,list) or len(claims)!=2:
        raise MembershipError("EXACTLY_TWO_CLAIMS_REQUIRED")
    claim_ids=set()
    for i,row in enumerate(claims):
        if not isinstance(row,Mapping) or set(row)!=_CLAIM_KEYS:
            raise MembershipError(f"CLAIM_KEYS_NOT_EXACT:{i}")
        cid=_token(row.get("claim_id"),f"CLAIM_ID:{i}")
        if cid in claim_ids:
            raise MembershipError("DUPLICATE_CLAIM_ID:"+cid)
        claim_ids.add(cid)
        _token(row.get("text"),f"CLAIM_TEXT:{cid}")
        if row.get("required") is not False:
            raise MembershipError("EXACT_CELL_REQUIRES_TWO_OPTIONAL_CLAIMS")

    evidence=task.get("evidence")
    if not isinstance(evidence,list) or len(evidence)!=2:
        raise MembershipError("EXACTLY_TWO_EVIDENCE_UNITS_REQUIRED")
    evidence_ids=set()
    for i,row in enumerate(evidence):
        if not isinstance(row,Mapping) or set(row)!=_EVIDENCE_KEYS:
            raise MembershipError(f"EVIDENCE_KEYS_NOT_EXACT:{i}")
        eid=_token(row.get("evidence_id"),f"EVIDENCE_ID:{i}")
        if eid in evidence_ids:
            raise MembershipError("DUPLICATE_EVIDENCE_ID:"+eid)
        evidence_ids.add(eid)
        _token(row.get("text"),f"EVIDENCE_TEXT:{eid}")
        if row.get("verified") is not True:
            raise MembershipError("UNVERIFIED_EVIDENCE:"+eid)
        _validate_provenance(row.get("provenance"),"PROVENANCE:"+eid)

    profile=task.get("audience_profile")
    if not isinstance(profile,Mapping) or set(profile)!=_PROFILE_KEYS:
        raise MembershipError("AUDIENCE_PROFILE_KEYS_NOT_EXACT")
    if profile.get("profile_id")!="EXPLICIT":
        raise MembershipError("EXPLICIT_AUDIENCE_PROFILE_REQUIRED")
    constraints=profile.get("constraints")
    if not isinstance(constraints,Mapping) or set(constraints)!=_CONSTRAINT_KEYS:
        raise MembershipError("AUDIENCE_CONSTRAINT_KEYS_NOT_EXACT")

    return objective_info


def compile_membership(raw_source:str|bytes,*,source_id:str)->dict[str,Any]:
    try:
        sid=_token(source_id,"SOURCE_ID")
        raw=raw_source.encode("utf-8") if isinstance(raw_source,str) else raw_source
        if not isinstance(raw,bytes):
            raise MembershipError("RAW_SOURCE_MUST_BE_TEXT_OR_BYTES")
        if not raw:
            raise MembershipError("RAW_SOURCE_EMPTY")
        if len(raw)>MAX_BYTES:
            raise MembershipError("RAW_SOURCE_TOO_LARGE")
        try:
            text=raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MembershipError("RAW_SOURCE_NOT_UTF8") from exc
        try:
            doc=json.loads(text,object_pairs_hook=_pairs)
        except MembershipError:
            raise
        except Exception as exc:
            raise MembershipError("RAW_SOURCE_JSON_INVALID") from exc
        if not isinstance(doc,Mapping):
            raise MembershipError("RAW_SOURCE_JSON_NOT_OBJECT")

        objective_info=_validate_doc(doc)
        expr=expression({"objective":doc["objective"],"v2_input":doc["v2_input"]})
        if expr.get("pass") is not True:
            raise MembershipError("VERIFIED_BOUND_CELL_EXPRESSION_DID_NOT_PASS:"+str(expr.get("reason") or expr.get("status")))
        if (
          expr.get("decision_expression_covered") is not True
          or expr.get("bound_cell_required_decision_coverage_complete") is not True
          or expr.get("real_context_semantic_scope_complete") is not False
          or expr.get("policy_adequacy_authority") is not False
          or expr.get("db_admission_authority") is not False
          or expr.get("u_subtraction_authority") is not False
          or expr.get("terminal_authority") is not False
          or expr.get("terminal_credit_delta")!=0
        ):
            raise MembershipError("DOWNSTREAM_EXPRESSION_AUTHORITY_BOUNDARY_INVALID")

        raw_sha=sha256(raw).hexdigest()
        normalized=json.dumps(doc,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
        normalized_sha=sha256(normalized).hexdigest()
        receipt="P3BINMEM:"+sha256((sid+"\0"+raw_sha+"\0"+normalized_sha).encode("utf-8")).hexdigest()
        return {
          "schema":SCHEMA,
          "status":"PASS__LOSSLESS_EXPLICIT_BOUND_BINARY_SOURCE_MEMBERSHIP",
          "pass":True,
          "source_id":sid,
          "contract_id":CONTRACT,
          "raw_source_sha256":raw_sha,
          "normalized_public_sha256":normalized_sha,
          "membership_receipt":receipt,
          "objective_relation":objective_info,
          "expression_receipt":expr,
          "real_context_semantic_scope_complete":True,
          "scope_membership_proved":True,
          "extra_source_semantic_fields_permitted":False,
          "source_authorization_verified":False,
          "policy_adequacy_authority":False,
          "db_admission_authority":False,
          "u_subtraction_authority":False,
          "terminal_authority":False,
          "terminal_credit_delta":0,
          "boundary":(
            "AUTHORITATIVE_RAW_SOURCE_IS_ITSELF_THE_STRICT_EXPLICIT_JSON_ENCODING_OF_"
            "THE_EXACT_BOUND_BINARY_OBJECTIVE_DECISION_EXPRESSION_CELL__"
            "NO_FREE_FORM_TO_SCHEMA_MAPPING__NO_UPSTREAM_SOURCE_AUTHORIZATION"
          ),
        }
    except MembershipError as exc:
        return {
          "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
          "errors":[str(exc)],
          "real_context_semantic_scope_complete":False,
          "scope_membership_proved":False,
          "source_authorization_verified":False,
          "policy_adequacy_authority":False,"db_admission_authority":False,
          "u_subtraction_authority":False,"terminal_authority":False,
          "terminal_credit_delta":0,
        }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    args=args or {}
    return compile_membership(args.get("raw_source") or "",source_id=str(args.get("source_id") or ""))
