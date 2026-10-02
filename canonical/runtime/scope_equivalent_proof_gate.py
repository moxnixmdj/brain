#!/usr/bin/env python3
"""Fail-closed scope-equivalent proof substitution gate.

This gate decides whether one evidence route may replace an inaccessible/private
terminal benchmark dependency. It does NOT decide whether the capability itself
passes. The substitute proof result must still be executed/adjudicated separately.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_SCOPE_EQUIVALENT_PROOF_GATE_VERDICT_V1"
PROOF_MODES={
    "THEORETICAL_CEILING",
    "FORMAL_PROOF",
    "EXHAUSTIVE_FINITE_VERIFICATION",
    "PUBLIC_FIXED_BAR_SCOPE_EQUIVALENT",
    "ABSOLUTE_BEHAVIORAL_PROTOCOL",
}
RELATIONS={
    "population":{"EXACT","CANDIDATE_SUPERSET_PROVEN"},
    "environment":{"EXACT","CANDIDATE_STRICTER_PROVEN"},
    "oracle":{"EXACT","CANDIDATE_STRONGER_PROVEN"},
}

def _strings(value: Any, name: str) -> list[str]:
    if not isinstance(value,list) or not value or not all(isinstance(x,str) and x for x in value):
        raise ValueError(f"{name} must be a nonempty string list")
    if len(value)!=len(set(value)):
        raise ValueError(f"{name} contains duplicates")
    return value

def evaluate(data: dict[str,Any]) -> dict[str,Any]:
    errors:list[str]=[]
    try:
        required=set(_strings(data.get("required_behavior_ids"),"required_behavior_ids"))
        covered=set(_strings(data.get("candidate_behavior_ids"),"candidate_behavior_ids"))
        req_inter=set(_strings(data.get("required_interaction_ids"),"required_interaction_ids"))
        cand_inter=set(_strings(data.get("candidate_interaction_ids"),"candidate_interaction_ids"))
    except ValueError as exc:
        return {"schema":SCHEMA,"admissible":False,"status":"FAIL_CLOSED","errors":[str(exc)]}

    missing_beh=sorted(required-covered)
    missing_inter=sorted(req_inter-cand_inter)
    if missing_beh: errors.append("MISSING_REQUIRED_BEHAVIORS:"+",".join(missing_beh))
    if missing_inter: errors.append("MISSING_REQUIRED_INTERACTIONS:"+",".join(missing_inter))

    mode=data.get("proof_mode")
    if mode not in PROOF_MODES:
        errors.append("UNAPPROVED_PROOF_MODE")

    relation_receipts=data.get("relation_receipts")
    if not isinstance(relation_receipts,dict):
        relation_receipts={}
        errors.append("RELATION_RECEIPTS_MISSING")

    for key,allowed in RELATIONS.items():
        field=f"{key}_relation"
        relation=data.get(field)
        if relation not in allowed:
            errors.append(f"{field.upper()}_NOT_PROVEN")
            continue
        if relation!="EXACT":
            receipt=relation_receipts.get(key)
            if not isinstance(receipt,str) or not receipt.strip():
                errors.append(f"{field.upper()}_IMPLICATION_RECEIPT_MISSING")

    unresolved=data.get("unresolved_required_dimensions")
    if not isinstance(unresolved,list) or not all(isinstance(x,str) for x in unresolved):
        errors.append("UNRESOLVED_DIMENSIONS_FIELD_INVALID")
    elif unresolved:
        errors.append("UNRESOLVED_REQUIRED_DIMENSIONS:"+",".join(sorted(set(unresolved))))

    subjective=set(data.get("required_subjective_quality_dimensions") or [])
    subjective_covered=set(data.get("candidate_subjective_quality_dimensions") or [])
    if not all(isinstance(x,str) and x for x in subjective|subjective_covered):
        errors.append("SUBJECTIVE_DIMENSION_FIELD_INVALID")
    missing_subjective=sorted(subjective-subjective_covered)
    if missing_subjective:
        errors.append("MISSING_SUBJECTIVE_QUALITY_DIMENSIONS:"+",".join(missing_subjective))

    required_true=[
        "zero_incremental_spend",
        "independent_acceptance",
        "contamination_safe",
        "candidate_route_owned_or_noncapability_jit_only",
    ]
    for key in required_true:
        if data.get(key) is not True:
            errors.append(key.upper()+"_NOT_TRUE")

    if data.get("opaque_target_capability_provider") is not False:
        errors.append("OPAQUE_TARGET_CAPABILITY_PROVIDER_NOT_FALSE")
    if data.get("target_weakened") is not False:
        errors.append("TARGET_WEAKENING_NOT_FALSE")

    source=data.get("source_private_or_nonexecutable_surface")
    candidate=data.get("candidate_proof_route")
    if not isinstance(source,str) or not source:
        errors.append("SOURCE_SURFACE_MISSING")
    if not isinstance(candidate,str) or not candidate:
        errors.append("CANDIDATE_ROUTE_MISSING")

    errors=sorted(set(errors))
    return {
        "schema":SCHEMA,
        "status":"ADMISSIBLE_SUBSTITUTION" if not errors else "FAIL_CLOSED",
        "admissible":not errors,
        "source_surface":source,
        "candidate_route":candidate,
        "proof_mode":mode,
        "required_behavior_count":len(required),
        "covered_behavior_count":len(required & covered),
        "required_interaction_count":len(req_inter),
        "covered_interaction_count":len(req_inter & cand_inter),
        "errors":errors,
        "rule":"ADMISSIBLE_ONLY_IF_SUBSTITUTE_LOGICALLY_COVERS_REQUIRED_SCOPE_WITH_EQUAL_OR_STRONGER_PROVEN_POPULATION_ENVIRONMENT_ORACLE_RELATIONS__NO_CAPABILITY_CREDIT_FROM_GATE"
    }

def self_test() -> None:
    base={
      "source_private_or_nonexecutable_surface":"PRIVATE_X",
      "candidate_proof_route":"ABSOLUTE_Y",
      "required_behavior_ids":["B1","B2"],
      "candidate_behavior_ids":["B1","B2","B3"],
      "required_interaction_ids":["I1"],
      "candidate_interaction_ids":["I1","I2"],
      "proof_mode":"EXHAUSTIVE_FINITE_VERIFICATION",
      "population_relation":"CANDIDATE_SUPERSET_PROVEN",
      "environment_relation":"EXACT",
      "oracle_relation":"CANDIDATE_STRONGER_PROVEN",
      "relation_receipts":{"population":"receipt/pop.json","oracle":"receipt/oracle.json"},
      "unresolved_required_dimensions":[],
      "required_subjective_quality_dimensions":["Q1"],
      "candidate_subjective_quality_dimensions":["Q1"],
      "zero_incremental_spend":True,
      "independent_acceptance":True,
      "contamination_safe":True,
      "candidate_route_owned_or_noncapability_jit_only":True,
      "opaque_target_capability_provider":False,
      "target_weakened":False,
    }
    assert evaluate(base)["admissible"] is True

    x=dict(base); x["candidate_behavior_ids"]=["B1"]
    assert evaluate(x)["admissible"] is False
    x=dict(base); x["relation_receipts"]={"oracle":"r"}
    assert evaluate(x)["admissible"] is False
    x=dict(base); x["candidate_subjective_quality_dimensions"]=[]
    assert evaluate(x)["admissible"] is False
    x=dict(base); x["opaque_target_capability_provider"]=True
    assert evaluate(x)["admissible"] is False
    x=dict(base); x["target_weakened"]=True
    assert evaluate(x)["admissible"] is False

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("input",type=Path,nargs="?")
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"status":"SELF_TEST_PASS"},sort_keys=True))
        return 0
    if args.input is None:
        ap.error("input required unless --self-test")
    out=evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["admissible"] else 1

if __name__=="__main__":
    raise SystemExit(main())
