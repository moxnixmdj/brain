from unittest.mock import patch

from canonical.runtime.p3_real_context_v3_admission_v11 import evaluate
from canonical.tests.test_p3_policy_influence_relevance_cell_v1 import public_case


def v10_capacity():
    return {
        "pass":False,
        "nonbinding_capacity_reason":"CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY",
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def source_pass():
    return {
        "pass":True,
        "p3_contract_cell_authorized":True,
        "selected_policy_adequacy_verified":True,
        "interpretation_set_enumeration_required":False,
        "complete_world_partition_required":False,
        "source_authorization_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "selected_policy_id":"P_B",
        "selected_claim_ids":["A","B"],
        "rendered_text":"ok",
        "render_trace":[],
    }


def payload():
    return {
        "context_id":"ctx",
        "v3_input":public_case(2),
        "source_positive_selection_contract":{"schema":"x"},
    }


def test_v10_positive_route_is_preserved():
    with patch("canonical.runtime.p3_real_context_v3_admission_v11.evaluate_v10",return_value={"pass":True,"route":"V10_PASS"}):
        out=evaluate({"context_id":"ctx","v3_input":public_case(2)})
    assert out["pass"] is True
    assert out["route"]=="V10_PASS"
    assert out["v10_preserved_positive_route"] is True


def test_v11_source_positive_route_closes_current_cell_without_world_partition():
    with patch("canonical.runtime.p3_real_context_v3_admission_v11.evaluate_v10",return_value=v10_capacity()), patch(
        "canonical.runtime.p3_real_context_v3_admission_v11.evaluate_source_positive",return_value=source_pass()
    ):
        out=evaluate(payload())
    assert out["pass"] is True,out
    assert out["route"]=="SOURCE_POSITIVE_SELECTION_CELL_V1"
    assert out["selected_claim_ids"]==["A","B"]
    assert out["complete_world_partition_required"] is False
    assert out["unused_semantic_dimensions_need_not_be_classified"] is True


def test_stronger_policy_influence_authority_cannot_fall_through():
    p=payload(); p["policy_influence_contract"]={"x":1}
    with patch("canonical.runtime.p3_real_context_v3_admission_v11.evaluate_v10",return_value={"pass":False,"reason":"POLICY_INFLUENCE_CONTRACT_UNSATISFIED"}):
        out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="POLICY_INFLUENCE_CONTRACT_UNSATISFIED"
    assert out["source_positive_selection_fast_path_pass"] is False


def test_non_relevance_failure_is_not_swallowed():
    with patch("canonical.runtime.p3_real_context_v3_admission_v11.evaluate_v10",return_value={"pass":False,"nonbinding_capacity_reason":"CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS"}):
        out=evaluate(payload())
    assert out["pass"] is False
    assert out["source_positive_selection_not_applicable_reason"]=="V10_DID_NOT_REACH_CAPACITY_BINDING_RELEVANCE_FRONTIER"


def test_bad_source_positive_contract_fails_closed():
    with patch("canonical.runtime.p3_real_context_v3_admission_v11.evaluate_v10",return_value=v10_capacity()), patch(
        "canonical.runtime.p3_real_context_v3_admission_v11.evaluate_source_positive",return_value={"pass":False,"reason":"SOURCE_POSITIVE_ADEQUACY_NOT_CERTIFIED"}
    ):
        out=evaluate(payload())
    assert out["pass"] is False
    assert out["reason"]=="SOURCE_POSITIVE_SELECTION_CONTRACT_UNSATISFIED"


def test_v11_never_mints_outer_authority():
    with patch("canonical.runtime.p3_real_context_v3_admission_v11.evaluate_v10",return_value=v10_capacity()), patch(
        "canonical.runtime.p3_real_context_v3_admission_v11.evaluate_source_positive",return_value=source_pass()
    ):
        out=evaluate(payload())
    assert out["pass"] is True
    for k in ("source_authorization_verified","policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
        assert out[k] is False
    assert out["terminal_credit_delta"]==0
