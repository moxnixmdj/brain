"""Fail-closed postwave global ownership reducer.

Consumes only frozen receipts from the already-spent terminal wave. It never reruns
terminal cases. It closes a global postcondition only when its exact evidence
chain is present and hash-bound in the frozen postwave proof bundle.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_POSTWAVE_GLOBAL_OWNERSHIP_VERDICT_V1"
WAVE="canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
REDUCTION="canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"
MUTATION="canonical/verification/FOUR_DIRECT_PROOF_MUTATION_PREFLIGHT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
COMPOSITION="canonical/verification/PREWAVE_OPAQUE_PROVIDER_COMPOSITION_AUDIT_20261002_V1.json"
DEPENDENCY="canonical/governance/PREWAVE_BRAIN_ROUTE_DEPENDENCY_MANIFEST_V2.json"
DONOR="canonical/governance/POSTWAVE_DONOR_FREE_TERMINAL_EXECUTION_AUDIT_V1.json"
BUNDLE="canonical/governance/POSTWAVE_GLOBAL_OWNERSHIP_PROOF_BUNDLE_V1.json"
SOURCES=(WAVE,REDUCTION,MUTATION,COMPOSITION,DEPENDENCY,DONOR)

def _blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()

def _load(root:Path, rel:str)->dict[str,Any]:
    x=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(rel+":NOT_OBJECT")
    return x

def _fail(errors:list[str], checks:dict[str,bool]|None=None)->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"achieved":False,
      "errors":sorted(set(errors)),"checks":checks or {},
      "terminal_replay_authorized":False,"capability_credit_delta":0,
      "family_credit_delta":0,
    }

def evaluate_documents(
    wave:Mapping[str,Any], reduction:Mapping[str,Any], mutation:Mapping[str,Any],
    composition:Mapping[str,Any], dependency:Mapping[str,Any], donor:Mapping[str,Any],
    bundle:Mapping[str,Any], *, current_blobs:Mapping[str,str]
)->dict[str,Any]:
    errors:list[str]=[]
    checks:dict[str,bool]={}

    checks["terminal_wave_immutable_pass"]=(
      wave.get("status")=="ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED"
      and wave.get("public_runner",{}).get("conclusion")=="success"
      and wave.get("direct_terminal_population",{}).get("total_cases")==2770
      and wave.get("direct_terminal_population",{}).get("total_failures")==0
      and wave.get("parent_terminal_population",{}).get("parent_reduction_status")=="PASS"
      and wave.get("parent_terminal_population",{}).get("multiplex_behavior_failures")==0
      and wave.get("total_fresh_terminal_case_executions")==3352
      and wave.get("result_guards",{}).get("no_case_replacement") is True
      and wave.get("result_guards",{}).get("no_tuning_replay") is True
      and wave.get("result_guards",{}).get("result_to_runtime_feedback_during_wave") is False
    )

    cv=reduction.get("contract_verdict",{})
    fv=reduction.get("family_verdict",{})
    checks["terminal_reduction_12_and_19_pass"]=(
      "12_OF_12_TERMINAL_CONTRACTS_PASS" in str(reduction.get("status",""))
      and cv.get("valid") is True and cv.get("contract_count")==12
      and cv.get("contract_pass_count")==12 and cv.get("all_contracts_pass") is True
      and fv.get("valid") is True and fv.get("family_count")==19
      and fv.get("family_pass_count")==19 and fv.get("all_families_pass") is True
      and reduction.get("candidate_package_commitment")==wave.get("package_commitment")
      and reduction.get("source_full_result_sha256")==wave.get("artifact",{}).get("full_result_sha256")
    )

    checks["verifier_mutations_closed"]=(
      str(mutation.get("status","")).startswith("INDEPENDENT_PASS__ALL_FOUR_FROZEN_DIRECT_PROOF_MUTATION_PREFLIGHTS_GREEN")
      and len(mutation.get("verified_routes",[]))==4
      and len(set(mutation.get("verified_routes",[])))==4
      and mutation.get("fresh_terminal_evidence_consumed")==0
    )

    cf=composition.get("findings",{})
    checks["prewave_composition_clean"]=(
      str(composition.get("status","")).startswith("PASS__NO_KNOWN_OPAQUE_TARGET_CAPABILITY_PROVIDER")
      and cf.get("opaque_target_capability_provider_present") is False
      and cf.get("known_unresolved_composition_defect_before_terminal_wave") is False
      and cf.get("current_controller_tested_blobs_match_independent_receipt") is True
    )
    checks["postwave_composition_closed"]=(
      checks["prewave_composition_clean"]
      and wave.get("parent_terminal_population",{}).get("parent_reduction_status")=="PASS"
      and wave.get("parent_terminal_population",{}).get("multiplex_behavior_failures")==0
    )

    pc=dependency.get("prewave_conclusion",{})
    checks["dependency_identity_frozen"]=(
      dependency.get("status")=="FROZEN_HASH_BOUND_PREWAVE_DEPENDENCY_MANIFEST__NO_TERMINAL_CAPABILITY_CREDIT"
      and pc.get("exact_runtime_dependencies_frozen") is True
      and pc.get("no_known_opaque_target_capability_provider") is True
      and pc.get("known_dependency_identity_complete_for_declared_operative_route") is True
    )

    da=donor.get("adjudication",{})
    ea=donor.get("executable_closure_audit",{})
    re=donor.get("runner_environment",{})
    checks["terminal_wave_donor_absent"]=(
      donor.get("source_terminal_wave",{}).get("runner_head_sha")==wave.get("public_runner",{}).get("head_sha")
      and donor.get("source_terminal_wave",{}).get("package_commitment")==wave.get("package_commitment")
      and donor.get("source_terminal_wave",{}).get("closure_blob_count")==53
      and ea.get("python_files_scanned")==33
      and ea.get("all_33_blob_shas_match_frozen_request") is True
      and ea.get("executable_files_with_forbidden_provider_or_network_hits")==0
      and ea.get("dynamic_exec_external_provider_route_count")==0
      and ea.get("target_capability_provider_client_import_count")==0
      and ea.get("general_cognition_model_import_count")==0
      and re.get("target_capability_provider_dependency_installed") is False
      and re.get("general_cognition_model_dependency_installed") is False
      and re.get("target_capability_credentials_declared_in_workflow") is False
      and da.get("target_capability_donor_present_in_terminal_execution_closure") is False
      and da.get("opaque_target_capability_provider_present") is False
      and da.get("general_cognition_substrate_present") is False
      and da.get("terminal_wave_itself_constitutes_donor_absent_execution_for_the_MEASURED_12_CONTRACT_BEHAVIORAL_BASIS") is True
      and donor.get("terminal_replay_authorized") is False
    )

    bs=bundle.get("sources")
    checks["proof_bundle_frozen"]=(
      bundle.get("status")=="FROZEN_EVIDENCE_BUNDLE__NO_TERMINAL_REPLAY__INDEPENDENT_REDUCER_VERIFICATION_PENDING"
      and bundle.get("proof_bundle_frozen") is True
      and bundle.get("candidate_package_commitment")==wave.get("package_commitment")
      and bundle.get("terminal_source_full_result_sha256")==wave.get("artifact",{}).get("full_result_sha256")
      and isinstance(bs,Mapping)
      and set(bs)==set(SOURCES)
      and all(bs.get(p)==current_blobs.get(p) for p in SOURCES)
    )

    for name,ok in checks.items():
        if not ok: errors.append("CHECK_FAILED:"+name)
    if errors: return _fail(errors,checks)

    return {
      "schema":SCHEMA,
      "status":"PASS__GLOBAL_POSTWAVE_OWNERSHIP_POSTCONDITIONS_CLOSED_FROM_IMMUTABLE_TERMINAL_EVIDENCE__NO_REPLAY",
      "pass":True,
      "achieved":True,
      "checks":checks,
      "derived_counters":{
        "donor_dependent_required_behaviors":0,
        "unresolved_verifier_mutations":0,
        "unresolved_composition_failures":0
      },
      "derived_predicates":{
        "donor_dependent_required_behaviors_zero":True,
        "unresolved_verifier_mutations_zero":True,
        "unresolved_composition_failures_zero":True,
        "final_donor_deletion_cleanroom_pass":True,
        "proof_bundle_frozen":True
      },
      "cleanroom_basis":"THE_ALREADY_CONSUMED_TERMINAL_WAVE_EXECUTED_THE_EXACT_MEASURED_BEHAVIORAL_CLOSURE_WITHOUT_TARGET_CAPABILITY_DONOR_OR_GENERAL_MODEL_ROUTE__NO_SECOND_TERMINAL_EXECUTION_REQUIRED",
      "terminal_replay_authorized":False,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"POSTWAVE_GLOBAL_FLAGS_MUST_BE_DERIVED_FROM_HASH_BOUND_RECEIPTS__NEVER_HANDWRITTEN_TRUE"
    }

def evaluate(root:Path=Path("."))->dict[str,Any]:
    try:
      docs={p:_load(root,p) for p in (*SOURCES,BUNDLE)}
      blobs={p:_blob(root/p) for p in SOURCES}
    except (OSError,ValueError,json.JSONDecodeError) as exc:
      return _fail(["INPUT_READ_FAILURE:"+type(exc).__name__])
    return evaluate_documents(
      docs[WAVE],docs[REDUCTION],docs[MUTATION],docs[COMPOSITION],
      docs[DEPENDENCY],docs[DONOR],docs[BUNDLE],current_blobs=blobs
    )

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
