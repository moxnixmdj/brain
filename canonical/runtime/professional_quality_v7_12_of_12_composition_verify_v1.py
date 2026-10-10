"""Execute the verified receipt-aware 12/12 professional same-subject composition gate.

This verifier grants composition-admissibility only. It explicitly does not
grant professional-quality closure, domain semantic/execution closure,
acceptance, promotion, live-default, or terminal authority.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_same_subject_composition_gate_v3 as gate

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_VERIFY_V1"
WORKLIST="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V18.json"
WORKLIST_BLOB="42a3341d2ec138744f2803c10534b88b5ee7dcf4"
SUBJECT_KIND="DECLARED_SYSTEM"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"

def _blob(p:Path)->str:
    d=p.read_bytes()
    return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "composition_admissible":False,"professional_quality_closed":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def evaluate_worklist(worklist:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(worklist,Mapping):
        return _fail("WORKLIST_NOT_OBJECT")
    if worklist.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_V7_SAME_SUBJECT_ROOT_BINDING_WORKLIST_V18":
        return _fail("WORKLIST_SCHEMA_INVALID")
    if worklist.get("verified_root_subject_binding_count")!=12:
        return _fail("VERIFIED_BINDING_COUNT_NOT_12")
    rows=worklist.get("roots")
    if not isinstance(rows,list) or len(rows)!=12:
        return _fail("WORKLIST_ROOT_CARDINALITY_INVALID")
    payload=[]
    seen=set()
    for row in rows:
        if not isinstance(row,Mapping):
            return _fail("WORKLIST_ROOT_ROW_INVALID")
        rid=row.get("root_id")
        if not isinstance(rid,str) or rid in seen:
            return _fail("WORKLIST_ROOT_ID_INVALID_OR_DUPLICATE")
        seen.add(rid)
        if not str(row.get("same_subject_binding_status") or "").startswith("PASS"):
            return _fail("WORKLIST_ROOT_NOT_VERIFIED",root_id=rid)
        b=row.get("binding");v=row.get("verification")
        if not isinstance(b,Mapping) or not isinstance(v,Mapping):
            return _fail("WORKLIST_BINDING_REFERENCE_MISSING",root_id=rid)
        payload.append({"root_id":rid,"binding":dict(b),"verification":dict(v)})
    out=gate.evaluate({"root_subject_bindings":payload},repo_root=repo_root)
    if out.get("pass") is not True:
        return _fail("COMPOSITION_GATE_NOT_PASS",gate_result=out)
    if out.get("status")!="PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE":
        return _fail("COMPOSITION_GATE_STATUS_INVALID",gate_result=out)
    if out.get("composition_admissible") is not True:
        return _fail("COMPOSITION_ADMISSIBILITY_NOT_TRUE",gate_result=out)
    if out.get("verified_root_subject_binding_count")!=12:
        return _fail("GATE_VERIFIED_BINDING_COUNT_NOT_12",gate_result=out)
    subj=out.get("composed_subject") or {}
    if (subj.get("subject_kind"),subj.get("subject_id"),subj.get("subject_sha256"))!=(SUBJECT_KIND,SUBJECT_ID,SUBJECT_SHA):
        return _fail("COMPOSED_SUBJECT_TUPLE_MISMATCH",gate_result=out)
    for field in ("professional_quality_closed","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if out.get(field) is not False:
            return _fail("GATE_OVERCLAIM:"+field,gate_result=out)
    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__V7_12_OF_12_SAME_SUBJECT_COMPOSITION_ADMISSIBLE_ONLY",
        "composition_admissible":True,
        "verified_root_subject_binding_count":12,
        "composed_subject":dict(subj),
        "professional_quality_closed":False,
        "domain_semantic_closure":False,
        "domain_execution_closure":False,
        "unknown_defeater_completeness_proved":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    p=(root/WORKLIST).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return _fail("WORKLIST_OUTSIDE_ROOT")
    if not p.is_file() or p.is_symlink():return _fail("WORKLIST_FILE_INVALID")
    if _blob(p)!=WORKLIST_BLOB:return _fail("WORKLIST_BLOB_STALE",actual_git_blob_sha=_blob(p))
    try:w=json.loads(p.read_text(encoding="utf-8"))
    except Exception:return _fail("WORKLIST_JSON_INVALID")
    return evaluate_worklist(w,repo_root=root)

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
