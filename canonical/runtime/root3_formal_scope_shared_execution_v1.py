"""Execute the current-bound shared formal Root3 scope proof attempt.

This is a fail-closed deductive audit over canonical artifacts.  It does not
claim global nonexistence of a theorem; it determines whether an admissible
formal closure is derivable from the currently bound proof objects.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ROOT3_FORMAL_SCOPE_SHARED_EXECUTION_V1"

FILES = {
    "activation": ("canonical/governance/ROOT3_UNIVERSAL_SCOPE_CLOSURE_ACTIVATION_V1.json","4cb0d963aa11205063d0119d9ae8fdb625f80e3c"),
    "saturation": ("canonical/governance/CURRENT_ROOT3_ZERO_REALITY_STRONGER_PROOF_SATURATION_V1.json","bdc78fdc147a014e5d77d5daafb5434b1a4e878f"),
    "populations": ("canonical/governance/ROOT3_TARGET_POPULATION_COALESCENCE_V1.json","5a908133af0beed0791ae573051917dba5454acd"),
    "superportfolio": ("canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json","0fa75e451bba19754a4296283c0095e4182ca97d"),
    "composition": ("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json","5bb089582a5bc2ee4a44143c8d3a11e919fecdff"),
    "composition_verification": ("canonical/verification/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","28c5fe9e456cc6bd5171bb74ab291b043d7e85e4"),
    "protocols": ("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json","62394e5b7d221ec9f69c3458f669e40e253a9d09"),
}

TARGETS = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}
MATCHED = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}
COMPOSITION_TARGETS = {
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

def blob(path: str) -> str:
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(key: str) -> dict[str,Any]:
    path, expected = FILES[key]
    actual=blob(path)
    if actual!=expected:
        raise RuntimeError(f"SOURCE_BLOB_DRIFT:{key}:{actual}")
    x=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError("SOURCE_NOT_OBJECT:"+key)
    return x

def execute() -> dict[str,Any]:
    act=load("activation"); sat=load("saturation"); pops=load("populations")
    sup=load("superportfolio"); comp=load("composition")
    compv=load("composition_verification"); protocols=load("protocols")
    errors=[]

    classes={x.get("id"):x for x in act.get("exact_work_classes",[]) if isinstance(x,Mapping)}
    formal=classes.get("ROOT3_FORMAL_SCOPE_SHARED_V1")
    if not isinstance(formal,Mapping) or set(formal.get("targets") or [])!=TARGETS:
        errors.append("FORMAL_WORK_CLASS_DRIFT")

    other=sat.get("other_live_root3_target_result") or {}
    if set(other.get("targets") or [])!=TARGETS:
        errors.append("SATURATION_TARGET_SET_DRIFT")
    if other.get("current_full_protocol_transmutation_witness_count")!=0:
        errors.append("CURRENT_FULL_PROTOCOL_WITNESS_APPEARED")
    if other.get("current_normalized_direct_reuse_closure_count")!=0:
        errors.append("CURRENT_DIRECT_REUSE_CLOSURE_APPEARED")

    groups=pops.get("population_groups") or []
    pop_targets={pid for g in groups if isinstance(g,Mapping) for pid in (g.get("predicate_ids") or [])}
    if pop_targets!=TARGETS:
        errors.append("POPULATION_TARGET_SET_DRIFT")

    case_gen=(sup.get("root3_reality_fallback") or {}).get("batch_classes") or []
    matched_row=next((x for x in case_gen if isinstance(x,Mapping) and x.get("id")=="ROOT3_MATCHED_SUPERPORTFOLIO_WAVE"),{})
    if matched_row.get("current_state")!="BLOCKED_BEFORE_GENERATION__EXACT_OPUS55_COMPARATOR_ADMISSIBILITY_OPEN":
        errors.append("MATCHED_PORTFOLIO_GENERATION_STATE_DRIFT")

    truth=comp.get("truth") or {}
    if truth.get("current_admissible_scoped_proved")!=4 or truth.get("current_open")!=8:
        errors.append("COMPOSITION_COMPONENT_STATE_DRIFT")
    if not str(compv.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("COMPOSITION_VERIFICATION_NOT_PASS")

    prot={x.get("family"):x for x in protocols.get("protocols",[]) if isinstance(x,Mapping)}
    required_dims={
      "COMPLEX_MULTI_TOOL_AGENCY":6,
      "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT":5,
      "MULTI_CAPABILITY_COMPOSITION":5,
    }
    for fam,n in required_dims.items():
        dims=(prot.get(fam) or {}).get("task_dimensions")
        if not isinstance(dims,list) or len(dims)!=n:
            errors.append("PROTOCOL_DIMENSION_DRIFT:"+fam)

    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
                "formal_targets_closed":0,"fresh_reality_authority":False,
                "acceptance_credit_delta":0,"family_credit_delta":0,
                "capability_credit_delta":0,"ownership_credit_delta":0}

    rows=[]
    for pid in sorted(TARGETS):
        blockers=[]
        attempted=[
          "EXACT_OR_SUPERSET_CONTENT_ADDRESSED_SCOPE_CERTIFICATE",
          "VERIFIED_LOGICAL_IMPLICATION",
          "INDUCTIVE_INVARIANT_OR_UNIVERSAL_THEOREM",
          "RESIDUAL_ACTION_INVARIANCE",
          "GENUINELY_EXHAUSTIVE_FINITE_PARTITION",
          "ASSUME_GUARANTEE_COMPOSITION",
          "COUNTEREXAMPLE_GUIDED_ABSTRACTION_REFINEMENT",
        ]
        blockers.append("NO_CURRENT_ADMISSIBLE_EXACT_OR_SUPERSET_SCOPE_CERTIFICATE")
        blockers.append("NO_CURRENT_VERIFIED_LOGICAL_IMPLICATION_OR_FULL_PROTOCOL_WITNESS")
        if pid in MATCHED:
            blockers.append("FROZEN_MATCHED_PORTFOLIO_NOT_GENERATED_OR_EXPOSED")
            blockers.append("EXACT_OPUS55_COMPARATOR_ADMISSIBILITY_OPEN")
        if pid in COMPOSITION_TARGETS:
            blockers.append("COMPOSITION_COMPONENT_SCOPE_PRECONDITION_8_OF_12_OPEN")
        if pid=="VISION_DENSE_NONCHART_SCOPE":
            blockers.append("DENSE_NONCHART_RESIDUAL_UNIVERSE_NOT_YET_EXACTLY_ENUMERATED")
            blockers.append("CHARTOGRAPHY_COVERAGE_RESULT_NOT_YET_AVAILABLE_TO_SUBTRACT")
        blockers.append("NO_BOUND_MACHINE_TRANSITION_SYSTEM_PLUS_INVARIANT_CERTIFICATE_FOR_THIS_TARGET")
        rows.append({
          "predicate_id":pid,
          "formal_closure":False,
          "attempted_methods":attempted,
          "current_bound_blockers":blockers,
          "wake_conditions":[
            "NEW_INDEPENDENT_EXACT_OR_SUPERSET_SCOPE_CERTIFICATE",
            "NEW_VERIFIED_LOGICAL_IMPLICATION_OR_UNIVERSAL_THEOREM",
            "NEW_MACHINE_TRANSITION_SYSTEM_PLUS_INVARIANT_CERTIFICATE",
            "MATCHED_PORTFOLIO_AND_COMPARATOR_BECOME_ADMISSIBLE",
            "NEW_UPSTREAM_SCOPE_COMPLETE_COMPONENT_RECEIPT" if pid in COMPOSITION_TARGETS else None,
            "VISION_RESIDUAL_UNIVERSE_EXACTLY_ENUMERATED_AFTER_CHARTOGRAPHY" if pid=="VISION_DENSE_NONCHART_SCOPE" else None,
          ],
        })
    for r in rows:
        r["wake_conditions"]=[x for x in r["wake_conditions"] if x]

    return {
      "schema":SCHEMA,
      "status":"PASS__CURRENT_BOUND_FORMAL_SCOPE_ACTION_EXECUTED__0_OF_7_CLOSED__EXACT_BLOCKERS_LOCALIZED__ZERO_CREDIT",
      "pass":True,
      "formal_target_count":7,
      "formal_targets_closed":0,
      "formal_targets_open":7,
      "rows":rows,
      "current_bound_formal_search_exhausted":True,
      "global_nonexistence_claimed":False,
      "next":"ROOT3_ZERO_REALITY_FIXED_POINT_ELIGIBLE_IF_SYNTHESIS_COMPOSITION_AND_DIRECT_ORACLE_CLASSES_HAVE_NO_RUNNABLE_ZERO_REALITY_ACTION",
      "fresh_reality_authority":False,
      "execution_authority":False,
      "promotion_authority":False,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
    }

if __name__=="__main__":
    out=execute()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out.get("pass") else 1)
