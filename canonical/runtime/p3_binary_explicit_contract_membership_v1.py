"""Lossless explicit-source membership for the bounded P3 binary decision class.

The authoritative root task source must itself be strict JSON containing exactly
the load-bearing structured fields consumed by the verified P3 binary policy.
No semantic extractor, caller-authored scope flag, or "independent_verified"
boolean is accepted.

This proves membership only relative to the upstream root task bytes supplied to
this compiler. As with every solver, whether those bytes are the user's actual
task is an ingress root-of-trust boundary, not something the solver can prove
from its own input.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime.p3_binary_decision_grounded_expression_v1 import evaluate as expression
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA

SCHEMA="PROJECT_BRAIN_P3_BINARY_EXPLICIT_CONTRACT_MEMBERSHIP_V1"
CONTRACT="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001::BOUND_BINARY_OBJECTIVE_V1"
MAX_BYTES=2_000_000
ID=re.compile(r"^[A-Za-z0-9_.:-]+$")

class MembershipError(ValueError):
    pass

def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out:
            raise MembershipError("DUPLICATE_JSON_KEY:"+str(k))
        out[k]=v
    return out

def _tok(v,label):
    if not isinstance(v,str) or not v.strip() or v!=v.strip():
        raise MembershipError(label+"_INVALID")
    return v

def _exact(obj,keys,label):
    if not isinstance(obj,Mapping) or set(obj)!=set(keys):
        raise MembershipError(label+"_KEYS_NOT_EXACT")

def compile_membership(raw_source: str|bytes, *, source_id: str)->dict[str,Any]:
    try:
        sid=_tok(source_id,"SOURCE_ID")
        raw=raw_source.encode("utf-8") if isinstance(raw_source,str) else raw_source
        if not isinstance(raw,bytes): raise MembershipError("RAW_SOURCE_MUST_BE_TEXT_OR_BYTES")
        if not raw: raise MembershipError("RAW_SOURCE_EMPTY")
        if len(raw)>MAX_BYTES: raise MembershipError("RAW_SOURCE_TOO_LARGE")
        try: text=raw.decode("utf-8")
        except UnicodeDecodeError as exc: raise MembershipError("RAW_SOURCE_NOT_UTF8") from exc
        try: doc=json.loads(text,object_pairs_hook=_pairs)
        except MembershipError: raise
        except Exception as exc: raise MembershipError("RAW_SOURCE_JSON_INVALID") from exc

        _exact(doc,{"contract","objective","task"},"TOP_LEVEL")
        if doc.get("contract")!=CONTRACT: raise MembershipError("P3_BINARY_CONTRACT_REQUIRED")
        objective=_tok(doc.get("objective"),"OBJECTIVE")
        task=doc.get("task")
        _exact(task,{"claims","evidence","audience_profile"},"TASK")

        claims=task.get("claims")
        if not isinstance(claims,list) or len(claims)!=2:
            raise MembershipError("EXACTLY_TWO_CLAIMS_REQUIRED")
        seen_c=set(); norm_claims=[]
        for i,row in enumerate(claims):
            _exact(row,{"claim_id","text","required"},"CLAIM:"+str(i))
            cid=_tok(row.get("claim_id"),"CLAIM_ID:"+str(i))
            if not ID.fullmatch(cid) or cid in seen_c: raise MembershipError("CLAIM_ID_INVALID_OR_DUPLICATE:"+cid)
            seen_c.add(cid)
            ctext=_tok(row.get("text"),"CLAIM_TEXT:"+cid)
            if row.get("required") is not False:
                raise MembershipError("EXACT_BINARY_CELL_REQUIRES_OPTIONAL_CLAIMS")
            norm_claims.append({"claim_id":cid,"text":ctext,"required":False})

        evidence=task.get("evidence")
        if not isinstance(evidence,list) or len(evidence)!=2:
            raise MembershipError("EXACTLY_TWO_EVIDENCE_ROWS_REQUIRED")
        seen_e=set(); norm_evidence=[]
        for i,row in enumerate(evidence):
            _exact(row,{"evidence_id","text","verified","provenance"},"EVIDENCE:"+str(i))
            eid=_tok(row.get("evidence_id"),"EVIDENCE_ID:"+str(i))
            if not ID.fullmatch(eid) or eid in seen_e: raise MembershipError("EVIDENCE_ID_INVALID_OR_DUPLICATE:"+eid)
            seen_e.add(eid)
            etext=_tok(row.get("text"),"EVIDENCE_TEXT:"+eid)
            if row.get("verified") is not True:
                raise MembershipError("UNVERIFIED_EVIDENCE:"+eid)
            prov=row.get("provenance")
            if not isinstance(prov,list) or not prov: raise MembershipError("PROVENANCE_REQUIRED:"+eid)
            nprov=[]; seen_p=set()
            for j,p in enumerate(prov):
                if not isinstance(p,Mapping) or set(p) not in ({"source_id"},{"source_id","locator"}):
                    raise MembershipError("PROVENANCE_KEYS_INVALID:"+eid+":"+str(j))
                ps=_tok(p.get("source_id"),"PROVENANCE_SOURCE:"+eid+":"+str(j))
                loc=p.get("locator")
                if loc is not None: loc=_tok(loc,"PROVENANCE_LOCATOR:"+eid+":"+str(j))
                key=(ps,loc or "")
                if key in seen_p: continue
                seen_p.add(key)
                q={"source_id":ps}
                if loc is not None:q["locator"]=loc
                nprov.append(q)
            norm_evidence.append({"evidence_id":eid,"text":etext,"verified":True,"provenance":nprov})

        profile=task.get("audience_profile")
        _exact(profile,{"profile_id","constraints"},"AUDIENCE_PROFILE")
        if profile.get("profile_id")!="EXPLICIT":
            raise MembershipError("EXPLICIT_AUDIENCE_PROFILE_REQUIRED")
        c=profile.get("constraints")
        keys={"output_format","citation_mode","style","required_sections","allowed_sections","max_items","max_chars","heading_level","require_title"}
        _exact(c,keys,"AUDIENCE_CONSTRAINTS")
        if str(c.get("output_format") or "").upper() not in {"BULLETS","PARAGRAPHS"}:
            raise MembershipError("OUTPUT_FORMAT_OUTSIDE_CELL")
        if str(c.get("citation_mode") or "").upper()!="INLINE_SOURCE_IDS":
            raise MembershipError("CITATION_MODE_OUTSIDE_CELL")
        if str(c.get("style") or "").upper()!="VERBATIM_GROUNDED":
            raise MembershipError("STYLE_OUTSIDE_CELL")
        if c.get("required_sections")!=[] or c.get("allowed_sections") is not None:
            raise MembershipError("SECTIONS_OUTSIDE_CELL")
        if c.get("require_title") is not False:
            raise MembershipError("TITLE_OUTSIDE_CELL")
        if type(c.get("max_items")) is not int or c["max_items"]<3:
            raise MembershipError("MAX_ITEMS_INVALID_OR_INFEASIBLE")
        if type(c.get("max_chars")) is not int or c["max_chars"]<=0:
            raise MembershipError("MAX_CHARS_INVALID")
        if type(c.get("heading_level")) is not int:
            raise MembershipError("HEADING_LEVEL_INVALID")

        public={
          "schema":INPUT_SCHEMA,
          "task":{
            "claims":norm_claims,
            "evidence":norm_evidence,
            "audience_profile":{
              "profile_id":"EXPLICIT",
              "constraints":dict(c),
            },
          },
        }
        policy=expression({"objective":objective,"v2_input":public})
        if policy.get("pass") is not True:
            raise MembershipError("BOUND_BINARY_POLICY_REJECTED:"+str(policy.get("reason") or policy.get("status")))
        if (
            policy.get("bound_cell_required_decision_coverage_complete") is not True
            or policy.get("decision_expression_covered") is not True
            or policy.get("policy_adequacy_authority") is not False
            or policy.get("terminal_authority") is not False
            or policy.get("terminal_credit_delta")!=0
        ):
            raise MembershipError("POLICY_AUTHORITY_BOUNDARY_INVALID")

        norm={"contract":CONTRACT,"objective":objective,"task":public["task"]}
        raw_sha=sha256(raw).hexdigest()
        norm_bytes=json.dumps(norm,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        norm_sha=sha256(norm_bytes).hexdigest()
        receipt="P3BINMEM:"+sha256((sid+"\0"+raw_sha+"\0"+norm_sha).encode()).hexdigest()
        return {
          "schema":SCHEMA,
          "status":"PASS__LOSSLESS_EXPLICIT_P3_BINARY_SOURCE_MEMBERSHIP",
          "pass":True,
          "source_id":sid,
          "raw_source_sha256":raw_sha,
          "normalized_contract_sha256":norm_sha,
          "membership_receipt":receipt,
          "objective":objective,
          "public":public,
          "policy_receipt":policy,
          "selected_class_membership_authenticated":True,
          "extra_source_semantic_fields_permitted":False,
          "membership_self_assertion_permitted":False,
          "semantic_extractor_required":False,
          "task_root_authority":{
            "state":"UPSTREAM_ROOT_OF_TRUST",
            "self_proved_by_membership_compiler":False,
          },
          "policy_adequacy_authority":False,
          "db_admission_authority":False,
          "u_subtraction_authority":False,
          "terminal_authority":False,
          "terminal_credit_delta":0,
          "scope":"STRICT_EXPLICIT_P3_BINARY_JSON_SOURCE_CLASS_ONLY",
        }
    except MembershipError as exc:
        return {
          "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
          "errors":[str(exc)],
          "selected_class_membership_authenticated":False,
          "membership_self_assertion_permitted":False,
          "policy_adequacy_authority":False,"db_admission_authority":False,
          "u_subtraction_authority":False,"terminal_authority":False,
          "terminal_credit_delta":0,
        }
