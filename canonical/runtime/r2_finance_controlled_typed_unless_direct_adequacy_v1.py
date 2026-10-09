"""R2 direct adequacy for controlled typed finance single-UNLESS cases.

The task names one repository-local case file containing exact source text and a
content-addressed typed context. Literal Boolean/decimal exception conditions are
evaluated by the existing certified engine; a separate verifier recomputes them.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_controlled_typed_unless_branch_v1 as producer
from canonical.runtime import finance_controlled_typed_unless_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_FINANCE_CONTROLLED_TYPED_UNLESS_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::FINANCE_CONTROLLED_TYPED_UNLESS_FAMILY_V1"
CAPABILITY_ID="finance.controlled_typed_unless.branch.stdlib"
VERIFIER_CAPABILITY_ID="finance.controlled_typed_unless.verify.stdlib"
POLICY_PREFIX="R2_FINANCE_CONTROLLED_TYPED_UNLESS::"
ROOT=Path(__file__).resolve().parents[2]
GRAMMAR=re.compile(
    r"Using the controlled typed finance UNLESS case at "
    r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), select and independently "
    r"verify the applicable branch and save it to "
    r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
    re.IGNORECASE,
)


def _base(status:str,*,passed:bool)->dict[str,Any]:
    return {"schema":SCHEMA,"status":status,"pass":passed,"matched":False,
            "semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,
            "direct_adequacy_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,"incremental_spend_usd":0}


def _safe(root:Path,rel:str)->Path:
    root=root.resolve(); p=Path(rel)
    if p.is_absolute() or ".." in p.parts: raise ValueError("PATH_INVALID")
    q=(root/p).resolve()
    if q==root or root not in q.parents: raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return q


def _sha_file(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _contract(goal:str)->dict[str,Any]:
    out=compile_contract(goal,source_id="user",routing_target_effects=["finance.controlled_typed_unless.branch"])
    if out.get("pass") is not True: raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return out


def preflight(request:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request,Mapping): return {**_base("FAIL_CLOSED",passed=False),"reason":"REQUEST_NOT_OBJECT"}
    task_id=str(request.get("task_id") or "").strip(); goal=str(request.get("goal") or "").strip()
    if not task_id or not goal: return {**_base("FAIL_CLOSED",passed=False),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    m=GRAMMAR.fullmatch(goal)
    if m is None: return {**_base("NOT_APPLICABLE",passed=False),"matched":False}
    try:
        inp=m.group("input"); outp=m.group("output")
        ip=_safe(root,inp); op=_safe(root,outp)
        if ip==op: raise ValueError("INPUT_OUTPUT_PATH_COLLISION")
        if not ip.is_file(): raise ValueError("FINANCE_TYPED_CASE_INPUT_MISSING")
        case=json.loads(ip.read_text(encoding="utf-8"))
        if not isinstance(case,dict) or case.get("schema")!=producer.INPUT_SCHEMA:
            raise ValueError("FINANCE_TYPED_CASE_SCHEMA_INVALID")
        produced=producer.compute(case)
        checked=verifier.verify(case,produced)
        if checked.get("verified") is not True:
            raise ValueError("PREFLIGHT_INDEPENDENT_RECOMPUTATION_FAILED:"+",".join(checked.get("errors") or []))
        contract=_contract(goal)
        raw_ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if not raw_ids: raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        input_sha=_sha_file(ip); goal_sha=sha256(goal.encode("utf-8")).hexdigest()
        return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED",passed=False),"matched":True,
                "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,
                "verifier_capability_id":VERIFIER_CAPABILITY_ID,
                "policy_id":POLICY_PREFIX+goal_sha+"::"+input_sha,
                "goal_sha256":goal_sha,"input_path":inp,"input_sha256":input_sha,
                "output_path":outp,"source_text_sha256":produced["source_text_sha256"],
                "typed_context_sha256":produced["typed_context_sha256"],
                "scope_id":produced["scope_id"],
                "raw_task_contract_sha256":contract.get("task_contract_sha256"),
                "raw_acceptance_obligation_ids":raw_ids,
                "semantic_scope":"CONTROLLED_SINGLE_UNLESS_LITERAL_TYPED_FIELD_BOOLEAN_OR_DECIMAL_CONDITION_RELATIVE_TO_TASK_BOUND_CONTENT_ADDRESSED_CONTEXT",
                "preflight_execution_authority":False}
    except Exception as exc:
        return {**_base("FAIL_CLOSED",passed=False),"matched":True,"route_id":ROUTE_ID,
                "reason":type(exc).__name__+":"+str(exc)}


def _restore(path:Path,existed:bool,original:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(original or b"")
    else:
        try: path.unlink()
        except FileNotFoundError: pass


def run(request:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED": return pf
    ip=_safe(root,str(pf["input_path"])); op=_safe(root,str(pf["output_path"]))
    existed=op.is_file(); original=op.read_bytes() if existed else None
    try:
        before=_sha_file(ip)
        if before!=pf["input_sha256"]: raise RuntimeError("INPUT_DRIFT_BEFORE_EXECUTION")
        case=json.loads(ip.read_text(encoding="utf-8"))
        produced=producer.compute(case)
        if produced.get("pass") is not True or produced.get("model_dependency_count")!=0:
            raise RuntimeError("PRODUCER_AUTHORITY_INVALID")
        if _sha_file(ip)!=before: raise RuntimeError("SOURCE_MUTATED_BY_PRODUCER")
        op.parent.mkdir(parents=True,exist_ok=True)
        op.write_text(json.dumps(produced,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        observed=json.loads(op.read_text(encoding="utf-8"))
        checked=verifier.verify(case,observed)
        if checked.get("verified") is not True:
            raise RuntimeError("INDEPENDENT_TYPED_UNLESS_VERIFICATION_FAILED:"+",".join(checked.get("errors") or []))
        if checked.get("producer_independent") is not True or checked.get("model_dependency_count")!=0:
            raise RuntimeError("VERIFIER_AUTHORITY_INVALID")
        if _sha_file(ip)!=before: raise RuntimeError("SOURCE_MUTATED_DURING_VERIFICATION")
        contract=_contract(str(request["goal"]))
        ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if not ids or ids!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
        return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",passed=True),"matched":True,
                "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,
                "verifier_capability_id":VERIFIER_CAPABILITY_ID,
                "selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],
                "input_path":pf["input_path"],"input_sha256":before,
                "output_path":pf["output_path"],"output_sha256":_sha_file(op),
                "source_text_sha256":produced["source_text_sha256"],
                "typed_context_sha256":produced["typed_context_sha256"],
                "scope_id":produced["scope_id"],"condition_holds":produced["condition_holds"],
                "field_name":produced["field_name"],"operator":produced["operator"],
                "literal":produced["literal"],"selected_branch":produced["selected_branch"],
                "semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,
                "actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,
                "accepted_raw_obligation_ids":ids,"raw_acceptance_obligation_count":len(ids),
                "producer_result":deepcopy(dict(produced)),"acceptance_receipt":deepcopy(dict(checked)),
                "execution_attempted":True,"retry_by_other_route_authorized":False,
                "source_immutability_verified":True,
                "authority_boundary":"CONTROLLED_LITERAL_FIELD_SINGLE_UNLESS_RELATIVE_TO_TASK_BOUND_TYPED_CONTEXT_ONLY__NO_TYPED_CONTEXT_EXTERNAL_WORLD_TRUTH_SYNONYMY_REFERENCE_RESOLUTION_OR_GENERAL_FINANCE_SEMANTICS"}
    except Exception as exc:
        _restore(op,existed,original)
        rollback=(op.is_file() and existed and op.read_bytes()==(original or b"")) if existed else not op.exists()
        return {**_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",passed=False),"matched":True,
                "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"goal_sha256":pf.get("goal_sha256"),
                "execution_attempted":True,"retry_by_other_route_authorized":False,
                "rollback_complete":rollback,"reason":type(exc).__name__+":"+str(exc)}
