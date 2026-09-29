#!/usr/bin/env python3
"""Fail-closed anti-drift validator for frontier-sensitive changes."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, pathlib, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

ROOT=pathlib.Path(os.environ.get("GITHUB_WORKSPACE") or pathlib.Path.cwd()).resolve()

SENSITIVE_PREFIXES=(
    "canonical/action_intents/",
    "canonical/runtime/",
    "canonical/experiments/",
    "canonical/capabilities/",
    "canonical/tasks/",
    "canonical/qualification/",
    "canonical/laws/",
    "canonical/gates/",
    "canonical/governance/",
    ".github/workflows/",
)
SENSITIVE_EXACT={"canonical/CANONICAL_POINTER.json"}
PROTECTED_GUARD_PATHS={
    "canonical/laws/GOAL_HIERARCHY_AND_DRIFT_IMMUNITY_LAW_V1.md",
    "canonical/laws/TRUTH_FIRST_AND_NO_DUPLICATE_EXECUTION_LAW_V1.md",
    "canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V1.md",
    "canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V2.md",
    "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V2.md",
    "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V3.md",
    "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V4.md",
    "canonical/laws/MISTAKE_PRESUMPTION_AND_ERROR_CONTAINMENT_LAW_V1.md",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V3.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V4.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V4.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V5.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V5.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V6.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V6.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V7.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V2.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V3.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V2.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_AND_MISTAKE_PREVENTION_TEMPLATE_V3.json",
    "canonical/governance/MISTAKE_PREVENTION_RECEIPT_SCHEMA_V1.json",
    "canonical/runtime/enforce_goal_hierarchy.py",
    ".github/workflows/drift-immunity-guard.yml",
}
GOVERNANCE_ACTIONS={
    "GOVERNANCE_GUARD",
    "USER_AUTHORIZED_GOVERNANCE_STRATEGY_PROMOTION",
}
REAL_TASK_ACTIONS={
    "REAL_CAPABILITY_ACQUISITION",
    "REAL_TASK_EXECUTION",
    "CAPABILITY_INHERITANCE",
    "FRESH_REUSE",
}
ALLOWED_NO_PROBE_ACTIONS=GOVERNANCE_ACTIONS|REAL_TASK_ACTIONS|{
    "RECONCILE_FRONTIER",
    "ORTHOGONAL_PROBE_SELECTION",
    "EVIDENCE_PRESERVATION",
}
OBS_DELETION_ORDER=("DELETE","BYPASS","REUSE","SUBSTITUTE","COMPOSE","REPAIR","BUILD")
ROUTE_FRONTIER_MAX_AGE_HOURS=24
ROUTE_FRONTIER_SOURCE_CLASSES={"BRAIN_INHERITED","OFFICIAL_PRIMARY","CODE_OR_PACKAGE_REGISTRY","BROAD_WEB_OR_COMMUNITY"}
ROUTE_FRONTIER_QUERY_INTENTS={"CAPABILITY_VECTOR","SUPPLIER_OR_PRODUCT","IMPLEMENTATION_FORM","RECENCY_OR_NEW_RELEASE"}
ROUTE_FRONTIER_COMPARISON_DIMENSIONS={"CORRECTNESS","CAPABILITY_STRENGTH","WALL_CLOCK","INCREMENTAL_COST","RELIABILITY","VERIFIABILITY"}
ROUTE_FRONTIER_REFRESH_TRIGGERS={"BEFORE_EXPENSIVE_EXECUTION","AFTER_MATERIAL_ROUTE_FAILURE","BEFORE_INFRASTRUCTURE_OR_REPAIR_CONTINUATION","BEFORE_SCARCE_GATE_SPEND"}
ROUTE_FRONTIER_QUALIFICATION_EVIDENCE_CLASSES={"OFFICIAL_PRIMARY","CODE_OR_PACKAGE_REGISTRY","DIRECT_PROBE","INDEPENDENT_VERIFIER"}
ROUTE_FRONTIER_DISCOVERY_EXEMPT_ACTIONS=GOVERNANCE_ACTIONS|{"RECONCILE_FRONTIER","EVIDENCE_PRESERVATION"}
OBS_REQUIRED_FIELDS=(
    "canonical_generation_or_commit",
    "canonical_base_commit",
    "real_outcome",
    "required_capability",
    "obs_goal",
    "obs_capability",
    "obs_blocker",
    "obs_solution",
    "obs_verification",
    "obs_inherited_system",
    "obs_obs",
    "routes_considered",
    "deleted_or_bypassed_paths",
    "selected_surviving_route",
    "why_selected_route_is_fastest_sufficient",
    "expected_parent_level_state_change",
    "stop_condition",
    "route_frontier",
)
OBS_LAYER_REQUIRED={
    "obs_goal":("real_outcome","proxy_goals_deleted","surviving_necessity"),
    "obs_capability":("existing_inherited_routes_checked","external_existing_routes_checked","capability_work_deleted","surviving_gap"),
    "obs_blocker":("intrinsic_or_path_specific","delete_bypass_substitute_options","surviving_causal_blocker"),
    "obs_solution":("deletion_first_order_applied","routes_ranked","losing_routes_reason","implementation_still_necessary"),
    "obs_verification":("direct_real_effect_verification_considered","existing_oracle_considered","synthetic_verification_necessity"),
    "obs_inherited_system":("downstream_work_to_delete_or_supersede","adjacent_capabilities_absorbed","fresh_reuse_plan"),
    "obs_obs":("analysis_steps_deleted_or_cached","search_stop_decision","affected_layers_only_on_revalidation"),
}
MISTAKE_FAILURE_DEFAULT="PRESUME_CONSEQUENTIAL_ACTION_WRONG_UNTIL_FALSIFIED"
MISTAKE_ALLOWED_CLAIM_SCOPES={
    "NO_PROMOTION","GOVERNANCE_HARDENING_NO_CAPABILITY_PROMOTION",
    "REAL_TASK_EVIDENCE","RESIDUAL_GAP_LOCALIZATION",
    "CAPABILITY_ACQUISITION","FRONTIER_DEPENDENCY_REMOVAL",
}
MISTAKE_PROMOTION_SCOPES={"CAPABILITY_ACQUISITION","FRONTIER_DEPENDENCY_REMOVAL"}
MISTAKE_PREMORTEM_FIELDS=("failure_mode","detection","prevention","abort_or_rollback")
COUPLED_CORE_STATE_PATHS={
    "canonical/CANONICAL_POINTER.json",
    "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json",
    "canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json",
    "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json",
}
SCOREBOARD_PATH="canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"
SCORE_SCOPE_ALLOWED={
    "reusable_capabilities_inherited":{"CAPABILITY_ACQUISITION","FRONTIER_DEPENDENCY_REMOVAL"},
    "verified_real_tasks_completed":{"REAL_TASK_EVIDENCE","CAPABILITY_ACQUISITION","FRONTIER_DEPENDENCY_REMOVAL"},
    "fresh_reuse_passes":{"CAPABILITY_ACQUISITION","FRONTIER_DEPENDENCY_REMOVAL"},
    "frontier_dependencies_removed":{"FRONTIER_DEPENDENCY_REMOVAL"},
    "residual_gaps_localized":{"RESIDUAL_GAP_LOCALIZATION","REAL_TASK_EVIDENCE","CAPABILITY_ACQUISITION","FRONTIER_DEPENDENCY_REMOVAL"},
}
FAIL=[]

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def fail(msg):
    FAIL.append(msg)

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()

def changed_files(base,head):
    out=git("diff","--name-only",f"{base}...{head}")
    return [x for x in out.splitlines() if x.strip()]

def added_diff(base,head,path):
    try:
        return git("diff","--unified=0",f"{base}...{head}","--",path)
    except subprocess.CalledProcessError:
        return ""

def is_sensitive(path):
    return path in SENSITIVE_EXACT or any(path.startswith(p) for p in SENSITIVE_PREFIXES)


def path_exists_at_ref(ref,path):
    proc=subprocess.run(
        ["git","cat-file","-e",f"{ref}:{path}"],
        cwd=ROOT,text=True,capture_output=True,
    )
    return proc.returncode==0

def load_at_ref(ref,path):
    raw=git("show",f"{ref}:{path}")
    return json.loads(raw)

def _nonempty_string(value):
    return isinstance(value,str) and bool(value.strip())

def _contains_placeholder(value):
    if isinstance(value,str):
        return "__REQUIRED_" in value or "__MUST_MATCH_" in value
    if isinstance(value,list):
        return any(_contains_placeholder(x) for x in value)
    if isinstance(value,dict):
        return any(_contains_placeholder(x) for x in value.values())
    return False

def _parse_utc_timestamp(value):
    if not _nonempty_string(value):
        raise ValueError("empty")
    raw=value.strip()
    if raw.endswith("Z"):
        raw=raw[:-1]+"+00:00"
    dt=datetime.fromisoformat(raw)
    if dt.tzinfo is None or dt.utcoffset()!=timedelta(0):
        raise ValueError("not_utc")
    return dt.astimezone(timezone.utc)

def _nonempty_string_list(value):
    return isinstance(value,list) and bool(value) and all(_nonempty_string(x) for x in value)

def enforce_live_route_frontier(intent,obs):
    frontier=obs.get("route_frontier")
    if not isinstance(frontier,dict):
        fail("LIVE_CHALLENGER_FRONTIER_MISSING")
        return

    required=frontier.get("discovery_required")
    if not isinstance(required,bool):
        fail("LIVE_CHALLENGER_FRONTIER_DISCOVERY_REQUIRED_NOT_BOOLEAN")
        return

    action_kind=str(intent.get("action_kind") or "")
    if required is False:
        if action_kind not in ROUTE_FRONTIER_DISCOVERY_EXEMPT_ACTIONS:
            fail("LIVE_CHALLENGER_FRONTIER_EXEMPTION_NOT_ALLOWED_FOR_ACTION_KIND")
        if not _nonempty_string(frontier.get("not_applicable_reason")):
            fail("LIVE_CHALLENGER_FRONTIER_EXEMPTION_REASON_MISSING")
        return

    try:
        checked=_parse_utc_timestamp(frontier.get("checked_at_utc"))
    except Exception:
        fail("LIVE_CHALLENGER_FRONTIER_CHECKED_AT_INVALID")
        checked=None

    max_age=frontier.get("max_age_hours")
    if not isinstance(max_age,(int,float)) or isinstance(max_age,bool) or not (0 < float(max_age) <= ROUTE_FRONTIER_MAX_AGE_HOURS):
        fail("LIVE_CHALLENGER_FRONTIER_MAX_AGE_INVALID")
        max_age=None

    if checked is not None and max_age is not None:
        age=datetime.now(timezone.utc)-checked
        if age < timedelta(minutes=-5):
            fail("LIVE_CHALLENGER_FRONTIER_TIMESTAMP_IN_FUTURE")
        elif age > timedelta(hours=float(max_age)):
            fail("LIVE_CHALLENGER_FRONTIER_EXPIRED")

    source_classes=frontier.get("source_classes_checked")
    if not isinstance(source_classes,list) or not ROUTE_FRONTIER_SOURCE_CLASSES.issubset(set(source_classes)):
        fail("LIVE_CHALLENGER_FRONTIER_SOURCE_DIVERSITY_INCOMPLETE")

    evidence=frontier.get("source_evidence")
    if not isinstance(evidence,dict):
        fail("LIVE_CHALLENGER_FRONTIER_SOURCE_EVIDENCE_MISSING")
    else:
        for cls in ROUTE_FRONTIER_SOURCE_CLASSES:
            values=evidence.get(cls)
            if not _nonempty_string_list(values):
                fail("LIVE_CHALLENGER_FRONTIER_SOURCE_EVIDENCE_EMPTY:"+cls)

    query_families=frontier.get("query_families")
    if not isinstance(query_families,list) or len(query_families)<4:
        fail("LIVE_CHALLENGER_FRONTIER_QUERY_DIVERSITY_INCOMPLETE")
    else:
        intents=set()
        queries=[]
        for item in query_families:
            if not isinstance(item,dict) or not _nonempty_string(item.get("intent")) or not _nonempty_string(item.get("query")):
                fail("LIVE_CHALLENGER_FRONTIER_QUERY_ENTRY_INVALID")
                continue
            intents.add(str(item["intent"]))
            queries.append(str(item["query"]).strip().casefold())
        if not ROUTE_FRONTIER_QUERY_INTENTS.issubset(intents):
            fail("LIVE_CHALLENGER_FRONTIER_QUERY_INTENTS_INCOMPLETE")
        if len(set(queries))!=len(queries):
            fail("LIVE_CHALLENGER_FRONTIER_QUERY_FAMILIES_NOT_DISTINCT")

    dimensions=frontier.get("comparison_dimensions")
    if not isinstance(dimensions,list) or not ROUTE_FRONTIER_COMPARISON_DIMENSIONS.issubset(set(dimensions)):
        fail("LIVE_CHALLENGER_FRONTIER_COMPARISON_DIMENSIONS_INCOMPLETE")

    triggers=frontier.get("refresh_triggers")
    if not isinstance(triggers,list) or not ROUTE_FRONTIER_REFRESH_TRIGGERS.issubset(set(triggers)):
        fail("LIVE_CHALLENGER_FRONTIER_REFRESH_TRIGGERS_INCOMPLETE")

    unresolved=frontier.get("unresolved_plausible_dominators")
    if not isinstance(unresolved,list):
        fail("LIVE_CHALLENGER_FRONTIER_UNRESOLVED_DOMINATORS_NOT_LIST")
    elif unresolved:
        fail("LIVE_CHALLENGER_FRONTIER_UNRESOLVED_PLAUSIBLE_DOMINATOR")

    selected=frontier.get("selected_route")
    if not _nonempty_string(selected):
        fail("LIVE_CHALLENGER_FRONTIER_SELECTED_ROUTE_MISSING")
    elif selected!=obs.get("selected_surviving_route"):
        fail("LIVE_CHALLENGER_FRONTIER_SELECTED_ROUTE_MISMATCH")

    if not _nonempty_string(frontier.get("incumbent_route")):
        fail("LIVE_CHALLENGER_FRONTIER_INCUMBENT_ROUTE_MISSING")

    challengers=frontier.get("challenger_routes")
    if not isinstance(challengers,list):
        fail("LIVE_CHALLENGER_FRONTIER_CHALLENGERS_NOT_LIST")
        challengers=[]
    if not challengers and not _nonempty_string(frontier.get("negative_search_summary")):
        fail("LIVE_CHALLENGER_FRONTIER_NO_CHALLENGER_WITHOUT_NEGATIVE_SEARCH_SUMMARY")

    for i,item in enumerate(challengers):
        if not isinstance(item,dict):
            fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_INVALID:{i}")
            continue
        if not _nonempty_string(item.get("route")):
            fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_ROUTE_MISSING:{i}")
        if not _nonempty_string_list(item.get("evidence")):
            fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_EVIDENCE_MISSING:{i}")
        if not _nonempty_string_list(item.get("qualification_evidence")):
            fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_QUALIFICATION_EVIDENCE_MISSING:{i}")
        qualification_classes=item.get("qualification_evidence_classes")
        if not isinstance(qualification_classes,list) or not set(qualification_classes).intersection(ROUTE_FRONTIER_QUALIFICATION_EVIDENCE_CLASSES):
            fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_QUALIFICATION_SOURCE_INVALID:{i}")
        resolution=str(item.get("resolution") or "")
        if resolution not in {"SELECTED","NON_DOMINATING","DISQUALIFIED"}:
            fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_UNRESOLVED:{i}")
        comparison=item.get("comparison")
        if not isinstance(comparison,dict):
            fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_COMPARISON_MISSING:{i}")
        else:
            missing=[d for d in ROUTE_FRONTIER_COMPARISON_DIMENSIONS if not _nonempty_string(comparison.get(d))]
            if missing:
                fail(f"LIVE_CHALLENGER_FRONTIER_CHALLENGER_COMPARISON_INCOMPLETE:{i}:"+",".join(sorted(missing)))

def enforce_recursive_obs(intent,files,base):
    bootstrap_path="canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V1.md"
    bootstrap=(
        bool(intent.get("governance_change"))
        and bool(intent.get("user_authorized_governance_change"))
        and bootstrap_path in files
        and not path_exists_at_ref(base,bootstrap_path)
    )
    if bootstrap:
        return

    obs=intent.get("recursive_obs")
    if not isinstance(obs,dict):
        fail("RECURSIVE_OBS_RECEIPT_MISSING")
        return

    if _contains_placeholder(obs):
        fail("RECURSIVE_OBS_TEMPLATE_PLACEHOLDER_PRESENT")

    missing=[k for k in OBS_REQUIRED_FIELDS if k not in obs]
    if missing:
        fail("RECURSIVE_OBS_RECEIPT_INCOMPLETE:"+",".join(missing))
        return

    bound=str(obs.get("canonical_generation_or_commit") or "")
    intent_generation=str(intent.get("canonical_generation") or "")
    if not bound or bound!=intent_generation:
        fail("RECURSIVE_OBS_GENERATION_BINDING_MISMATCH")

    exact_base=str(obs.get("canonical_base_commit") or "").lower()
    actual_base=str(base or "").lower()
    if len(exact_base)!=40 or any(ch not in "0123456789abcdef" for ch in exact_base):
        fail("RECURSIVE_OBS_BASE_COMMIT_INVALID")
    elif exact_base!=actual_base:
        fail("RECURSIVE_OBS_STALE_BASE_COMMIT")

    for field in (
        "real_outcome","required_capability","selected_surviving_route",
        "why_selected_route_is_fastest_sufficient",
        "expected_parent_level_state_change","stop_condition",
    ):
        if not _nonempty_string(obs.get(field)):
            fail("RECURSIVE_OBS_EMPTY_REQUIRED_FIELD:"+field)

    if obs.get("expected_parent_level_state_change")!=intent.get("expected_parent_frontier_change"):
        fail("RECURSIVE_OBS_PARENT_CHANGE_MISMATCH")
    if obs.get("stop_condition")!=intent.get("stop_condition"):
        fail("RECURSIVE_OBS_STOP_CONDITION_MISMATCH")

    considered=obs.get("routes_considered")
    if not isinstance(considered,list) or not considered:
        fail("RECURSIVE_OBS_ROUTE_RACE_MISSING")
    deleted=obs.get("deleted_or_bypassed_paths")
    if not isinstance(deleted,list):
        fail("RECURSIVE_OBS_DELETED_PATHS_NOT_LIST")

    for layer,required in OBS_LAYER_REQUIRED.items():
        payload=obs.get(layer)
        if not isinstance(payload,dict) or not payload:
            fail("RECURSIVE_OBS_LAYER_MISSING:"+layer)
            continue
        absent=[key for key in required if key not in payload]
        if absent:
            fail("RECURSIVE_OBS_LAYER_INCOMPLETE:"+layer+":"+",".join(absent))

    solution=obs.get("obs_solution") if isinstance(obs.get("obs_solution"),dict) else {}
    if tuple(solution.get("deletion_first_order_applied") or ())!=OBS_DELETION_ORDER:
        fail("RECURSIVE_OBS_DELETION_FIRST_ORDER_MISMATCH")
    if not isinstance(solution.get("routes_ranked"),list) or not solution.get("routes_ranked"):
        fail("RECURSIVE_OBS_RANKED_ROUTES_MISSING")
    if not isinstance(solution.get("implementation_still_necessary"),bool):
        fail("RECURSIVE_OBS_IMPLEMENTATION_NECESSITY_NOT_BOOLEAN")

    verification=obs.get("obs_verification") if isinstance(obs.get("obs_verification"),dict) else {}
    if verification.get("direct_real_effect_verification_considered") is not True:
        fail("RECURSIVE_OBS_DIRECT_VERIFICATION_NOT_CONSIDERED")
    if verification.get("existing_oracle_considered") is not True:
        fail("RECURSIVE_OBS_EXISTING_ORACLE_NOT_CONSIDERED")

    meta=obs.get("obs_obs") if isinstance(obs.get("obs_obs"),dict) else {}
    if meta.get("affected_layers_only_on_revalidation") is not True:
        fail("RECURSIVE_OBS_AFFECTED_LAYER_REVALIDATION_NOT_ENABLED")
    if not _nonempty_string(meta.get("search_stop_decision")):
        fail("RECURSIVE_OBS_SEARCH_STOP_DECISION_MISSING")

    enforce_live_route_frontier(intent,obs)


def _nonempty_list(value):
    return isinstance(value,list) and bool(value)

def _supplier_set(value):
    if not isinstance(value,list):
        return set()
    return {str(x).strip() for x in value if str(x).strip()}

def enforce_mistake_prevention(intent,files,base,head):
    mp=intent.get("mistake_prevention")
    if not isinstance(mp,dict):
        fail("MISTAKE_PREVENTION_RECEIPT_MISSING")
        return
    if _contains_placeholder(mp):
        fail("MISTAKE_PREVENTION_TEMPLATE_PLACEHOLDER_PRESENT")

    required=(
        "schema","failure_default","claim_scope","pre_mortem","circularity_check",
        "independence_check","state_transition","evidence_claim_map",
        "post_action_checks","rollback_triggers","residual_uncertainty",
    )
    missing=[k for k in required if k not in mp]
    if missing:
        fail("MISTAKE_PREVENTION_RECEIPT_INCOMPLETE:"+",".join(missing))
        return

    if mp.get("schema")!="PROJECT_BRAIN_MISTAKE_PREVENTION_RECEIPT_V1":
        fail("MISTAKE_PREVENTION_SCHEMA_INVALID")
    if mp.get("failure_default")!=MISTAKE_FAILURE_DEFAULT:
        fail("MISTAKE_PREVENTION_FAILURE_DEFAULT_INVALID")

    claim_scope=str(mp.get("claim_scope") or "")
    if claim_scope not in MISTAKE_ALLOWED_CLAIM_SCOPES:
        fail("MISTAKE_PREVENTION_CLAIM_SCOPE_INVALID")

    premortem=mp.get("pre_mortem")
    if not isinstance(premortem,list) or len(premortem)<3:
        fail("MISTAKE_PREVENTION_PREMORTEM_TOO_SMALL")
    else:
        modes=[]
        for i,item in enumerate(premortem):
            if not isinstance(item,dict):
                fail(f"MISTAKE_PREVENTION_PREMORTEM_ENTRY_INVALID:{i}")
                continue
            absent=[k for k in MISTAKE_PREMORTEM_FIELDS if not _nonempty_string(item.get(k))]
            if absent:
                fail(f"MISTAKE_PREVENTION_PREMORTEM_ENTRY_INCOMPLETE:{i}:"+",".join(absent))
            modes.append(str(item.get("failure_mode") or "").strip().casefold())
        if len([x for x in modes if x])!=len(set(x for x in modes if x)):
            fail("MISTAKE_PREVENTION_PREMORTEM_DUPLICATE_FAILURE_MODES")

    circular=mp.get("circularity_check")
    if not isinstance(circular,dict):
        fail("MISTAKE_PREVENTION_CIRCULARITY_CHECK_MISSING")
        circular={}
    for key in (
        "target_frontier_implementation_in_execution_path",
        "target_frontier_implementation_in_verification_path",
        "proof_depends_on_claim_being_proven",
    ):
        if not isinstance(circular.get(key),bool):
            fail("MISTAKE_PREVENTION_CIRCULARITY_BOOLEAN_MISSING:"+key)

    indep=mp.get("independence_check")
    if not isinstance(indep,dict):
        fail("MISTAKE_PREVENTION_INDEPENDENCE_CHECK_MISSING")
        indep={}
    if indep.get("self_certification_allowed") is not False:
        fail("MISTAKE_PREVENTION_SELF_CERTIFICATION_NOT_FORBIDDEN")
    if not isinstance(indep.get("producer_verifier_independent"),bool):
        fail("MISTAKE_PREVENTION_PRODUCER_VERIFIER_INDEPENDENCE_NOT_BOOLEAN")
    if not _nonempty_string(indep.get("verifier_identity")):
        fail("MISTAKE_PREVENTION_VERIFIER_IDENTITY_MISSING")
    if not isinstance(indep.get("target_supplier_excluded_from_proof_path"),bool):
        fail("MISTAKE_PREVENTION_TARGET_SUPPLIER_EXCLUSION_NOT_BOOLEAN")

    if claim_scope in MISTAKE_PROMOTION_SCOPES:
        if circular.get("target_frontier_implementation_in_execution_path") is not False:
            fail("MISTAKE_PREVENTION_CIRCULAR_FRONTIER_EXECUTION")
        if circular.get("target_frontier_implementation_in_verification_path") is not False:
            fail("MISTAKE_PREVENTION_CIRCULAR_FRONTIER_VERIFICATION")
        if circular.get("proof_depends_on_claim_being_proven") is not False:
            fail("MISTAKE_PREVENTION_CIRCULAR_PROOF_DEPENDENCY")
        if indep.get("producer_verifier_independent") is not True:
            fail("MISTAKE_PREVENTION_PROMOTION_NOT_INDEPENDENT")
        if indep.get("target_supplier_excluded_from_proof_path") is not True:
            fail("MISTAKE_PREVENTION_TARGET_SUPPLIER_NOT_EXCLUDED")
        target_suppliers=_supplier_set(indep.get("target_frontier_supplier_ids"))
        execution_suppliers=_supplier_set(indep.get("execution_supplier_ids"))
        verification_suppliers=_supplier_set(indep.get("verification_supplier_ids"))
        if not target_suppliers:
            fail("MISTAKE_PREVENTION_PROMOTION_TARGET_SUPPLIER_IDS_MISSING")
        if not execution_suppliers:
            fail("MISTAKE_PREVENTION_PROMOTION_EXECUTION_SUPPLIER_IDS_MISSING")
        if not verification_suppliers:
            fail("MISTAKE_PREVENTION_PROMOTION_VERIFICATION_SUPPLIER_IDS_MISSING")
        if target_suppliers.intersection(execution_suppliers):
            fail("MISTAKE_PREVENTION_TARGET_SUPPLIER_IN_EXECUTION_SET")
        if target_suppliers.intersection(verification_suppliers):
            fail("MISTAKE_PREVENTION_TARGET_SUPPLIER_IN_VERIFICATION_SET")
        if execution_suppliers.intersection(verification_suppliers):
            fail("MISTAKE_PREVENTION_PRODUCER_VERIFIER_SUPPLIER_OVERLAP")

    state=mp.get("state_transition")
    if not isinstance(state,dict):
        fail("MISTAKE_PREVENTION_STATE_TRANSITION_MISSING")
        state={}
    if state.get("exact_head_readback_required") is not True:
        fail("MISTAKE_PREVENTION_EXACT_HEAD_READBACK_NOT_REQUIRED")
    if not _nonempty_string_list(state.get("expected_invariants")):
        fail("MISTAKE_PREVENTION_EXPECTED_INVARIANTS_MISSING")
    if not _nonempty_string_list(state.get("expected_deltas")):
        fail("MISTAKE_PREVENTION_EXPECTED_DELTAS_MISSING")

    changed_core=sorted(set(files).intersection(COUPLED_CORE_STATE_PATHS))
    if len(changed_core)>1:
        if state.get("atomic_update_required") is not True:
            fail("MISTAKE_PREVENTION_COUPLED_STATE_ATOMIC_REQUIRED")
        if state.get("strategy")!="ATOMIC_SINGLE_TREE_COMMIT":
            fail("MISTAKE_PREVENTION_COUPLED_STATE_STRATEGY_INVALID")
        final_files=set(git("diff-tree","--no-commit-id","--name-only","-r",head).splitlines())
        missing_final=[p for p in changed_core if p not in final_files]
        if missing_final:
            fail("MISTAKE_PREVENTION_COUPLED_STATE_NOT_ATOMIC_FINAL_COMMIT:"+",".join(missing_final))

    claims=mp.get("evidence_claim_map")
    if not isinstance(claims,list) or not claims:
        fail("MISTAKE_PREVENTION_EVIDENCE_CLAIM_MAP_MISSING")
    else:
        for i,item in enumerate(claims):
            if not isinstance(item,dict) or not _nonempty_string(item.get("claim")) or not _nonempty_string_list(item.get("evidence")) or not _nonempty_string(item.get("strength")):
                fail(f"MISTAKE_PREVENTION_EVIDENCE_CLAIM_ENTRY_INVALID:{i}")

    if not _nonempty_string_list(mp.get("post_action_checks")):
        fail("MISTAKE_PREVENTION_POST_ACTION_CHECKS_MISSING")
    if not _nonempty_string_list(mp.get("rollback_triggers")):
        fail("MISTAKE_PREVENTION_ROLLBACK_TRIGGERS_MISSING")
    if not _nonempty_string(mp.get("residual_uncertainty")):
        fail("MISTAKE_PREVENTION_RESIDUAL_UNCERTAINTY_MISSING")

    if SCOREBOARD_PATH in files and path_exists_at_ref(base,SCOREBOARD_PATH):
        try:
            old=load_at_ref(base,SCOREBOARD_PATH).get("counters_since_epoch_start") or {}
            new=load(SCOREBOARD_PATH).get("counters_since_epoch_start") or {}
        except Exception as exc:
            fail("MISTAKE_PREVENTION_SCOREBOARD_DELTA_READ_FAILED:"+type(exc).__name__)
            old={}; new={}
        increases=[]
        decreases=[]
        for key in sorted(set(old)|set(new)):
            try:
                before=int(old.get(key,0)); after=int(new.get(key,0))
            except Exception:
                fail("MISTAKE_PREVENTION_SCOREBOARD_COUNTER_NONINTEGER:"+key)
                continue
            if after>before:
                increases.append((key,before,after))
                if claim_scope not in SCORE_SCOPE_ALLOWED.get(key,set()):
                    fail("MISTAKE_PREVENTION_CLAIM_SCOPE_TOO_WEAK_FOR_COUNTER:"+key)
            elif after<before:
                decreases.append((key,before,after))

        if decreases:
            if mp.get("counter_rollback_authorized") is not True or not _nonempty_string(mp.get("counter_rollback_reason")):
                fail("MISTAKE_PREVENTION_COUNTER_DECREASE_WITHOUT_ROLLBACK_AUTHORIZATION")

        if increases:
            pe=mp.get("promotion_evidence")
            if not isinstance(pe,dict):
                fail("MISTAKE_PREVENTION_PROMOTION_EVIDENCE_MISSING")
                pe={}
            paths=pe.get("evidence_paths")
            if not _nonempty_string_list(paths):
                fail("MISTAKE_PREVENTION_PROMOTION_EVIDENCE_PATHS_MISSING")
                paths=[]
            for p in paths:
                if not path_exists_at_ref(head,p):
                    fail("MISTAKE_PREVENTION_PROMOTION_EVIDENCE_PATH_MISSING_AT_HEAD:"+p)
            if not _nonempty_string(pe.get("independent_verifier_id")):
                fail("MISTAKE_PREVENTION_PROMOTION_INDEPENDENT_VERIFIER_MISSING")
            producers=_supplier_set(pe.get("producer_supplier_ids"))
            verifiers=_supplier_set(pe.get("verifier_supplier_ids"))
            if not producers or not verifiers:
                fail("MISTAKE_PREVENTION_PROMOTION_SUPPLIER_IDS_MISSING")
            if pe.get("supplier_independent") is not True or producers.intersection(verifiers):
                fail("MISTAKE_PREVENTION_PROMOTION_SUPPLIER_INDEPENDENCE_FAIL")
            if any(k=="frontier_dependencies_removed" for k,_,_ in increases):
                for field in ("replacement_route_id","frontier_reference_id","fresh_reuse_evidence_path"):
                    if not _nonempty_string(pe.get(field)):
                        fail("MISTAKE_PREVENTION_FRONTIER_REMOVAL_FIELD_MISSING:"+field)
                fresh=pe.get("fresh_reuse_evidence_path")
                if _nonempty_string(fresh) and not path_exists_at_ref(head,fresh):
                    fail("MISTAKE_PREVENTION_FRONTIER_REMOVAL_FRESH_REUSE_EVIDENCE_MISSING")


def blocker_lease_key(intent):
    parts=[
        str(intent.get("canonical_generation") or ""),
        str(intent.get("capability_target") or ""),
        str(intent.get("causal_blocker") or ""),
        str(intent.get("action_kind") or ""),
    ]
    return "::".join(parts)

def _github_json(path):
    token=os.environ.get("GITHUB_TOKEN")
    repo=os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        raise RuntimeError("GITHUB_DEDUPE_CONTEXT_MISSING")
    req=urllib.request.Request(
        "https://api.github.com"+path,
        headers={
            "Authorization":"Bearer "+token,
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28",
            "User-Agent":"ProjectBrain-DriftGuard/1",
        },
    )
    with urllib.request.urlopen(req,timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _open_pr_intents():
    repo=os.environ.get("GITHUB_REPOSITORY")
    current=int(os.environ.get("CURRENT_PR_NUMBER") or "0")
    if not repo or not os.environ.get("GITHUB_TOKEN") or current<=0:
        return []
    prs=_github_json(f"/repos/{repo}/pulls?state=open&per_page=100")
    out=[]
    for pr in prs:
        number=int(pr.get("number") or 0)
        if number==current:
            continue
        files=_github_json(f"/repos/{repo}/pulls/{number}/files?per_page=100")
        for item in files:
            path=str(item.get("filename") or "")
            if not (path.startswith("canonical/action_intents/") and path.endswith(".json")):
                continue
            if item.get("status")=="removed":
                continue
            ref=str((pr.get("head") or {}).get("sha") or "")
            encoded=urllib.parse.quote(path,safe="/")
            try:
                payload=_github_json(f"/repos/{repo}/contents/{encoded}?ref={urllib.parse.quote(ref,safe='')}")
                raw=base64.b64decode(payload.get("content") or b"")
                intent=json.loads(raw.decode("utf-8"))
            except Exception as exc:
                raise RuntimeError(f"OPEN_PR_INTENT_READ_FAILED:{number}:{path}:{type(exc).__name__}") from exc
            out.append({"pr":number,"path":path,"intent":intent})
    return out

def enforce_blocker_lease(intent):
    expected=blocker_lease_key(intent)
    actual=str(intent.get("blocker_lease_key") or "")
    if actual!=expected:
        fail("BLOCKER_LEASE_KEY_MISSING_OR_MISMATCH")
        return
    try:
        peers=_open_pr_intents()
    except Exception as exc:
        fail("BLOCKER_LEASE_DEDUPE_CHECK_FAILED:"+str(exc))
        return
    for peer in peers:
        other=peer["intent"]
        if blocker_lease_key(other)!=expected:
            continue
        if str(other.get("blocker_lease_key") or "")!=expected:
            continue
        if bool(intent.get("intentional_route_race")) and bool(other.get("intentional_route_race")):
            race_a=str(intent.get("route_race_id") or "")
            race_b=str(other.get("route_race_id") or "")
            if race_a and race_a==race_b:
                continue
        fail(f"DUPLICATE_BLOCKER_LEASE_OPEN_PR:{peer['pr']}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True)
    ap.add_argument("--head",default="HEAD")
    ns=ap.parse_args()

    files=changed_files(ns.base,ns.head)
    sensitive=[x for x in files if is_sensitive(x)]
    if not sensitive:
        print("DRIFT_GUARD_PASS no frontier-sensitive changes")
        return 0

    pointer=load("canonical/CANONICAL_POINTER.json")
    hierarchy=load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
    queue=load("canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json")

    intents=[
        x for x in files
        if x.startswith("canonical/action_intents/") and x.endswith(".json")
    ]
    if not intents:
        fail("ACTION_INTENT_MISSING")
        intents=[]
    if len(intents)>1:
        fail("MULTIPLE_ACTION_INTENTS_IN_ONE_PR")
    intent=load(intents[0]) if intents else {}

    if intent:
        enforce_blocker_lease(intent)
        enforce_recursive_obs(intent,files,ns.base)
        enforce_mistake_prevention(intent,files,ns.base,ns.head)

    terminal=str(pointer.get("mission_lock",{}).get("terminal_objective") or "")
    if hierarchy.get("terminal_objective")!=terminal:
        fail("HIERARCHY_TERMINAL_OBJECTIVE_MISMATCH")
    if intent.get("terminal_objective")!=terminal:
        fail("INTENT_TERMINAL_OBJECTIVE_MISMATCH")

    program=str(pointer.get("current_frontier",{}).get("program") or "")
    if hierarchy.get("active_program")!=program:
        fail("HIERARCHY_ACTIVE_PROGRAM_MISMATCH")
    if intent.get("active_program")!=program:
        fail("INTENT_ACTIVE_PROGRAM_MISMATCH")

    selected=(queue.get("immediate_frontier") or {}).get("selected_capability")
    htarget=hierarchy.get("active_capability_target")
    if selected and selected!=htarget:
        fail("QUEUE_HIERARCHY_CAPABILITY_TARGET_MISMATCH")
    action_kind=str(intent.get("action_kind") or "")
    governance_action=action_kind in GOVERNANCE_ACTIONS and bool(intent.get("governance_change"))
    if not governance_action and intent.get("capability_target")!=htarget:
        fail("INTENT_CAPABILITY_TARGET_MISMATCH")
    if governance_action and intent.get("user_authorized_governance_change") is not True:
        fail("USER_AUTHORIZED_GOVERNANCE_CHANGE_REQUIRED")

    if not intent.get("expected_parent_frontier_change"):
        fail("PARENT_LEVEL_STATE_CHANGE_MISSING")
    if intent.get("highest_leverage_now") is not True:
        fail("ACTION_NOT_ASSERTED_HIGHEST_LEVERAGE")
    if not intent.get("stop_condition"):
        fail("STOP_CONDITION_MISSING")

    probe=intent.get("probe_id")
    active_probe=hierarchy.get("active_probe")
    quarantined={
        str(x.get("probe_id"))
        for x in hierarchy.get("quarantined_probes",[])
        if x.get("may_define_frontier") is False
    }
    if not governance_action:
        if action_kind in REAL_TASK_ACTIONS:
            if probe:
                fail("REAL_TASK_ACTION_MUST_NOT_TARGET_SYNTHETIC_PROBE")
            if active_probe is not None:
                fail("REAL_TASK_ACTION_WHILE_ACTIVE_PROBE_NOT_RECONCILED")
        else:
            if probe and str(probe) in quarantined:
                fail("QUARANTINED_PROBE_CANNOT_DEFINE_NEW_ACTION")
            if probe and active_probe and probe!=active_probe:
                fail("INTENT_PROBE_NOT_ACTIVE_PROBE")
            if probe and active_probe is None and action_kind not in {"ORTHOGONAL_PROBE_SELECTION","RECONCILE_FRONTIER"}:
                fail("NO_ACTIVE_PROBE_BUT_ACTION_TARGETS_PROBE")
            if not probe and action_kind not in ALLOWED_NO_PROBE_ACTIONS:
                fail("PROBE_REQUIRED_FOR_THIS_ACTION_KIND")

    probe_specific=bool(intent.get("probe_specific"))
    one_probe_repair=bool(intent.get("generic_repair_from_single_probe"))
    recurrence=int(intent.get("orthogonal_recurrence_count") or 0)
    precommitted=bool(intent.get("precommitted_acceptance_gate_exception"))
    budget=hierarchy.get("probe_budget") or {}
    used=int(budget.get("repairs_used_on_active_probe") or 0)
    max_repairs=int(budget.get("max_repairs_from_single_probe") or 1)
    if one_probe_repair and used>=max_repairs and recurrence<2 and not precommitted:
        fail("SECOND_REPAIR_FROM_SINGLE_PROBE_FORBIDDEN")
    if probe_specific and recurrence<2 and not precommitted:
        fail("PROBE_SPECIFIC_REPAIR_REQUIRES_ORTHOGONAL_RECURRENCE")

    literals=[str(x).lower() for x in intent.get("probe_specific_literals",[]) if str(x).strip()]
    if probe_specific and not literals:
        fail("PROBE_SPECIFIC_ACTION_MUST_DECLARE_PROBE_LITERALS")
    runtime_changes=[x for x in sensitive if x.startswith("canonical/runtime/")]
    for path in runtime_changes:
        diff=added_diff(ns.base,ns.head,path).lower()
        added="\n".join(
            line[1:] for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        for lit in literals:
            if lit and lit in added:
                fail(f"PROBE_LITERAL_CONTAMINATION:{path}:{lit}")

    governance_change=any(x in PROTECTED_GUARD_PATHS for x in files)
    if governance_change and intent.get("governance_change") is not True:
        fail("GUARD_CHANGE_WITHOUT_GOVERNANCE_INTENT")
    if governance_change and intent.get("weakens_existing_guard") is True:
        auth=str(intent.get("explicit_user_authorization") or "").lower()
        if "weaken" not in auth and "disable" not in auth:
            fail("GUARD_WEAKENING_WITHOUT_EXPLICIT_USER_AUTHORIZATION")

    non_intent_sensitive=[
        x for x in sensitive if not x.startswith("canonical/action_intents/")
    ]
    if len(non_intent_sensitive)>15 and action_kind!="GOVERNANCE_GUARD":
        fail("FRONTIER_PR_SCOPE_TOO_BROAD_RECONCILE_AND_SPLIT")

    expected_generation=str(intent.get("canonical_generation") or "")
    actual_generation=str(pointer.get("canonical_generation") or "")
    if expected_generation!=actual_generation:
        fail("CANONICAL_GENERATION_MISMATCH")

    if FAIL:
        print("DRIFT_GUARD_FAIL")
        for item in FAIL:
            print(" -",item)
        return 1

    digest=hashlib.sha256(terminal.encode()).hexdigest()
    print("DRIFT_GUARD_PASS")
    print(" terminal_objective_sha256",digest)
    print(" capability_target",htarget)
    print(" action_id",intent.get("action_id"))
    print(" sensitive_files",len(non_intent_sensitive))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
