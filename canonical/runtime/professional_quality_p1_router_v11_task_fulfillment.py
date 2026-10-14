"""Professional P1 Router V11: exact positive task-fulfillment gate.

V10/V9 already provide the universal fail-closed professional semantic law and
the executable R12 positive-path firewall. V11 adds one narrower load-bearing
condition: a positive certificate may escape only when the exact single
artifact in the authenticated run context has an independently verified,
scope-complete task-fulfillment certificate.

This first slice is deliberately single-artifact. Multi-artifact winner
selection is not inferred from caller preference. Missing or ambiguous artifact
identity fails closed.

No quality, acceptance, promotion, GDPval, or terminal authority is granted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v9 as base
from canonical.runtime import professional_task_fulfillment_bridge_v1 as fulfillment

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V11_TASK_FULFILLMENT_GATE"
TASK_FULFILLMENT_KEY="task_fulfillment_bundle"
SUBJECT_REF_KEY=base.base.SUBJECT_REF_KEY
TARGET_KEY="professional_target_instance"
TARGET_FIELDS=frozenset({
    "objective","audience","source_evidence","artifact_type",
    "constraints","current_draft_or_render",
})
REQUIRED_V11_COMPONENTS=frozenset({
    "canonical/runtime/professional_quality_p1_router_v11_task_fulfillment.py",
    "canonical/runtime/professional_task_fulfillment_bridge_v1.py",
})


def _canon(value:Any)->bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    ).encode("utf-8")


def _target_sha256(payload:Any)->str:
    if not isinstance(payload,Mapping):
        raise ValueError("DECISION_PAYLOAD_REQUIRED")
    target=payload.get(TARGET_KEY)
    if not isinstance(target,Mapping):
        raise ValueError("PROFESSIONAL_TARGET_INSTANCE_REQUIRED")
    if set(target)!=TARGET_FIELDS:
        missing=sorted(TARGET_FIELDS-set(target))
        extra=sorted(set(target)-TARGET_FIELDS)
        if missing:
            raise ValueError("PROFESSIONAL_TARGET_FIELDS_MISSING:"+",".join(missing))
        raise ValueError("PROFESSIONAL_TARGET_FIELDS_UNKNOWN:"+",".join(extra))
    return sha256(_canon(dict(target))).hexdigest()


def _single_artifact(root:Path,artifact_paths:Any)->tuple[str,str]:
    if not isinstance(artifact_paths,list) or len(artifact_paths)!=1:
        raise ValueError("EXACTLY_ONE_ARTIFACT_PATH_REQUIRED")
    rel=artifact_paths[0]
    if not isinstance(rel,str) or not rel.strip():
        raise ValueError("ARTIFACT_PATH_INVALID")
    rel=rel.strip()
    p=Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("ARTIFACT_PATH_MUST_BE_REPOSITORY_RELATIVE")
    full=(root/p).resolve(strict=False)
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise ValueError("ARTIFACT_PATH_OUTSIDE_REPOSITORY") from exc
    if not full.is_file() or full.is_symlink():
        raise ValueError("ARTIFACT_FILE_INVALID")
    return rel,sha256(full.read_bytes()).hexdigest()


def _v11_subject_ok(ref:Any,*,root:Path)->dict[str,Any]:
    prior=base._v9_subject_ok(ref,root=root)
    if prior.get("pass") is not True:
        return {"pass":False,"reason":"V9_DECLARED_SYSTEM_SUBJECT_INVALID","v9_subject":prior}
    if not isinstance(ref,Mapping):
        return {"pass":False,"reason":"V11_SUBJECT_REFERENCE_REQUIRED"}
    rel=ref.get("path")
    if not isinstance(rel,str) or not rel.startswith("canonical/governance/"):
        return {"pass":False,"reason":"V11_SUBJECT_PATH_INVALID"}
    path=(root/rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return {"pass":False,"reason":"V11_SUBJECT_PATH_OUTSIDE_REPOSITORY"}
    try:
        doc=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"reason":"V11_SUBJECT_LOAD_FAILED:"+type(exc).__name__}
    comps=(doc.get("system_material") or {}).get("components") or []
    paths={x.get("path") for x in comps if isinstance(x,Mapping)}
    missing=sorted(REQUIRED_V11_COMPONENTS-paths)
    if missing:
        return {"pass":False,"reason":"V11_LOAD_BEARING_COMPONENTS_NOT_IN_SUBJECT","missing":missing}
    return {
        "pass":True,
        "subject_id":prior.get("subject_id"),
        "subject_sha256":prior.get("subject_sha256"),
        "subject_git_blob_sha":prior.get("subject_git_blob_sha"),
    }


def _reject(base_result:Mapping[str,Any],reason:str,**extra:Any)->dict[str,Any]:
    out=deepcopy(dict(base_result))
    out.update({
        "schema":SCHEMA,
        "status":"FAIL_CLOSED__POSITIVE_TASK_FULFILLMENT_GATE",
        "reason":reason,
        "positive_certification_authorized":False,
        "task_fulfillment_verified":False,
        "semantic_truth_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    })
    return out


def route(state:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(state,Mapping):
        return _reject({},"STATE_NOT_OBJECT")
    root=(
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )

    delegated=deepcopy(dict(state))
    bundle=delegated.pop(TASK_FULFILLMENT_KEY,None)
    prior=base.route(delegated,repo_root=root)
    if not isinstance(prior,Mapping):
        return _reject({},"V9_RESULT_NOT_OBJECT")

    result=deepcopy(dict(prior))
    result["schema"]=SCHEMA

    is_positive=(
        result.get("final_step_outcome")=="POSITIVE_CERTIFICATE"
        and result.get("positive_certification_authorized") is True
    )
    if not is_positive:
        result["task_fulfillment_verified"]=False
        result["task_fulfillment_gate_required_for_nonpositive"]=False
        result["semantic_truth_authority"]=False
        result["quality_authority"]=False
        result["acceptance_authority"]=False
        result["promotion_authority"]=False
        result["terminal_authority"]=False
        result["terminal_credit_delta"]=0
        result["incremental_spend_usd"]=0
        return result

    subject=_v11_subject_ok(state.get(SUBJECT_REF_KEY),root=root)
    if subject.get("pass") is not True:
        return _reject(result,"V11_DECLARED_SYSTEM_SUBJECT_INVALID",subject_verification=subject)
    if not isinstance(bundle,Mapping):
        return _reject(result,"TASK_FULFILLMENT_BUNDLE_REQUIRED_AFTER_V9_POSITIVE")

    run_context=str(result.get("run_context_sha256") or "")
    if not run_context.startswith("sha256:") or len(run_context)!=71:
        return _reject(result,"RUN_CONTEXT_SHA256_INVALID")

    try:
        expected_task_sha=_target_sha256(state.get("decision_payload"))
        artifact_rel,artifact_sha=_single_artifact(root,state.get("artifact_paths"))
    except Exception as exc:
        return _reject(result,type(exc).__name__+":"+str(exc))

    expected_task_id="professional-run:"+run_context
    task=bundle.get("task")
    if not isinstance(task,Mapping):
        return _reject(result,"TASK_FULFILLMENT_TASK_NOT_OBJECT")
    if task.get("task_id")!=expected_task_id:
        return _reject(result,"TASK_FULFILLMENT_TASK_ID_MISMATCH")
    if task.get("task_sha256")!=expected_task_sha:
        return _reject(result,"TASK_FULFILLMENT_TASK_SHA256_MISMATCH")
    if bundle.get("artifact_sha256")!=artifact_sha:
        return _reject(result,"TASK_FULFILLMENT_ARTIFACT_SHA256_MISMATCH")

    verified=fulfillment.verify(bundle,repo_root=root)
    if verified.get("pass") is not True:
        return _reject(
            result,
            "TASK_FULFILLMENT_BRIDGE_REJECTED",
            task_fulfillment_verification=verified,
        )

    result["task_fulfillment_verified"]=True
    result["task_fulfillment_gate_required_for_positive"]=True
    result["task_fulfillment_task_id"]=expected_task_id
    result["task_fulfillment_task_sha256"]=expected_task_sha
    result["task_fulfillment_artifact_path"]=artifact_rel
    result["task_fulfillment_artifact_sha256"]=artifact_sha
    result["task_fulfillment_target_scope_id"]=verified.get("target_scope_id")
    result["task_fulfillment_obligation_count"]=verified.get("obligation_count")
    result["task_fulfillment_verified_obligation_count"]=verified.get("verified_obligation_count")
    result["semantic_truth_authority"]=False
    result["quality_authority"]=False
    result["acceptance_authority"]=False
    result["promotion_authority"]=False
    result["terminal_authority"]=False
    result["terminal_credit_delta"]=0
    result["incremental_spend_usd"]=0
    return result


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return route(args or {},repo_root=root)
