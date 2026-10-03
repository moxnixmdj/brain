"""Fail-closed falsification of the V3 conditional refinement and V4 repair check."""
from __future__ import annotations
import json
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_V4_SOUNDNESS_REPAIR_V1"

def _base():
    return {
        "required_capabilities":["CAP_A"],
        "constraint":None,
        "visible_tools":[],
        "prior_probe_receipts":[],
        "discovery_sources":[],
        "discovery_receipts":[],
        "version_events":[],
    }

def evaluate():
    c=_base()
    c["visible_tools"]=[{
        "tool_id":"EXPENSIVE","cost":10.0,"available":True,
        "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
    }]
    c["prior_probe_receipts"]=[{
        "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
        "capability":"CAP_A","epoch":0,"supported":True,
    }]
    c["discovery_sources"]=[{"source_id":"S0","cost":0.1,"available":True}]
    v3_action=v3.next_action(c)
    v4_pre=v4.next_action(c)

    d=_base()
    d["visible_tools"]=[
        {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"]},
        {"tool_id":"EXPENSIVE","cost":10.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"]},
    ]
    d["prior_probe_receipts"]=[
        {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP","capability":"CAP_A","epoch":0,"supported":True},
        {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE","capability":"CAP_A","epoch":0,"supported":True},
    ]
    d["discovery_sources"]=[{"source_id":"S0","cost":0.1,"available":True}]
    d["discovery_receipts"]=[{"kind":"DISCOVERY_RESULT","source_id":"S0"}]
    v4_post=v4.next_action(d)

    unsafe=_base()
    unsafe["visible_tools"]=[
        {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":[]},
        {"tool_id":"SAFE","cost":2.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"]},
    ]
    unsafe["prior_probe_receipts"]=[{
        "kind":"SAFE_CAPABILITY_PROBE","tool_id":"SAFE",
        "capability":"CAP_A","epoch":0,"supported":True,
    }]
    v4_unsafe=v4.next_action(unsafe)

    v3_falsified=(
        v3_action=={"action":"SELECT","tool_id":"EXPENSIVE"}
        and v4_pre=={"action":"DISCOVER","source_id":"S0","query":"CAP_A"}
    )
    v4_checks=(
        v4_post=={"action":"SELECT","tool_id":"CHEAP"}
        and v4_unsafe=={"action":"SELECT","tool_id":"SAFE"}
    )
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__V3_CONDITIONAL_REFINEMENT_FALSIFIED_BY_CHEAPER_UNDISCOVERED_ROUTE__"
            "V4_REPAIR_CHECKS_PASS__ZERO_CREDIT"
            if v3_falsified and v4_checks else
            "FAIL_CLOSED__SOUNDNESS_REPAIR_CHECK_FAILED"
        ),
        "counterexample":{
            "complete_interface_allows_unqueried_source_to_reveal_cheaper_sufficient_tool":True,
            "v3_action":v3_action,
            "v4_action_before_discovery":v4_pre,
            "v4_action_after_complete_discovery":v4_post,
        },
        "prior_refinement_claim_invalidated":"LEAST_COST_EVIDENCE_SUPPORTED_SELECTION",
        "prior_residual_reduction_to_interface_instance_only_sound":False,
        "v3_falsified":v3_falsified,
        "v4_repair_checks_pass":v4_checks,
        "v4_safe_probe_gate_check":v4_unsafe,
        "replacement_interface_contract":"canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2.json",
        "universal_target_proved":False,
        "minimum_missing_fact":(
            "INDEPENDENT_VERIFY_V4_PROGRAM_SIDE_REPAIR__THEN_"
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
            "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2"
        ),
        "hard_nonclaims":[
            "NO_TOOL_DISCOVERY_ACCEPTANCE_CREDIT",
            "NO_UNIVERSAL_SCOPE_CREDIT",
            "NO_TERMINAL_REPLAY",
            "V4_REQUIRES_INDEPENDENT_VERIFICATION_BEFORE_PROGRAM_SIDE_REDUCTION",
        ],
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def main():
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["status"].startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
