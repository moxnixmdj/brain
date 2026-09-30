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
    "canonical/laws/FAIL_CLOSED_MISTAKE_IMMUNITY_LAW_V1.md",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V3.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V4.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V4.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V5.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V5.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V6.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V6.json",
    "canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V7.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V2.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V3.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V4.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V2.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V3.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V4.json",
    "canonical/governance/OPERATOR_OBS_DECISION_BOUNDARY_V1.json",
    "canonical/governance/OPERATOR_OBS_AUTHORITY_ENVELOPE_V1.json",
    "canonical/regressions/2026-09-30_RECURRING_FRONTIER_MISTAKE_CLASSES.json",
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
MODEL_DEPENDENCY_KINDS={"MODEL_API","LOCAL_MODEL","MODEL_ARTIFACT"}
COGNITIVE_PARENT_FAMILIES={"RESEARCH_AND_KNOWLEDGE_SYNTHESIS","TECHNICAL_SCIENTIFIC_REASONING","TOOL_SELECTION_AND_TOOL_LEARNING","MULTI_CAPABILITY_COMPOSITION","SELF_CRITIQUE_FALSIFICATION_AND_VERIFICATION","UNKNOWN_DOMAIN_ADAPTATION"}
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
FAIL=[]

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def load_at_ref(ref,path):
    try:
        raw=git("show",f"{ref}:{path}")
    except Exception as exc:
        raise RuntimeError("REF_JSON_READ_FAILED:"+str(path)+":"+type(exc).__name__) from exc
    return json.loads(raw)

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


def _frontier_scope_chain(capability_id):
    chain=[]
    visited=set()
    current=str(capability_id or "").strip()
    while current:
        if current in visited:
            fail("FRONTIER_CAPABILITY_PARENT_CYCLE:"+current)
            break
        visited.add(current)
        path=ROOT/"canonical"/"capabilities"/"frontier"/(current+".json")
        if not path.is_file():
            if not chain:
                fail("MODEL_NON_DEPENDENCE_TARGET_METADATA_MISSING:"+current)
            break
        try:
            record=json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            fail("MODEL_NON_DEPENDENCE_TARGET_METADATA_INVALID:"+current)
            break
        chain.append(record)
        parent=str(record.get("parent_frontier_capability") or "").strip()
        current=parent
    return chain

def enforce_model_independent_cognition(intent,obs):
    action_kind=str(intent.get("action_kind") or "")
    if action_kind not in REAL_TASK_ACTIONS:
        return

    capability_id=str(intent.get("capability_target") or "").strip()
    if not capability_id:
        fail("MODEL_NON_DEPENDENCE_CAPABILITY_TARGET_MISSING")
        return

    chain=_frontier_scope_chain(capability_id)
    if not chain:
        return
    families=set()
    for target in chain:
        families.update(str(x) for x in (target.get("parent_families") or []))
    if not families.intersection(COGNITIVE_PARENT_FAMILIES):
        return

    frontier=obs.get("route_frontier")
    if not isinstance(frontier,dict):
        fail("MODEL_NON_DEPENDENCE_ROUTE_FRONTIER_MISSING")
        return
    preflight=frontier.get("selected_route_preflight")
    if not isinstance(preflight,dict):
        fail("MODEL_NON_DEPENDENCE_SELECTED_ROUTE_PREFLIGHT_MISSING")
        return
    deps=preflight.get("execution_dependencies")
    if not isinstance(deps,list):
        fail("MODEL_NON_DEPENDENCE_DEPENDENCY_INVENTORY_MISSING")
        return

    model_dependencies=[]
    for dep in deps:
        if not isinstance(dep,dict):
            continue
        if str(dep.get("kind") or "") in MODEL_DEPENDENCY_KINDS:
            model_dependencies.append(str(dep.get("dependency") or dep.get("kind") or "MODEL"))

    if model_dependencies:
        fail(
            "MODEL_PRESENT_IN_COGNITION_EXECUTION_PATH_FOR_COGNITIVE_CAPABILITY:"
            +",".join(sorted(model_dependencies))
        )


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
    enforce_model_independent_cognition(intent,obs)


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
    current=int(os.environ.get("CURRENT_PR_NUMBER") or "0")
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

        peer_pr=int(peer.get("pr") or 0)
        # Accidental duplicate leases use a deterministic single owner so a
        # near-simultaneous race cannot deadlock both PRs. Lowest PR number wins.
        if current>0 and peer_pr>current:
            continue
        if current>0 and peer_pr<current:
            fail(f"DUPLICATE_BLOCKER_LEASE_OWNER_EXISTS:{peer_pr}")
        else:
            fail(f"DUPLICATE_BLOCKER_LEASE_OPEN_PR:{peer_pr}")

def enforce_target_continuity(intent,base,hierarchy):
    action_kind=str(intent.get("action_kind") or "")
    try:
        prior=load_at_ref(base,"canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
    except Exception as exc:
        fail("BASE_HIERARCHY_READ_FAILED:"+str(exc))
        return
    before=str(prior.get("active_capability_target") or "")
    after=str(hierarchy.get("active_capability_target") or "")
    if before==after:
        return
    if action_kind in GOVERNANCE_ACTIONS:
        return
    if action_kind!="RECONCILE_FRONTIER":
        fail("ACTIVE_CAPABILITY_TARGET_CHANGE_REQUIRES_EXPLICIT_RECONCILIATION:"+before+"->"+after)
        return
    rec=intent.get("frontier_reconciliation")
    if not isinstance(rec,dict):
        fail("FRONTIER_RECONCILIATION_EVIDENCE_REQUIRED")
        return
    if str(rec.get("previous_target") or "")!=before:
        fail("FRONTIER_RECONCILIATION_PREVIOUS_TARGET_MISMATCH")
    if str(rec.get("new_target") or "")!=after:
        fail("FRONTIER_RECONCILIATION_NEW_TARGET_MISMATCH")
    relationship=str(rec.get("relationship") or "")
    if relationship not in {"SUBCAPABILITY_OF","RESIDUAL_OF","NEXT_FRONTIER_AFTER_VERIFIED_CLOSURE","REOPENED_BY_FALSIFICATION"}:
        fail("FRONTIER_RECONCILIATION_RELATIONSHIP_INVALID")
    if not _nonempty_string_list(rec.get("evidence")):
        fail("FRONTIER_RECONCILIATION_EVIDENCE_MISSING")

def _collect_key_values(value,key):
    out=[]
    if isinstance(value,dict):
        if key in value:
            out.append(value.get(key))
        for item in value.values():
            out.extend(_collect_key_values(item,key))
    elif isinstance(value,list):
        for item in value:
            out.extend(_collect_key_values(item,key))
    return out

def _require_existing_paths(values,label):
    if not isinstance(values,list) or not values:
        fail(label+"_MISSING")
        return
    for raw in values:
        if not _nonempty_string(raw):
            fail(label+"_INVALID")
            continue
        path=ROOT/str(raw)
        if not path.is_file():
            fail(label+"_PATH_MISSING:"+str(raw))

def enforce_promotion_truth(intent,files,base):
    score_path="canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"
    if score_path not in files:
        return
    try:
        old=load_at_ref(base,score_path)
        new=load(score_path)
    except Exception as exc:
        fail("SCOREBOARD_COMPARISON_FAILED:"+str(exc))
        return

    oldc=old.get("counters_since_epoch_start") or {}
    newc=new.get("counters_since_epoch_start") or {}
    counters=(
        "reusable_capabilities_inherited",
        "verified_real_tasks_completed",
        "fresh_reuse_passes",
        "frontier_dependencies_removed",
        "residual_gaps_localized",
    )
    deltas={}
    for key in counters:
        try:
            delta=int(newc.get(key,0))-int(oldc.get(key,0))
        except Exception:
            fail("SCOREBOARD_COUNTER_INVALID:"+key)
            continue
        if delta>0:
            deltas[key]=delta

    if not deltas:
        return

    evidence=intent.get("promotion_evidence")
    if not isinstance(evidence,dict):
        fail("PROMOTION_EVIDENCE_REQUIRED_FOR_SCOREBOARD_INCREASE")
        return
    if evidence.get("claim_scope_exact") is not True:
        fail("PROMOTION_CLAIM_SCOPE_NOT_EXACT")
    falsification=evidence.get("falsification_attempts")
    no_cheap=str(evidence.get("cheap_falsification_not_available_reason") or "").strip()
    if not isinstance(falsification,list) or not falsification:
        if not no_cheap:
            fail("PROMOTION_ADVERSARIAL_FALSIFICATION_REQUIRED")

    action_kind=str(intent.get("action_kind") or "")
    allowed={
        "reusable_capabilities_inherited":{"CAPABILITY_INHERITANCE"},
        "verified_real_tasks_completed":{"REAL_CAPABILITY_ACQUISITION","REAL_TASK_EXECUTION","CAPABILITY_INHERITANCE","FRESH_REUSE"},
        "fresh_reuse_passes":{"FRESH_REUSE"},
        "frontier_dependencies_removed":{"CAPABILITY_INHERITANCE","FRESH_REUSE","RECONCILE_FRONTIER"},
        "residual_gaps_localized":{"REAL_CAPABILITY_ACQUISITION","REAL_TASK_EXECUTION","FRESH_REUSE","RECONCILE_FRONTIER"},
    }
    for key in deltas:
        if action_kind not in allowed[key]:
            fail("SCOREBOARD_COUNTER_ACTION_KIND_MISMATCH:"+key+":"+action_kind)

    if any(k in deltas for k in ("reusable_capabilities_inherited","verified_real_tasks_completed","fresh_reuse_passes","frontier_dependencies_removed")):
        _require_existing_paths(evidence.get("real_task_evidence_paths"),"PROMOTION_REAL_TASK_EVIDENCE")

    if any(k in deltas for k in ("reusable_capabilities_inherited","frontier_dependencies_removed")):
        _require_existing_paths(evidence.get("independent_verification_evidence_paths"),"PROMOTION_INDEPENDENT_VERIFICATION_EVIDENCE")

    if "reusable_capabilities_inherited" in deltas:
        package=str(evidence.get("capability_package_path") or "").strip()
        if not package or not (ROOT/package).is_file():
            fail("PROMOTION_CAPABILITY_PACKAGE_MISSING")

    if "fresh_reuse_passes" in deltas:
        reuse=str(evidence.get("fresh_reuse_evidence_path") or "").strip()
        if not reuse or not (ROOT/reuse).is_file():
            fail("PROMOTION_FRESH_REUSE_EVIDENCE_MISSING")
        if evidence.get("fresh_reuse_distinct_task") is not True:
            fail("PROMOTION_FRESH_REUSE_NOT_DISTINCT_TASK")

    capability_id=str(intent.get("capability_target") or "")
    chain=_frontier_scope_chain(capability_id) if capability_id else []
    families=set()
    for record in chain:
        families.update(str(x) for x in (record.get("parent_families") or []))
    cognitive_credit=bool(families.intersection(COGNITIVE_PARENT_FAMILIES)) and any(
        k in deltas for k in (
            "reusable_capabilities_inherited",
            "verified_real_tasks_completed",
            "fresh_reuse_passes",
            "frontier_dependencies_removed",
        )
    )
    if cognitive_credit:
        counts=[]; authorities=[]; modes=[]; planners=[]
        for raw in evidence.get("real_task_evidence_paths") or []:
            try:
                doc=load(str(raw))
            except Exception as exc:
                fail("COGNITIVE_PROMOTION_EVIDENCE_READ_FAILED:"+str(raw)+":"+type(exc).__name__)
                continue
            counts.extend(_collect_key_values(doc,"model_dependency_count"))
            authorities.extend(_collect_key_values(doc,"cognition_provenance_authority"))
            modes.extend(_collect_key_values(doc,"controller_mode"))
            planners.extend(_collect_key_values(doc,"planner_model_last"))
        if not counts:
            fail("COGNITIVE_PROMOTION_RUNTIME_MODEL_DEPENDENCY_COUNT_MISSING")
        for raw in counts:
            try:
                if int(raw)!=0:
                    fail("COGNITIVE_PROMOTION_RUNTIME_MODEL_DEPENDENCY_NONZERO")
            except Exception:
                fail("COGNITIVE_PROMOTION_RUNTIME_MODEL_DEPENDENCY_COUNT_INVALID")
        if "ASTRA_RUNTIME_DERIVED_V1" not in {str(x) for x in authorities}:
            fail("COGNITIVE_PROMOTION_RUNTIME_PROVENANCE_AUTHORITY_MISSING")
        if any(str(x or "").startswith("OPTIONAL_MODEL_ADVISORY") for x in modes):
            fail("COGNITIVE_PROMOTION_ADVISORY_MODEL_CONTROLLER_PRESENT")
        if any(x not in (None,"") for x in planners):
            fail("COGNITIVE_PROMOTION_PLANNER_MODEL_PRESENT")
    cross_domain_required=any(
        bool((record.get("minimum_acquisition_evidence") or {}).get("cross_domain_transfer_required"))
        for record in chain
    )
    if cross_domain_required and any(k in deltas for k in ("fresh_reuse_passes","frontier_dependencies_removed")):
        if evidence.get("cross_domain_distinct") is not True:
            fail("PROMOTION_CROSS_DOMAIN_EVIDENCE_REQUIRED")

    if "frontier_dependencies_removed" in deltas:
        if evidence.get("frontier_dependency_removed") is not True:
            fail("PROMOTION_FRONTIER_DEPENDENCY_REMOVAL_NOT_PROVEN")
        target_supplier=str(evidence.get("target_frontier_supplier") or "").strip()
        producer=[str(x).strip() for x in (evidence.get("producer_execution_suppliers") or []) if str(x).strip()]
        verifiers=[str(x).strip() for x in (evidence.get("independent_verifier_suppliers") or []) if str(x).strip()]
        if not target_supplier:
            fail("PROMOTION_TARGET_FRONTIER_SUPPLIER_MISSING")
        else:
            folded=target_supplier.casefold()
            if any(x.casefold()==folded for x in producer):
                fail("CIRCULAR_FRONTIER_PROOF_TARGET_SUPPLIER_IN_PRODUCER_PATH")
            if any(x.casefold()==folded for x in verifiers):
                fail("CIRCULAR_FRONTIER_PROOF_TARGET_SUPPLIER_IS_VERIFIER")
        if not producer:
            fail("PROMOTION_PRODUCER_SUPPLIERS_MISSING")
        if not verifiers:
            fail("PROMOTION_INDEPENDENT_VERIFIER_SUPPLIERS_MISSING")

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
    scoreboard=load("canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json")

    current=pointer.get("current_frontier") or {}
    immediate=queue.get("immediate_frontier") or {}
    if str(current.get("active_capability_target") or "")!=str(hierarchy.get("active_capability_target") or ""):
        fail("POINTER_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH")
    if str(current.get("critical_blocker") or "")!=str(hierarchy.get("current_parent_blocker") or ""):
        fail("POINTER_HIERARCHY_CRITICAL_BLOCKER_MISMATCH")
    if str(current.get("next_step") or "")!=str(hierarchy.get("next_required_action_class") or ""):
        fail("POINTER_HIERARCHY_NEXT_ACTION_MISMATCH")
    if str(immediate.get("exact_blocker") or "")!=str(hierarchy.get("current_parent_blocker") or ""):
        fail("QUEUE_HIERARCHY_CRITICAL_BLOCKER_MISMATCH")
    if str(immediate.get("next_action") or "")!=str(hierarchy.get("next_required_action_class") or ""):
        fail("QUEUE_HIERARCHY_NEXT_ACTION_MISMATCH")
    accounting=scoreboard.get("active_frontier_accounting") or {}
    if str(accounting.get("parent_frontier_capability") or "")!=str(hierarchy.get("active_capability_target") or ""):
        fail("SCOREBOARD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH")
    if str(scoreboard.get("next_progress_event_target") or "")!=str(hierarchy.get("next_required_action_class") or ""):
        fail("SCOREBOARD_HIERARCHY_NEXT_ACTION_MISMATCH")

    boot=pointer.get("boot_requirements") or {}
    operator_obs_path="canonical/governance/OPERATOR_OBS_DECISION_BOUNDARY_V1.json"
    if boot.get("operator_obs_decision_boundary_required") is not True:
        fail("OPERATOR_OBS_DECISION_BOUNDARY_NOT_REQUIRED")
    if boot.get("operator_obs_decision_boundary_path")!=operator_obs_path:
        fail("OPERATOR_OBS_DECISION_BOUNDARY_PATH_MISMATCH")
    if boot.get("consequential_operator_reasoning_requires_current_obs") is not True:
        fail("CONSEQUENTIAL_OPERATOR_REASONING_NOT_GATED_BY_CURRENT_OBS")
    if boot.get("memory_only_frontier_diagnosis_forbidden") is not True:
        fail("MEMORY_ONLY_FRONTIER_DIAGNOSIS_NOT_FORBIDDEN")
    if boot.get("operator_exploration_before_obs_is_non_authoritative") is not True:
        fail("PRE_OBS_EXPLORATION_AUTHORITY_NOT_REVOKED")
    if boot.get("operator_obs_required_before_current_blocker_or_route_claim") is not True:
        fail("CURRENT_BLOCKER_OR_ROUTE_CLAIM_NOT_GATED_BY_OBS")
    if not (ROOT/operator_obs_path).is_file():
        fail("OPERATOR_OBS_DECISION_BOUNDARY_FILE_MISSING")

    operator_obs_envelope_path="canonical/governance/OPERATOR_OBS_AUTHORITY_ENVELOPE_V1.json"
    if boot.get("operator_obs_authority_envelope_required") is not True:
        fail("OPERATOR_OBS_AUTHORITY_ENVELOPE_NOT_REQUIRED")
    if boot.get("operator_obs_authority_envelope_path")!=operator_obs_envelope_path:
        fail("OPERATOR_OBS_AUTHORITY_ENVELOPE_PATH_MISMATCH")
    if boot.get("bare_chat_has_zero_canonical_authority") is not True:
        fail("BARE_CHAT_CANONICAL_AUTHORITY_NOT_REVOKED")
    if boot.get("canonical_consequential_decision_requires_repository_backed_current_base_obs") is not True:
        fail("CANONICAL_DECISION_NOT_BOUND_TO_REPOSITORY_OBS")
    if not (ROOT/operator_obs_envelope_path).is_file():
        fail("OPERATOR_OBS_AUTHORITY_ENVELOPE_FILE_MISSING")

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
        enforce_target_continuity(intent,ns.base,hierarchy)
        enforce_promotion_truth(intent,files,ns.base)

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
