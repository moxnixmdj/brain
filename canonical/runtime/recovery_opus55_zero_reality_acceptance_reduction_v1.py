"""Zero-reality strict Recovery acceptance reduction candidate.

This reducer never uses the quarantined P1 public recovery batch. It combines:
1) the frozen Recovery target-to-P1 semantic/metric relation,
2) the independently verified universal P1 generator theorem,
3) the independently verified exact scope reduction, and
4) the independently verified P1 whole-scope restoration.

It answers only whether the three frozen Recovery acceptance predicates are
eligible for independent promotion by a scope-complete stronger proof at
objective ceiling/floor. It does not mutate the acceptance ledger itself.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_RECOVERY_OPUS55_ZERO_REALITY_ACCEPTANCE_REDUCTION_V1"

REL="canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json"
THEOREM="canonical/verification/P1_UNIVERSAL_GENERATOR_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
SCOPE="canonical/verification/P1_UNIVERSAL_GENERATOR_TRANSPORT_SCOPE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
RESTORE="canonical/verification/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
BINDING="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
TARGETS="canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V2.json"
PRED="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
REG="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

EXPECTED={
 REL:"5159f145fad8b07fe2164716aedf653a0b34a6e0",
 THEOREM:"95422fdb13ada158930486442c9441c9c5cd9852",
 SCOPE:"f327bfdb5d52bb9551b52f67da14a4cd425533a3",
 RESTORE:"2c6bb594d353e4c6a169821da5f84a91be212ca7",
 BINDING:"8703c6aa08227467a619a7ae90d0d61f8e54da39",
 TARGETS:"65978d10375093162f24fa61f5fce6cc1ba4d179",
 PRED:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 REG:"ee187f611a0e82b2de495ee377682f39bc31dd31",
}

RECOVERY={
 "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
 "RECOVERY_TERMINAL_NONINFERIOR",
 "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
}
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"

def blob(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(path:str)->dict[str,Any]:
    obj=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError(path+":NOT_OBJECT")
    return obj

def target_map(obj:dict[str,Any])->dict[str,dict[str,Any]]:
    return {x["predicate_id"]:x for x in obj.get("targets",[]) if isinstance(x,dict) and x.get("predicate_id")}

def predicate_map(obj:dict[str,Any])->dict[str,dict[str,Any]]:
    return {x["id"]:x for x in obj.get("predicates",[]) if isinstance(x,dict) and x.get("id")}

def evaluate()->dict[str,Any]:
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","pass":False,
                "errors":["SOURCE_BLOB_DRIFT"],"drift":drift,"promotion_authority":False}

    rel,theorem,scope,restore,binding,targets,pred,reg=map(load,(REL,THEOREM,SCOPE,RESTORE,BINDING,TARGETS,PRED,REG))
    errors:list[str]=[]
    def req(cond:bool,code:str):
        if not cond: errors.append(code)

    req(rel.get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY","RELATION_FAMILY")
    req(rel.get("source_behavior_id")==BEHAVIOR,"RELATION_BEHAVIOR")
    req(rel.get("relation")=="QUARANTINED","RELATION_EXPECTED_HISTORICAL_QUARANTINE")
    basis=rel.get("family_scope_basis") or {}
    req(basis.get("exact_family_to_residual_contracts")==[BEHAVIOR],"RECOVERY_EXACT_ONE_CONTRACT_BASIS")
    req("EXECUTED_TERMINAL_P1_SCORER_IS_NARROWER_THAN_THE_FROZEN_P1_BINDING" in set(rel.get("limitations") or []),
        "HISTORICAL_QUARANTINE_CAUSE_MISSING")

    tv=theorem.get("verified") or {}
    req(str(theorem.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"THEOREM_NOT_INDEPENDENT_PASS")
    req(tv.get("structural_equivalence_classes")==30,"THEOREM_CLASS_COUNT")
    req(tv.get("deterministic_proof_executions")==2292,"THEOREM_EXECUTION_COUNT")
    req(tv.get("all_v7_intervention_scorer_pass") is True,"INTERVENTION_SCORER_NOT_UNIVERSAL_PASS")
    req(tv.get("all_source_native_rescue_scorer_pass") is True,"NATIVE_RESCUE_NOT_UNIVERSAL_PASS")
    req(tv.get("quarantined_execution_used_as_proof") is False,"QUARANTINED_BATCH_USED")
    req(tv.get("new_reality_units_consumed")==0,"THEOREM_REALITY_NONZERO")

    sv=scope.get("verified") or {}
    req(str(scope.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"SCOPE_NOT_INDEPENDENT_PASS")
    req(sv.get("scope_relation")=="EXACT_FROZEN_SELECTION_DOMAIN_SUBSET_OF_EXHAUSTIVE_GENERATOR_QUOTIENT","SCOPE_RELATION")
    req(sv.get("all_three_transport_requirements_deductively_covered") is True,"TRANSPORT_NOT_COVERED")
    req(sv.get("remaining_failure_semantics_information_residual")==0,"P1_RESIDUAL_NONZERO")
    req(sv.get("quarantined_execution_used_as_proof") is False,"SCOPE_USED_QUARANTINED_BATCH")

    rv=restore.get("verified") or {}
    req(str(restore.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"RESTORE_NOT_INDEPENDENT_PASS")
    req(rv.get("whole_p1_contract_restored") is True,"P1_NOT_RESTORED")
    req(rv.get("whole_scope_contract_pass_count")==12,"WHOLE_SCOPE_NOT_12")
    req(rv.get("whole_scope_quarantined_contract_count")==0,"P1_QUARANTINE_REMAINS")
    req(rv.get("provisional_behavioral_family_pass_count")==19,"BEHAVIORAL_SCOPE_NOT_19")
    req((restore.get("decisive_source") or {}).get("quarantined_execution_used_as_proof") is False,"RESTORE_USED_QUARANTINED_BATCH")

    req(binding.get("behavior_id")==BEHAVIOR,"BINDING_BEHAVIOR")
    req(binding.get("proof_mode")=="T0_T2_MULTIPLEXED_DETERMINISTIC_INTERVENTION_RESCUE_GATE","BINDING_MODE")
    checks=set((binding.get("evaluator") or {}).get("required_checks") or [])
    for c in (
      "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
      "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
      "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
      "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
      "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
      "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
      "NOMINATED_REPAIR_IS_FALSIFIABLE",
      "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
    ):
        req(c in checks,"MISSING_BINDING_CHECK:"+c)

    tm=target_map(targets)
    pm=predicate_map(pred)
    req(RECOVERY.issubset(tm),"TARGET_NORMALIZATION_MISSING_RECOVERY")
    req(RECOVERY.issubset(pm),"PREDICATE_REGISTRY_MISSING_RECOVERY")
    for p in RECOVERY:
        req(pm[p].get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY","PREDICATE_FAMILY:"+p)

    expected_atoms={
      "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR":{
        "dimension:earliest_causal_failure_localization",
        "requirement:intervention_or_rescue_establishes_causality",
        "metric:true_root_cause_topk",
      },
      "RECOVERY_TERMINAL_NONINFERIOR":{
        "dimension:semantic_self_check","dimension:counterexample_discovery",
        "dimension:earliest_causal_failure_localization","dimension:repair_selection",
        "dimension:recovery_after_injected_failure","metric:terminal_recovery",
      },
      "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES":{"invariant:zero_critical_fail_closed_misses"},
    }
    for p,atoms in expected_atoms.items():
        req(set(tm[p].get("required_atoms") or [])==atoms,"TARGET_ATOMS_DRIFT:"+p)

    dim=rel.get("target_dimension_to_source_checks") or {}
    for k in ("semantic self-check","counterexample discovery","earliest causal failure localization",
              "repair selection","recovery after injected failure"):
        req(bool(dim.get(k)),"RELATION_DIMENSION_MISSING:"+k)

    bounds=rel.get("acceptance_to_objective_floor_ceiling") or {}
    causal=bounds.get("causal_localization") or {}
    terminal=bounds.get("terminal_recovery") or {}
    misses=bounds.get("critical_fail_closed_misses") or {}
    # Historical observed_bound values in REL came from the earlier terminal-era
    # relation and are deliberately NOT load-bearing here. The relation contributes
    # only semantic target mapping and theoretical ceiling/floor orientation.
    # Achieved universal bounds come from the independently verified universal
    # theorem plus whole-scope restoration above.
    req(causal.get("direction")=="higher" and causal.get("theoretical_bound")==1,
        "CAUSAL_THEORETICAL_CEILING_DRIFT")
    req(terminal.get("direction")=="higher" and terminal.get("theoretical_bound")==1,
        "RECOVERY_THEORETICAL_CEILING_DRIFT")
    req(misses.get("direction")=="lower" and misses.get("theoretical_bound")==0,
        "FAIL_CLOSED_THEORETICAL_FLOOR_DRIFT")

    fmap=reg.get("family_to_residual_contracts") or {}
    req(fmap.get("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")==[BEHAVIOR],"REGISTRY_RECOVERY_SCOPE_DRIFT")

    verdicts={
      "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR":"ELIGIBLE__SCOPE_COMPLETE_STRONGER_PROOF_AT_OBJECTIVE_CEILING",
      "RECOVERY_TERMINAL_NONINFERIOR":"ELIGIBLE__SCOPE_COMPLETE_STRONGER_PROOF_AT_OBJECTIVE_CEILING",
      "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES":"ELIGIBLE__SCOPE_COMPLETE_STRONGER_PROOF_AT_OBJECTIVE_FLOOR",
    }
    ok=not errors
    return {
      "schema":SCHEMA,
      "status":"PASS__RECOVERY_THREE_PREDICATES_ELIGIBLE_BY_SCOPE_COMPLETE_ZERO_REALITY_STRONGER_PROOF" if ok else "FAIL_CLOSED",
      "pass":ok,"errors":sorted(set(errors)),
      "family":"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
      "source_behavior_id":BEHAVIOR,
      "predicate_verdicts":verdicts if ok else {},
      "stronger_proof_basis":{
        "scope_complete":ok,
        "objective_ceiling_or_floor":ok,
        "universal_achieved_bounds":{
          "causal_localization":1 if ok else None,
          "terminal_recovery":1 if ok else None,
          "critical_fail_closed_misses":0 if ok else None,
        },
        "bound_derivation":"UNIVERSAL_INTERVENTION_AND_NATIVE_RESCUE_PASS_PLUS_INDEPENDENT_WHOLE_P1_CONTRACT_RESTORATION__NOT_HISTORICAL_OBSERVED_BOUND",
        "exact_opus_case_level_access_required":False if ok else None,
        "historical_narrow_terminal_run_used_as_proof":False,
        "historical_relation_observed_bound_used_as_proof":False,
        "quarantined_public_recovery_run_used_as_proof":False,
      },
      "proposed_atomic_acceptance_delta":3 if ok else 0,
      "proposed_family_acceptance_delta":1 if ok else 0,
      "promotion_eligible":ok,
      "new_reality_units_consumed":0,
      "terminal_results_replayed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "hard_nonclaims":[
        "THIS_REDUCER_DOES_NOT_MUTATE_THE_ACCEPTANCE_LEDGER",
        "NO_CREDIT_FROM_THE_OLD_NARROW_TERMINAL_P1_RESULT",
        "NO_CREDIT_FROM_RUN_37108111537",
        "INDEPENDENT_EXACT_BYTE_VERIFICATION_REQUIRED_BEFORE_ACCEPTANCE_PROMOTION",
      ],
    }

def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") is True else 1

if __name__=="__main__":
    raise SystemExit(main())
