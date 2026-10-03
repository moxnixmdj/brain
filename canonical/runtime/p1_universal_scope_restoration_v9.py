"""Fail-closed zero-reality P1 whole-scope restoration reducer.

Restores only the behavioral scope quarantine after the independently verified
universal generator theorem has deductively discharged the exact three frozen
failure-semantics transport requirements. It never reads the quarantined
192-case recovery execution and grants zero Opus-5.5 acceptance credit.
"""
from __future__ import annotations
import copy, json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
BINDING=ROOT/"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
V7_CURRENT=ROOT/"canonical/verification/P1_V7_CURRENT_MAIN_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V7_PROVENANCE=ROOT/"canonical/verification/P1_V7_PROVENANCE_AND_MINIMUM_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
V6=ROOT/"canonical/verification/P1_TYPED_CAUSAL_INTERVENTION_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
SCOPE_AUDIT=ROOT/"canonical/verification/P1_TERMINAL_EXECUTION_SCOPE_AUDIT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
POSTWAVE=ROOT/"canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"
QUARANTINE=ROOT/"canonical/verification/TERMINAL_SCOPE_QUARANTINE_PROPAGATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
REGISTRY=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
UNIVERSAL_SCOPE=ROOT/"canonical/verification/P1_UNIVERSAL_GENERATOR_TRANSPORT_SCOPE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"

BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
REQ={
 "P1_FAILURE_SEMANTICS_TRANSPORT_CURSORBENCH",
 "P1_FAILURE_SEMANTICS_TRANSPORT_FRONTIERCODE",
 "P1_FAILURE_SEMANTICS_TRANSPORT_RECOVERY_SCOPE_COMPOSITION",
}
CHECKS={
 "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
 "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
 "NOMINATED_REPAIR_IS_FALSIFIABLE",
 "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
 "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
 "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
 "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
 "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}
MUTATIONS={
 "SELECT_DOWNSTREAM_SYMPTOM","SELECT_LATER_CORRELATED_STEP",
 "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT","UNFALSIFIABLE_DIAGNOSIS",
 "REPAIR_TARGET_WITH_NO_RESCUE","FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE",
 "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN","SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS",
 "DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
}
FAMILIES={
 "ADVANCED_AGENTIC_CODING","AGENTIC_SCIENTIFIC_RESEARCH",
 "BUSINESS_WORKFLOW_AUTOMATION","COMPLEX_MULTI_TOOL_AGENCY",
 "COMPUTER_AND_BROWSER_USE","INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
 "MULTI_CAPABILITY_COMPOSITION","SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
}

def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text())
    if not isinstance(x,dict): raise ValueError(str(p)+":NOT_OBJECT")
    return x

def evaluate(*,binding:Mapping[str,Any]|None=None,v7_current:Mapping[str,Any]|None=None,
             v7_provenance:Mapping[str,Any]|None=None,v6:Mapping[str,Any]|None=None,
             scope_audit:Mapping[str,Any]|None=None,postwave:Mapping[str,Any]|None=None,
             quarantine:Mapping[str,Any]|None=None,registry:Mapping[str,Any]|None=None,
             universal_scope:Mapping[str,Any]|None=None)->dict[str,Any]:
    binding=copy.deepcopy(dict(binding or load(BINDING)))
    v7_current=copy.deepcopy(dict(v7_current or load(V7_CURRENT)))
    v7_provenance=copy.deepcopy(dict(v7_provenance or load(V7_PROVENANCE)))
    v6=copy.deepcopy(dict(v6 or load(V6)))
    scope_audit=copy.deepcopy(dict(scope_audit or load(SCOPE_AUDIT)))
    postwave=copy.deepcopy(dict(postwave or load(POSTWAVE)))
    quarantine=copy.deepcopy(dict(quarantine or load(QUARANTINE)))
    registry=copy.deepcopy(dict(registry or load(REGISTRY)))
    universal_scope=copy.deepcopy(dict(universal_scope or load(UNIVERSAL_SCOPE)))
    e=[]
    def q(c,code):
        if not c:e.append(code)

    q(binding.get("behavior_id")==BEHAVIOR,"BINDING_BEHAVIOR")
    ev=binding.get("evaluator") or {}
    q(set(ev.get("required_checks") or [])==CHECKS,"FROZEN_REQUIRED_CHECK_SET")
    q(set(ev.get("required_mutations") or [])==MUTATIONS,"FROZEN_MUTATION_SET")
    q(set(binding.get("direct_surface_bindings") or [])=={
      "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
      "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
      "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    },"FROZEN_DIRECT_SURFACE_SET")

    q(str(v6.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"V6_NOT_PASS")
    vv6=v6.get("verified") or {}
    for k in ("scope_first_class","provenance_erasure_killed","unbound_output_killed",
              "partial_interaction_repair_killed","symptom_only_repair_killed",
              "fake_repair_string_killed","hidden_oracle_isolated",
              "rescue_depends_on_candidate_visible_trajectory_semantics"):
        q(vv6.get(k) is True,"V6_PROPERTY:"+k)
    q(vv6.get("cross_product_cases")==192,"V6_CASE_COUNT")

    q(str(v7_current.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"V7_NOT_PASS")
    props=set(v7_current.get("verified_properties") or [])
    for k in ("INHERITED_V6_192_CASE_SUITE_PRESERVED",
              "DERIVED_ONLY_FAILURE_IS_NOT_PROMOTED_TO_CAUSAL_ROOT",
              "SERIAL_DIRECT_COFAULT_RETAINS_BOTH_DIRECT_REPAIRS",
              "PARTIAL_SERIAL_REPAIR_DOES_NOT_RESCUE",
              "FAILURE_SEMANTICS_IS_LOAD_BEARING",
              "INVALID_FAILURE_SEMANTICS_FAILS_CLOSED"):
        q(k in props,"V7_PROPERTY:"+k)

    q(str(v7_provenance.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"V7_PROVENANCE_NOT_PASS")
    vp=v7_provenance.get("result") or {}
    q(vp.get("provenance_mutation_closed_under_current_v7") is True,"PROVENANCE_MUTATION_OPEN")
    q(vp.get("remaining_p1_information_residual")=="FAILURE_SEMANTICS_TRANSPORT_TO_THREE_FROZEN_DIRECT_SURFACES","PRETRANSPORT_RESIDUAL_NOT_EXACT")

    q(str(scope_audit.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"SCOPE_AUDIT_NOT_PASS")
    q(scope_audit.get("scope_mismatch_proved") is True,"ORIGINAL_SCOPE_MISMATCH_NOT_PROVED")
    q(scope_audit.get("broad_p1_transport_admissible") is False,"OLD_BROAD_TRANSPORT_NOT_QUARANTINED")

    q(str(universal_scope.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"UNIVERSAL_SCOPE_NOT_PASS")
    us=universal_scope.get("verified") or {}
    q(us.get("scope_relation")=="EXACT_FROZEN_SELECTION_DOMAIN_SUBSET_OF_EXHAUSTIVE_GENERATOR_QUOTIENT","UNIVERSAL_SCOPE_RELATION")
    q(set(us.get("transport_requirements_discharged") or [])==REQ,"UNIVERSAL_REQUIREMENT_SET")
    q(us.get("all_three_transport_requirements_deductively_covered") is True,"UNIVERSAL_NOT_ALL_COVERED")
    q(us.get("remaining_failure_semantics_information_residual")==0,"UNIVERSAL_RESIDUAL_NONZERO")
    q(us.get("p1_scope_quarantine_lift_eligible") is True,"UNIVERSAL_NOT_LIFT_ELIGIBLE")
    q(us.get("quarantined_execution_used_as_proof") is False,"QUARANTINED_RUN_USED")
    q(us.get("quarantined_execution_run_id")==37108111537,"QUARANTINED_RUN_ID_DRIFT")
    q(us.get("new_reality_units_consumed")==0,"UNIVERSAL_REALITY_NONZERO")
    q(us.get("terminal_results_replayed")==0,"UNIVERSAL_REPLAY")

    cv=postwave.get("contract_verdict") or {}; fv=postwave.get("family_verdict") or {}
    q(cv.get("valid") is True and cv.get("contract_pass_count")==12,"SOURCE_12_CONTRACTS")
    q(BEHAVIOR in set(cv.get("passed_contracts") or []),"SOURCE_P1_PASS_ABSENT")
    q(fv.get("valid") is True and fv.get("family_pass_count")==19,"SOURCE_19_FAMILIES")

    q(str(quarantine.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"QUARANTINE_NOT_PASS")
    q(set(quarantine.get("quarantined_families") or [])==FAMILIES,"QUARANTINED_FAMILY_SET")
    fmap=registry.get("family_to_residual_contracts") or {}
    mapped={n for n,c in fmap.items() if isinstance(c,list) and BEHAVIOR in c}
    q(mapped==FAMILIES,"REGISTRY_P1_FAMILY_MAPPING")

    errors=sorted(set(e)); ok=not errors
    return {
      "schema":"PROJECT_BRAIN_P1_UNIVERSAL_SCOPE_RESTORATION_V9_VERDICT",
      "status":"PASS__P1_WHOLE_FROZEN_SCOPE_RESTORED__12_OF_12_CONTRACTS__19_OF_19_PROVISIONAL_BEHAVIORAL_ROWS__ZERO_OPUS55_ACCEPTANCE_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,"errors":errors,"behavior_id":BEHAVIOR,
      "transport_requirements_discharged":sorted(REQ) if ok else [],
      "whole_p1_contract_restored":ok,"p1_scope_quarantine_clearable":ok,
      "contract_accounting":{"whole_scope_pass_count":12 if ok else 11,"whole_scope_quarantined_count":0 if ok else 1},
      "behavioral_family_accounting":{"provisional_behavioral_pass_count":19 if ok else 11,"quarantined_family_count":0 if ok else 8,"reactivated_families":sorted(FAMILIES) if ok else []},
      "quarantined_execution_used_as_proof":False,
      "source_fresh_reality_units_consumed":0,
      "restoration_new_reality_units_consumed":0,
      "terminal_results_replayed":0,"incremental_spend_usd":0,
      "opus55_acceptance_credit_delta":0,"capability_credit_delta":0,"family_credit_delta":0,
      "execution_authority":False,"promotion_authority":False
    }

def main()->int:
    out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
