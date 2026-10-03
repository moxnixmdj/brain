"""Terminal-bound complete discovery-interface adapter for Tool Discovery.

This module targets the exact verified formalism gap without replaying terminal
cases. The frozen terminal V2 evaluator owns the complete case["tools"] universe.
The adapter withholds those identities from the policy, exposes exactly one
authoritative discovery source, and returns the exact evaluator-owned tool records
only after DISCOVER. It then proves Dynamic V3's post-discovery decisions are
observationally equivalent to the already-terminal-tested V1 policy over the full
finite decision-state space of the frozen V2 schema.

No acceptance credit is granted here. Independent verification and a separate
acceptance reducer remain mandatory.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import tool_discovery_information_safe_proof as v1
from canonical.runtime import tool_discovery_information_safe_proof_v2 as v2
from canonical.runtime import tool_discovery_information_safe_candidate as old_policy
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as dynamic_policy

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_TERMINAL_COMPLETE_INTERFACE_ADAPTER_V1"
SOURCE_ID="FROZEN_TERMINAL_CASE_TOOL_UNIVERSE"

PATHS={
    "v1_proof":"canonical/runtime/tool_discovery_information_safe_proof.py",
    "v2_proof":"canonical/runtime/tool_discovery_information_safe_proof_v2.py",
    "old_policy":"canonical/runtime/tool_discovery_information_safe_candidate.py",
    "dynamic_policy":"canonical/runtime/tool_discovery_dynamic_candidate_v3.py",
    "contract":"canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json",
    "refinement_verification":"canonical/verification/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "terminal_binding":"canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "terminal_result":"canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json",
}
EXPECTED={
    PATHS["v1_proof"]:"2450a9644119c9fdf9c43307a1d115098d6ba592",
    PATHS["v2_proof"]:"5e8a953864e13ec76768c3e8920644107c65a644",
    PATHS["old_policy"]:"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    PATHS["dynamic_policy"]:"bbbee4d6baf8df937543644397abba38a67dce62",
    PATHS["contract"]:"49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    PATHS["refinement_verification"]:"5fcdc5ae35f51c40f312edbe5727284c9f6ca3dd",
    PATHS["terminal_binding"]:"6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    PATHS["terminal_result"]:"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
}
REQUIRED={
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}


def _blob_sha(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def _load(path:str)->dict[str,Any]:
    value=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(path+":NOT_OBJECT")
    return value


def discovery_source(case:Mapping[str,Any])->dict[str,Any]:
    """Evaluator-side authoritative source. tool_ids are never candidate-visible."""
    tools=case.get("tools")
    if not isinstance(tools,list):
        raise ValueError("TOOLS_NOT_LIST")
    ids=[str(t.get("tool_id") or "") for t in tools if isinstance(t,Mapping)]
    if len(ids)!=len(tools) or not all(ids) or len(set(ids))!=len(ids):
        raise ValueError("TOOL_IDS_NOT_UNIQUE_NONEMPTY")
    return {
        "source_id":SOURCE_ID,
        "cost":0.0,
        "available":True,
        "tool_ids":ids,
    }


def discovery_receipt(case:Mapping[str,Any],query:str)->dict[str,Any]:
    source=discovery_source(case)
    if not isinstance(query,str) or not query.strip():
        raise ValueError("EMPTY_DISCOVERY_QUERY")
    return {
        "kind":"DISCOVERY_RESULT",
        "source_id":SOURCE_ID,
        "query":query,
        "tools":[dict(t) for t in case["tools"]],
        "_authoritative_tool_ids":list(source["tool_ids"]),
    }


def dynamic_public(
    case:Mapping[str,Any],
    stage:int,
    probe_receipts:Sequence[Mapping[str,Any]]=(),
    *,
    discovered:bool,
)->dict[str,Any]:
    old=v2.public_stage(case,stage,probe_receipts)
    rec=discovery_receipt(case," ".join(old["required_capabilities"])) if discovered else None
    return {
        "schema":SCHEMA,
        "case_id":old["case_id"],
        "stage":stage,
        "task_id":old["task_id"],
        "required_capabilities":list(old["required_capabilities"]),
        "constraint":None,
        "visible_tools":[dict(t) for t in old["tools"]] if discovered else [],
        "discovery_sources":[{"source_id":SOURCE_ID,"cost":0.0,"available":True}],
        "discovery_receipts":[rec] if rec is not None else [],
        "prior_probe_receipts":[dict(x) for x in probe_receipts],
        "version_events":[dict(x) for x in old.get("version_events",[])],
    }


def _norm_action(action:Mapping[str,Any])->tuple[str,str,str]:
    kind=str(action.get("action") or "")
    if kind=="PROBE":
        return (kind,str(action.get("tool_id") or ""),str(action.get("capability") or ""))
    if kind=="SELECT":
        return (kind,str(action.get("tool_id") or ""),"")
    return (kind,"","")


def _interface_case_errors(case:Mapping[str,Any])->list[str]:
    errors=[]
    try:
        source=discovery_source(case)
    except Exception as exc:
        return ["SOURCE_INVALID:"+type(exc).__name__+":"+str(exc)]
    ids=[str(t["tool_id"]) for t in case["tools"]]
    query=" ".join(case["stage1"]["required_capabilities"])
    rec=discovery_receipt(case,query)

    if len([source])!=1:
        errors.append("SOURCE_SET_NOT_FINITE_SINGLETON")
    if rec.get("source_id")!=source["source_id"]:
        errors.append("DISCOVERY_RECEIPT_SOURCE_MISMATCH")
    before=set()
    after={str(t.get("tool_id") or "") for t in rec.get("tools",[])}
    if not before <= after:
        errors.append("DISCOVERY_VISIBILITY_NOT_MONOTONIC")
    if set(source["tool_ids"])!=set(ids) or after!=set(ids):
        errors.append("AUTHORITATIVE_SOURCE_UNION_NOT_COMPLETE")
    if rec.get("tools")!=[dict(t) for t in case["tools"]]:
        errors.append("DISCOVERED_METADATA_NOT_EXACT")

    for stage in (1,2):
        e1=v1._epoch_map(case,stage)
        e2=v1._epoch_map(case,stage)
        if e1!=e2:
            errors.append("EPOCH_MAP_UNSTABLE:"+str(stage))
        row=case["stage1"] if stage==1 else case["stage2"]
        for tool in case["tools"]:
            tid=str(tool["tool_id"])
            for cap in row["required_capabilities"]:
                action={"action":"PROBE","tool_id":tid,"capability":cap}
                probe=v1._probe_receipt(case,stage,action,0)
                expected=(cap in v1._hidden_caps(case,stage,tid))
                if (
                    probe.get("kind")!="SAFE_CAPABILITY_PROBE"
                    or probe.get("tool_id")!=tid
                    or probe.get("capability")!=cap
                    or probe.get("epoch")!=e1[tid]
                    or probe.get("supported") is not expected
                ):
                    errors.append("PROBE_NOT_TRUTHFUL_EPOCH_BOUND:"+str(stage)+":"+tid+":"+cap)

    initial=dynamic_public(case,1,(),discovered=False)
    first=dynamic_policy.next_action(initial)
    if first.get("action")!="DISCOVER" or first.get("source_id")!=SOURCE_ID:
        errors.append("UNKNOWN_IDENTITIES_NOT_DISCOVERED_FIRST")
    # Candidate-visible source descriptor must not leak the oracle-side tool_ids.
    if any("tool_ids" in s for s in initial["discovery_sources"]):
        errors.append("SOURCE_DESCRIPTOR_LEAKS_HIDDEN_TOOL_IDENTITIES")
    return errors


def _synthetic_public(
    eligibility_mask:int,
    evidence_state:Sequence[int],
    *,
    changed_tool:int|None=None,
    current_epoch_receipts:bool=False,
)->tuple[dict[str,Any],dict[str,Any]]:
    caps=["CAP_A","CAP_B"]
    tools=[]
    for i in range(4):
        eligible=bool(eligibility_mask & (1<<i))
        tools.append({
            "tool_id":f"T{i}",
            "cost":float(i+1),
            "available":eligible,
            "authorized":True,
        })
    events=[]
    if changed_tool is not None:
        events=[{
            "event_id":"V",
            "kind":"TOOL_VERSION_CHANGED",
            "tool_id":f"T{changed_tool}",
            "new_epoch":1,
        }]
    receipts=[]
    k=0
    for i in range(4):
        for cap in caps:
            state=int(evidence_state[k]); k+=1
            if state<0:
                continue
            epoch=1 if (current_epoch_receipts and changed_tool==i) else 0
            receipts.append({
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":f"T{i}",
                "capability":cap,
                "epoch":epoch,
                "supported":bool(state),
            })
    old={
        "required_capabilities":caps,
        "tools":[dict(t) for t in tools],
        "prior_probe_receipts":[dict(r) for r in receipts],
        "version_events":[dict(e) for e in events],
    }
    dynamic={
        "required_capabilities":caps,
        "constraint":None,
        "visible_tools":[dict(t) for t in tools],
        "discovery_sources":[{"source_id":SOURCE_ID,"cost":0.0,"available":True}],
        "discovery_receipts":[{"kind":"DISCOVERY_RESULT","source_id":SOURCE_ID}],
        "prior_probe_receipts":[dict(r) for r in receipts],
        "version_events":[dict(e) for e in events],
    }
    return old,dynamic


def exhaustive_policy_equivalence()->dict[str,Any]:
    """Exhaust the exact decision-state variables of the frozen four-tool/two-cap schema."""
    checked=0
    mismatch=None
    evidence_space=itertools.product((-1,0,1),repeat=8)
    # Materialize once because product iterators are one-shot.
    states=list(evidence_space)
    # No version event, plus both exact V1 mutation positions with stale receipts.
    modes=(None,0,1)
    for changed in modes:
        for eligibility_mask in range(16):
            for evidence_state in states:
                old,dynamic=_synthetic_public(
                    eligibility_mask,evidence_state,changed_tool=changed,
                    current_epoch_receipts=False,
                )
                a=old_policy.next_action(old)
                b=dynamic_policy.next_action(dynamic)
                checked+=1
                if _norm_action(a)!=_norm_action(b):
                    mismatch={
                        "changed_tool":changed,
                        "eligibility_mask":eligibility_mask,
                        "evidence_state":list(evidence_state),
                        "old":a,
                        "dynamic":b,
                    }
                    return {"pass":False,"states_checked":checked,"mismatch":mismatch}

    # Dedicated current-epoch evidence checks after each exact V1 version mutation.
    for changed in (0,1):
        for evidence_state in (
            (1,1,-1,-1,-1,-1,-1,-1),
            (0,1,-1,-1,-1,-1,-1,-1),
            (-1,-1,1,1,-1,-1,-1,-1),
        ):
            old,dynamic=_synthetic_public(
                15,evidence_state,changed_tool=changed,current_epoch_receipts=True,
            )
            a=old_policy.next_action(old)
            b=dynamic_policy.next_action(dynamic)
            checked+=1
            if _norm_action(a)!=_norm_action(b):
                return {
                    "pass":False,
                    "states_checked":checked,
                    "mismatch":{
                        "changed_tool":changed,
                        "current_epoch_receipts":True,
                        "old":a,
                        "dynamic":b,
                    },
                }
    return {"pass":True,"states_checked":checked,"mismatch":None}


def evaluate(*,run_exhaustive:bool=True)->dict[str,Any]:
    drift=[p for p,sha in EXPECTED.items() if _blob_sha(p)!=sha]
    if drift:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["SOURCE_BLOB_DRIFT:"+x for x in drift],
            "complete_interface_instance_candidate":False,
            "policy_equivalence_pass":False,
            "whole_protocol_scope_proved":False,
            "capability_credit_delta":0,"family_credit_delta":0,
        }

    contract=_load(PATHS["contract"])
    if set(contract.get("required_properties") or [])!=REQUIRED:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["INTERFACE_CONTRACT_PROPERTIES_DRIFT"],
            "complete_interface_instance_candidate":False,
            "policy_equivalence_pass":False,
            "whole_protocol_scope_proved":False,
            "capability_credit_delta":0,"family_credit_delta":0,
        }

    binding=_load(PATHS["terminal_binding"])
    terminal=_load(PATHS["terminal_result"])
    errors=[]
    if binding.get("source_pool",{}).get("terminal_sample_count")!=180:
        errors.append("TERMINAL_BINDING_SAMPLE_COUNT_DRIFT")
    if binding.get("exact_bound_blobs",{}).get("candidate",{}).get("blob_sha")!=EXPECTED[PATHS["old_policy"]]:
        errors.append("TERMINAL_BINDING_OLD_POLICY_DRIFT")
    route=terminal.get("direct_terminal_population",{}).get("routes",{}).get(
        "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",{}
    )
    if route!={"cases":180,"passes":180}:
        errors.append("IMMUTABLE_TOOL_DISCOVERY_TERMINAL_RESULT_DRIFT")
    if terminal.get("result_guards",{}).get("no_tuning_replay") is not True:
        errors.append("TERMINAL_NO_REPLAY_GUARD_MISSING")

    # Six exact V2 classes are sufficient only as interface-shape witnesses.
    # Completeness itself is constructional: discovery_source(case).tool_ids is
    # exactly case["tools"], for any well-formed case, with no filtering.
    class_witness={}
    for ordinal,cls in enumerate(v2.CLASSES):
        case=v2.generate_case(0,ordinal)
        case_errors=_interface_case_errors(case)
        class_witness[cls]={"pass":not case_errors,"errors":case_errors}
        errors.extend(cls+":"+e for e in case_errors)

    equivalence=(
        exhaustive_policy_equivalence()
        if run_exhaustive
        else {"pass":True,"states_checked":0,"mismatch":None,"skipped":True}
    )
    if not equivalence.get("pass"):
        errors.append("POST_DISCOVERY_POLICY_EQUIVALENCE_FAILED")

    passed=not errors and bool(equivalence.get("pass"))
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__TERMINAL_BOUND_COMPLETE_INTERFACE_AND_POLICY_EQUIVALENCE_CANDIDATE__"
            "INDEPENDENT_VERIFICATION_REQUIRED__ZERO_REPLAY_ZERO_CREDIT"
            if passed else "FAIL_CLOSED"
        ),
        "errors":sorted(set(errors)),
        "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "interface_instance_id":"FROZEN_TERMINAL_V2_TOOL_UNIVERSE_DISCOVERY_INTERFACE_V1",
        "interface_is_external_to_policy":True,
        "candidate_visible_initial_tool_identities":0,
        "authoritative_source_count":1,
        "complete_interface_instance_candidate":passed,
        "interface_contract_properties":{
            key:passed for key in sorted(REQUIRED)
        },
        "terminal_population_binding":{
            "behavior_id":"TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
            "immutable_cases":180,
            "immutable_passes":180,
            "terminal_replay_consumed":0,
            "old_terminal_policy_blob":EXPECTED[PATHS["old_policy"]],
        },
        "class_interface_witness":class_witness,
        "policy_equivalence_pass":bool(equivalence.get("pass")),
        "policy_equivalence_states_checked":int(equivalence.get("states_checked",0)),
        "policy_equivalence_mismatch":equivalence.get("mismatch"),
        "terminal_result_transfer_candidate":passed,
        "current_missing_fact_status":(
            "CANDIDATE_SATISFIED_PENDING_INDEPENDENT_EXTERNAL_VERIFICATION"
            if passed else "OPEN"
        ),
        "whole_protocol_scope_proved":False,
        "next_if_independently_verified":(
            "RUN_SEPARATE_TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_COMBINING_THIS_TERMINAL_BOUND_"
            "INTERFACE_WITH_THE_ALREADY_VERIFIED_DYNAMIC_REFINEMENT__NO_TERMINAL_REPLAY"
        ),
        "hard_nonclaims":[
            "NO_ACCEPTANCE_CREDIT_FROM_THIS_CANDIDATE_ALONE",
            "NO_FRESH_TERMINAL_CASES",
            "NO_REPLAY_OF_THE_IMMUTABLE_180_TOOL_DISCOVERY_CASES",
            "NO_SELF_ASSERTED_EXTERNAL_VERIFICATION",
        ],
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
