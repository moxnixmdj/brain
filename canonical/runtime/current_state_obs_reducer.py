#!/usr/bin/env python3
"""Receipt-derived current-state OBS reducer.

Fails closed when Project Brain's current authority surfaces disagree, when the
continuous OBS membrane is not wired into the current V11 controls, or when an
old lease still advertises live authority outside the current frontier.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

DEFAULT_ROOT=pathlib.Path(__file__).resolve().parents[2]

POINTER="canonical/CANONICAL_POINTER.json"
HIERARCHY="canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json"
QUEUE="canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json"
SCOREBOARD="canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"
GATE="canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V11.json"
TEMPLATE="canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V11.json"
OBS_POLICY="canonical/governance/OBS_DEPENDENCY_FRESHNESS_V1.json"
OBS_RUNTIME="canonical/runtime/continuous_obs_runtime.py"
EVIDENCE_LAW="canonical/laws/EVIDENCE_SATURATION_AND_MINIMUM_REALITY_QUERY_LAW_V1.md"
COUNTERFACTUAL_COMPILER="canonical/governance/COUNTERFACTUAL_TERMINAL_COMPILER_V1.json"
MINIMUM_REALITY_CUT_RUNTIME="canonical/runtime/minimum_reality_cut.py"

REQUIRED_GATE_CHECKS={
    "CONTINUOUS_OBS_CONTEXT_PRESENT_AND_CURRENT",
    "MATERIAL_WORLD_STATE_DEPENDENCIES_COMPLETE",
    "UNKNOWN_MATERIAL_DEPENDENCIES_EMPTY",
    "CANONICAL_STATE_HASH_BINDINGS_CURRENT",
    "INFORMATION_BOUNDARY_COMPLETE_AND_CURRENT",
    "POST_EXPOSURE_EXTERNAL_DISCOVERY_DISABLED",
    "POST_RECEIPT_OBS_REVALIDATION_REQUIRED",
    "EXISTING_EVIDENCE_SATURATION_COMPLETE_BEFORE_NEW_REALITY_QUERY",
    "DEDUCTIVE_CLOSURE_COMPLETE_BEFORE_NEW_REALITY_QUERY",
    "COUNTERFACTUAL_TERMINAL_DISTINCTIONS_EXPLICIT",
    "DOMINATED_REALITY_QUERIES_DELETED",
    "REALITY_QUERY_HAS_TERMINAL_DECISION_VALUE",
    "MINIMUM_REALITY_CUT_MEMBER_OR_GRANDFATHERED_CURRENT_VALID_ACTION",
    "NO_REACQUISITION_OF_ALREADY_KNOWN_TERMINAL_RELEVANT_INFORMATION",
    "EXECUTION_AUTHORITY_BINDS_EXACT_ACTIVE_CARRIER_IDENTITY",
    "SECOND_OPEN_CARRIER_FAILS_CLOSED",
    "LIVE_AUTHORITY_REVALIDATED_AFTER_LAST_MATERIAL_STATE_TRANSITION_BEFORE_IRREVERSIBLE_COMMAND",
    "EXECUTION_PATH_USES_CANONICAL_AUTHORITY_REDUCER_AND_MAY_NOT_BYPASS_IT",
}

def load(root:pathlib.Path, rel:str)->dict[str,Any]:
    p=root/rel
    if not p.is_file():
        raise FileNotFoundError(rel)
    return json.loads(p.read_text(encoding="utf-8"))

def _s(v:Any)->str:
    return str(v or "").strip()

def _task_rank(doc:dict[str,Any])->tuple[str|None,int|None]:
    task=doc.get("task")
    rank=doc.get("rank")
    if not task:
        tl=doc.get("task_lease")
        if isinstance(tl,dict):
            task=tl.get("task")
            rank=tl.get("sample_rank",rank)
    if rank is None:
        rank=doc.get("sample_rank")
    try:
        rank_i=int(rank) if rank is not None else None
    except (TypeError,ValueError):
        rank_i=None
    return (_s(task) or None,rank_i)

def _looks_live(status:str)->bool:
    u=status.upper()
    if not u:
        return False
    if u.startswith("ACTIVE"):
        return True
    if u.startswith("LEASED_FRESH_TASK"):
        return True
    if "AUTHORIZED__NOT_YET_EXECUTED" in u:
        return True
    if "ONE_SHOT" in u and "AUTHORIZED" in u and not any(x in u for x in ("REVOKED","SPENT","ZERO_AUTHORITY","SUPERSEDED","CONTAMINATED")):
        return True
    return False

def _same_task_rank(doc:dict[str,Any]|None, task:str|None, rank:int|None)->bool:
    if not isinstance(doc,dict) or not task:
        return False
    dt=_s(doc.get("task"))
    dr=doc.get("rank")
    try:
        dri=int(dr) if dr is not None else None
    except (TypeError,ValueError):
        dri=None
    return dt==task and (rank is None or dri is None or dri==rank)

def evaluate(root:pathlib.Path)->dict[str,Any]:
    errors:list[str]=[]
    notes:list[str]=[]
    try:
        pointer=load(root,POINTER)
        hierarchy=load(root,HIERARCHY)
        queue=load(root,QUEUE)
        score=load(root,SCOREBOARD)
        gate=load(root,GATE)
        template=load(root,TEMPLATE)
        obs=load(root,OBS_POLICY)
    except Exception as exc:
        return {
            "schema":"PROJECT_BRAIN_CURRENT_STATE_OBS_REDUCER_V1",
            "pass":False,
            "errors":["CONTROL_SURFACE_UNREADABLE:"+type(exc).__name__+":"+str(exc)],
        }

    target_id=_s(hierarchy.get("active_capability_target"))
    blocker=_s(hierarchy.get("current_parent_blocker"))
    next_action=_s(hierarchy.get("next_required_action_class"))
    next_event=_s(hierarchy.get("next_progress_event_target"))
    target_rel=f"canonical/capabilities/frontier/{target_id}.json" if target_id else ""
    try:
        target=load(root,target_rel) if target_rel else {}
    except Exception as exc:
        target={}
        errors.append("ACTIVE_TARGET_UNREADABLE:"+type(exc).__name__)

    current=pointer.get("current_frontier") or {}
    if _s(current.get("active_capability_target"))!=target_id:
        errors.append("POINTER_TARGET_DRIFT")
    if _s(current.get("critical_blocker"))!=blocker:
        errors.append("POINTER_BLOCKER_DRIFT")
    if _s(current.get("next_step"))!=next_action:
        errors.append("POINTER_NEXT_ACTION_DRIFT")

    immediate=queue.get("immediate_frontier") or {}
    if _s(immediate.get("selected_capability"))!=target_id:
        errors.append("QUEUE_TARGET_DRIFT")
    if _s(immediate.get("exact_blocker"))!=blocker:
        errors.append("QUEUE_BLOCKER_DRIFT")
    if _s(immediate.get("next_action"))!=next_action:
        errors.append("QUEUE_NEXT_ACTION_DRIFT")

    accounting=score.get("active_frontier_accounting") or {}
    if accounting and _s(accounting.get("parent_frontier_capability"))!=target_id:
        errors.append("SCOREBOARD_TARGET_DRIFT")
    if _s(score.get("next_required_action"))!=next_action:
        errors.append("SCOREBOARD_NEXT_ACTION_DRIFT")
    if _s(score.get("next_progress_event_target"))!=next_event:
        errors.append("SCOREBOARD_NEXT_EVENT_DRIFT")

    if target:
        if _s(target.get("capability_id"))!=target_id:
            errors.append("TARGET_ID_DRIFT")
        if _s(target.get("current_atomic_blocker"))!=blocker:
            errors.append("TARGET_ATOMIC_BLOCKER_DRIFT")
        if _s(target.get("current_atomic_next_action"))!=next_action:
            errors.append("TARGET_ATOMIC_NEXT_ACTION_DRIFT")
        if _s(target.get("current_atomic_progress_event"))!=next_event:
            errors.append("TARGET_ATOMIC_EVENT_DRIFT")

    boot=pointer.get("boot_requirements") or {}
    expected={
      "pre_action_gate_path":"canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V11.json",
      "goal_hierarchy_action_gate_path":GATE,
      "recursive_obs_receipt_schema_path":"canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V6.json",
      "recursive_obs_action_intent_template_path":TEMPLATE,
      "continuous_obs_policy_path":OBS_POLICY,
      "continuous_obs_runtime_path":OBS_RUNTIME,
      "execution_authority_reducer_path":"canonical/runtime/execution_authority_reducer.py",
    }
    for key,value in expected.items():
        if _s(boot.get(key))!=value:
            errors.append("POINTER_CONTROL_PATH_DRIFT:"+key)
        if not (root/value).is_file():
            errors.append("CONTROL_PATH_MISSING:"+value)
    for key in (
      "continuous_obs_required",
      "continuous_obs_on_every_material_state_transition",
      "material_world_state_unknown_fails_closed",
      "information_action_authorization_required",
      "execution_authority_reducer_required",
      "exact_active_carrier_identity_binding_required",
      "second_open_execution_carrier_forbidden",
      "post_material_transition_authority_revalidation_required",
    ):
        if boot.get(key) is not True:
            errors.append("POINTER_CONTINUOUS_OBS_FLAG_FALSE:"+key)

    recursive=gate.get("recursive_obs") or {}
    if _s(recursive.get("continuous_obs_policy"))!=OBS_POLICY:
        errors.append("GATE_OBS_POLICY_DRIFT")
    if _s(recursive.get("continuous_obs_runtime"))!=OBS_RUNTIME:
        errors.append("GATE_OBS_RUNTIME_DRIFT")
    for key in (
      "event_driven_revalidation_required",
      "material_unknown_fails_closed",
      "information_action_authorization_required",
    ):
        if recursive.get(key) is not True:
            errors.append("GATE_CONTINUOUS_OBS_FLAG_FALSE:"+key)
    checks=set(str(x) for x in (gate.get("required_checks") or []))
    missing=sorted(REQUIRED_GATE_CHECKS-checks)
    if missing:
        errors.extend("GATE_CONTINUOUS_OBS_CHECK_MISSING:"+x for x in missing)

    if "continuous_obs" not in (template.get("action_fields") or []):
        errors.append("ACTION_TEMPLATE_CONTINUOUS_OBS_FIELD_MISSING")
    required=template.get("required_continuous_obs")
    if not isinstance(required,dict) or required.get("required") is not True:
        errors.append("ACTION_TEMPLATE_CONTINUOUS_OBS_NOT_REQUIRED")
    else:
        if _s(required.get("policy"))!=OBS_POLICY:
            errors.append("ACTION_TEMPLATE_OBS_POLICY_DRIFT")
        if _s(required.get("runtime"))!=OBS_RUNTIME:
            errors.append("ACTION_TEMPLATE_OBS_RUNTIME_DRIFT")
        if required.get("material_unknown_fails_closed") is not True:
            errors.append("ACTION_TEMPLATE_UNKNOWN_NOT_FAIL_CLOSED")
        if required.get("post_receipt_revalidation_required") is not True:
            errors.append("ACTION_TEMPLATE_POST_RECEIPT_REVALIDATION_MISSING")
        if required.get("post_exposure_discovery_forbidden") is not True:
            errors.append("ACTION_TEMPLATE_POST_EXPOSURE_DISCOVERY_NOT_FORBIDDEN")

    # Information-minimization controls must be live across the canonical surfaces.
    eg=pointer.get("execution_governance") or {}
    if _s(eg.get("execution_authority_reducer"))!="canonical/runtime/execution_authority_reducer.py":
        errors.append("POINTER_EXECUTION_AUTHORITY_REDUCER_DRIFT")
    if _s(eg.get("execution_authority_carrier_binding_verification"))!="canonical/verification/EXECUTION_AUTHORITY_CARRIER_BINDING_VERIFICATION_20261002_V1.json":
        errors.append("POINTER_CARRIER_BINDING_VERIFICATION_DRIFT")
    if _s(eg.get("duplicate_carrier_regression"))!="canonical/regressions/2026-10-02_DUPLICATE_CARRIER_AUTHORITY_HASH_COLLISION.json":
        errors.append("POINTER_DUPLICATE_CARRIER_REGRESSION_DRIFT")
    if eg.get("static_carrier_agnostic_authority_forbidden") is not True:
        errors.append("POINTER_CARRIER_AGNOSTIC_AUTHORITY_NOT_FORBIDDEN")
    expected_info_paths={
      "evidence_saturation_and_minimum_reality_query_law":EVIDENCE_LAW,
      "counterfactual_terminal_compiler":COUNTERFACTUAL_COMPILER,
      "minimum_reality_cut_runtime":MINIMUM_REALITY_CUT_RUNTIME,
    }
    for key,value in expected_info_paths.items():
        if _s(eg.get(key))!=value:
            errors.append("POINTER_INFORMATION_MINIMIZATION_PATH_DRIFT:"+key)
        if not (root/value).is_file():
            errors.append("INFORMATION_MINIMIZATION_CONTROL_MISSING:"+value)
    if eg.get("new_fresh_evidence_requires_minimum_reality_cut") is not True:
        errors.append("POINTER_MINIMUM_REALITY_CUT_NOT_REQUIRED")
    if eg.get("reacquire_existing_terminal_information_without_invalidation") is not False:
        errors.append("POINTER_REACQUISITION_GUARD_NOT_FAIL_CLOSED")

    him=hierarchy.get("information_minimization_control") or {}
    if not _s(him.get("status")).startswith("ACTIVE_CANONICAL"):
        errors.append("HIERARCHY_INFORMATION_MINIMIZATION_NOT_ACTIVE")
    if _s(him.get("law"))!=EVIDENCE_LAW:
        errors.append("HIERARCHY_EVIDENCE_LAW_DRIFT")
    if _s(him.get("compiler"))!=COUNTERFACTUAL_COMPILER:
        errors.append("HIERARCHY_COUNTERFACTUAL_COMPILER_DRIFT")
    if _s(him.get("exact_minimum_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("HIERARCHY_MINIMUM_REALITY_CUT_RUNTIME_DRIFT")

    gim=gate.get("information_minimization") or {}
    if _s(gim.get("law"))!=EVIDENCE_LAW:
        errors.append("GATE_EVIDENCE_LAW_DRIFT")
    if _s(gim.get("compiler"))!=COUNTERFACTUAL_COMPILER:
        errors.append("GATE_COUNTERFACTUAL_COMPILER_DRIFT")
    if _s(gim.get("exact_minimum_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("GATE_MINIMUM_REALITY_CUT_RUNTIME_DRIFT")
    if gim.get("required_for_new_fresh_evidence") is not True:
        errors.append("GATE_INFORMATION_MINIMIZATION_NOT_REQUIRED")

    if "reality_query_admission" not in (template.get("action_fields") or []):
        errors.append("ACTION_TEMPLATE_REALITY_QUERY_ADMISSION_FIELD_MISSING")
    rqa=template.get("required_reality_query_admission") or {}
    if _s(rqa.get("law"))!=EVIDENCE_LAW:
        errors.append("ACTION_TEMPLATE_EVIDENCE_LAW_DRIFT")
    if _s(rqa.get("compiler"))!=COUNTERFACTUAL_COMPILER:
        errors.append("ACTION_TEMPLATE_COUNTERFACTUAL_COMPILER_DRIFT")
    if _s(rqa.get("exact_minimum_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("ACTION_TEMPLATE_MINIMUM_REALITY_CUT_RUNTIME_DRIFT")
    if rqa.get("fail_closed_on_unknown") is not True:
        errors.append("ACTION_TEMPLATE_REALITY_QUERY_UNKNOWN_NOT_FAIL_CLOSED")

    sim=score.get("information_acquisition_optimization") or {}
    if _s(sim.get("law"))!=EVIDENCE_LAW:
        errors.append("SCOREBOARD_EVIDENCE_LAW_DRIFT")
    if _s(sim.get("compiler"))!=COUNTERFACTUAL_COMPILER:
        errors.append("SCOREBOARD_COUNTERFACTUAL_COMPILER_DRIFT")
    if _s(sim.get("exact_minimum_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("SCOREBOARD_MINIMUM_REALITY_CUT_RUNTIME_DRIFT")
    if sim.get("minimum_reality_cut_required_for_future_fresh_spend") is not True:
        errors.append("SCOREBOARD_MINIMUM_REALITY_CUT_NOT_REQUIRED")

    if _s(obs.get("status"))!="CANONICAL_FAIL_CLOSED_RUNTIME_REQUIREMENT":
        errors.append("OBS_POLICY_NOT_CANONICAL_FAIL_CLOSED")
    if not (root/OBS_RUNTIME).is_file():
        errors.append("OBS_RUNTIME_MISSING")

    active_execution=hierarchy.get("active_stage1_execution")
    next_task=hierarchy.get("stage1_next_clean_task")
    active_lease_rows=[]
    gov=root/"canonical"/"governance"
    for path in sorted(gov.glob("LEASE_*.json")):
        rel=path.relative_to(root).as_posix()
        try:
            doc=json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            errors.append("LEASE_UNREADABLE:"+rel)
            continue
        status=_s(doc.get("status"))
        task,rank=_task_rank(doc)
        authorized=doc.get("task_execution_authorized") is True
        looks_live=_looks_live(status)
        if not looks_live and not authorized:
            continue
        row={"path":rel,"status":status,"task":task,"rank":rank,"authorized":authorized}
        active_lease_rows.append(row)
        matches_active=_same_task_rank(active_execution,task,rank)
        matches_next=_same_task_rank(next_task,task,rank)
        if authorized:
            if not matches_active:
                errors.append("ZOMBIE_EXECUTION_AUTHORITY:"+rel)
        elif looks_live and not (matches_active or matches_next):
            errors.append("ZOMBIE_ACTIVE_LEASE:"+rel)

    # Any live execution surface must itself require continuous OBS.
    executor_policy=load(root,"canonical/runtime/EXECUTOR_POLICY_V1.json")
    eco=executor_policy.get("continuous_obs") or {}
    if eco.get("required") is not True or eco.get("fail_closed") is not True:
        errors.append("EXECUTOR_POLICY_OBS_NOT_FAIL_CLOSED")
    if _s(eco.get("runtime"))!=OBS_RUNTIME:
        errors.append("EXECUTOR_POLICY_OBS_RUNTIME_DRIFT")

    errors=sorted(set(errors))
    return {
      "schema":"PROJECT_BRAIN_CURRENT_STATE_OBS_REDUCER_V1",
      "pass":not errors,
      "active_capability_target":target_id,
      "current_parent_blocker":blocker,
      "next_required_action":next_action,
      "next_progress_event_target":next_event,
      "active_execution":active_execution,
      "next_clean_task":next_task,
      "live_lease_rows":active_lease_rows,
      "errors":errors,
      "notes":notes,
      "rule":"RECEIPT_DERIVED_CURRENT_STATE_MUST_BE_CROSS_SURFACE_CONSISTENT__ZOMBIE_AUTHORITY_FORBIDDEN",
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=pathlib.Path,default=DEFAULT_ROOT)
    ap.add_argument("--output",type=pathlib.Path)
    args=ap.parse_args()
    out=evaluate(args.root.resolve())
    raw=json.dumps(out,indent=2,sort_keys=True)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw,encoding="utf-8")
    print(raw,end="")
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
