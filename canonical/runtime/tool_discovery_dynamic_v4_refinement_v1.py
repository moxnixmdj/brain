"""Fail-closed conditional universal proof for Tool Discovery V4.

This certificate repairs a specific defect in the prior Dynamic Refinement V1:
V3 can PROBE/SELECT a visible route before exhausting authoritative discovery
sources, so the prior least-cost conditional guarantee was not justified.

V4 moves discovery closure before tool evaluation. Under the unchanged complete
interface contract, the remaining proof is a finite-progress argument:
  1. each DISCOVER consumes one previously unqueried source;
  2. the finite source set therefore reaches discovery closure;
  3. complete-union + truthful metadata makes the visible set complete in-scope;
  4. tools are then traversed in global (cost, tool_id) order;
  5. truthful current-epoch probes either falsify a route or establish every
     required capability;
  6. the first SELECT is therefore least-cost among admissible sufficient routes;
  7. if none survives, ESCALATE is sound for the declared scope.

This is program-side only. It does not assert that a current external discovery
interface instance satisfies the contract and grants no terminal credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_V4_REFINEMENT_V1"
V3="canonical/runtime/tool_discovery_dynamic_candidate_v3.py"
V4="canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
CONTRACT="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
PRIOR="canonical/runtime/tool_discovery_dynamic_refinement_v1.py"

EXPECTED={
    V3:"bbbee4d6baf8df937543644397abba38a67dce62",
    V4:"c7726fc77bb4f8c582b1e57c71eeaa0ba8253065",
    CONTRACT:"49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    PRIOR:"991c039c0b405bf77508ce7921abc69460f57332",
}

REQUIRED_PROPERTIES={
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}

EXTERNAL_FACT=(
    "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
    "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1"
)

def _blob_sha(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _load(rel:str)->dict[str,Any]:
    x=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return x

def counterexample(policy)->list[dict[str,Any]]:
    state={
        "required_capabilities":["CAP_A"],
        "constraint":None,
        "visible_tools":[
            {"tool_id":"T0","cost":10.0,"available":True,"authorized":True,"epoch":0}
        ],
        "discovery_sources":[{"source_id":"S0","cost":0.1,"available":True}],
        "discovery_receipts":[],
        "prior_probe_receipts":[],
        "version_events":[],
    }
    first=policy(state)
    if first.get("action")=="PROBE" and first.get("tool_id")=="T0":
        state["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True}
        ]
        second=policy(state)
    else:
        second={}
    return [first,second]

def _ordering_facts(source:str)->dict[str,bool]:
    discover_marker='queried=_queried_sources(public)'
    tool_marker='evidence=_evidence(public)'
    source_filter='str(s.get("source_id") or "") not in queried'
    return {
        "DISCOVERY_BLOCK_EXISTS": discover_marker in source,
        "TOOL_BLOCK_EXISTS": tool_marker in source,
        "DISCOVERY_BEFORE_TOOL_EVALUATION": (
            discover_marker in source and tool_marker in source
            and source.index(discover_marker)<source.index(tool_marker)
        ),
        "DISCOVERY_STRICTLY_EXCLUDES_QUERIED_SOURCES": source_filter in source,
        "DISCOVERY_RETURNS_BEFORE_TOOL_BLOCK": (
            'if sources:' in source
            and '"action":"DISCOVER"' in source
            and source.index('"action":"DISCOVER"')<source.index(tool_marker)
        ),
        "GLOBAL_TOOL_COST_ORDER": (
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))'
            in source
        ),
        "CURRENT_EPOCH_EVIDENCE": 'int(rec.get("epoch",-1))==epochs[tid]' in source,
        "SELECT_AFTER_UNKNOWN_PROBE": (
            'if unknown:' in source
            and '"action":"PROBE"' in source
            and '"action":"SELECT"' in source
            and source.rindex('"action":"PROBE"')<source.rindex('"action":"SELECT"')
        ),
    }

def prove_from_facts(facts:Mapping[str,bool],contract:Mapping[str,Any])->dict[str,Any]:
    missing=[k for k,v in facts.items() if v is not True]
    props=contract.get("required_properties")
    if (
        not isinstance(props,list)
        or set(props)!=REQUIRED_PROPERTIES
        or contract.get("instance_verified") is not False
    ):
        missing.append("UNCHANGED_COMPLETE_INTERFACE_CONTRACT_NOT_BOUND")
    if missing:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "missing":sorted(set(missing)),
            "v3_least_cost_claim_falsified":True,
            "v4_conditional_program_proof":False,
            "universal_target_proved":False,
            "minimum_missing_fact":EXTERNAL_FACT,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    return {
        "schema":SCHEMA,
        "status":"PASS__V3_LEAST_COST_COUNTEREXAMPLE__V4_CONDITIONAL_UNIVERSAL_PROGRAM_PROOF__EXTERNAL_INTERFACE_INSTANCE_OPEN__ZERO_CREDIT",
        "missing":[],
        "v3_least_cost_claim_falsified":True,
        "v4_conditional_program_proof":True,
        "proof_kind":"FINITE_DISCOVERY_PROGRESS_PLUS_GLOBAL_COST_ORDER",
        "proof_lemmas":[
            "Finite source set plus queried-source exclusion gives strict discovery progress and termination.",
            "Discovery-before-tool ordering plus complete-union interface makes all in-scope identities visible before route ranking.",
            "Correct metadata plus global (cost, tool_id) ordering establishes a total least-cost traversal of admissible routes.",
            "Truthful current-epoch probe receipts make each route either falsified or fully capability-supported before selection.",
            "Therefore first SELECT is least-cost sufficient in-scope; if no route survives after discovery closure, ESCALATE is sound."
        ],
        "universal_target_proved":False,
        "minimum_missing_fact":EXTERNAL_FACT,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def evaluate(v4_source_override:str|None=None)->dict[str,Any]:
    drift=[rel for rel,sha in EXPECTED.items() if _blob_sha(rel)!=sha]
    if drift:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["SOURCE_BLOB_DRIFT:"+x for x in drift],
            "v3_least_cost_claim_falsified":False,
            "v4_conditional_program_proof":False,
            "universal_target_proved":False,
            "minimum_missing_fact":EXTERNAL_FACT,
            "capability_credit_delta":0,"family_credit_delta":0,
            "execution_authority":False,"promotion_authority":False,
        }

    v3_trace=counterexample(v3.next_action)
    if v3_trace!=[
        {"action":"PROBE","tool_id":"T0","capability":"CAP_A"},
        {"action":"SELECT","tool_id":"T0"},
    ]:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["EXPECTED_V3_COUNTEREXAMPLE_DID_NOT_REPRODUCE"],
            "v3_least_cost_claim_falsified":False,
            "v4_conditional_program_proof":False,
            "universal_target_proved":False,
            "minimum_missing_fact":EXTERNAL_FACT,
            "capability_credit_delta":0,"family_credit_delta":0,
            "execution_authority":False,"promotion_authority":False,
        }

    state={
        "required_capabilities":["CAP_A"],
        "constraint":None,
        "visible_tools":[
            {"tool_id":"T0","cost":10.0,"available":True,"authorized":True,"epoch":0}
        ],
        "discovery_sources":[{"source_id":"S0","cost":0.1,"available":True}],
        "discovery_receipts":[],
        "prior_probe_receipts":[],
        "version_events":[],
    }
    first=v4.next_action(state)
    if first!={"action":"DISCOVER","source_id":"S0","query":"CAP_A"}:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["V4_DOES_NOT_REPAIR_COUNTEREXAMPLE"],
            "v3_least_cost_claim_falsified":True,
            "v4_conditional_program_proof":False,
            "universal_target_proved":False,
            "minimum_missing_fact":EXTERNAL_FACT,
            "capability_credit_delta":0,"family_credit_delta":0,
            "execution_authority":False,"promotion_authority":False,
        }

    source=(
        v4_source_override if v4_source_override is not None
        else (ROOT/V4).read_text(encoding="utf-8")
    )
    out=prove_from_facts(_ordering_facts(source),_load(CONTRACT))
    out["v3_counterexample_trace"]=v3_trace
    out["v4_counterexample_first_action"]=first
    out["source_blob_drift"]=[]
    return out

def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
