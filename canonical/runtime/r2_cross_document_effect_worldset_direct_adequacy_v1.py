"""R2 direct adequacy for decision-invariant cross-document effect world sets."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as producer
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_CROSS_DOCUMENT_EFFECT_WORLDSET_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1"
CAPABILITY_ID="cross_document.effect_worldset.invariant.stdlib"
VERIFIER_CAPABILITY_ID="cross_document.effect_worldset.verify.stdlib"
ROOT=Path(__file__).resolve().parents[2]

GRAMMAR=re.compile(
 r"Using the cross-document effect hypothesis case at "
 r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), compute and independently "
 r"verify the effective value and save it to "
 r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
 re.I,
)

def _base(status:str,passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "matched":False,
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
    try:
        obj=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("JSON_INPUT_INVALID") from exc
    if not isinstance(obj,dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return raw,obj

def _contract(goal:str)->dict[str,Any]:
    out=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["cross_document.effect_worldset"],
    )
    if out.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return out

def _material(case:Mapping[str,Any])->tuple[dict[str,Any],dict[str,Any]]:
    result=producer.evaluate(case)
    if result.get("status")=="FAIL_CLOSED":
        raise ValueError("WORLDSET_PRODUCER_FAIL_CLOSED:"+str(result.get("reason")))
    checked=verifier.verify(case,result)
    if checked.get("verified") is not True:
        raise ValueError(
            "PREFLIGHT_INDEPENDENT_WORLDSET_RECOMPUTATION_FAILED:"
            + ",".join(checked.get("errors") or [])
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
        ip=_safe(root,inp,True)
        op=_safe(root,out)
        if ip==op:
            raise ValueError("INPUT_OUTPUT_COLLISION")
        case_raw,case=_load(ip)
        result,checked=_material(case)
        if result.get("pass") is not True:
            return {
                **_base("NOT_APPLICABLE__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY"),
                "matched":False,
                "route_id":ROUTE_ID,
                "direct_route_semantic_open":True,
                "effect_status":result.get("status"),
                "minimum_discriminator_slots":deepcopy(
                    result.get("minimum_discriminator_slots") or []
                ),
                "possible_outcomes":deepcopy(result.get("possible_outcomes") or []),
                "world_count":result.get("world_count"),
            }

        contract=_contract(goal)
        ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if not ids:
            raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        gsha=sha256(goal.encode("utf-8")).hexdigest()
        case_sha=sha256(case_raw).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "verifier_capability_id":VERIFIER_CAPABILITY_ID,
            "goal_sha256":gsha,
            "policy_id":"R2_CROSS_DOCUMENT_EFFECT_WORLDSET::"+gsha+"::"+case_sha,
            "input_path":inp,
            "input_sha256":case_sha,
            "output_path":out,
            "effective_value":deepcopy(result.get("effective_value")),
            "world_count":result.get("world_count"),
            "raw_acceptance_obligation_ids":ids,
            "semantic_scope":(
                "COMMON_EFFECTIVE_VALUE_OVER_DECLARED_COMPLETE_FINITE_TYPED_EFFECT_"
                "HYPOTHESIS_UNIVERSE__NO_RAW_LANGUAGE_HYPOTHESIS_COMPLETENESS_AUTHORITY"
            ),
            "preflight_execution_authority":False,
            "preflight_verification":deepcopy(checked),
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "reason":type(exc).__name__+":"+str(exc),
        }

def _restore(path:Path,existed:bool,raw:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw or b"")
    else:
        try:path.unlink()
        except FileNotFoundError:pass

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf

    ip=_safe(root,pf["input_path"],True)
    op=_safe(root,pf["output_path"])
    existed=op.is_file()
    old=op.read_bytes() if existed else None
    try:
        before=ip.read_bytes()
        if sha256(before).hexdigest()!=pf["input_sha256"]:
            raise RuntimeError("CASE_DRIFT_BEFORE_EXECUTION")
        case=json.loads(before.decode("utf-8"))

        result=producer.evaluate(case)
        if result.get("pass") is not True:
            raise RuntimeError("WORLDSET_NO_LONGER_PROVES_COMMON_EFFECTIVE_VALUE")
        checked=verifier.verify(case,result)
        if checked.get("verified") is not True:
            raise RuntimeError(
                "INDEPENDENT_WORLDSET_VERIFICATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )
        if ip.read_bytes()!=before:
            raise RuntimeError("CASE_MUTATION_DETECTED")

        op.parent.mkdir(parents=True,exist_ok=True)
        op.write_text(
            json.dumps(result,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
        reread=json.loads(op.read_text(encoding="utf-8"))
        check2=verifier.verify(case,reread)
        if check2.get("verified") is not True:
            raise RuntimeError("OUTPUT_READBACK_VERIFICATION_FAILED")

        contract=_contract(str(request["goal"]))
        ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if ids!=pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "verifier_capability_id":VERIFIER_CAPABILITY_ID,
            "selected_policy_id":pf["policy_id"],
            "goal_sha256":pf["goal_sha256"],
            "input_path":pf["input_path"],
            "input_sha256":pf["input_sha256"],
            "output_path":pf["output_path"],
            "output_sha256":sha256(op.read_bytes()).hexdigest(),
            "effective_value":deepcopy(result["effective_value"]),
            "world_count":result["world_count"],
            "minimum_discriminator_slots":[],
            "semantic_scope":pf["semantic_scope"],
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":ids,
            "raw_acceptance_obligation_count":len(ids),
            "acceptance_receipt":deepcopy(check2),
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "source_immutability_verified":True,
            "authority_boundary":(
                "DIRECT_ROUTE_CLAIMS_ONLY_DECISION_INVARIANT_EFFECT_WORLDSETS__"
                "TERMINALLY_RELEVANT_EFFECT_AMBIGUITY_DOES_NOT_MATCH"
            ),
        }
    except Exception as exc:
        _restore(op,existed,old)
        rollback=(op.is_file() and existed and op.read_bytes()==(old or b"")) if existed else not op.exists()
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "goal_sha256":pf.get("goal_sha256"),
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "rollback_complete":rollback,
            "reason":type(exc).__name__+":"+str(exc),
        }
