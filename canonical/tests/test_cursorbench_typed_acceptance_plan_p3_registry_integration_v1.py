from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry
from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3

A="CURSORBENCH_TYPED_ACCEPTANCE_PLAN_REGION_V1"
P="BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"

def atom():
    return {"op":"ATOM","id":A}

def test_registry_injects_only_on_exact_atom():
    good=registry.augment_problem({"decision_basis":[A]})
    assert good["pass"] is True
    assert good["injected_policy_ids"]==[P]
    assert good["problem"]["policy_conditions"][P]==atom()
    miss=registry.augment_problem({"decision_basis":["other"]})
    assert P not in miss["injected_policy_ids"]

def test_p3_uses_typed_policy_only_after_atom_is_proved():
    x=atom()
    out=p3.solve({"decision_basis":[A],"formal_source_constraints":[x],"proposed_refinements":[x]})
    assert out["pass"] is True, out
    assert out["selected_policy_id"]==P
    assert out["policy_adequacy_authority"] is True
    assert out["terminal_authority"] is False

def test_registry_presence_does_not_prove_membership():
    out=p3.solve({"decision_basis":[A]})
    assert out["pass"] is False
    assert out["reason"]=="AUTHENTICATED_POLICY_COVER_INCOMPLETE"
    assert any(row["valuation"].get(A) is False for row in out["detail"]["uncovered_models"])
