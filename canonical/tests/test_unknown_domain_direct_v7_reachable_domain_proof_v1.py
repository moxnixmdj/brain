from canonical.runtime import unknown_domain_direct_v7_reachable_domain_proof_v1 as p


def test_v7_reachable_runtime_domain_proof_passes_without_credit():
    out=p.prove()
    assert out["status"]==p.STATUS
    assert out["falsified_v6_component_reused"] is False
    assert out["runtime_input_domain"]["instance_class_spoof_str_rejected"] is True
    assert out["runtime_input_domain"]["instance_class_spoof_bytes_rejected"] is True
    assert out["runtime_input_domain"]["genuine_str_subclasses_retained"] is True
    assert out["runtime_input_domain"]["genuine_bytes_subclasses_retained"] is True
    assert out["accounting"]["acceptance_credit_delta"]==0
    assert out["accounting"]["terminal_cases_consumed"]==0


def test_v7_reuses_only_nonfalsified_v6_lemmas():
    out=p.prove()
    assert set(out["retained_v6_components"])=={
        "IDENTIFIER_TOTALITY",
        "TRANSFER_THEOREM",
        "ABSTENTION_THEOREM",
    }
    assert "STRING_TOTALITY" not in out["retained_v6_components"]


def test_v7_keeps_external_origin_binding_fail_closed():
    out=p.prove()
    required=set(out["required_external_binding_before_acceptance"])
    assert "PRODUCTION_BEACON_ORIGIN_IS_GENUINE_RUNTIME_STR" in required
    assert "EVALUATOR_SECRET_ORIGIN_IS_GENUINE_RUNTIME_STR_OR_BYTES" in required
    assert "INDEPENDENT_CONTENT_BOUND_EXECUTION_OF_THIS_EXACT_PROOF_AND_TEST_SET" in required
