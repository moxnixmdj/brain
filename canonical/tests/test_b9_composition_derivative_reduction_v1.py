from canonical.runtime.b9_composition_derivative_reduction_v1 import (
    five_role_escape_projection,
    localize_b9_failure,
    reduce_b9,
)

def test_b9_dominance_is_implied_by_primitive_dominance_plus_c():
    x=reduce_b9({"B1":True,"B2":True,"B7":True},composition_closure_bound=True)
    assert x.b9_dominance_implied is True
    assert x.b9_independent_escape is False
    assert x.terminal_credit_delta==0

def test_b9_failure_localizes_to_primitive_role_when_one_is_open():
    x=localize_b9_failure(
        {"B1":True,"B2":False,"B7":True},
        composition_closure_bound=True,
    )
    assert x["b9_dominance_implied"] is False
    assert x["localized_cause"]=="PRIMITIVE_ROLE_DOMINANCE_OPEN_OR_FALSE"
    assert x["primitive_failures"]==["B2"]

def test_b9_stays_independent_only_when_c_is_not_bound():
    x=localize_b9_failure(
        {"B1":True,"B2":True},
        composition_closure_bound=False,
    )
    assert x["b9_dominance_implied"] is False
    assert x["b9_independent_escape"] is True
    assert x["localized_cause"]=="COMPOSITION_CLOSURE_OPEN_OR_FALSE"

def test_six_role_escape_becomes_five_conditional_on_c():
    out=five_role_escape_projection(
        (
            "B0_INPUT_PERCEPTION_AND_GROUNDING",
            "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
            "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
            "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
            "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION",
            "B9_MULTI_ROLE_COMPOSITION",
        ),
        composition_closure_bound=True,
    )
    assert out==(
        "B0_INPUT_PERCEPTION_AND_GROUNDING",
        "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
        "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
        "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
        "B7_OUTPUT_COMMUNICATION_SYNTHESIS_AND_ARTIFACT_CONSTRUCTION",
    )
