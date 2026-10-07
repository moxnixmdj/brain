from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    "v6":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V6.json","fafde6e942a423798c8cadd0d2a2ccfe140a9f53"),
    "escape":("canonical/governance/TARGET_UNDOMINATED_ESCAPE_REDUCTION_20261007_V1.json","c6757e71f862dd592402199ac12afb8bca45c256"),
    "role_frontier":("canonical/governance/TARGET_ROLE_ESCAPE_FRONTIER_20261007_V1.json","388dd2cb544b7b7bd7ded5779f51a06d3acb3ee3"),
    "b9":("canonical/governance/B9_COMPOSITION_DERIVATIVE_REDUCTION_20261007_V1.json","719ad74545f73f4f3e458892b7cd91005499cebd"),
    "five_role":("canonical/governance/FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_20261007_V1.json","eb316b0a674a3542280c71706fffe850d22e44fa"),
    "kernel":("canonical/governance/STOCHASTIC_KERNEL_TRANSFORM_UNIVERSALITY_20261007_V1.json","658f12eba91a85dbf67dac82b8fb1f6650cc3934"),
    "effects":("canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILER_20261007_V1.json","a8448eb871831242a204fdb579bce6717d7b6621"),
    "continuity":("canonical/governance/CONTINUITY_CREDITED_REBIND_20261007_V1.json","839af46fd8ef214251b44bd1398fa2d1543f00c5"),
    "v7":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V7.json","5ad4fd7600fe6db3cf7e28c925600d22470f5757"),
}

PRIMITIVE={
    "B0_INPUT_PERCEPTION_AND_GROUNDING",
    "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
    "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
    "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
    "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION",
}
COARSE=PRIMITIVE|{"B9_MULTI_ROLE_COMPOSITION"}

def git_blob(rel:str)->str:
    cp=subprocess.run(
        ["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],
        text=True,capture_output=True,check=False,
    )
    return cp.stdout.strip() if cp.returncode==0 else ""

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def verify()->dict:
    errors=[]
    for name,(path,sha) in SOURCES.items():
        got=git_blob(path)
        if got!=sha:
            errors.append(f"DRIFT:{name}:{got or 'MISSING'}")

    if errors:
        return {
            "schema":"PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_V7_VERIFIER",
            "status":"FAIL_CLOSED_SOURCE_DRIFT",
            "pass":False,"errors":sorted(errors),"terminal":False,
            "terminal_credit_delta":0,
        }

    v6=load(SOURCES["v6"][0])
    esc=load(SOURCES["escape"][0])
    role=load(SOURCES["role_frontier"][0])
    b9=load(SOURCES["b9"][0])
    five=load(SOURCES["five_role"][0])
    kernel=load(SOURCES["kernel"][0])
    effects=load(SOURCES["effects"][0])
    continuity=load(SOURCES["continuity"][0])
    v7=load(SOURCES["v7"][0])

    preserved=v7["preserved_truth"]
    if preserved != {
        "open_truth_obligations":29,
        "accepted_families":5,
        "open_families":14,
        "terminal":False,
    }:
        errors.append("PRESERVED_TRUTH_DRIFT")
    if v6["preserved_truth"] != preserved:
        errors.append("V6_TRUTH_NOT_PRESERVED")

    if set(role["structural_escape_roles"])!=COARSE:
        errors.append("COARSE_ESCAPE_SET_DRIFT")
    if set(b9["conditional_escape_projection"]["if_C_closes"])!=PRIMITIVE:
        errors.append("B9_PRIMITIVE_PROJECTION_DRIFT")
    if set(five["projected_primitive_escape_roles"])!=PRIMITIVE:
        errors.append("FIVE_ROLE_SET_DRIFT")
    cond=five.get("conditionality") or {}
    if cond.get("B9")!="REMAINS_OPEN_WHILE_C_IS_OPEN__DERIVATIVE_ONLY_AFTER_C_CLOSES":
        errors.append("FIVE_ROLE_B9_CONDITIONALITY_DRIFT")
    if cond.get("five_role_projection")!="VALID_AS_THE_PRIMITIVE_A_B_SEARCH_FRONTIER_CONDITIONAL_ON_C":
        errors.append("FIVE_ROLE_C_CONDITIONALITY_DRIFT")

    theorem=esc["theorem"]
    if "U_INTERSECTION_E_IS_EMPTY" not in theorem["statement"]:
        errors.append("ESCAPE_THEOREM_DRIFT")

    cfix=kernel["C_repair_if_verified"]
    if cfix.get("delete")!="PROVE_PRIMITIVE_TRANSFORM_GENERATOR_COMPLETENESS_AS_A_FINITE_KIND_ENUMERATION":
        errors.append("C_TAXONOMY_DELETION_DRIFT")
    if len(cfix.get("replace_with") or [])!=4:
        errors.append("C_BINDING_CUT_COUNT_DRIFT")

    inp=effects["input_contract"]
    if inp.get("credited_routes")!="NONEMPTY_LIST_OF_CONTENT_ADDRESSED_CREDITED_ROUTE_BINDINGS":
        errors.append("D_CREDITED_ROUTE_INPUT_DRIFT")
    guarantees=set(effects["compiler_guarantees"])
    if "UNION_ONLY_EFFECTS_DECLARED_BY_COMPLETE_CONSERVATIVE_RECEIPTS_FOR_CREDITED_ROUTES" not in guarantees:
        errors.append("D_EFFECT_UNION_RULE_DRIFT")

    if continuity.get("credited_path")!="canonical/runtime/same_identity_supervisor_credited_v1.py":
        errors.append("CONTINUITY_CREDITED_PATH_DRIFT")
    if continuity.get("credited_path_blob")!="47c461f502e840def0c38728e1bfd7c6401cb804":
        errors.append("CONTINUITY_CREDITED_BLOB_DRIFT")

    nf=v7["invariant_normal_form"]
    if set(nf["A_B_TARGET_COVERAGE_AND_RELATIVE_DOMINANCE"]["current_coarse_escape_roles"])!=COARSE:
        errors.append("V7_COARSE_ESCAPE_DRIFT")
    if set(nf["A_B_TARGET_COVERAGE_AND_RELATIVE_DOMINANCE"]["after_C_closes_primitive_escape_roles"])!=PRIMITIVE:
        errors.append("V7_PRIMITIVE_ESCAPE_DRIFT")
    if nf["A_B_TARGET_COVERAGE_AND_RELATIVE_DOMINANCE"]["generic_new_implementation_hunt_authorized"] is not False:
        errors.append("V7_GENERIC_IMPLEMENTATION_AUTHORITY_DRIFT")
    if nf["C_COMPOSITION_AND_TRANSFORM_CLOSURE"]["closed"] is not False:
        errors.append("V7_C_FALSE_DRIFT")
    if len(nf["C_COMPOSITION_AND_TRANSFORM_CLOSURE"]["remaining"])!=4:
        errors.append("V7_C_REMAINING_COUNT_DRIFT")
    if nf["D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE"]["scope"]!="ACTUAL_CREDITED_DEPLOYED_ROUTES_ONLY":
        errors.append("V7_D_SCOPE_DRIFT")
    if nf["D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE"]["continuity_route_exact_runtime_bound"] is not True:
        errors.append("V7_CONTINUITY_BINDING_DRIFT")

    scheduler=v7["scheduler"]
    if not scheduler or not scheduler[0].startswith("C_FIRST__"):
        errors.append("V7_SCHEDULER_NOT_C_FIRST")
    if len(scheduler)!=4:
        errors.append("V7_SCHEDULER_LENGTH_DRIFT")

    for section in nf.values():
        if section.get("closed") is not False:
            errors.append("INVARIANT_CLOSED_WITHOUT_EVIDENCE")
    if v7["accounting"]["terminal_credit_delta"]!=0:
        errors.append("NONZERO_TERMINAL_CREDIT")
    if v7["accounting"]["fresh_reality_units_consumed"]!=0:
        errors.append("NONZERO_FRESH_REALITY")
    if "NO_TERMINAL_CREDIT" not in v7["hard_nonclaims"]:
        errors.append("TERMINAL_NONCLAIM_MISSING")

    ok=not errors
    return {
        "schema":"PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_V7_VERIFIER",
        "status":"PASS__V7_SEMANTIC_ESCAPE_NORMAL_FORM__TERMINAL_FALSE__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":sorted(errors),
        "open_truth_obligations":29 if ok else None,
        "accepted_families":5 if ok else None,
        "open_families":14 if ok else None,
        "coarse_escape_role_count":6 if ok else None,
        "primitive_escape_role_count_after_C":5 if ok else None,
        "C_remaining_binding_count":4 if ok else None,
        "scheduler_first":"C" if ok else None,
        "terminal":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
