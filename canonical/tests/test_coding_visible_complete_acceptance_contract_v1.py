from canonical.runtime.coding_visible_complete_acceptance_contract_v1 import evaluate, POLICY_ID


def test_accepts_when_every_visible_checker_passes():
    candidate = {"x": 3, "name": "ok"}
    out = evaluate(
        candidate,
        ["positive", "named"],
        {
            "positive": lambda c: c["x"] > 0,
            "named": lambda c: c["name"] == "ok",
        },
        max_checks=2,
    )
    assert out["pass"] is True
    assert out["policy_id"] == POLICY_ID
    assert out["candidate_accepted"] is True
    assert out["counterexample_checker_ids"] == []
    assert out["candidate_space_finiteness_required"] is False
    assert out["transform_taxonomy_required"] is False


def test_rejects_candidate_and_returns_discriminating_failed_checker_ids():
    out = evaluate(
        {"x": -1, "name": "bad"},
        ["positive", "named"],
        {
            "positive": lambda c: c["x"] > 0,
            "named": lambda c: c["name"] == "ok",
        },
        max_checks=2,
    )
    assert out["pass"] is True
    assert out["candidate_accepted"] is False
    assert out["counterexample_checker_ids"] == ["positive", "named"]
    assert out["counterexample_present"] is True


def test_checker_exception_fails_closed():
    def boom(_):
        raise RuntimeError("boom")
    out = evaluate({"x": 1}, ["boom"], {"boom": boom}, max_checks=1)
    assert out["pass"] is False
    assert out["reason"] == "CHECKER_EXCEPTION"


def test_nonboolean_checker_fails_closed():
    out = evaluate({"x": 1}, ["bad"], {"bad": lambda _: 1}, max_checks=1)
    assert out["pass"] is False
    assert out["reason"] == "CHECKER_NONBOOLEAN_RESULT"


def test_missing_checker_fails_closed():
    out = evaluate({"x": 1}, ["missing"], {}, max_checks=1)
    assert out["pass"] is False
    assert out["reason"] == "CHECKER_MISSING_OR_NOT_CALLABLE"


def test_duplicate_checker_ids_fail_closed():
    out = evaluate({"x": 1}, ["a", "a"], {"a": lambda _: True}, max_checks=2)
    assert out["pass"] is False
    assert out["reason"] == "CHECKER_ID_DUPLICATE"


def test_insufficient_budget_fails_closed():
    out = evaluate(
        {"x": 1},
        ["a", "b"],
        {"a": lambda _: True, "b": lambda _: True},
        max_checks=1,
    )
    assert out["pass"] is False
    assert out["reason"] == "CHECK_BUDGET_INSUFFICIENT"


def test_runtime_never_creates_semantic_or_terminal_authority():
    out = evaluate({"x": 1}, ["a"], {"a": lambda _: True}, max_checks=1)
    assert out["semantic_premises_self_certified"] is False
    assert out["semantic_authority_created"] is False
    assert out["terminal_authority"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["terminal_credit_delta"] == 0
