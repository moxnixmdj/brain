from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ROLE_BASIS=ROOT/"canonical/governance/OPUS55_OBSERVABLE_BEHAVIOR_FUNCTIONAL_BASIS_CHARACTERIZATION_20261005_V1.json"
ROLE_FRONTIER=ROOT/"canonical/governance/TARGET_ROLE_ESCAPE_FRONTIER_20261007_V1.json"
B9_REDUCTION=ROOT/"canonical/governance/B9_COMPOSITION_DERIVATIVE_REDUCTION_20261007_V1.json"
SEMANTIC_REDUCTION=ROOT/"canonical/governance/G6_G7_SINGLE_SEMANTIC_RESIDUAL_REDUCTION_20261006_V1.json"
K6=ROOT/"canonical/governance/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_PROJECTION_20261006_V4.json"
GREC=ROOT/"canonical/governance/G_ROUTE_FIVE_GENERATOR_DOMINANCE_RECONCILIATION_20261007_V1.json"

EXPECTED={
    ROLE_BASIS:"62c0e207ce935a02611700a69e0917f938792b11",
    ROLE_FRONTIER:"388dd2cb544b7b7bd7ded5779f51a06d3acb3ee3",
    B9_REDUCTION:"719ad74545f73f4f3e458892b7cd91005499cebd",
    SEMANTIC_REDUCTION:"fe9c5a159fef01d13169c82426f9bacf15d1b0ef",
    K6:"3e021b353dfe3dd6e9c5ea9843968e7fe75a02eb",
    GREC:"2bb66217cf42c737282428e053ad42033c30811b",
}

ESCAPE_PRIMITIVES=(
    "B0_INPUT_PERCEPTION_AND_GROUNDING",
    "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
    "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
    "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
    "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION",
)

ROLE_TO_SEMANTIC_RESPONSIBILITY={
    "B0_INPUT_PERCEPTION_AND_GROUNDING":"SEMANTIC_INTERPRETATION_OF_LOSSLESS_OBSERVATION_PAYLOAD",
    "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT":"TASK_CONTRACT_CONSTRAINT_AND_TERMINAL_RELEVANCE_SEMANTICS",
    "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING":"TASK_CONDITIONED_INFERENCE_PROPOSAL_AND_TYPED_MODEL_SEMANTICS",
    "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL":"TASK_CONDITIONED_PLAN_ACTION_SELECTION_AND_EFFECT_MODEL_SEMANTICS",
    "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION":"TASK_CONDITIONED_SYNTHESIS_OUTPUT_SELECTION_AND_UTILITY_SEMANTICS",
}

def git_blob(path:Path)->str:
    try:
        rel=path.relative_to(ROOT).as_posix()
    except ValueError:
        return ""
    cp=subprocess.run(
        ["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],
        text=True,capture_output=True,check=False,
    )
    return cp.stdout.strip() if cp.returncode==0 else ""

def project()->dict:
    errors=[]
    for p,h in EXPECTED.items():
        if git_blob(p)!=h:
            errors.append("SOURCE_DRIFT:"+p.name)

    basis=json.loads(ROLE_BASIS.read_text(encoding="utf-8"))
    frontier=json.loads(ROLE_FRONTIER.read_text(encoding="utf-8"))
    b9=json.loads(B9_REDUCTION.read_text(encoding="utf-8"))
    sem=json.loads(SEMANTIC_REDUCTION.read_text(encoding="utf-8"))
    k6=json.loads(K6.read_text(encoding="utf-8"))
    grec=json.loads(GREC.read_text(encoding="utf-8"))

    role_ids={x["id"] for x in basis["functional_basis"]}
    if not set(ESCAPE_PRIMITIVES)<=role_ids:
        errors.append("ROLE_SET_NOT_IN_FUNCTIONAL_BASIS")

    current_six=set(frontier["structural_escape_roles"])
    expected_six=set(ESCAPE_PRIMITIVES)|{"B9_MULTI_ROLE_COMPOSITION"}
    if current_six!=expected_six:
        errors.append("COARSE_ESCAPE_FRONTIER_DRIFT")

    b9_if_c=set(b9["conditional_escape_projection"]["if_C_closes"])
    if b9_if_c!=set(ESCAPE_PRIMITIVES):
        errors.append("B9_CONDITIONAL_PROJECTION_DRIFT")

    common=sem["reduction"]["common_semantic_object"]
    if "TASK_CONDITIONED_STOCHASTIC_TRACE_POLICY" not in common:
        errors.append("COMMON_TRACE_POLICY_SOURCE_MISSING")

    resp=sem["reduction"]["new_residual_generator"]["responsibility"]
    for token in ("semantic interpretations","plans","outputs","admissible next actions"):
        if token not in resp:
            errors.append("SEMANTIC_RESPONSIBILITY_MISSING:"+token)

    comp=k6["candidate_global_compression"]
    if comp["current_generic_unbound_preproof_implementation_generator_count"]!=0:
        errors.append("GENERIC_IMPLEMENTATION_RESIDUAL_REOPENED")
    if comp["remaining_unbound_semantic_binding_residual_count"]!=1:
        errors.append("SEMANTIC_BINDING_RESIDUAL_COUNT_DRIFT")
    if comp["remaining_unbound_semantic_binding_residual"]!="K6_SOUND_POLICY_COVER_WITNESS_AND_SELECTED_DISCRIMINATOR_BINDING":
        errors.append("SEMANTIC_BINDING_RESIDUAL_ID_DRIFT")
    if grec["k6_role"]["preproof_generic_implementation_generator"] is not False:
        errors.append("G_ROUTE_GENERIC_K6_REOPENED")

    ok=not errors
    return {
        "schema":"PROJECT_BRAIN_FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_V2",
        "status":"PASS__CONDITIONAL_ON_C__5_PRIMITIVE_ESCAPE_ROLES_PROJECT_TO_ONE_SHARED_SEMANTIC_CERTIFICATE_FRONTIER__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":errors,
        "coarse_escape_role_count":6,
        "b9_is_conditionally_derivative":True,
        "conditional_on_C":True,
        "primitive_escape_role_count":5,
        "primitive_escape_roles":list(ESCAPE_PRIMITIVES),
        "shared_semantic_frontier":"TASK_CONDITIONED_TRACE_POLICY_SEMANTIC_CERTIFICATE_AND_SELECTED_DISCRIMINATOR_BINDING",
        "role_to_semantic_responsibility":ROLE_TO_SEMANTIC_RESPONSIBILITY,
        "independent_new_implementation_searches_required":0 if ok else None,
        "context_specific_semantic_certificate_work_remains":True,
        "distributional_dominance_remains":True,
        "resource_and_ownership_remain":True,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(project(),indent=2,sort_keys=True))
