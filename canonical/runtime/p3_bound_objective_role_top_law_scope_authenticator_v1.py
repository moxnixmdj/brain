"""P3 bound objective-role top-law scope authenticator v1.

This is a closed-language membership checker for the exact V12 binary-objective
presentation subregion. It proves membership only when every input-bearing byte
is assigned to a declared role consumed by the already-verified presentation
compiler:

- the objective is one whole explicit binary numeric-comparison sentence;
- its LEFT/RIGHT operands exactly equal the two numeric claim subjects;
- exactly two optional claims exist and exactly match exactly two verified
  evidence texts;
- payload/task/claim/evidence/provenance/audience mappings contain no unknown
  fields;
- the audience profile is the explicit typed constraint profile with no title,
  section, caller include/order, or other side channel;
- the existing bounded objective-role presentation compiler passes.

Anything outside this closed grammar fails closed. This authenticates membership
only for this syntactic/typed subregion. It does not prove general presentation
adequacy, source authority, policy adequacy, DB admission, U-empty, or terminality.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import objective_claim_operand_binding as binder
from canonical.runtime import synthesis_certified_visible_support_policy_v2 as policy_v2
from canonical.runtime.p3_bounded_objective_role_presentation_compiler_v1 import (
    evaluate as compile_presentation,
)

SCHEMA="PROJECT_BRAIN_P3_BOUND_OBJECTIVE_ROLE_TOP_LAW_SCOPE_AUTHENTICATOR_V1"

_PAYLOAD_FIELDS={"objective","v2_input"}
_INPUT_FIELDS={"schema","task"}
_TASK_FIELDS={"claims","evidence","audience_profile"}
_CLAIM_FIELDS={"claim_id","text","required"}
_EVIDENCE_FIELDS={"evidence_id","text","verified","provenance"}
_PROVENANCE_FIELDS={"source_id","locator"}
_PROFILE_FIELDS={"profile_id","constraints"}
_CONSTRAINT_FIELDS={
    "output_format","citation_mode","style","required_sections","allowed_sections",
    "max_items","max_chars","heading_level","require_title",
}
_SUBJECT=re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _+/%°µμ^·*'-]{0,239}$")


def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "explicit_payload_surface_exhaustively_consumed":False,
      "real_context_top_law_scope_membership_authenticated":False,
      "no_unmodeled_payload_presentation_channels":False,
      "presentation_policy_constructed":False,
      "policy_adequacy_authority":False,"db_admission_authority":False,
      "u_subtraction_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def _canon(x:Any)->str:
    return " ".join(str(x if x is not None else "").strip().split())


def _exact_fields(row:Any,allowed:set[str])->bool:
    return isinstance(row,Mapping) and set(row)==allowed


def _numeric_claim(text:Any)->dict[str,str]|None:
    raw=_canon(text)
    if not raw:
        return None
    if raw.endswith("."):
        raw=raw[:-1].rstrip()
    # The subject is deliberately a restricted opaque role label. It cannot
    # contain sentence/control punctuation that could carry a second directive.
    m=re.fullmatch(
      r"(?P<subject>[A-Za-z0-9][A-Za-z0-9 _+/%°µμ^·*'-]{0,239})\s+is\s+(?P<value>.+)",
      raw,
    )
    if not m:
        return None
    subject=_canon(m.group("subject"))
    value=_canon(m.group("value"))
    if not _SUBJECT.fullmatch(subject):
        return None
    if re.fullmatch(binder._NUM_SURFACE,value) is None:
        return None
    return {"subject":subject,"value":value}


def _full_objective(text:Any)->dict[str,Any]|None:
    raw=_canon(text)
    if not raw:
        return None
    full=[]
    for rx,op,threshold_group in binder._RELATION_PATTERNS:
        m=rx.fullmatch(raw)
        if not m:
            continue
        left=binder._clean_entity(m.group(1))
        right=binder._clean_entity(m.group(2))
        threshold=(
          _canon(m.group(threshold_group)).rstrip(".,;:")
          if threshold_group else None
        )
        # No second sentence / punctuation-bearing operand is admitted.
        if not _SUBJECT.fullmatch(left) or not _SUBJECT.fullmatch(right):
            continue
        full.append((op,left,right,threshold))
    if len(full)!=1:
        return None
    parsed,reason=binder._parse_objective(raw)
    if reason or not isinstance(parsed,dict) or parsed.get("mode")!="NUMERIC_RELATION":
        return None
    op,left,right,threshold=full[0]
    if (
      parsed.get("operator")!=op
      or _canon(parsed.get("left_entity"))!=left
      or _canon(parsed.get("right_entity"))!=right
      or parsed.get("threshold")!=threshold
    ):
        return None
    return {"operator":op,"left":left,"right":right,"threshold":threshold}


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    try:
        if not _exact_fields(payload,_PAYLOAD_FIELDS):
            return _fail("PAYLOAD_FIELDS_NOT_CLOSED")
        objective=_full_objective(payload.get("objective"))
        if objective is None:
            return _fail("OBJECTIVE_NOT_EXACT_WHOLE_BINARY_NUMERIC_COMPARISON")

        public=payload.get("v2_input")
        if not _exact_fields(public,_INPUT_FIELDS):
            return _fail("V2_INPUT_FIELDS_NOT_CLOSED")
        if public.get("schema")!=policy_v2.INPUT_SCHEMA:
            return _fail("V2_INPUT_SCHEMA_INVALID")
        task=public.get("task")
        if not _exact_fields(task,_TASK_FIELDS):
            return _fail("TASK_FIELDS_NOT_CLOSED")

        claims=task.get("claims")
        evidence=task.get("evidence")
        profile=task.get("audience_profile")
        if not isinstance(claims,list) or len(claims)!=2:
            return _fail("EXACTLY_TWO_CLAIMS_REQUIRED")
        if not isinstance(evidence,list) or len(evidence)!=2:
            return _fail("EXACTLY_TWO_EVIDENCE_ROWS_REQUIRED")
        if not _exact_fields(profile,_PROFILE_FIELDS):
            return _fail("AUDIENCE_PROFILE_FIELDS_NOT_CLOSED")
        if profile.get("profile_id")!="EXPLICIT":
            return _fail("AUDIENCE_PROFILE_ID_MUST_BE_EXPLICIT")
        constraints=profile.get("constraints")
        if not _exact_fields(constraints,_CONSTRAINT_FIELDS):
            return _fail("AUDIENCE_CONSTRAINT_FIELDS_NOT_CLOSED")

        claim_subjects=[]
        claim_texts=[]
        claim_ids=set()
        for i,row in enumerate(claims):
            if not _exact_fields(row,_CLAIM_FIELDS):
                return _fail("CLAIM_FIELDS_NOT_CLOSED",claim_index=i)
            cid=row.get("claim_id")
            if not isinstance(cid,str) or not cid.strip() or cid in claim_ids:
                return _fail("CLAIM_ID_INVALID_OR_DUPLICATE",claim_index=i)
            claim_ids.add(cid)
            if row.get("required") is not False:
                return _fail("EXACT_CELL_REQUIRES_TWO_OPTIONAL_CLAIMS",claim_id=cid)
            parsed=_numeric_claim(row.get("text"))
            if parsed is None:
                return _fail("CLAIM_NOT_EXACT_NUMERIC_FACT",claim_id=cid)
            claim_subjects.append(parsed["subject"])
            claim_texts.append(_canon(row["text"]))

        if len(set(x.casefold() for x in claim_subjects))!=2:
            return _fail("CLAIM_SUBJECTS_NOT_DISTINCT")
        objective_subjects={objective["left"].casefold(),objective["right"].casefold()}
        if {x.casefold() for x in claim_subjects}!=objective_subjects:
            return _fail(
              "OBJECTIVE_OPERANDS_NOT_EXACT_CLAIM_SUBJECTS",
              objective_operands=sorted(objective_subjects),
              claim_subjects=sorted(x.casefold() for x in claim_subjects),
            )

        evidence_texts=[]
        evidence_ids=set()
        for i,row in enumerate(evidence):
            if not _exact_fields(row,_EVIDENCE_FIELDS):
                return _fail("EVIDENCE_FIELDS_NOT_CLOSED",evidence_index=i)
            eid=row.get("evidence_id")
            if not isinstance(eid,str) or not eid.strip() or eid in evidence_ids:
                return _fail("EVIDENCE_ID_INVALID_OR_DUPLICATE",evidence_index=i)
            evidence_ids.add(eid)
            if row.get("verified") is not True:
                return _fail("UNVERIFIED_EVIDENCE_UNIT",evidence_id=eid)
            parsed=_numeric_claim(row.get("text"))
            if parsed is None:
                return _fail("EVIDENCE_NOT_EXACT_NUMERIC_FACT",evidence_id=eid)
            provenance=row.get("provenance")
            if not isinstance(provenance,list) or not provenance:
                return _fail("EVIDENCE_PROVENANCE_REQUIRED",evidence_id=eid)
            for j,p in enumerate(provenance):
                if not isinstance(p,Mapping) or not set(p)<=_PROVENANCE_FIELDS or "source_id" not in p:
                    return _fail("PROVENANCE_FIELDS_NOT_CLOSED",evidence_id=eid,provenance_index=j)
                sid=p.get("source_id"); loc=p.get("locator")
                if not isinstance(sid,str) or not sid.strip():
                    return _fail("PROVENANCE_SOURCE_ID_REQUIRED",evidence_id=eid)
                if loc is not None and (not isinstance(loc,str) or not loc.strip()):
                    return _fail("PROVENANCE_LOCATOR_INVALID",evidence_id=eid)
            evidence_texts.append(_canon(row["text"]))

        if sorted(x.casefold() for x in evidence_texts)!=sorted(x.casefold() for x in claim_texts):
            return _fail("EVIDENCE_TEXT_SET_NOT_EXACT_CLAIM_TEXT_SET")

        compiled=compile_presentation(payload)
        if compiled.get("pass") is not True:
            return _fail("BOUND_PRESENTATION_COMPILER_DID_NOT_PASS",compiler_result=compiled)
        if (
          compiled.get("declared_cell_top_law_conditions_mechanically_satisfied") is not True
          or compiled.get("presentation_policy_constructed") is not True
          or compiled.get("policy_adequacy_authority") is not False
          or compiled.get("db_admission_authority") is not False
          or compiled.get("u_subtraction_authority") is not False
          or compiled.get("terminal_authority") is not False
          or compiled.get("terminal_credit_delta") != 0
        ):
            return _fail("BOUND_PRESENTATION_COMPILER_AUTHORITY_BOUNDARY_INVALID")

        return {
          "schema":SCHEMA,"pass":True,
          "status":"PASS__CLOSED_BOUND_OBJECTIVE_ROLE_TOP_LAW_SCOPE_MEMBERSHIP",
          "explicit_payload_surface_exhaustively_consumed":True,
          "real_context_top_law_scope_membership_authenticated":True,
          "no_unmodeled_payload_presentation_channels":True,
          "closed_language":{
            "objective":"ONE_WHOLE_EXPLICIT_BINARY_NUMERIC_COMPARISON",
            "claims":"EXACT_TWO_OPTIONAL_NUMERIC_FACTS_WHOSE_SUBJECTS_EQUAL_OBJECTIVE_OPERANDS",
            "evidence":"EXACT_TWO_VERIFIED_NUMERIC_FACTS_BYTE_NORMALIZED_EQUAL_TO_CLAIMS",
            "audience":"EXPLICIT_PROFILE_WITH_EXACT_TYPED_REALIZER_CONSTRAINT_FIELDS",
            "unknown_fields":"FORBIDDEN",
          },
          "objective_operator":objective["operator"],
          "objective_role_subjects":[objective["left"],objective["right"]],
          "presentation_policy_constructed":True,
          "presentation_compiler_receipt":compiled,
          "policy_adequacy_authority":False,"db_admission_authority":False,
          "u_subtraction_authority":False,"terminal_authority":False,
          "terminal_credit_delta":0,
          "boundary":(
            "SCOPE_MEMBERSHIP_ONLY_FOR_THE_EXACT_CLOSED_INPUT_LANGUAGE__"
            "NO_GENERAL_PRESENTATION_ADEQUACY__NO_GENERAL_NATURAL_LANGUAGE_SCOPE__"
            "NO_SOURCE_AUTHORIZATION_POLICY_ADEQUACY_DB_U_EMPTY_OR_TERMINAL_AUTHORITY"
          ),
        }
    except Exception as exc:
        return _fail("INVALID_INPUT",exception_type=type(exc).__name__,detail_text=str(exc)[:200])


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {})
