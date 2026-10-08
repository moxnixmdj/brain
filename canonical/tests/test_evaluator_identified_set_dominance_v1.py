from canonical.runtime.evaluator_identified_set_dominance_v1 import (
    IdentifiedSetError,
    solve,
)


def d(p0, p1):
    return [
        {"id": "bad", "probability": p0},
        {"id": "good", "probability": p1},
    ]


def w(i, bad, good, **facts):
    return {
        "world_id": i,
        "utility": {"bad": bad, "good": good},
        "facts": facts,
    }


def test_pass_when_even_worst_admissible_evaluator_prefers_brain():
    out = solve({
        "target_distribution": d("1/2", "1/2"),
        "brain_distribution": d("1/4", "3/4"),
        "evaluator_worlds": [
            w("W1", 0, 1, judge="A"),
            w("W2", "1/4", 1, judge="B"),
        ],
    })
    assert out["status"].startswith("PASS")
    assert out["identified_interval"]["lower_delta"] == "3/16"


def test_fail_when_every_admissible_evaluator_prefers_target():
    out = solve({
        "target_distribution": d("1/4", "3/4"),
        "brain_distribution": d("3/4", "1/4"),
        "evaluator_worlds": [
            w("W1", 0, 1),
            w("W2", "1/4", 1),
        ],
    })
    assert out["status"].startswith("FAIL")
    assert out["identified_interval"]["upper_delta"] < "0"


def test_unknown_returns_opposing_compatible_world_witnesses():
    out = solve({
        "target_distribution": d("1/2", "1/2"),
        "brain_distribution": d("1/4", "3/4"),
        "evaluator_worlds": [
            w("GOOD_HIGH", 0, 1, orientation="normal"),
            w("BAD_HIGH", 1, 0, orientation="reversed"),
        ],
    })
    assert out["status"].startswith("UNKNOWN")
    assert out["worst_case_world"]["delta"] == "-1/4"
    assert out["best_case_world"]["delta"] == "1/4"


def test_fact_query_can_perfectly_resolve_current_ambiguity():
    out = solve({
        "target_distribution": d("1/2", "1/2"),
        "brain_distribution": d("1/4", "3/4"),
        "evaluator_worlds": [
            w("W1", 0, 1, polarity="normal", irrelevant="x"),
            w("W2", "1/4", 1, polarity="normal", irrelevant="y"),
            w("W3", 1, 0, polarity="reversed", irrelevant="x"),
        ],
        "candidate_fact_keys": ["irrelevant", "polarity"],
    })
    top = out["minimum_information_candidates"][0]
    assert top["fact_key"] == "polarity"
    assert top["all_observation_branches_decisive"] is True


def test_incomplete_utility_support_fails_closed():
    try:
        solve({
            "target_distribution": d("1/2", "1/2"),
            "brain_distribution": d("1/2", "1/2"),
            "evaluator_worlds": [{"world_id": "W", "utility": {"good": 1}}],
        })
    except IdentifiedSetError as exc:
        assert "UTILITY_SUPPORT_MISMATCH" in str(exc)
    else:
        raise AssertionError("expected fail closed")


def test_runtime_never_self_certifies_world_set_completeness_or_terminal_authority():
    out = solve({
        "target_distribution": d("1/2", "1/2"),
        "brain_distribution": d("1/2", "1/2"),
        "evaluator_worlds": [w("W", 0, 1)],
    })
    assert out["semantic_world_set_completeness_verified_by_this_runtime"] is False
    assert out["terminal_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0
