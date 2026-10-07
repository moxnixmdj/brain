from canonical.runtime.typed_acceptance_finite_search_v1 import search


PROGRAM = {
    "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
    "fields": [
        {"id": "x", "type": "integer", "dimension": "score", "source": "candidate"},
        {"id": "safe", "type": "boolean", "dimension": "dimensionless", "source": "candidate"},
    ],
    "accept_when": {
        "op": "and",
        "args": [
            {
                "op": "ge",
                "left": {"op": "ref", "id": "x"},
                "right": {"op": "const", "type": "number", "dimension": "score", "value": 2},
            },
            {"op": "ref", "id": "safe"},
        ],
    },
}


def test_exhaustive_search_finds_deterministic_first_passing_candidate():
    out = search(
        PROGRAM,
        trusted_values={},
        candidate_domains={"x": [1, 2, 3], "safe": [False, True]},
    )
    assert out["pass"] is True, out
    assert out["examined"] == 6
    assert out["complete_over_declared_domains"] is True
    assert out["selected_candidate"] == {"safe": True, "x": 2}


def test_no_candidate_is_reported_without_inventing_one():
    out = search(
        PROGRAM,
        trusted_values={},
        candidate_domains={"x": [0, 1], "safe": [False]},
    )
    assert out["pass"] is False
    assert out["status"] == "NO_ACCEPTED_CANDIDATE_IN_DECLARED_DOMAINS"
    assert out["complete_over_declared_domains"] is True


def test_candidate_domain_bound_is_hard():
    out = search(
        PROGRAM,
        trusted_values={},
        candidate_domains={"x": list(range(100)), "safe": [False, True]},
        max_candidates=100,
    )
    assert out["status"] == "BOUND_EXCEEDED"
    assert out["complete_over_declared_domains"] is False


def test_invalid_typed_domain_value_fails_closed():
    out = search(
        PROGRAM,
        trusted_values={},
        candidate_domains={"x": ["not-an-int"], "safe": [True]},
    )
    assert out["status"] == "FAIL_CLOSED"
