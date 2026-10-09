from canonical.runtime.mission_carrier_factorization_v1 import evaluate

CLAIM = "a" * 64
SCOPE = "b" * 64
SEMANTICS = "c" * 64


def base(worlds):
    return {
        "mission_id": "MISSION_V1",
        "carrier_schema_id": "CARRIER_V1",
        "claim_id": CLAIM,
        "scope_sha256": SCOPE,
        "semantics_sha256": SEMANTICS,
        "worlds": worlds,
    }


def test_direct_aliasing_counterexample():
    out = evaluate(base([
        {"world_id": "w1", "carrier_value_id": "x", "mission_verdict": True},
        {"world_id": "w2", "carrier_value_id": "x", "mission_verdict": False},
    ]))
    assert out["status"] == "CARRIER_FACTORIZATION_COUNTEREXAMPLE"
    assert out["universal_factorization_proved"] is False
    assert out["global_mission_completion_derivable"] is False
    assert "R4_SEMANTIC_BINDING_FAILURE" in out["root_classification"]
    assert out["new_semantic_root_required"] is False
    assert out["claim_id"] == CLAIM


def test_stochastic_same_support_different_risk_is_detected():
    out = evaluate(base([
        {"world_id": "law_low_failure", "carrier_value_id": "support_{ok,fail}", "mission_verdict": True},
        {"world_id": "law_high_failure", "carrier_value_id": "support_{ok,fail}", "mission_verdict": False},
    ]))
    assert out["status"] == "CARRIER_FACTORIZATION_COUNTEREXAMPLE"


def test_hyperproperty_single_trace_projection_is_detected():
    out = evaluate(base([
        {"world_id": "noninterfering_system", "carrier_value_id": "visible_trace_t", "mission_verdict": True},
        {"world_id": "interfering_system", "carrier_value_id": "visible_trace_t", "mission_verdict": False},
    ]))
    assert out["status"] == "CARRIER_FACTORIZATION_COUNTEREXAMPLE"


def test_temporal_prefix_aliasing_is_detected():
    out = evaluate(base([
        {"world_id": "eventually_completes", "carrier_value_id": "finite_prefix_p", "mission_verdict": True},
        {"world_id": "stutters_forever", "carrier_value_id": "finite_prefix_p", "mission_verdict": False},
    ]))
    assert out["status"] == "CARRIER_FACTORIZATION_COUNTEREXAMPLE"


def test_unknown_verdict_fails_closed():
    out = evaluate(base([
        {"world_id": "w1", "carrier_value_id": "x", "mission_verdict": "UNKNOWN"},
    ]))
    assert out["status"] == "UNKNOWN_FAIL_CLOSED"
    assert out["universal_factorization_proved"] is False


def test_no_conflict_in_sample_is_not_proof():
    out = evaluate(base([
        {"world_id": "w1", "carrier_value_id": "x", "mission_verdict": True},
        {"world_id": "w2", "carrier_value_id": "x", "mission_verdict": True},
        {"world_id": "w3", "carrier_value_id": "y", "mission_verdict": False},
    ]))
    assert out["status"] == "NO_COUNTEREXAMPLE_IN_DECLARED_WITNESS_SET__NOT_PROOF"
    assert out["pass"] is False
    assert out["universal_factorization_proved"] is False
    assert out["global_mission_completion_derivable"] is False


def test_separate_carriers_do_not_create_false_counterexample():
    out = evaluate(base([
        {"world_id": "w1", "carrier_value_id": "x", "mission_verdict": True},
        {"world_id": "w2", "carrier_value_id": "y", "mission_verdict": False},
    ]))
    assert out["status"] == "NO_COUNTEREXAMPLE_IN_DECLARED_WITNESS_SET__NOT_PROOF"


def test_duplicate_world_id_fails_closed():
    out = evaluate(base([
        {"world_id": "w", "carrier_value_id": "x", "mission_verdict": True},
        {"world_id": "w", "carrier_value_id": "y", "mission_verdict": False},
    ]))
    assert out["status"] == "FAIL_CLOSED"
    assert any("DUPLICATE_WORLD_ID" in e for e in out["errors"])


def test_invalid_verdict_fails_closed():
    out = evaluate(base([
        {"world_id": "w", "carrier_value_id": "x", "mission_verdict": "MAYBE"},
    ]))
    assert out["status"] == "FAIL_CLOSED"


def test_missing_carrier_schema_fails_closed():
    data = base([{"world_id": "w", "carrier_value_id": "x", "mission_verdict": True}])
    data.pop("carrier_schema_id")
    out = evaluate(data)
    assert out["status"] == "FAIL_CLOSED"


def test_invalid_claim_id_fails_closed():
    data = base([{"world_id": "w", "carrier_value_id": "x", "mission_verdict": True}])
    data["claim_id"] = "not-a-sha"
    out = evaluate(data)
    assert out["status"] == "FAIL_CLOSED"
    assert "CLAIM_ID_INVALID" in out["errors"]


def test_invalid_scope_digest_fails_closed():
    data = base([{"world_id": "w", "carrier_value_id": "x", "mission_verdict": True}])
    data["scope_sha256"] = "bad"
    out = evaluate(data)
    assert out["status"] == "FAIL_CLOSED"
    assert "SCOPE_SHA256_INVALID" in out["errors"]


def test_invalid_semantics_digest_fails_closed():
    data = base([{"world_id": "w", "carrier_value_id": "x", "mission_verdict": True}])
    data["semantics_sha256"] = "bad"
    out = evaluate(data)
    assert out["status"] == "FAIL_CLOSED"
    assert "SEMANTICS_SHA256_INVALID" in out["errors"]
