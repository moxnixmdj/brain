from canonical.runtime.prepromotion_falsification_gate_v1 import evaluate


SHA40 = "a" * 40


def R(*, independent=False):
    return {
        "status": "PASS",
        "content_addressed": True,
        "receipt_sha": SHA40,
        "independent": independent,
    }


def base_spec():
    return {
        "candidate_id": "TEST-CANDIDATE",
        "claim_type": "UNIVERSAL_FORMAL",
        "risk_features": {
            "uses_floating_point": False,
            "uses_opaque_identifiers": False,
            "accepts_open_string_domain": False,
            "has_transitive_runtime_dependencies": False,
        },
        "receipts": {
            "SUBJECT_BYTES_BOUND": R(),
            "QUANTIFIED_DOMAIN_BOUND": R(),
            "COUNTEREXAMPLE_SEARCH_PASS": R(),
            "BOUNDARY_SEARCH_PASS": R(),
            "METAMORPHIC_SEARCH_PASS": R(),
            "INDEPENDENT_REPLAY_PASS": R(independent=True),
            "SEPARATE_REDUCTION_PRECOMMIT": R(),
        },
        "known_counterexamples": [],
        "post_outcome_rule_change": False,
    }


def test_complete_package_only_becomes_eligible_for_separate_reduction():
    out = evaluate(base_spec())
    assert out["status"].startswith("PASS__")
    assert out["eligible_for_separate_reduction"] is True
    assert out["acceptance_credit"] is False
    assert out["promotion_authority"] is False


def test_known_counterexample_forces_fail_closed():
    x = base_spec()
    x["known_counterexamples"] = ["reachable-falsifier"]
    out = evaluate(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "KNOWN_COUNTEREXAMPLE_REMAINS_OPEN" in out["errors"]


def test_exact_float_risk_requires_exact_float_receipt():
    x = base_spec()
    x["risk_features"]["uses_floating_point"] = True
    out = evaluate(x)
    assert out["status"] == "FAIL_CLOSED"
    assert any("EXACT_FLOAT_SEMANTICS_BOUND" in e for e in out["errors"])

    x["receipts"]["EXACT_FLOAT_SEMANTICS_BOUND"] = R()
    assert evaluate(x)["eligible_for_separate_reduction"] is True


def test_opaque_identifier_risk_requires_totality_proof():
    x = base_spec()
    x["risk_features"]["uses_opaque_identifiers"] = True
    out = evaluate(x)
    assert out["status"] == "FAIL_CLOSED"
    assert any("IDENTIFIER_TOTALITY_PROVED" in e for e in out["errors"])


def test_open_string_domain_requires_totality_proof():
    x = base_spec()
    x["risk_features"]["accepts_open_string_domain"] = True
    out = evaluate(x)
    assert out["status"] == "FAIL_CLOSED"
    assert any("STRING_DOMAIN_TOTALITY_PROVED" in e for e in out["errors"])


def test_transitive_dependencies_require_closure_receipt():
    x = base_spec()
    x["risk_features"]["has_transitive_runtime_dependencies"] = True
    out = evaluate(x)
    assert out["status"] == "FAIL_CLOSED"
    assert any("TRANSITIVE_DEPENDENCY_CLOSURE_BOUND" in e for e in out["errors"])


def test_independent_replay_must_really_be_independent():
    x = base_spec()
    x["receipts"]["INDEPENDENT_REPLAY_PASS"] = R(independent=False)
    out = evaluate(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "INDEPENDENT_REPLAY_NOT_INDEPENDENT" in out["errors"]


def test_post_outcome_rule_change_is_forbidden():
    x = base_spec()
    x["post_outcome_rule_change"] = True
    out = evaluate(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "POST_OUTCOME_RULE_CHANGE_FORBIDDEN" in out["errors"]
