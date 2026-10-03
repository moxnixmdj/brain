"""Fail-closed Tool Discovery refinement V2.

V1's conditional refinement was too strong: Dynamic V3 can select an already
verified expensive visible tool before querying an unqueried authoritative
discovery source that contains a cheaper sufficient tool.

V2 permanently compiles that counterexample, binds discovery-exhaustive V4,
checks the discovery-first invariant, and narrows the remaining proof burden.
It does NOT claim the frozen family is closed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_REFINEMENT_V2"

V3="canonical/runtime/tool_discovery_dynamic_candidate_v3.py"
V4="canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
PROTOCOL="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
CUT="canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"
CONTRACT="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2.json"
COUNTEREXAMPLE="canonical/governance/TOOL_DISCOVERY_DYNAMIC_V3_LEAST_COST_COUNTEREXAMPLE_V1.json"

EXPECTED={
 V3:"bbbee4d6baf8df937543644397abba38a67dce62",
 V4:"b8cd817a07c0b93ff740120f869e7fbb5650f801",
 PROTOCOL:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 REGISTRY:"ee187f611a0e82b2de495ee377682f39bc31dd31",
 CUT:"48ba33998e73b8eec2731be51a7ec78077ed0d4a",
 CONTRACT:"d342962d6d90f4fdb78446d7f7711c05938a3a25",
 COUNTEREXAMPLE:"062a8b11f75d702ab8fc0e6369091aeb4f7bb6a9",
}

REQUIRED_PROPERTIES={
 "FINITE_AUTHORITATIVE_DISCOVERY_SOURCE_SET_WITH_UNIQUE_SOURCE_IDS_PER_DECISION_EPOCH",
 "DISCOVERY_RECEIPT_IDENTIFIES_EXACT_QUERIED_SOURCE_AND_ATOMICALLY_INCORPORATES_ITS_RESULT",
 "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
 "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
 "DISCOVERED_TOOL_IDS_ARE_CANONICAL_UNIQUE_AND_CROSS_SOURCE_METADATA_IS_CONSISTENT",
 "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
 "DECLARED_TOOL_COST_IS_FINITE_NUMERIC_AND_INDUCES_A_TOTAL_ORDER_WITH_TOOL_ID_TIEBREAK",
 "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
 "DECISION_EPOCH_SOURCE_SET_AND_ROUTE_RANKING_FIELDS_STABLE_UNTIL_SELECT_OR_ESCALATE_OR_CHANGE_RESTARTS_EPISODE",
 "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_CHANGE_RESTARTS_EPISODE",
}

EXTERNAL_INTERFACE_FACT=(
 "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
 "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2"
)
FULL_ACCEPTANCE_FACT=(
 "INDEPENDENT_SCOPE_COMPLETE_FORMAL_OR_EXHAUSTIVE_ACCEPTANCE_PROOF_FOR_"
 "DISCOVERY_EXHAUSTIVE_V4_OVER_THE_FROZEN_TOOL_DISCOVERY_TARGET"
)

def _sha(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _load(path:str)->dict[str,Any]:
    x=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(path+":NOT_OBJECT")
    return x

def _find(obj:Any,key:str,value:str)->Mapping[str,Any]|None:
    if isinstance(obj,Mapping):
        if obj.get(key)==value: return obj
        for child in obj.values():
            got=_find(child,key,value)
            if got is not None: return got
    elif isinstance(obj,list):
        for child in obj:
            got=_find(child,key,value)
            if got is not None: return got
    return None

def counterexample_public()->dict[str,Any]:
    return {
      "required_capabilities":["CAP_A"],
      "constraint":None,
      "visible_tools":[
        {"tool_id":"EXPENSIVE","cost":10.0,"available":True,"authorized":True,"epoch":0}
      ],
      "discovery_sources":[{"source_id":"S0","cost":0.1,"available":True}],
      "discovery_receipts":[],
      "prior_probe_receipts":[{
        "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
        "capability":"CAP_A","epoch":0,"supported":True
      }],
      "version_events":[],
    }

def _fail(*errors:str)->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
      "v1_conditional_implication_valid":False,
      "v3_least_cost_counterexample_confirmed":False,
      "v4_discovery_first_invariant_pass":False,
      "universal_target_proved":False,
      "minimum_missing_facts":[EXTERNAL_INTERFACE_FACT,FULL_ACCEPTANCE_FACT],
      "new_reality_units_consumed":0,"terminal_results_replayed":0,
      "incremental_spend_usd":0,"capability_credit_delta":0,
      "family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }

def evaluate(*, v4_policy=v4.next_action)->dict[str,Any]:
    drift=[p for p,s in EXPECTED.items() if _sha(p)!=s]
    if drift: return _fail(*["SOURCE_BLOB_DRIFT:"+p for p in drift])

    protocol=_load(PROTOCOL); registry=_load(REGISTRY); cut=_load(CUT)
    contract=_load(CONTRACT); frozen_counterexample=_load(COUNTEREXAMPLE)
    family=_find(protocol,"family","TOOL_DISCOVERY_SELECTION_AND_LEARNING")
    behavior=_find(registry,"behavior_id","TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")
    if family is None or behavior is None: return _fail("FROZEN_TARGET_NOT_FOUND")

    target_ok=(
      "unknown tool discovery" in list(family.get("task_dimensions") or [])
      and "Discover candidate tools if needed" in str(behavior.get("required_output_or_action") or "")
      and "least-cost admissible route" in str(behavior.get("required_output_or_action") or "")
    )
    if not target_ok: return _fail("FROZEN_TARGET_LITERALS_DRIFT")

    props=contract.get("required_properties")
    if not isinstance(props,list) or set(props)!=REQUIRED_PROPERTIES:
        return _fail("INTERFACE_V2_PROPERTIES_NOT_EXACT")
    if contract.get("instance_verified") is not False:
        return _fail("INTERFACE_CONTRACT_MUST_NOT_SELF_ASSERT_INSTANCE")

    p=counterexample_public()
    v3_action=v3.next_action(p)
    v4_action=v4_policy(p)
    v3_failure=(v3_action=={"action":"SELECT","tool_id":"EXPENSIVE"})
    v4_fix=(v4_action=={"action":"DISCOVER","source_id":"S0","query":"CAP_A"})
    if not v3_failure: return _fail("V3_COUNTEREXAMPLE_NO_LONGER_REPRODUCES")
    if not v4_fix: return _fail("V4_DOES_NOT_DISCOVER_BEFORE_SELECT")

    # General executable discovery-first invariant over representative adversarial
    # visible-route states. Any nonempty required-capability state with an
    # available unqueried source must produce DISCOVER, irrespective of existing
    # positive/negative/absent evidence and visible route cost.
    invariant_rows=[]
    for support in (True,False,None):
      for visible_cost in (0.0,1.0,10.0):
        q=counterexample_public()
        q["visible_tools"][0]["cost"]=visible_cost
        if support is None:
          q["prior_probe_receipts"]=[]
        else:
          q["prior_probe_receipts"][0]["supported"]=support
        got=v4_policy(q)
        ok=(got.get("action")=="DISCOVER" and got.get("source_id")=="S0")
        invariant_rows.append({"support":support,"visible_cost":visible_cost,"action":got,"pass":ok})
    invariant_pass=all(x["pass"] for x in invariant_rows)
    if not invariant_pass: return _fail("V4_DISCOVERY_FIRST_INVARIANT_FAILED")

    src=(ROOT/V4).read_text(encoding="utf-8")
    ordering_pass=(
      src.find("if sources:")>=0
      and src.find('constraint=public.get("constraint")')>=0
      and src.find("if sources:") < src.find('constraint=public.get("constraint")')
      and "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY" in src
    )
    if not ordering_pass: return _fail("V4_SOURCE_ORDERING_INVARIANT_NOT_BOUND")

    return {
      "schema":SCHEMA,
      "status":"PASS__V3_LEAST_COST_COUNTEREXAMPLE_COMPILED__V4_DISCOVERY_FIRST_REPAIR_BOUND__EXTERNAL_INTERFACE_AND_FULL_ACCEPTANCE_OPEN__ZERO_CREDIT",
      "errors":[],
      "source_blob_drift":[],
      "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
      "target_proof_atom":cut.get("target_proof_atom"),
      "frozen_target_preserved":True,
      "v1_conditional_implication_valid":False,
      "v1_disposition":"FALSIFIED_BY_LOAD_BEARING_LEAST_COST_COUNTEREXAMPLE__MUST_NOT_PROMOTE",
      "v3_least_cost_counterexample_confirmed":True,
      "v3_observed_action":v3_action,
      "v4_observed_first_action":v4_action,
      "permanent_counterexample":COUNTEREXAMPLE,
      "v4_candidate":V4,
      "v4_discovery_first_invariant_pass":True,
      "v4_source_ordering_invariant_pass":True,
      "adversarial_invariant_rows":invariant_rows,
      "interface_contract":{
        "path":CONTRACT,"required_properties":sorted(REQUIRED_PROPERTIES),
        "instance_verified":False,
      },
      "conditional_program_side_claim":(
        "UNDER_A_STABLE_COMPLETE_AUTHORITATIVE_DISCOVERY_INTERFACE_V2__V4_EXHAUSTS_"
        "DISCOVERY_BEFORE_PROBE_OR_SELECT_AND_THEREFORE_REMOVES_THE_V3_CHEAPER_"
        "UNDISCOVERED_ROUTE_FAILURE_CLASS"
      ),
      "universal_target_proved":False,
      "minimum_missing_facts":[EXTERNAL_INTERFACE_FACT,FULL_ACCEPTANCE_FACT],
      "next":(
        "INDEPENDENTLY_VERIFY_EXACT_V2_V4_BYTES__THEN_PROVE_OR_FALSIFY_A_COMPLETE_"
        "DISCOVERY_INTERFACE_INSTANCE__THEN_DISCHARGE_THE_FULL_FROZEN_TOOL_DISCOVERY_"
        "ACCEPTANCE_WITH_FORMAL_OR_EXHAUSTIVE_EVIDENCE__NO_FRESH_TERMINAL_REPLAY"
      ),
      "new_reality_units_consumed":0,"terminal_results_replayed":0,
      "incremental_spend_usd":0,"capability_credit_delta":0,
      "family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }

def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
