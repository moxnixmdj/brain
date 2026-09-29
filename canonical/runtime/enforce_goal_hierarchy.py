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
    "canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V3.md",
    "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V2.md",
    "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V3.md",
    "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V4.md",
    "canonical/laws/ADVERSARIAL_ERROR_CONTROL_LAW_V1.md",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V3.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V4.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V4.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V5.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V5.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V6.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V6.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V7.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V7.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V8.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V2.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V3.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V4.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V2.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V3.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V4.json",
    "canonical/governance/ADVERSARIAL_ERROR_CONTROL_SCHEMA_V1.json",
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
ROUTE_PREFLIGHT_MAX_AGE_HOURS=2
ROUTE_PREFLIGHT_VOLATILE_EVIDENCE_CLASSES={"DIRECT_PROBE","INDEPENDENT_VERIFIER"}
ROUTE_PREFLIGHT_DEPENDENCY_EVIDENCE_CLASSES={"OFFICIAL_PRIMARY","CODE_OR_PACKAGE_REGISTRY","DIRECT_PROBE","INDEPENDENT_VERIFIER","BRAIN_INHERITED"}
ROUTE_PREFLIGHT_VOLATILITY={"STATIC","VOLATILE"}
ROUTE_PREFLIGHT_SCOPES={"GLOBAL","ACCOUNT_SPECIFIC","LOCAL","REGION_SPECIFIC"}
ROUTE_PREFLIGHT_KINDS={"CARRIER","ACCOUNT_ENTITLEMENT","MODEL_API","NETWORK_ENDPOINT","REMOTE_SERVICE","CAPACITY_POOL","AUTH_CREDENTIAL","LOCAL_RUNTIME","LOCAL_MODEL","CODE_ARTIFACT","DATA_SOURCE","STORAGE","PACKAGE_REGISTRY","MODEL_ARTIFACT"}
ROUTE_PREFLIGHT_INTRINSIC_VOLATILE_KINDS={"CARRIER","ACCOUNT_ENTITLEMENT","MODEL_API","NETWORK_ENDPOINT","REMOTE_SERVICE","CAPACITY_POOL","AUTH_CREDENTIAL"}
ROUTE_PREFLIGHT_EXECUTION_SUBSTRATE_KINDS={"CARRIER","LOCAL_RUNTIME","MODEL_API","REMOTE_SERVICE"}
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

ADVERSARIAL_REQUIRED_FAILURE_CLASSES={
    "STALE_STATE","TARGET_SUBSTITUTION","PROXY_GOAL","CIRCULAR_PROOF","SELF_CERTIFICATION",
    "NARROW_CAPABILITY_INFLATION","SAME_DOMAIN_REUSE_INFLATION","ROUTE_READINESS",
    "DUPLICATE_EXECUTION","ACTIVITY_AS_PROGRESS","POST_STATE_MISMATCH","HIDDEN_DEPENDENCY",
    "FALSIFIED_ROUTE_REPLAY","SEMANTIC_DUPLICATE_EXECUTION",
}
ADVERSARIAL_CLAIM_LEVELS={
    "GOVERNANCE_ONLY","SUPPORT_ONLY","TASK_EVIDENCE","FRESH_REUSE_PROOF",
    "CAPABILITY_PROMOTION","FRONTIER_DEPENDENCY_REMOVAL",
}
ADVERSARIAL_PROOF_BEARING_LEVELS={
    "FRESH_REUSE_PROOF","CAPABILITY_PROMOTION","FRONTIER_DEPENDENCY_REMOVAL",
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

def enforce_selected_route_preflight(frontier,obs):
    preflight=frontier.get("selected_route_preflight")
    if not isinstance(preflight,dict):
        fail("SELECTED_ROUTE_PREFLIGHT_MISSING")
        return

    try:
        checked=_parse_utc_timestamp(preflight.get("checked_at_utc"))
    except Exception:
        fail("SELECTED_ROUTE_PREFLIGHT_CHECKED_AT_INVALID")
        checked=None

    max_age=preflight.get("max_age_hours")
    if not isinstance(max_age,(int,float)) or isinstance(max_age,bool) or not (0 < float(max_age) <= ROUTE_PREFLIGHT_MAX_AGE_HOURS):
        fail("SELECTED_ROUTE_PREFLIGHT_MAX_AGE_INVALID")
        max_age=None

    if checked is not None and max_age is not None:
        age=datetime.now(timezone.utc)-checked
        if age < timedelta(minutes=-5):
            fail("SELECTED_ROUTE_PREFLIGHT_TIMESTAMP_IN_FUTURE")
        elif age > timedelta(hours=float(max_age)):
            fail("SELECTED_ROUTE_PREFLIGHT_EXPIRED")

    selected=preflight.get("selected_route")
    if not _nonempty_string(selected):
        fail("SELECTED_ROUTE_PREFLIGHT_ROUTE_MISSING")
    elif selected!=frontier.get("selected_route") or selected!=obs.get("selected_surviving_route"):
        fail("SELECTED_ROUTE_PREFLIGHT_ROUTE_MISMATCH")

    if preflight.get("status")!="READY":
        fail("SELECTED_ROUTE_PREFLIGHT_NOT_READY")
    if preflight.get("all_required_dependencies_ready") is not True:
        fail("SELECTED_ROUTE_PREFLIGHT_REQUIRED_DEPENDENCIES_NOT_READY")
    if preflight.get("execution_dependencies_complete") is not True:
        fail("SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_INVENTORY_NOT_ASSERTED_COMPLETE")

    failed=preflight.get("failed_dependencies")
    if not isinstance(failed,list):
        fail("SELECTED_ROUTE_PREFLIGHT_FAILED_DEPENDENCIES_NOT_LIST")
    elif failed:
        fail("SELECTED_ROUTE_PREFLIGHT_FAILED_DEPENDENCY_PRESENT")

    deps=preflight.get("execution_dependencies")
    if not isinstance(deps,list) or not deps:
        fail("SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_INVENTORY_MISSING")
        return

    substrate_seen=False
    for i,dep in enumerate(deps):
        if not isinstance(dep,dict):
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_INVALID:{i}")
            continue
        if not _nonempty_string(dep.get("dependency")):
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_NAME_MISSING:{i}")
        kind=str(dep.get("kind") or "")
        if not kind:
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_KIND_MISSING:{i}")
        elif kind not in ROUTE_PREFLIGHT_KINDS:
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_KIND_INVALID:{i}")
        if kind in ROUTE_PREFLIGHT_EXECUTION_SUBSTRATE_KINDS:
            substrate_seen=True
        required=dep.get("required")
        if not isinstance(required,bool):
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_REQUIRED_NOT_BOOLEAN:{i}")
            required=False
        volatility=str(dep.get("volatility") or "")
        if volatility not in ROUTE_PREFLIGHT_VOLATILITY:
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_VOLATILITY_INVALID:{i}")
        scope=str(dep.get("scope") or "")
        if scope not in ROUTE_PREFLIGHT_SCOPES:
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_SCOPE_INVALID:{i}")
        evidence_scope=str(dep.get("evidence_scope") or "")
        if evidence_scope not in ROUTE_PREFLIGHT_SCOPES:
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_EVIDENCE_SCOPE_INVALID:{i}")
        status=str(dep.get("status") or "")
        if required and status!="READY":
            fail(f"SELECTED_ROUTE_PREFLIGHT_REQUIRED_DEPENDENCY_NOT_READY:{i}")

        evidence=dep.get("evidence")
        if not _nonempty_string_list(evidence):
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_EVIDENCE_MISSING:{i}")
        classes=dep.get("evidence_classes")
        if not isinstance(classes,list) or not classes:
            fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_EVIDENCE_CLASSES_MISSING:{i}")
            class_set=set()
        else:
            class_set=set(classes)
            if not class_set.issubset(ROUTE_PREFLIGHT_DEPENDENCY_EVIDENCE_CLASSES):
                fail(f"SELECTED_ROUTE_PREFLIGHT_DEPENDENCY_EVIDENCE_CLASS_INVALID:{i}")

        if kind in ROUTE_PREFLIGHT_INTRINSIC_VOLATILE_KINDS and volatility!="VOLATILE":
            fail(f"SELECTED_ROUTE_PREFLIGHT_INTRINSIC_VOLATILE_DEPENDENCY_MARKED_STATIC:{i}")

        if required and volatility=="VOLATILE":
            try:
                observed=_parse_utc_timestamp(dep.get("observed_at_utc"))
            except Exception:
                fail(f"SELECTED_ROUTE_PREFLIGHT_VOLATILE_OBSERVED_AT_INVALID:{i}")
                observed=None
            if observed is not None and max_age is not None:
                age=datetime.now(timezone.utc)-observed
                if age < timedelta(minutes=-5):
                    fail(f"SELECTED_ROUTE_PREFLIGHT_VOLATILE_TIMESTAMP_IN_FUTURE:{i}")
                elif age > timedelta(hours=float(max_age)):
                    fail(f"SELECTED_ROUTE_PREFLIGHT_VOLATILE_DEPENDENCY_STALE:{i}")
            if not class_set.intersection(ROUTE_PREFLIGHT_VOLATILE_EVIDENCE_CLASSES):
                fail(f"SELECTED_ROUTE_PREFLIGHT_VOLATILE_DEPENDENCY_LACKS_DIRECT_OR_INDEPENDENT_EVIDENCE:{i}")

        if required and scope in {"ACCOUNT_SPECIFIC","REGION_SPECIFIC"}:
            if not class_set.intersection(ROUTE_PREFLIGHT_VOLATILE_EVIDENCE_CLASSES):
                fail(f"SELECTED_ROUTE_PREFLIGHT_SCOPED_DEPENDENCY_LACKS_DIRECT_OR_INDEPENDENT_EVIDENCE:{i}")
            if evidence_scope!=scope:
                fail(f"SELECTED_ROUTE_PREFLIGHT_SCOPED_DEPENDENCY_EVIDENCE_SCOPE_MISMATCH:{i}")

    if not substrate_seen:
        fail("SELECTED_ROUTE_PREFLIGHT_EXECUTION_SUBSTRATE_MISSING")


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

    enforce_selected_route_preflight(frontier,obs)


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



def _load_json_at_ref(ref,path):
    raw=git("show",f"{ref}:{path}")
    value=json.loads(raw)
    if not isinstance(value,dict):
        raise ValueError("json_object_required")
    return value

def _nested_json_field(value,field):
    cur=value
    for part in str(field or "").split("."):
        if not part or not isinstance(cur,dict) or part not in cur:
            raise KeyError(part)
        cur=cur[part]
    return cur

def _score_counter_delta(base,name):
    path="canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"
    try:
        before=_load_json_at_ref(base,path).get("counters_since_epoch_start") or {}
        after=load(path).get("counters_since_epoch_start") or {}
        return int(after.get(name) or 0)-int(before.get(name) or 0)
    except Exception:
        return 0

def enforce_adversarial_error_control(intent,files,base):
    ctrl=intent.get("adversarial_error_control")
    if not isinstance(ctrl,dict):
        fail("ADVERSARIAL_ERROR_CONTROL_MISSING_OR_INVALID")
        return
    if ctrl.get("schema")!="PROJECT_BRAIN_ADVERSARIAL_ERROR_CONTROL_V1":
        fail("ADVERSARIAL_ERROR_CONTROL_SCHEMA_INVALID")
    if ctrl.get("assume_action_wrong") is not True:
        fail("ADVERSARIAL_ASSUME_ACTION_WRONG_REQUIRED")

    hypotheses=ctrl.get("strongest_disconfirming_hypotheses")
    if not isinstance(hypotheses,list) or len(hypotheses)<3 or not all(_nonempty_string(x) for x in hypotheses):
        fail("ADVERSARIAL_DISCONFIRMING_HYPOTHESES_INSUFFICIENT")

    checked=ctrl.get("known_failure_classes_checked")
    if not isinstance(checked,list) or not ADVERSARIAL_REQUIRED_FAILURE_CLASSES.issubset(set(checked)):
        fail("ADVERSARIAL_KNOWN_FAILURE_CLASS_SWEEP_INCOMPLETE")

    risks=ctrl.get("unresolved_material_risks")
    if not isinstance(risks,list) or risks:
        fail("ADVERSARIAL_UNRESOLVED_MATERIAL_RISK")
    if ctrl.get("abort_if_any_unresolved") is not True:
        fail("ADVERSARIAL_ABORT_ON_UNRESOLVED_REQUIRED")

    fidelity=ctrl.get("target_fidelity")
    if not isinstance(fidelity,dict):
        fail("TARGET_FIDELITY_MISSING")
    else:
        if fidelity.get("intended_target")!=intent.get("capability_target"):
            fail("TARGET_FIDELITY_MISMATCH")
        if fidelity.get("proxy_substitution_detected") is not False:
            fail("TARGET_PROXY_SUBSTITUTION_DETECTED")

    proof=ctrl.get("proof_claim")
    if not isinstance(proof,dict):
        fail("ADVERSARIAL_PROOF_CLAIM_MISSING")
        proof={}
    level=str(proof.get("claim_level") or "")
    if level not in ADVERSARIAL_CLAIM_LEVELS:
        fail("ADVERSARIAL_CLAIM_LEVEL_INVALID")
    if proof.get("execution_supplier_manifest_complete") is not True:
        fail("EXECUTION_SUPPLIER_MANIFEST_INCOMPLETE")
    unknown=proof.get("unknown_execution_suppliers")
    opaque=proof.get("opaque_supplier_aliases")
    if not isinstance(unknown,list) or unknown:
        fail("UNKNOWN_EXECUTION_SUPPLIER_FORBIDDEN")
    if not isinstance(opaque,list) or opaque:
        fail("OPAQUE_EXECUTION_SUPPLIER_ALIAS_FORBIDDEN")

    promotion_delta=_score_counter_delta(base,"reusable_capabilities_inherited")
    reuse_delta=_score_counter_delta(base,"fresh_reuse_passes")
    dependency_delta=_score_counter_delta(base,"frontier_dependencies_removed")
    proof_bearing=(level in ADVERSARIAL_PROOF_BEARING_LEVELS or promotion_delta>0 or reuse_delta>0 or dependency_delta>0)
    if proof_bearing:
        if proof.get("target_frontier_supplier_in_producer_path") is not False:
            fail("CIRCULAR_FRONTIER_PROOF_FORBIDDEN:TARGET_SUPPLIER_IN_PRODUCER_PATH")
        if proof.get("target_frontier_supplier_in_verifier_path") is not False:
            fail("CIRCULAR_FRONTIER_PROOF_FORBIDDEN:TARGET_SUPPLIER_IN_VERIFIER_PATH")
        if proof.get("producer_verifier_independent") is not True:
            fail("CIRCULAR_FRONTIER_PROOF_FORBIDDEN:PRODUCER_VERIFIER_NOT_INDEPENDENT")
        if proof.get("independent_verifier_present") is not True:
            fail("CIRCULAR_FRONTIER_PROOF_FORBIDDEN:INDEPENDENT_VERIFIER_MISSING")

    semantic_key=ctrl.get("semantic_execution_key")
    if not _nonempty_string(semantic_key):
        fail("SEMANTIC_EXECUTION_KEY_MISSING")
    else:
        try:
            semantic_peers=_open_pr_intents()
        except Exception as exc:
            fail("SEMANTIC_EXECUTION_DEDUPE_CHECK_FAILED:"+str(exc))
            semantic_peers=[]
        for peer in semantic_peers:
            other=peer.get("intent") or {}
            other_ctrl=other.get("adversarial_error_control") or {}
            if other_ctrl.get("semantic_execution_key")!=semantic_key:
                continue
            if bool(intent.get("intentional_route_race")) and bool(other.get("intentional_route_race")):
                race_a=str(intent.get("route_race_id") or "")
                race_b=str(other.get("route_race_id") or "")
                if race_a and race_a==race_b:
                    continue
            fail(f"SEMANTIC_DUPLICATE_EXECUTION_OPEN_PR:{peer['pr']}")

    expected=ctrl.get("expected_sensitive_paths")
    actual=sorted(x for x in files if is_sensitive(x) and not x.startswith("canonical/action_intents/"))
    if not isinstance(expected,list) or not all(_nonempty_string(x) for x in expected):
        fail("EXPECTED_SENSITIVE_PATHS_INVALID")
    elif sorted(set(expected))!=actual or len(set(expected))!=len(expected):
        fail("SENSITIVE_PATH_CONTRACT_MISMATCH")

    post=ctrl.get("postconditions")
    if not isinstance(post,list) or not post:
        fail("EXACT_HEAD_POSTCONDITIONS_MISSING")
        return
    for i,cond in enumerate(post):
        if not isinstance(cond,dict):
            fail(f"EXACT_HEAD_POSTCONDITION_INVALID:{i}")
            continue
        typ=str(cond.get("type") or "")
        path=str(cond.get("path") or "").strip()
        if not path or not is_sensitive(path):
            fail(f"EXACT_HEAD_POSTCONDITION_PATH_INVALID:{i}")
            continue
        target=ROOT/path
        try:
            if typ=="file_exists":
                ok=target.is_file()
            elif typ=="json_field_equals":
                ok=target.is_file() and _nested_json_field(json.loads(target.read_text(encoding="utf-8")),cond.get("field"))==cond.get("value")
            elif typ=="text_contains":
                token=cond.get("text")
                ok=target.is_file() and _nonempty_string(token) and token in target.read_text(encoding="utf-8")
            else:
                fail(f"EXACT_HEAD_POSTCONDITION_TYPE_UNKNOWN:{i}")
                continue
        except Exception:
            ok=False
        if not ok:
            fail(f"EXACT_HEAD_POSTCONDITION_FAILED:{i}")

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
        enforce_adversarial_error_control(intent,files,ns.base)

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
