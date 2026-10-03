"""Tool Discovery complete-interface contract V2 hardening proof.

This is a zero-reality truth-repair. It does not prove a complete discovery
interface exists. It establishes which V4 preconditions are load-bearing, makes
those preconditions explicit in V2, and leaves the common-scope completeness
fact external/formal and uncredited.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_INTERFACE_CONTRACT_V2_HARDENING_PROOF"

V4="canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
V1="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
V2="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2.json"
PROTOCOL="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
ACTIVATION="canonical/governance/TOOL_DISCOVERY_DYNAMIC_V4_REPAIR_ACTIVATION_V1.json"

EXPECTED={
 V4:"e614d0bed8e291e31f57189cd6f0f75aa39b0f74",
 V1:"49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
 V2:"f03f01a531d0a023173629a7a7f4bc0bb65a3b39",
 PROTOCOL:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 REGISTRY:"ee187f611a0e82b2de495ee377682f39bc31dd31",
 ACTIVATION:"36a7a97f3d68066337bb2cf45778d4100c22c185",
}

REQUIRED_V2={
 "FINITE_AUTHORITATIVE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
 "AUTHORITATIVE_DISCOVERY_SOURCE_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
 "DISCOVERY_RECEIPT_IDENTIFIES_EXACTLY_ONE_QUERIED_SOURCE_AND_IS_EPOCH_BOUND",
 "DISCOVERY_RESULT_IS_ATOMICALLY_INCORPORATED_INTO_VISIBLE_TOOL_STATE_BEFORE_SOURCE_IS_MARKED_QUERIED",
 "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
 "AVAILABLE_AUTHORITATIVE_DISCOVERY_SOURCE_UNION_IS_COMPLETE_FOR_COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY_IN_THE_DECISION_EPOCH",
 "VISIBLE_TOOL_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
 "CROSS_SOURCE_METADATA_FOR_THE_SAME_CANONICAL_TOOL_ID_IS_CONSISTENT_OR_FORCES_EPISODE_RESTART",
 "DISCOVERED_TOOL_METADATA_IS_TRUTHFUL_FOR_AVAILABILITY_AUTHORIZATION_COST_CONSTRAINT_AND_VERSION_FIELDS",
 "DECLARED_SOURCE_AND_TOOL_COSTS_ARE_FINITE_NUMERIC_VALUES_WITH_DETERMINISTIC_ID_TIEBREAKS",
 "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_TOOL_AND_VERSION_EPOCH_BOUND",
 "SOURCE_SET_TOOL_METADATA_AND_ROUTE_RANKING_STATE_ARE_STABLE_THROUGH_ONE_ACTION_LINEARIZATION_POINT_OR_ANY_CHANGE_RESTARTS_THE_EPISODE",
 "VERSION_CHANGE_INVALIDATES_STALE_CAPABILITY_EVIDENCE_BEFORE_SELECTION",
 "NO_SOURCE_OR_TOOL_IDENTITY_OUTSIDE_THE_ALLOWED_INFORMATION_BOUNDARY_IS_SILENTLY_ASSUMED_ENUMERATED",
}

LOAD_BEARING_EXPLICIT_V2_ONLY={
 "AUTHORITATIVE_DISCOVERY_SOURCE_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
 "DISCOVERY_RESULT_IS_ATOMICALLY_INCORPORATED_INTO_VISIBLE_TOOL_STATE_BEFORE_SOURCE_IS_MARKED_QUERIED",
 "VISIBLE_TOOL_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
 "CROSS_SOURCE_METADATA_FOR_THE_SAME_CANONICAL_TOOL_ID_IS_CONSISTENT_OR_FORCES_EPISODE_RESTART",
 "DECLARED_SOURCE_AND_TOOL_COSTS_ARE_FINITE_NUMERIC_VALUES_WITH_DETERMINISTIC_ID_TIEBREAKS",
 "SOURCE_SET_TOOL_METADATA_AND_ROUTE_RANKING_STATE_ARE_STABLE_THROUGH_ONE_ACTION_LINEARIZATION_POINT_OR_ANY_CHANGE_RESTARTS_THE_EPISODE",
}

def _sha(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _load(path:str)->dict[str,Any]:
    obj=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise ValueError(path+":NOT_OBJECT")
    return obj

def _base()->dict[str,Any]:
    return {
      "required_capabilities":["CAP_A"],
      "constraint":None,
      "visible_tools":[
        {"tool_id":"EXPENSIVE","cost":10.0,"available":True,"authorized":True,"epoch":0}
      ],
      "discovery_sources":[],
      "discovery_receipts":[],
      "prior_probe_receipts":[{
        "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
        "capability":"CAP_A","epoch":0,"supported":True
      }],
      "version_events":[],
    }

def duplicate_source_id_countermodel()->dict[str,Any]:
    p=_base()
    p["discovery_sources"]=[
      {"source_id":"S0","cost":0.1,"available":True,"latent_tools":[]},
      {
        "source_id":"S0","cost":0.2,"available":True,
        "latent_tools":[
          {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0}
        ],
      },
    ]
    # One receipt for the first physical source aliases both records under V4's
    # source-id set membership, so the second physical source is never queried.
    p["discovery_receipts"]=[{"kind":"DISCOVERY_RESULT","source_id":"S0","tools":[]}]
    return {
      "public":p,
      "observed":v4.next_action(p),
      "failure_class":"SOURCE_ID_ALIAS_CAN_HIDE_AN_UNQUERIED_PHYSICAL_SOURCE",
      "required_property":"AUTHORITATIVE_DISCOVERY_SOURCE_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
    }

def non_atomic_incorporation_countermodel()->dict[str,Any]:
    p=_base()
    p["discovery_sources"]=[{"source_id":"S0","cost":0.1,"available":True}]
    cheap={"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0}
    # Receipt says discovery returned CHEAP but visible state has not incorporated
    # it. V4 quite reasonably trusts the state contract and will not query S0 again.
    p["discovery_receipts"]=[{"kind":"DISCOVERY_RESULT","source_id":"S0","tools":[cheap]}]
    return {
      "public":p,
      "observed":v4.next_action(p),
      "failure_class":"SOURCE_MARKED_QUERIED_BEFORE_RESULT_VISIBLE",
      "required_property":"DISCOVERY_RESULT_IS_ATOMICALLY_INCORPORATED_INTO_VISIBLE_TOOL_STATE_BEFORE_SOURCE_IS_MARKED_QUERIED",
    }

def duplicate_tool_id_countermodel()->dict[str,Any]:
    p=_base()
    p["visible_tools"]=[
      {"tool_id":"DUP","cost":10.0,"available":True,"authorized":True,"epoch":0,"origin":"A"},
      {"tool_id":"DUP","cost":1.0,"available":True,"authorized":True,"epoch":0,"origin":"B"},
    ]
    p["prior_probe_receipts"]=[{
      "kind":"SAFE_CAPABILITY_PROBE","tool_id":"DUP",
      "capability":"CAP_A","epoch":0,"supported":True
    }]
    return {
      "public":p,
      "observed":v4.next_action(p),
      "failure_class":"TOOL_ID_ALIAS_MAKES_SELECTED_PHYSICAL_ROUTE_AMBIGUOUS",
      "required_property":"VISIBLE_TOOL_IDS_ARE_CANONICAL_NONEMPTY_AND_UNIQUE_WITHIN_EPOCH",
    }

def nonfinite_cost_countermodel()->dict[str,Any]:
    p=_base()
    p["visible_tools"]=[
      {"tool_id":"NAN_ROUTE","cost":"nan","available":True,"authorized":True,"epoch":0},
      {"tool_id":"FINITE_ROUTE","cost":1.0,"available":True,"authorized":True,"epoch":0},
    ]
    p["prior_probe_receipts"]=[
      {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"NAN_ROUTE","capability":"CAP_A","epoch":0,"supported":True},
      {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"FINITE_ROUTE","capability":"CAP_A","epoch":0,"supported":True},
    ]
    return {
      "public":p,
      "observed":v4.next_action(p),
      "nan_is_nonfinite":not math.isfinite(float("nan")),
      "failure_class":"NONFINITE_COST_DOES_NOT_DEFINE_A_TOTAL_LEAST_COST_ORDER",
      "required_property":"DECLARED_SOURCE_AND_TOOL_COSTS_ARE_FINITE_NUMERIC_VALUES_WITH_DETERMINISTIC_ID_TIEBREAKS",
    }

def evaluate()->dict[str,Any]:
    drift=[p for p,s in EXPECTED.items() if _sha(p)!=s]
    if drift:
      return {
        "schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT",
        "source_blob_drift":drift,"universal_target_proved":False,
        "capability_credit_delta":0,"family_credit_delta":0,
        "execution_authority":False,"promotion_authority":False,
      }

    v1=_load(V1); v2=_load(V2); protocol=_load(PROTOCOL); registry=_load(REGISTRY); activation=_load(ACTIVATION)
    props_v1=set(v1.get("required_properties") or [])
    props_v2=set(v2.get("required_properties") or [])
    explicit_delta=LOAD_BEARING_EXPLICIT_V2_ONLY-props_v1

    family=next((x for x in protocol.get("protocols",[])
                 if isinstance(x,Mapping) and x.get("family")=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"),None)
    registry_text=json.dumps(registry,sort_keys=True)
    scope_preserved=(
      family is not None
      and "unknown tool discovery" in list(family.get("task_dimensions") or [])
      and "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001" in registry_text
      and v2.get("scope_authority",{}).get("non_narrowing_rule")
         =="BRAIN_ONLY_REGISTRY_COMPLETENESS_IS_NOT_COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY_COMPLETENESS"
      and "COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY" in json.dumps(v2,sort_keys=True)
    )

    countermodels=[
      duplicate_source_id_countermodel(),
      non_atomic_incorporation_countermodel(),
      duplicate_tool_id_countermodel(),
      nonfinite_cost_countermodel(),
    ]
    duplicate_source_exposes=countermodels[0]["observed"]=={"action":"SELECT","tool_id":"EXPENSIVE"}
    incorporation_exposes=countermodels[1]["observed"]=={"action":"SELECT","tool_id":"EXPENSIVE"}
    duplicate_tool_ambiguous=countermodels[2]["observed"]=={"action":"SELECT","tool_id":"DUP"}
    nonfinite_exposes=(
      countermodels[3]["observed"].get("action")=="SELECT"
      and countermodels[3]["nan_is_nonfinite"] is True
    )
    load_bearing=all((duplicate_source_exposes,incorporation_exposes,duplicate_tool_ambiguous,nonfinite_exposes))

    v2_exact=(props_v2==REQUIRED_V2)
    v1_not_exact_machine_complete=bool(explicit_delta)
    current_activation_preserved=(
      activation.get("remaining_primitive_fact")
      =="PROVE_COMPLETE_TARGET_SCOPE_DISCOVERY_INTERFACE_OR_EQUIVALENT_UNIVERSAL_SCOPE_RELATION_WITHOUT_NARROWING_THE_COMMON_BRAIN_OPUS_TOOL_AUTHORITY"
      and activation.get("forbidden_shortcut")
      =="BRAIN_ONLY_REGISTRY_COMPLETENESS_MUST_NOT_BE_SUBSTITUTED_FOR_COMMON_FROZEN_TOOL_AUTHORITY_COMPLETENESS"
    )

    ok=all((v2_exact,v1_not_exact_machine_complete,scope_preserved,load_bearing,current_activation_preserved))
    return {
      "schema":SCHEMA,
      "status":(
        "PASS__V2_EXPLICIT_PRECONDITION_HARDENING_LOAD_BEARING__COMMON_SCOPE_COMPLETENESS_STILL_OPEN__ZERO_CREDIT"
        if ok else "FAIL_CLOSED__HARDENING_PROOF_FAILED"
      ),
      "source_blob_drift":[],
      "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
      "scope_preserved_without_brain_only_narrowing":scope_preserved,
      "current_v4_blob":EXPECTED[V4],
      "v1_machine_complete_for_all_v4_preconditions":False if v1_not_exact_machine_complete else None,
      "v2_required_property_set_exact":v2_exact,
      "explicit_load_bearing_v2_delta":sorted(explicit_delta),
      "countermodels":[
        {
          "failure_class":x["failure_class"],
          "required_property":x["required_property"],
          "observed":x["observed"],
        } for x in countermodels
      ],
      "countermodels_expose_missing_explicit_preconditions":load_bearing,
      "universal_target_proved":False,
      "complete_interface_instance_verified":False,
      "remaining_irreducible_facts":[
        "INDEPENDENT_EVIDENCE_THAT_AVAILABLE_AUTHORITATIVE_DISCOVERY_SOURCE_UNION_IS_COMPLETE_FOR_COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY_IN_THE_DECISION_EPOCH",
        "INDEPENDENT_EVIDENCE_OR_FORMAL_GUARANTEE_OF_DISCOVERY_AND_PROBE_METADATA_TRUTHFULNESS_FOR_FIELDS_USED_BY_V4",
        "ACTION_LINEARIZATION_OR_RESTART_ON_MATERIAL_TOOL_ECOSYSTEM_CHANGE"
      ],
      "next":"VERIFY_EXACT_V2_HARDENING_PUBLICLY__THEN_SEARCH_FOR_OR_BUILD_A_COMMON_SCOPE_INTERFACE_INSTANCE__NO_FRESH_TERMINAL_REPLAY",
      "new_reality_units_consumed":0,
      "terminal_results_replayed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
