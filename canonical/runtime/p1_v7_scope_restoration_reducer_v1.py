"""Fail-closed P1 V7 scope-restoration reducer after the authorized recovery batch.

This reducer is deliberately unable to lift the historical P1 quarantine by
itself. It proves only lift eligibility by combining:
- the independently adjudicated one-use 192/192 failure-semantics transport batch;
- independently verified current V7 mechanism/provenance hardening;
- the frozen P1 required-check/mutation set; and
- preserved clean T0/T2 terminal intervention/rescue receipts.

A separate independently verified quarantine-lift reducer is required after this
candidate itself receives independent exact-byte verification.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof
from canonical.runtime.p1_v7_provenance_mutation_closure_v1 import evaluate as provenance_probe

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V7_SCOPE_RESTORATION_VERDICT_V1"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"

RECOVERY="canonical/verification/P1_PUBLIC_RECOVERY_RESULT_INDEPENDENT_ADJUDICATION_20261003_V1.json"
V7="canonical/verification/P1_V7_CURRENT_MAIN_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
PROV="canonical/verification/P1_V7_PROVENANCE_AND_MINIMUM_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
BINDING="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
WAVE="canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
QUARANTINE="canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"

EXPECTED_SURFACES={
 "P1_FAILURE_SEMANTICS_TRANSPORT_FRONTIERCODE",
 "P1_FAILURE_SEMANTICS_TRANSPORT_CURSORBENCH",
 "P1_FAILURE_SEMANTICS_TRANSPORT_RECOVERY_SCOPE_COMPOSITION",
}
V7_CHECKS={
 "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
 "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
 "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
 "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}
TERMINAL_CHECKS={
 "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
 "NOMINATED_REPAIR_IS_FALSIFIABLE",
 "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
 "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
}
V7_MUTATIONS={
 "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT",
 "FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE",
 "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN",
 "SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS",
 "DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
 "UNFALSIFIABLE_DIAGNOSIS",
}
TERMINAL_MUTATIONS={
 "SELECT_DOWNSTREAM_SYMPTOM",
 "SELECT_LATER_CORRELATED_STEP",
 "REPAIR_TARGET_WITH_NO_RESCUE",
}

def _load(rel:str)->dict[str,Any]:
    obj=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return obj

def _p1_receipt(wave:Mapping[str,Any], tier:str)->Mapping[str,Any]|None:
    rows=(((wave.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts") or {}).get(tier,[])
    hits=[x for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR]
    return hits[0] if len(hits)==1 else None

def _solve_case(*,seed:int,pattern:str,domain:str,kind:str)->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    case=proof.generate_case(seed,pattern=pattern,domain=domain,kind=kind)
    public=proof.public_task(case)
    out=candidate.solve(copy.deepcopy(public))
    verdict=proof.score_case(case,out)
    return case,out,verdict

def _executable_mutation_probes()->dict[str,Any]:
    errors:list[str]=[]

    # Exact current V7 provenance mutation closure.
    prov=provenance_probe()
    if prov.get("pass") is not True or prov.get("scorer_pass_after_mutation") is not False:
        errors.append("DROP_PROVENANCE_MUTATION_NOT_KILLED")

    # Exact V6 scorer rejects arbitrary unfalsifiable diagnosis baggage.
    case,out,base=_solve_case(seed=81001,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
    mutated=copy.deepcopy(out)
    mutated["diagnosis"]={
        "claim":"UNOBSERVABLE_ASSERTION",
        "falsifiable":False,
        "supporting_receipts":[],
    }
    diagnosis_verdict=proof.score_case(case,mutated)
    if base.get("pass") is not True or diagnosis_verdict.get("pass") is not False or diagnosis_verdict.get("reason")!="OUTPUT_SCHEMA_NOT_EXACT":
        errors.append("UNFALSIFIABLE_DIAGNOSIS_MUTATION_NOT_KILLED")

    # Mechanism classification / authority-scope classes are exact and load-bearing.
    _,auth_out,auth_v=_solve_case(seed=81002,pattern="SINGLE",domain="BROWSER",kind="AUTHORITY")
    if auth_v.get("pass") is not True or auth_out.get("mechanism_classes")!=["AUTHORITY"]:
        errors.append("AUTHORITY_MECHANISM_NOT_EXACT")

    _,scope_out,scope_v=_solve_case(seed=81003,pattern="SINGLE",domain="TOOL_API",kind="SCOPE")
    if scope_v.get("pass") is not True or scope_out.get("mechanism_classes")!=["SCOPE"]:
        errors.append("SCOPE_MECHANISM_NOT_EXACT")

    # Nonidentifiability: forcing a unique cause must fail the unchanged scorer.
    amb_case,amb_out,amb_v=_solve_case(seed=81004,pattern="AMBIGUOUS",domain="FILESYSTEM",kind="SCHEMA")
    forced=copy.deepcopy(amb_out)
    forced["cause_action_id"]="A1"
    forced_v=proof.score_case(amb_case,forced)
    if amb_v.get("pass") is not True or forced_v.get("pass") is not False or forced_v.get("reason")!="NONIDENTIFIABILITY_OVERCLAIM":
        errors.append("FORCE_UNIQUE_CAUSE_MUTATION_NOT_KILLED")

    # Multi-root interaction: dropping one causal predecessor must fail.
    int_case,int_out,int_v=_solve_case(seed=81005,pattern="INTERACTION",domain="CODE",kind="DEPENDENCY")
    dropped=copy.deepcopy(int_out)
    dropped["cause_action_ids"]=dropped.get("cause_action_ids",[])[:1]
    dropped_v=proof.score_case(int_case,dropped)
    if int_v.get("pass") is not True or dropped_v.get("pass") is not False:
        errors.append("DROP_CAUSAL_PREDECESSOR_MUTATION_NOT_KILLED")

    # Delayed causal root: selecting the downstream derived symptom must fail.
    delayed_case,delayed_out,delayed_v=_solve_case(seed=81006,pattern="DELAYED",domain="ARTIFACT",kind="INVARIANT")
    symptom=copy.deepcopy(delayed_out)
    symptom["cause_action_id"]="A4"
    symptom["cause_action_ids"]=["A4"]
    symptom["critical_action_id"]="A4"
    delayed_bad=proof.score_case(delayed_case,symptom)
    if delayed_v.get("pass") is not True or delayed_bad.get("pass") is not False:
        errors.append("DOWNSTREAM_OR_LATE_CAUSE_MUTATION_NOT_KILLED")

    # A claimed repair that does not clear the full causal slice must not rescue.
    int_partial=copy.deepcopy(int_out)
    int_partial["repair_targets"]=int_partial.get("repair_targets",[])[:1]
    iv=proof.execute_intervention(proof.public_task(int_case),int_partial)
    if iv.get("terminal_rescued") is not False:
        errors.append("PARTIAL_NONRESCUING_REPAIR_NOT_KILLED")

    return {
        "pass":not errors,
        "errors":sorted(set(errors)),
        "drop_provenance":prov,
        "unfalsifiable_diagnosis_rejected":diagnosis_verdict.get("reason")=="OUTPUT_SCHEMA_NOT_EXACT",
        "authority_mechanism_exact":auth_v.get("pass") is True,
        "scope_mechanism_exact":scope_v.get("pass") is True,
        "forced_unique_cause_rejected":forced_v.get("pass") is False,
        "dropped_interaction_root_rejected":dropped_v.get("pass") is False,
        "downstream_delayed_root_rejected":delayed_bad.get("pass") is False,
        "partial_repair_not_rescue":iv.get("terminal_rescued") is False,
    }

def evaluate(
    recovery:Mapping[str,Any]|None=None,
    v7:Mapping[str,Any]|None=None,
    prov:Mapping[str,Any]|None=None,
    binding:Mapping[str,Any]|None=None,
    wave:Mapping[str,Any]|None=None,
    quarantine:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    recovery=dict(recovery or _load(RECOVERY))
    v7=dict(v7 or _load(V7))
    prov=dict(prov or _load(PROV))
    binding=dict(binding or _load(BINDING))
    wave=dict(wave or _load(WAVE))
    quarantine=dict(quarantine or _load(QUARANTINE))
    errors:list[str]=[]

    if binding.get("behavior_id")!=BEHAVIOR:
        errors.append("P1_BINDING_BEHAVIOR_DRIFT")
    evaluator=binding.get("evaluator") if isinstance(binding.get("evaluator"),Mapping) else {}
    required_checks=set(evaluator.get("required_checks") or [])
    required_mutations=set(evaluator.get("required_mutations") or [])
    if V7_CHECKS|TERMINAL_CHECKS != required_checks or V7_CHECKS&TERMINAL_CHECKS:
        errors.append("REQUIRED_CHECK_PARTITION_NOT_EXACT")
    if V7_MUTATIONS|TERMINAL_MUTATIONS != required_mutations or V7_MUTATIONS&TERMINAL_MUTATIONS:
        errors.append("REQUIRED_MUTATION_PARTITION_NOT_EXACT")

    expected_recovery_status="INDEPENDENT_PUBLIC_RUNNER_PASS__ONE_FRESH_P1_REALITY_UNIT__192_OF_192_DUAL_SCORER_PASS__THREE_FAILURE_SEMANTICS_TRANSPORT_REQUIREMENTS_DISCHARGED"
    if recovery.get("status")!=expected_recovery_status:
        errors.append("RECOVERY_ADJUDICATION_NOT_EXACT_INDEPENDENT_PASS")
    verified=recovery.get("verified") if isinstance(recovery.get("verified"),Mapping) else {}
    if verified.get("cases")!=192 or verified.get("passes")!=192 or verified.get("failures")!=0:
        errors.append("RECOVERY_NOT_192_OF_192")
    if verified.get("surface_count")!=3 or verified.get("passes_per_surface")!=64:
        errors.append("RECOVERY_SURFACE_COVERAGE_INVALID")
    if verified.get("both_failure_semantics_classes_present_every_case") is not True:
        errors.append("RECOVERY_SEMANTICS_CLASSES_INCOMPLETE")
    if verified.get("v7_intervention_scorer_all_pass") is not True or verified.get("source_native_rescue_scorer_all_pass") is not True:
        errors.append("RECOVERY_DUAL_SCORER_NOT_ALL_PASS")
    if verified.get("p1_failure_semantics_transport_pass") is not True:
        errors.append("RECOVERY_TRANSPORT_FACT_NOT_PASS")
    if set(verified.get("transport_requirements_discharged") or [])!=EXPECTED_SURFACES:
        errors.append("RECOVERY_TRANSPORT_REQUIREMENT_SET_DRIFT")
    if recovery.get("fresh_reality_units_consumed")!=1 or recovery.get("terminal_v3_replayed")!=0 or recovery.get("incremental_spend_usd")!=0:
        errors.append("RECOVERY_REALITY_OR_REPLAY_ACCOUNTING_INVALID")
    if recovery.get("execution_authority_consumed") is not True or recovery.get("p1_quarantine_lifted") is not False:
        errors.append("RECOVERY_AUTHORITY_BOUNDARY_INVALID")

    if not str(v7.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_CURRENT_MAIN_V7_BYTES"):
        errors.append("V7_CURRENT_MAIN_NOT_INDEPENDENT_PASS")
    props=set(v7.get("verified_properties") or [])
    for needed in {
        "INHERITED_V6_192_CASE_SUITE_PRESERVED",
        "DERIVED_ONLY_FAILURE_IS_NOT_PROMOTED_TO_CAUSAL_ROOT",
        "SERIAL_DIRECT_COFAULT_RETAINS_BOTH_DIRECT_REPAIRS",
        "FAILURE_SEMANTICS_IS_LOAD_BEARING",
        "INVALID_FAILURE_SEMANTICS_FAILS_CLOSED",
    }:
        if needed not in props:
            errors.append("V7_PROPERTY_MISSING:"+needed)

    if not str(prov.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__V7_KILLS_DROP_PROVENANCE__EXACT_MINIMUM_REALITY_ONE_SHARED_P1_BATCH"):
        errors.append("V7_PROVENANCE_MIN_REALITY_NOT_INDEPENDENT_PASS")
    result=prov.get("result") if isinstance(prov.get("result"),Mapping) else {}
    if result.get("provenance_mutation_closed_under_current_v7") is not True:
        errors.append("V7_PROVENANCE_MUTATION_NOT_CLOSED")
    if result.get("remaining_p1_information_residual")!="FAILURE_SEMANTICS_TRANSPORT_TO_THREE_FROZEN_DIRECT_SURFACES":
        errors.append("PRE_RECOVERY_RESIDUAL_NOT_EXACT_FAILURE_SEMANTICS")
    if result.get("selected_observation")!="P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH" or result.get("minimum_new_reality_units")!=1:
        errors.append("MINIMUM_REALITY_SELECTION_DRIFT")

    if quarantine.get("independent_scope_mismatch_proved") is not True:
        errors.append("PRIOR_QUARANTINE_NOT_INDEPENDENT")
    if "WHOLE_FROZEN_P1_CONTRACT_PASS" not in set(quarantine.get("quarantine_active") or []):
        errors.append("PRIOR_P1_QUARANTINE_NOT_ACTIVE")

    historical_cases=0
    for tier in ("T0","T2"):
        row=_p1_receipt(wave,tier)
        if row is None:
            errors.append("TERMINAL_P1_RECEIPT_MISSING:"+tier)
            continue
        for k in ("load_bearing","direct_instrumentation_pass","parent_terminal_acceptance_pass"):
            if row.get(k) is not True:
                errors.append(f"TERMINAL_P1_{tier}_{k.upper()}_NOT_TRUE")
        for k in ("case_replaced","tuning_replay","result_to_runtime_feedback"):
            if row.get(k) is not False:
                errors.append(f"TERMINAL_P1_{tier}_{k.upper()}_NOT_FALSE")
        try:
            historical_cases += int(str(row.get("case_id")).rsplit("::",1)[-1])
        except Exception:
            errors.append("TERMINAL_P1_CASE_COUNT_INVALID:"+tier)
    if historical_cases!=60:
        errors.append("TERMINAL_P1_HISTORICAL_CASE_COUNT_NOT_60")

    probes=_executable_mutation_probes()
    errors.extend("PROBE:"+x for x in probes["errors"])

    unique=sorted(set(errors))
    eligible=not unique
    return {
        "schema":SCHEMA,
        "status":"PASS__P1_V7_COMPOSITE_SCOPE_RESTORATION_PROVED__QUARANTINE_LIFT_ELIGIBLE__SEPARATE_INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT" if eligible else "FAIL_CLOSED",
        "pass":eligible,
        "errors":unique,
        "behavior_id":BEHAVIOR,
        "recovery_transport_requirements_closed":eligible,
        "required_check_partition_complete":eligible,
        "required_mutation_partition_complete":eligible,
        "historical_terminal_intervention_receipts_preserved":eligible,
        "historical_terminal_p1_case_count":historical_cases,
        "v7_executable_mutation_probes":probes,
        "whole_p1_contract_restoration_candidate":eligible,
        "quarantine_lift_eligible":eligible,
        "quarantine_lifted":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "terminal_credit_delta":0,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "incremental_spend_usd":0,
        "execution_authority":False,
        "promotion_authority":False,
        "rule":"FRESH_RECOVERY_RECEIPT_CLOSES_ONLY_THE_PREDECLARED_FAILURE_SEMANTICS_TRANSPORT_RESIDUAL__CURRENT_V7_MUST_EXECUTABLY_KILL_PRIOR_COMPOSITE_COUNTEREXAMPLES__HISTORICAL_T0_T2_INTERVENTION_RECEIPTS_REMAIN_IMMUTABLE__THIS_REDUCER_CANNOT_SELF_LIFT_QUARANTINE",
        "next":"INDEPENDENTLY_VERIFY_EXACT_RESTORATION_REDUCER_AND_INPUT_BLOBS__ONLY_THEN_RUN_SEPARATE_MONOTONIC_P1_QUARANTINE_LIFT_AND_RECOMPUTE_FAMILY_ACCEPTANCE_FIXED_POINT",
    }

def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
