from canonical.runtime.policy_adequacy_executable_predicate_cover_v1 import (
    _structural_cover,
    _trusted_catalog,
    evaluate_universal_overapproximation,
    P3_ATOM,
    P2_ATOM,
)


def row(pid, condition):
    return {
        "policy_id": pid,
        "condition": condition,
        "trusted_provenance": "TEST_ONLY_PREAUTHENTICATED_FACT",
    }


def test_complementary_executable_policy_predicates_cover_true():
    a = {"op": "ATOM", "id": "a"}
    out = _structural_cover(
        {"op": "TRUE"},
        [
            row("p_true", a),
            row("p_false", {"op": "NOT", "arg": a}),
        ],
    )
    assert out["pass"] is True
    assert out["positive_cover_proved"] is True
    assert out["separate_selected_discriminator_required"] is False
    assert out["scope_model_count"] == 2
    assert out["terminal_credit_delta"] == 0


def test_one_sided_predicate_returns_exact_abstract_residual_not_failure():
    a = {"op": "ATOM", "id": "a"}
    out = _structural_cover({"op": "TRUE"}, [row("p", a)])
    assert out["pass"] is False
    assert out["status"].startswith("UNRESOLVED")
    assert out["negative_capability_failure_authorized"] is False
    assert out["uncovered_abstract_valuations"] == [{"a": False}]
    assert out["terminal_credit_delta"] == 0


def test_false_negatives_are_allowed_when_other_policy_covers():
    a = {"op": "ATOM", "id": "a"}
    b = {"op": "ATOM", "id": "b"}
    # p_a deliberately recognizes only a subset. p_rest covers its complement.
    out = _structural_cover(
        {"op": "TRUE"},
        [
            row("p_a", {"op": "AND", "args": [a, b]}),
            row("p_rest", {"op": "NOT", "arg": {"op": "AND", "args": [a, b]}}),
        ],
    )
    assert out["pass"] is True


def test_malformed_formula_fails_closed():
    out = _structural_cover(
        {"op": "TRUE"},
        [row("p", {"op": "ATOM", "id": ""})],
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"


def test_real_catalog_admits_only_repository_checked_executable_predicates():
    accepted, rejected = _trusted_catalog()
    p3 = [x for x in accepted if x["condition"] == {"op": "ATOM", "id": P3_ATOM}]
    p2 = [x for x in accepted if x["condition"] == {"op": "ATOM", "id": P2_ATOM}]
    assert p3, (accepted, rejected)
    assert p2, (accepted, rejected)
    assert all(x["trusted_provenance"].startswith("canonical.runtime.") for x in accepted)
    assert not any(x.get("candidate") == "P2" for x in rejected), rejected


def test_universal_production_entry_point_never_turns_incomplete_cover_into_negative_claim():
    out = evaluate_universal_overapproximation()
    assert out["scope_initialization"] == "TRUE__NO_CALLER_SCOPE_NARROWING_ACCEPTED"
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
    if not out["pass"]:
        assert out["negative_capability_failure_authorized"] is False
        assert out["uncovered_abstract_valuations"] == [{
            P2_ATOM: False,
            P3_ATOM: False,
        }]
