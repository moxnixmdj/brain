from unittest.mock import patch

from canonical.runtime.p3_real_context_v3_admission_v12 import evaluate


def payload():
    return {
        "context_id":"ctx",
        "v3_input":{"task":{}},
        "bound_relevance_cegar_loop":{
            "cegar_problem":{},
            "truth_payloads_by_discriminator_id":{},
            "source_positive_selection_contracts":{},
        },
    }


def capacity():
    return {
        "pass":False,
        "nonbinding_capacity_reason":"CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY",
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def loop_pass():
    return {
        "pass":True,
        "status":"PASS__P3_BOUND_RELEVANCE_CEGAR_LOOP_REALIZED",
        "selected_policy_id":"p",
        "selected_claim_ids":["A"],
        "rendered_text":"A",
        "render_trace":[],
        "refinement_steps":1,
        "trace":[],
        "p3_contract_cell_authorized":True,
        "relevance_control_loop_authorized":True,
        "source_authorization_verified":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def test_v11_positive_route_is_preserved():
    with patch("canonical.runtime.p3_real_context_v3_admission_v12.evaluate_v11",return_value={"pass":True,"route":"V11_PASS"}):
        out=evaluate({"context_id":"ctx","v3_input":{"task":{}}})
    assert out["pass"] is True
    assert out["route"]=="V11_PASS"
    assert out["v11_preserved_positive_route"] is True


def test_v12_runs_loop_only_at_capacity_binding_frontier():
    with patch("canonical.runtime.p3_real_context_v3_admission_v12.evaluate_v11",return_value=capacity()), patch(
        "canonical.runtime.p3_real_context_v3_admission_v12.evaluate_loop",return_value=loop_pass()
    ):
        out=evaluate(payload())
    assert out["pass"] is True,out
    assert out["route"]=="BOUND_RELEVANCE_CEGAR_LOOP_V1"
    assert out["refinement_steps"]==1


def test_failed_stronger_source_positive_contract_never_falls_through():
    p=payload()
    p["source_positive_selection_contract"]={"schema":"x"}
    with patch("canonical.runtime.p3_real_context_v3_admission_v12.evaluate_v11",return_value={"pass":False,"reason":"SOURCE_POSITIVE_SELECTION_CONTRACT_UNSATISFIED"}), patch(
        "canonical.runtime.p3_real_context_v3_admission_v12.evaluate_loop"
    ) as loop:
        out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="SOURCE_POSITIVE_SELECTION_CONTRACT_UNSATISFIED"
    loop.assert_not_called()


def test_non_relevance_failure_is_not_swallowed():
    with patch("canonical.runtime.p3_real_context_v3_admission_v12.evaluate_v11",return_value={"pass":False,"nonbinding_capacity_reason":"CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS"}), patch(
        "canonical.runtime.p3_real_context_v3_admission_v12.evaluate_loop"
    ) as loop:
        out=evaluate(payload())
    assert out["pass"] is False
    assert out["bound_relevance_cegar_loop_not_applicable_reason"]=="V11_DID_NOT_REACH_CAPACITY_BINDING_RELEVANCE_FRONTIER"
    loop.assert_not_called()


def test_loop_open_result_remains_fail_closed_at_front_door():
    open_loop={"pass":False,"status":"OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED","reason":"UNKNOWN"}
    with patch("canonical.runtime.p3_real_context_v3_admission_v12.evaluate_v11",return_value=capacity()), patch(
        "canonical.runtime.p3_real_context_v3_admission_v12.evaluate_loop",return_value=open_loop
    ):
        out=evaluate(payload())
    assert out["pass"] is False
    assert out["reason"]=="BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED"
    assert out["detail"]["loop_status"]=="OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED"


def test_nested_loop_cannot_override_v3_or_context():
    p=payload()
    p["bound_relevance_cegar_loop"]["v3_input"]={"forged":True}
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="BOUND_RELEVANCE_CEGAR_LOOP_FIELDS_INVALID"


def test_v12_success_never_mints_outer_authority():
    with patch("canonical.runtime.p3_real_context_v3_admission_v12.evaluate_v11",return_value=capacity()), patch(
        "canonical.runtime.p3_real_context_v3_admission_v12.evaluate_loop",return_value=loop_pass()
    ):
        out=evaluate(payload())
    assert out["pass"] is True
    assert out["source_authorization_verified"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
