from canonical.runtime.livebench_if_response_interface_gap_v1 import verify

def test_exact_frozen_response_interface_gap():
    out=verify()
    assert out["status"]=="PASS"
    assert out["response_interface_gap_proved"] is True
    assert out["answer_set_cardinality"]==3
    assert set(out["successful_model_independent_answer_set"])=={
      "PLAIN_GOAL_COMPLETE",
      "COMPOUND_GOAL_COMPLETE",
      "GROUNDED_CAPABILITY_COMPOSITION_COMPLETE",
    }
    assert out["answer_set_input_independent"] is True
    assert out["optional_model_finalizer_reachable"] is False
    assert out["terminal_cases_consumed"]==0
    assert out["livebench_score_proved"] is False
    assert out["acceptance_credit_authorized"] is False
    assert out["execution_authority"] is False
    assert out["fresh_reality_authority"] is False
