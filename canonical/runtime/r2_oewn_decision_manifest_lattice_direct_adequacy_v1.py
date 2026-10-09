"""Closed-only R2 direct route for proof-carrying OEWN decision-manifest lattice V1."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import oewn_decision_manifest_lattice_v1 as producer
from canonical.runtime import oewn_decision_manifest_lattice_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_OEWN_DECISION_MANIFEST_LATTICE_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::OEWN_DECISION_MANIFEST_LATTICE_V1"
CAPABILITY_ID="oewn.decision_manifest_lattice.stdlib"
VERIFIER_CAPABILITY_ID="oewn.decision_manifest_lattice.verify.stdlib"
ROOT=Path(__file__).resolve().parents[2]

GRAMMAR=re.compile(
    r"Using the OEWN decision manifest lattice case at "
    r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), compute and independently "
    r"verify the decision and save it to "
    r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
    re.I,
)


def _base(status:str,passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,"matched":False,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "direct_adequacy_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _safe(root:Path,rel:Any,file:bool=False)->Path:
    root=Path(root).resolve()
    p=Path(str(rel or "").strip())
    if p.is_absolute() or ".." in p.parts or not p.as_posix().startswith("canonical/"):
        raise ValueError("PATH_INVALID")
    q=(root/p).resolve()
    if q==root or root not in q.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    if file and (not q.is_file() or q.is_symlink()):
        raise ValueError("FILE_REQUIRED")
    return q


def _load(path:Path)->tuple[bytes,dict[str,Any]]:
    raw=path.read_bytes()
    try:obj=json.loads(raw.decode("utf-8"))
    except Exception as exc:raise ValueError("JSON_INPUT_INVALID") from exc
    if not isinstance(obj,dict):raise ValueError("JSON_OBJECT_REQUIRED")
    return raw,obj


def _contract(goal:str)->dict[str,Any]:
    out=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["oewn.decision_manifest_lattice"],
    )
    if out.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return out


def _material(problem:Mapping[str,Any])->tuple[dict[str,Any],dict[str,Any]]:
    result=producer.evaluate(problem)
    if result.get("status")=="FAIL_CLOSED":
        raise ValueError("MANIFEST_LATTICE_FAIL_CLOSED:"+str(result.get("reason") or "UNKNOWN"))
    checked=verifier.verify(problem,result)
    if checked.get("verified") is not True:
        raise ValueError(
            "INDEPENDENT_MANIFEST_LATTICE_VERIFY_FAILED:"
            +",".join(checked.get("errors") or [])
        )
    return result,checked


def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
    goal=str(request.get("goal") or "").strip()
    task=str(request.get("task_id") or "").strip()
    if not goal or not task:
        return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    m=GRAMMAR.fullmatch(goal)
    if not m:
        return {**_base("NOT_APPLICABLE"),"matched":False}
    try:
        inp,out=m.group("input"),m.group("output")
        ip=_safe(root,inp,True);op=_safe(root,out)
        if ip==op:raise ValueError("INPUT_OUTPUT_COLLISION")
        raw,problem=_load(ip)
        result,checked=_material(problem)
        if result.get("pass") is not True:
            return {
                **_base("NOT_APPLICABLE__DECISION_MANIFEST_LATTICE_OPEN"),
                "matched":False,
                "open_status":result.get("status"),
                "next_proof_obligations":deepcopy(
                    result.get("next_proof_obligations") or []
                ),
                "next_observation_id":result.get("next_observation_id"),
            }

        contract=_contract(goal)
        ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if not ids:raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        gsha=sha256(goal.encode("utf-8")).hexdigest()
        psha=sha256(raw).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched":True,"route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "verifier_capability_id":VERIFIER_CAPABILITY_ID,
            "goal_sha256":gsha,
            "policy_id":"R2_OEWN_MANIFEST_LATTICE::"+gsha+"::"+psha,
            "input_path":inp,"input_sha256":psha,"output_path":out,
            "identified_sense_id":result.get("identified_sense_id"),
            "terminal_signature":deepcopy(result.get("terminal_signature")),
            "surviving_sense_ids":deepcopy(result.get("surviving_sense_ids") or []),
            "raw_acceptance_obligation_ids":ids,
            "preflight_execution_authority":False,
            "preflight_verification":deepcopy(checked),
            "semantic_scope":"OEWN_RELEASE_RELATIVE_SOURCE_PROVED_DECISION_MANIFEST_LATTICE_CLOSED_CASES_ONLY",
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,
            "reason":type(exc).__name__+":"+str(exc),
        }


def _restore(path:Path,existed:bool,raw:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw or b"")
    else:
        try:path.unlink()
        except FileNotFoundError:pass


def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf
    ip=_safe(root,pf["input_path"],True);op=_safe(root,pf["output_path"])
    existed=op.is_file();old=op.read_bytes() if existed else None
    try:
        before=ip.read_bytes()
        if sha256(before).hexdigest()!=pf["input_sha256"]:
            raise RuntimeError("CASE_DRIFT_BEFORE_EXECUTION")
        problem=json.loads(before.decode("utf-8"))
        result=producer.evaluate(problem)
        if result.get("pass") is not True:
            raise RuntimeError("DECISION_MANIFEST_LATTICE_NO_LONGER_CLOSED")
        checked=verifier.verify(problem,result)
        if checked.get("verified") is not True:
            raise RuntimeError("INDEPENDENT_MANIFEST_LATTICE_VERIFY_FAILED")
        if ip.read_bytes()!=before:
            raise RuntimeError("CASE_MUTATION_DETECTED")

        op.parent.mkdir(parents=True,exist_ok=True)
        op.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        reread=json.loads(op.read_text(encoding="utf-8"))
        check2=verifier.verify(problem,reread)
        if check2.get("verified") is not True:
            raise RuntimeError("OUTPUT_READBACK_VERIFICATION_FAILED")

        contract=_contract(str(request["goal"]))
        ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if ids!=pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),
            "matched":True,"route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "verifier_capability_id":VERIFIER_CAPABILITY_ID,
            "selected_policy_id":pf["policy_id"],
            "goal_sha256":pf["goal_sha256"],
            "input_path":pf["input_path"],"input_sha256":pf["input_sha256"],
            "output_path":pf["output_path"],
            "output_sha256":sha256(op.read_bytes()).hexdigest(),
            "identified_sense_id":result.get("identified_sense_id"),
            "terminal_signature":deepcopy(result.get("terminal_signature")),
            "surviving_sense_ids":deepcopy(result.get("surviving_sense_ids") or []),
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":ids,
            "raw_acceptance_obligation_count":len(ids),
            "acceptance_receipt":deepcopy(check2),
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "source_immutability_verified":True,
            "authority_boundary":"CLOSED_SOURCE_PROVED_OEWN_RELEASE_RELATIVE_DECISION_CASE_ONLY__OPEN_LATTICE_DOES_NOT_MATCH",
        }
    except Exception as exc:
        _restore(op,existed,old)
        rollback=(op.is_file() and existed and op.read_bytes()==(old or b"")) if existed else not op.exists()
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
            "matched":True,"route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "rollback_complete":rollback,
            "reason":type(exc).__name__+":"+str(exc),
        }
