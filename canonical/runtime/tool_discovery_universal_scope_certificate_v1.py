"""Fail-closed Tool Discovery universal-scope certificate.

This is a narrow implication reducer:
  verified conditional dynamic-refinement theorem
  + verified complete discovery-interface instance
  => Tool Discovery's missing universal scope atom is satisfied.

No acceptance or family credit is granted here.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
CONTRACT=ROOT/"canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
DYNAMIC=ROOT/"canonical/verification/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
PROTOCOLS=ROOT/"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
BINDINGS=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"

FAMILY="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
PREDICATE="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
ATOM="INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_THE_CLAIMED_PROTOCOL_POPULATION"

def load(path:Path)->dict[str,Any]:
    x=json.loads(path.read_text())
    if not isinstance(x,dict): raise ValueError(str(path))
    return x

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def evaluate(interface_report:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    contract=load(CONTRACT)
    dyn=load(DYNAMIC)
    protocols=load(PROTOCOLS)
    bindings=load(BINDINGS)
    required=set(contract.get("required_properties") or [])
    props=interface_report.get("property_results")

    if len(required)!=7:
        errors.append("FROZEN_INTERFACE_PROPERTY_COUNT_NOT_7")
    if not isinstance(props,Mapping) or set(props)!=required or any(props.get(x) is not True for x in required):
        errors.append("INTERFACE_INSTANCE_DOES_NOT_PROVE_EXACT_SEVEN_PROPERTIES")
    if interface_report.get("pass") is not True:
        errors.append("INTERFACE_INSTANCE_NOT_PASS")
    if interface_report.get("new_reality_units_consumed")!=1:
        errors.append("INTERFACE_REALITY_UNIT_COUNT_NOT_1")
    if interface_report.get("incremental_spend_usd")!=0:
        errors.append("INTERFACE_NONZERO_SPEND")
    if interface_report.get("capability_credit_delta")!=0 or interface_report.get("family_credit_delta")!=0:
        errors.append("INTERFACE_PREMATURE_CREDIT")
    if interface_report.get("epoch_stable") is not True:
        errors.append("INTERFACE_EPOCH_NOT_STABLE")
    if int(interface_report.get("source_count") or 0)<=0:
        errors.append("INTERFACE_SOURCE_SET_EMPTY")
    if int(interface_report.get("union_unique_tool_identity_count") or 0)<=1000:
        errors.append("INTERFACE_NOT_NONTRIVIAL_EXTERNAL_ECOSYSTEM")
    if (interface_report.get("safe_probe_receipt") or {}).get("pass") is not True:
        errors.append("INTERFACE_SAFE_PROBE_NOT_PASS")

    if not str(dyn.get("status") or "").startswith(
        "INDEPENDENT_PUBLIC_RUNNER_PASS__CONDITIONAL_DYNAMIC_REFINEMENT"
    ):
        errors.append("DYNAMIC_REFINEMENT_NOT_INDEPENDENT_PASS")
    if dyn.get("target_predicate")!=PREDICATE or dyn.get("target_preserved") is not True:
        errors.append("DYNAMIC_REFINEMENT_TARGET_DRIFT")
    expected=(
        "IF_AN_INDEPENDENTLY_VERIFIED_DISCOVERY_INTERFACE_INSTANCE_SATISFIES_"
        "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1__THEN_DYNAMIC_V3_PROGRAM_SIDE_"
        "UNKNOWN_IDENTITY_DISCOVERY_PROGRESS_AND_SELECTION_OBLIGATIONS_ARE_DISCHARGED_"
        "UNDER_THE_BOUND_FROZEN_TARGET"
    )
    if dyn.get("verified_conditional_implication")!=expected:
        errors.append("CONDITIONAL_IMPLICATION_DRIFT")
    if dyn.get("minimum_missing_fact_after_verified_reduction")!=(
        "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
        "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1"
    ):
        errors.append("DYNAMIC_MINIMUM_MISSING_FACT_DRIFT")

    exact=dyn.get("exact_brain_blobs") if isinstance(dyn.get("exact_brain_blobs"),Mapping) else {}
    if exact.get("canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json")!=blob(CONTRACT):
        errors.append("DYNAMIC_CONTRACT_BLOB_DRIFT")

    prow=next((x for x in protocols.get("protocols",[]) if isinstance(x,Mapping) and x.get("family")==FAMILY),None)
    if not isinstance(prow,Mapping):
        errors.append("TOOL_DISCOVERY_PROTOCOL_ROW_MISSING")
    elif prow.get("status")!="DEFINED_RESULT_OPEN":
        errors.append("TOOL_DISCOVERY_PROTOCOL_NOT_OPEN")

    claim=next((x for x in bindings.get("claims",[]) if isinstance(x,Mapping) and x.get("predicate_id")==PREDICATE),None)
    if not isinstance(claim,Mapping):
        errors.append("TOOL_DISCOVERY_ACCEPTANCE_PREDICATE_MISSING")
    else:
        if claim.get("state")!="EXTERNAL_BLOCKED":
            errors.append("TOOL_DISCOVERY_PREDICATE_NOT_BLOCKED")
        if claim.get("blocker")!="ABSOLUTE_SCOPE_COMPLETENESS_MISSING":
            errors.append("TOOL_DISCOVERY_BLOCKER_NOT_SCOPE_COMPLETENESS")
        if "UNIVERSAL_FORMAL_SCOPE_PROOF" not in str(claim.get("discharge_condition") or ""):
            errors.append("TOOL_DISCOVERY_DISCHARGE_RULE_DRIFT")

    if errors:
        return {
            "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_UNIVERSAL_SCOPE_CERTIFICATE_VERDICT_V1",
            "status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
            "universal_scope_proved":False,"scope_atom_satisfied_candidate":False,
            "capability_credit_delta":0,"family_credit_delta":0,
            "execution_authority":False,"promotion_authority":False,
        }

    return {
        "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_UNIVERSAL_SCOPE_CERTIFICATE_VERDICT_V1",
        "status":"PASS__VERIFIED_CONDITIONAL_THEOREM_PLUS_COMPLETE_EXTERNAL_INTERFACE_DISCHARGES_TOOL_DISCOVERY_SCOPE_ATOM__ZERO_CREDIT",
        "pass":True,
        "errors":[],
        "target_family":FAMILY,
        "target_predicate":PREDICATE,
        "target_proof_atom":ATOM,
        "basis_kind":"UNIVERSAL_FORMAL_SCOPE_PROOF",
        "universal_scope_proved":True,
        "scope_atom_satisfied_candidate":True,
        "proof":{
            "conditional_theorem":"INDEPENDENT_DYNAMIC_V3_REFINEMENT_PROVES_PROGRAM_SIDE_UNKNOWN_IDENTITY_DISCOVERY_PROGRESS_AND_SELECTION_OBLIGATIONS_FOR_ANY_INTERFACE_SATISFYING_THE_FROZEN_SEVEN_PROPERTY_CONTRACT",
            "verified_premise":"THE_EXTERNAL_INTERFACE_REPORT_SATISFIES_EXACTLY_ALL_SEVEN_FROZEN_PROPERTIES",
            "deduction":"THE_ONLY_OPEN_FORMALISM_PREMISE_IDENTIFIED_BY_THE_INDEPENDENT_REDUCTION_IS_TRUE__THEREFORE_THE_BOUND_FROZEN_TARGET_SCOPE_OBLIGATION_IS_DISCHARGED",
        },
        "uses_empirical_generalization":False,
        "interface_instance_reality_units":1,
        "terminal_cases_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "next":"INDEPENDENTLY_VERIFY_WITH_EXACT_INTERFACE_REPORT__THEN_RUN_SEPARATE_ACCEPTANCE_TRANSMUTER_REDUCTION"
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("interface_report",type=Path)
    a=ap.parse_args()
    out=evaluate(load(a.interface_report))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") is True else 1

if __name__=="__main__":
    raise SystemExit(main())
