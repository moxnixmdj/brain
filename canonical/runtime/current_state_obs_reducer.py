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
GLOBAL_PROOF_LAW="canonical/laws/GLOBAL_TERMINAL_PROOF_TREE_COLLAPSE_LAW_V1.md"
GLOBAL_CUT="canonical/governance/GLOBAL_TERMINAL_PROOF_CUT_V1.json"
GLOBAL_UNIVERSE="canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json"
OUTER_OBSERVATION_CUT="canonical/governance/OUTER_GLOBAL_MINIMUM_REALITY_CUT_VERDICT_V2.json"

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
    "GLOBAL_TERMINAL_PROOF_CUT_CURRENT",
    "FAMILY_AND_BENCHMARK_RANK_ARE_NOT_SCHEDULING_AUTHORITY",
    "UNTOUCHED_TASK_SELECTION_REQUIRES_GLOBAL_CUT_MEMBERSHIP",
    "UNTOUCHED_SOURCE_READ_REQUIRES_GLOBAL_CUT_MEMBERSHIP",
    "LOCAL_STAGE_A_PASS_CANNOT_ALONE_AUTHORIZE_SOURCE_READ",
    "UNADMITTED_SOURCE_READ_QUARANTINED_FROM_CLEAN_PROMOTION",
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
        global_cut=load(root,GLOBAL_CUT)
        global_universe=load(root,GLOBAL_UNIVERSE)
        outer_observation_cut=load(root,OUTER_OBSERVATION_CUT)
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
    precedence=hierarchy.get("control_plane_precedence") or {}
    allowed_targets={target_id}
    allowed_blockers={blocker}
    allowed_next={next_action}
    allowed_events={next_event}
    if precedence.get("development_scheduling")=="canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json":
        try:
            opus=load(root,"canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json")
            allowed_targets.add(_s(opus.get("capability_id")))
            allowed_blockers.add(_s(opus.get("current_atomic_blocker")))
            allowed_next.add(_s(opus.get("current_atomic_next_action")))
            allowed_events.add(_s(opus.get("next_progress_event_target")))
        except Exception:
            pass
    if _s(current.get("active_capability_target")) not in allowed_targets:
        errors.append("POINTER_TARGET_DRIFT")
    if _s(current.get("critical_blocker")) not in allowed_blockers:
        errors.append("POINTER_BLOCKER_DRIFT")
    if _s(current.get("next_step")) not in allowed_next:
        errors.append("POINTER_NEXT_ACTION_DRIFT")

    immediate=queue.get("immediate_frontier") or {}
    if _s(immediate.get("selected_capability")) not in allowed_targets:
        errors.append("QUEUE_TARGET_DRIFT")
    if _s(immediate.get("exact_blocker")) not in allowed_blockers:
        errors.append("QUEUE_BLOCKER_DRIFT")
    if _s(immediate.get("next_action")) not in allowed_next:
        errors.append("QUEUE_NEXT_ACTION_DRIFT")

    accounting=score.get("active_frontier_accounting") or {}
    if accounting and _s(accounting.get("parent_frontier_capability")) not in allowed_targets:
        errors.append("SCOREBOARD_TARGET_DRIFT")
    if _s(score.get("next_required_action")) not in allowed_next:
        errors.append("SCOREBOARD_NEXT_ACTION_DRIFT")
    if _s(score.get("next_progress_event_target")) not in allowed_events:
        errors.append("SCOREBOARD_NEXT_EVENT_DRIFT")

    if target:
        if _s(target.get("capability_id"))!=target_id:
            errors.append("TARGET_ID_DRIFT")
        if _s(target.get("current_atomic_blocker"))!=blocker:
            errors.append("TARGET_ATOMIC_BLOCKER_DRIFT")
        if _s(target.get("current_atomic_next_action"))!=next_action:
            errors.append("TARGET_ATOMIC_NEXT_ACTION_DRIFT")
        if _s(target.get("current_atomic_progress_event")) not in allowed_events:
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
      "global_terminal_proof_tree_law":GLOBAL_PROOF_LAW,
      "global_terminal_proof_cut":GLOBAL_CUT,
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
    if eg.get("untouched_source_read_requires_global_cut_membership") is not True:
        errors.append("POINTER_UNTOUCHED_SOURCE_READ_GLOBAL_CUT_NOT_REQUIRED")
    if eg.get("untouched_task_selection_requires_global_cut_membership") is not True:
        errors.append("POINTER_UNTOUCHED_TASK_SELECTION_GLOBAL_CUT_NOT_REQUIRED")
    if eg.get("family_local_rank_progression_is_scheduling_authority") is not False:
        errors.append("POINTER_FAMILY_LOCAL_RANK_STILL_SCHEDULING_AUTHORITY")

    if not _s(global_cut.get("status")).startswith("ACTIVE"):
        errors.append("GLOBAL_TERMINAL_PROOF_CUT_NOT_ACTIVE")
    if _s(global_cut.get("law"))!=GLOBAL_PROOF_LAW:
        errors.append("GLOBAL_TERMINAL_PROOF_CUT_LAW_DRIFT")
    if _s(global_cut.get("exact_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("GLOBAL_TERMINAL_PROOF_CUT_RUNTIME_DRIFT")
    scheduling=global_cut.get("scheduling_authority") or {}
    if scheduling.get("global_terminal_proof_cut") is not True:
        errors.append("GLOBAL_CUT_NOT_SCHEDULING_AUTHORITY")
    if scheduling.get("family_labels") is not False or scheduling.get("benchmark_rank_order") is not False:
        errors.append("GLOBAL_CUT_LOCAL_ORDER_STILL_AUTHORITATIVE")

    # The outer universe dominates every local residual cut until the entire
    # terminal graph has no open specification/mechanism holes and an exact
    # outer cut is frozen. Local optimality is not terminal authority.
    outer=global_universe.get("global_cut") or {}
    outer_auth=global_universe.get("execution_authority") or {}
    if not _s(global_universe.get("status")).startswith("FROZEN_OUTER_UNIVERSE"):
        errors.append("GLOBAL_TERMINAL_UNIVERSE_NOT_FROZEN")
    exact_outer=outer.get("exact_cut_ready") is True
    observation_cut_exact=outer.get("terminal_observation_cut_exact") is True
    fresh_allowed=outer_auth.get("fresh_terminal_evidence_allowed") is True
    if not exact_outer and fresh_allowed:
        errors.append("OUTER_UNIVERSE_PREMATURE_FRESH_EVIDENCE_AUTHORITY")
    if observation_cut_exact:
        if outer.get("execution_ready") is not False:
            errors.append("OUTER_OBSERVATION_CUT_EXECUTION_READINESS_NOT_FALSE_WHILE_MECHANISMS_OPEN")
        if outer_auth.get("exact_terminal_observation_cut_frozen") is not True:
            errors.append("OUTER_OBSERVATION_CUT_NOT_BOUND_IN_EXECUTION_AUTHORITY")
        if _s(outer_auth.get("exact_terminal_observation_cut"))!=OUTER_OBSERVATION_CUT:
            errors.append("OUTER_OBSERVATION_CUT_AUTHORITY_PATH_DRIFT")
        if _s(outer.get("terminal_observation_cut_verdict"))!=OUTER_OBSERVATION_CUT:
            errors.append("OUTER_OBSERVATION_CUT_UNIVERSE_PATH_DRIFT")
        if outer_observation_cut.get("exact_minimum") is not True:
            errors.append("OUTER_OBSERVATION_CUT_NOT_EXACT")
        if outer_observation_cut.get("execution_authority") is not False:
            errors.append("OUTER_OBSERVATION_CUT_PREMATURE_EXECUTION_AUTHORITY")
        hcut=hierarchy.get("exact_outer_terminal_observation_cut") or {}
        if _s(hcut.get("verdict"))!=OUTER_OBSERVATION_CUT:
            errors.append("HIERARCHY_OUTER_OBSERVATION_CUT_DRIFT")
        if hcut.get("execution_authorized") is not False:
            errors.append("HIERARCHY_OUTER_OBSERVATION_CUT_PREMATURE_AUTHORITY")
    if not exact_outer:
        if not observation_cut_exact and "OUTER_GLOBAL_TERMINAL_UNIVERSE" not in blocker:
            errors.append("HIERARCHY_IGNORES_OPEN_OUTER_GLOBAL_UNIVERSE")
        if observation_cut_exact and "OPERATIVE_ROUTE_CLOSURE" not in blocker:
            errors.append("HIERARCHY_IGNORES_POST_CUT_MECHANISM_BLOCKER")
        if any(token in next_action for token in ("PREQUALIFY_IN_PARALLEL","EXECUTE_","EXPOSE_")):
            errors.append("HIERARCHY_PREMATURE_FRESH_ACTION_WHILE_OUTER_CUT_OPEN")
        local_v6=hierarchy.get("v6_residual_cut") or {}
        if local_v6.get("execution_authorized") is True or local_v6.get("prequalification_parallel") is True:
            errors.append("LOCAL_V6_ESCAPES_OUTER_GLOBAL_GUARD")
    eg_outer=_s(eg.get("outer_global_terminal_universe"))
    if eg_outer!=GLOBAL_UNIVERSE:
        errors.append("POINTER_OUTER_GLOBAL_UNIVERSE_DRIFT")
    if eg.get("local_v6_is_global_execution_authority") is not False:
        errors.append("POINTER_LOCAL_V6_WRONGLY_GLOBAL")
    if eg.get("fresh_terminal_evidence_requires_outer_exact_cut") is not True:
        errors.append("POINTER_OUTER_EXACT_CUT_NOT_REQUIRED")
    if observation_cut_exact:
        if _s(eg.get("outer_global_terminal_observation_cut"))!=OUTER_OBSERVATION_CUT:
            errors.append("POINTER_OUTER_OBSERVATION_CUT_DRIFT")
        if eg.get("outer_global_terminal_observation_cut_exact") is not True:
            errors.append("POINTER_OUTER_OBSERVATION_CUT_EXACT_FLAG_FALSE")
        if eg.get("outer_global_terminal_observation_cut_execution_authorized") is not False:
            errors.append("POINTER_OUTER_OBSERVATION_CUT_PREMATURE_AUTHORITY")
    expected_open_mechanism_lanes=(global_universe.get("counts") or {}).get("open_mechanism_lanes")
    pointer_open_mechanism_count=eg.get("open_mechanism_residual_count")
    if expected_open_mechanism_lanes is not None and pointer_open_mechanism_count!=expected_open_mechanism_lanes:
        errors.append("POINTER_OPEN_MECHANISM_RESIDUAL_COUNT_DRIFT")

    him=hierarchy.get("information_minimization_control") or {}
    if not _s(him.get("status")).startswith("ACTIVE_CANONICAL"):
        errors.append("HIERARCHY_INFORMATION_MINIMIZATION_NOT_ACTIVE")
    if _s(him.get("law"))!=EVIDENCE_LAW:
        errors.append("HIERARCHY_EVIDENCE_LAW_DRIFT")
    if _s(him.get("compiler"))!=COUNTERFACTUAL_COMPILER:
        errors.append("HIERARCHY_COUNTERFACTUAL_COMPILER_DRIFT")
    if _s(him.get("exact_minimum_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("HIERARCHY_MINIMUM_REALITY_CUT_RUNTIME_DRIFT")
    hglobal=hierarchy.get("global_terminal_proof_cut_control") or {}
    if _s(hglobal.get("cut"))!=GLOBAL_CUT:
        errors.append("HIERARCHY_GLOBAL_CUT_DRIFT")
    if _s(hglobal.get("law"))!=GLOBAL_PROOF_LAW:
        errors.append("HIERARCHY_GLOBAL_PROOF_LAW_DRIFT")
    if hglobal.get("family_or_rank_order_is_scheduling_authority") is not False:
        errors.append("HIERARCHY_LOCAL_ORDER_STILL_SCHEDULING_AUTHORITY")

    gim=gate.get("information_minimization") or {}
    if _s(gim.get("law"))!=EVIDENCE_LAW:
        errors.append("GATE_EVIDENCE_LAW_DRIFT")
    if _s(gim.get("compiler"))!=COUNTERFACTUAL_COMPILER:
        errors.append("GATE_COUNTERFACTUAL_COMPILER_DRIFT")
    if _s(gim.get("exact_minimum_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("GATE_MINIMUM_REALITY_CUT_RUNTIME_DRIFT")
    if gim.get("required_for_new_fresh_evidence") is not True:
        errors.append("GATE_INFORMATION_MINIMIZATION_NOT_REQUIRED")
    gglobal=gate.get("global_terminal_proof_cut") or {}
    if gglobal.get("required") is not True or gglobal.get("fail_closed") is not True:
        errors.append("GATE_GLOBAL_CUT_NOT_FAIL_CLOSED")
    if _s(gglobal.get("cut"))!=GLOBAL_CUT or _s(gglobal.get("law"))!=GLOBAL_PROOF_LAW:
        errors.append("GATE_GLOBAL_CUT_PATH_DRIFT")

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
    gt=template.get("required_global_terminal_proof_cut") or {}
    if _s(gt.get("cut"))!=GLOBAL_CUT or _s(gt.get("law"))!=GLOBAL_PROOF_LAW:
        errors.append("ACTION_TEMPLATE_GLOBAL_CUT_DRIFT")
    if gt.get("fail_closed_on_missing_or_unknown") is not True:
        errors.append("ACTION_TEMPLATE_GLOBAL_CUT_NOT_FAIL_CLOSED")
    if gt.get("stage_a_cleanliness_does_not_imply_membership") is not True:
        errors.append("ACTION_TEMPLATE_STAGE_A_CLEANLINESS_CONFUSION")

    sim=score.get("information_acquisition_optimization") or {}
    if _s(sim.get("law"))!=EVIDENCE_LAW:
        errors.append("SCOREBOARD_EVIDENCE_LAW_DRIFT")
    if _s(sim.get("compiler"))!=COUNTERFACTUAL_COMPILER:
        errors.append("SCOREBOARD_COUNTERFACTUAL_COMPILER_DRIFT")
    if _s(sim.get("exact_minimum_cut_runtime"))!=MINIMUM_REALITY_CUT_RUNTIME:
        errors.append("SCOREBOARD_MINIMUM_REALITY_CUT_RUNTIME_DRIFT")
    if sim.get("minimum_reality_cut_required_for_future_fresh_spend") is not True:
        errors.append("SCOREBOARD_MINIMUM_REALITY_CUT_NOT_REQUIRED")
    if _s(sim.get("global_terminal_proof_cut"))!=GLOBAL_CUT:
        errors.append("SCOREBOARD_GLOBAL_CUT_DRIFT")
    if sim.get("family_or_benchmark_rank_progression_authority") is not False:
        errors.append("SCOREBOARD_LOCAL_ORDER_STILL_SCHEDULING_AUTHORITY")

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
