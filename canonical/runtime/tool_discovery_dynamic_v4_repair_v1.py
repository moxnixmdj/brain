"""Fail-closed falsification + repair verifier for Tool Discovery V3/V4.

Reproduces a concrete counterexample to the currently activated V3 conditional
least-cost implication, then checks that V4 removes that control-flow defect
and preserves the existing dynamic V3 1200-case behavioral grid.

This is a candidate verification target only. It grants no acceptance credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_V4_REPAIR_VERDICT_V1"

EXPECTED={
 "canonical/runtime/tool_discovery_dynamic_candidate_v3.py":"bbbee4d6baf8df937543644397abba38a67dce62",
 "canonical/runtime/tool_discovery_dynamic_candidate_v4.py":"b19c01ce2c501e3a9883be6aa00b4b6ef2e2141f",
 "canonical/runtime/tool_discovery_dynamic_refinement_v1.py":"991c039c0b405bf77508ce7921abc69460f57332",
 "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json":"49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
}

def _sha(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _public(discovered:bool=False,t1_positive:bool=False)->dict[str,Any]:
    tools=[{
      "tool_id":"T0","cost":10.0,"available":True,"authorized":True,
      "epoch":0,"meta":{},"schema_tags":["CAP_A"],
    }]
    discoveries=[]
    receipts=[{
      "kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A",
      "epoch":0,"supported":True,
    }]
    if discovered:
        tools.append({
          "tool_id":"T1","cost":1.0,"available":True,"authorized":True,
          "epoch":0,"meta":{},"schema_tags":["CAP_A"],
        })
        discoveries.append({"kind":"DISCOVERY_RESULT","source_id":"S0"})
        if t1_positive:
            receipts.append({
              "kind":"SAFE_CAPABILITY_PROBE","tool_id":"T1","capability":"CAP_A",
              "epoch":0,"supported":True,
            })
    return {
      "required_capabilities":["CAP_A"],
      "constraint":None,
      "visible_tools":tools,
      "discovery_sources":[{"source_id":"S0","cost":0.0,"available":True}],
      "prior_probe_receipts":receipts,
      "discovery_receipts":discoveries,
      "version_events":[],
    }

def verify()->dict[str,Any]:
    drift=[p for p,s in EXPECTED.items() if _sha(p)!=s]
    if drift:
        return {
          "schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT",
          "errors":["SOURCE_BLOB_DRIFT:"+p for p in drift],
          "v3_conditional_implication_sound":False,
          "v4_repair_candidate_pass":False,
          "capability_credit_delta":0,"family_credit_delta":0,
          "execution_authority":False,"promotion_authority":False,
        }

    v3_first=v3.next_action(_public())
    v4_first=v4.next_action(_public())
    v4_after_discovery=v4.next_action(_public(discovered=True))
    v4_after_probe=v4.next_action(_public(discovered=True,t1_positive=True))
    grid=proof.run_batch(20261002,1200,v4.next_action)

    counterexample=(
        v3_first=={"action":"SELECT","tool_id":"T0"}
        and v4_first.get("action")=="DISCOVER"
        and v4_first.get("source_id")=="S0"
        and v4_after_discovery=={
          "action":"PROBE","tool_id":"T1","capability":"CAP_A"
        }
        and v4_after_probe=={"action":"SELECT","tool_id":"T1"}
    )
    passed=counterexample and grid.get("pass") is True and grid.get("failed")==0
    return {
      "schema":SCHEMA,
      "status":(
        "PASS__V3_LEAST_COST_CONDITIONAL_IMPLICATION_FALSIFIED__"
        "V4_DISCOVERY_FIRST_REPAIR_GRID_PASS__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT"
        if passed else "FAIL_CLOSED__V4_REPAIR_NOT_ESTABLISHED"
      ),
      "errors":[] if passed else ["COUNTEREXAMPLE_OR_GRID_FAILED"],
      "counterexample":{
        "premise":"S0_IS_AUTHORITATIVE_COMPLETE_AND_CONTAINS_T1",
        "initial_visible_sufficient_route":{"tool_id":"T0","cost":10.0},
        "undiscovered_sufficient_route":{"tool_id":"T1","cost":1.0},
        "v3_first_action":v3_first,
        "v4_first_action":v4_first,
        "v4_after_discovery":v4_after_discovery,
        "v4_after_positive_probe":v4_after_probe,
        "violated_v3_claim":"FIRST_SELECTED_ROUTE_IS_LEAST_COST_ADMISSIBLE_ROUTE_UNDER_COMPLETE_INTERFACE",
      },
      "v3_conditional_implication_sound":False,
      "falsified_active_refinement_obligation":"LEAST_COST_EVIDENCE_SUPPORTED_SELECTION",
      "v4_repair_candidate_pass":passed,
      "v4_existing_dynamic_grid":{"count":grid.get("count"),"failed":grid.get("failed"),"pass":grid.get("pass")},
      "remaining_external_fact":"INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1",
      "universal_target_proved":False,
      "new_reality_units_consumed":0,
      "terminal_results_replayed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

def main()->int:
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
