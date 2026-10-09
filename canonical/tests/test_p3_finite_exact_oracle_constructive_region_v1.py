from canonical.runtime.p3_conditioned_policy_adequacy_registry_v1 import catalog
from canonical.runtime.p3_robust_policy_adequacy_cegar_v1 import solve

ATOMS=[
 "CODING_FINITE_SOLVER_CANDIDATE_SET_FINITE_V1",
 "CODING_FINITE_SOLVER_ORACLE_TOTAL_V1",
 "CODING_FINITE_SOLVER_ORACLE_SOUND_COMPLETE_V1",
 "CODING_FINITE_SOLVER_VALID_MEMBER_EXISTS_V1",
 "CODING_FINITE_SOLVER_CALL_BUDGET_SUFFICIENT_V1",
 "CODING_FINITE_SOLVER_ORACLE_PRETERMINAL_ADMISSIBLE_V1",
]
POLICY="BRAIN_FINITE_CANDIDATE_EXACT_ORACLE_SOLVER_V1"

def atom(a):
    return {"op":"ATOM","id":a}

def problem(proved):
    constraints=[atom(a) for a in proved]
    return {
        "decision_basis":list(ATOMS),
        "formal_source_constraints":constraints,
        "proposed_refinements":constraints,
        "policy_conditions":{},
        "policy_adequacy_bindings":{},
        "discriminators":[],
    }

def test_catalog_registers_second_coding_constructive_region():
    c=catalog()
    ids={x["policy_id"] for x in c["policies"]}
    assert POLICY in ids
    assert "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1" in ids
    assert c["membership_self_certified"] is False
    assert c["terminal_credit_delta"]==0

def test_all_six_source_authorized_atoms_certify_common_constructive_policy():
    out=solve(problem(ATOMS))
    assert out["pass"] is True
    assert out["status"]=="COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS"
    assert out["selected_policy_id"]==POLICY
    assert out["certified_common_policies"]==[POLICY]
    assert out["common_policy_certified"] is True
    assert out["source_authorization_verified"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0

def test_missing_any_one_atom_leaves_an_uncovered_false_world():
    for missing in ATOMS:
        proved=[a for a in ATOMS if a!=missing]
        out=solve(problem(proved))
        assert out["pass"] is False, missing
        assert out["reason"]=="AUTHENTICATED_POLICY_COVER_INCOMPLETE", (missing,out)
        uncovered=out["detail"]["uncovered_models"]
        assert any(row["valuation"][missing] is False for row in uncovered), missing
