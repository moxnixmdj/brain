from canonical.runtime import livebench_frozen_schema19_envelope_v1 as env
from canonical.runtime import livebench_schema19_pointwise_candidate_v1 as s
from canonical.runtime import livebench_union25_archetypes_v1 as u


def test_schema19_has_exactly_six_extra_signatures():
    out = s.verify_scope_closure()
    assert out["schema19_extra_signature_count"] == 6
    assert out["remaining_new_constructor_shapes_beyond_active15_plus_one"] == 2
    assert out["independent_exact_checker_verification_required"] is True


def test_case_normalization_preserves_comma_identity():
    for text in ["alpha", "alpha, beta", '"Section 1, alpha?"']:
        assert ("," in text) == ("," in text.upper())
        assert ("," in text) == ("," in text.lower())


def test_observed_schema19_extra_signatures_match_solver_domain():
    observed = {frozenset(x) for x in env.verify()["remaining_extra_signatures"]}
    expected = {
        frozenset({u.CONSTRAINED}),
        frozenset({u.ENGLISH_CAPITAL}),
        frozenset({u.ENGLISH_LOWERCASE}),
        frozenset({u.NO_COMMA}),
        frozenset({u.ENGLISH_CAPITAL, u.NO_COMMA}),
        frozenset({u.ENGLISH_LOWERCASE, u.NO_COMMA}),
    }
    assert observed == expected


def test_outside_schema19_fails_closed():
    out = s.solve_contracts([
        {
            "instruction_id": u.LANGUAGE,
            "slots": {"language": "en"},
        }
    ])
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "OUTSIDE_FROZEN_SCHEMA19_ENVELOPE"
