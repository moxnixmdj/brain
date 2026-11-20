"""Fail-closed tests for targeted refutation of PROVISIONAL rules."""
from __future__ import annotations

from canonical.runtime import instant_condition_store_v1 as STORE
from canonical.runtime import provisional_repair_v1 as REPAIR


def _store(required, status=STORE.PROVISIONAL, support=None):
    store = STORE.new_store()
    argv = ("git", "stash", "pop")
    STORE.upsert_rule(store, argv, required=required, condition_status=status,
                      source={"survivor_count": 512})
    if support is not None:
        REPAIR.attach_support(store, argv, support, source={"repo": "source"})
    return store, argv


def test_no_support_quarantines_instead_of_guessing():
    store, argv = _store(["a"])
    result = REPAIR.repair(store, argv, ["a"], False)
    assert result["repair"] == REPAIR.QUARANTINED
    assert STORE.choose(store, argv, ["a"])["decision"] == STORE.OPEN
    assert REPAIR.report(store, argv)["confidence"] == "NONE"


def test_over_application_narrows_by_smallest_computed_fact():
    store, argv = _store(["a"], support=["a", "b", "c"])
    result = REPAIR.repair(store, argv, ["a"], False)
    assert result["repair"] == REPAIR.NARROWED
    assert result["required_before"] == ["a"]
    assert "a" in result["required"]
    assert result["added_fact"] in {"b", "c"}
    assert set(result["required"]) == {"a", result["added_fact"]}
    assert STORE.choose(store, argv, ["a"])["applies"] is False
    assert STORE.choose(store, argv, ["a", "b", "c"])["applies"] is True
    assert REPAIR.report(store, argv)["confidence"] == "PROVISIONAL"


def test_narrowing_preserves_existing_required_fact():
    """One refutation cannot licence deleting a fact the old rule required."""
    store, argv = _store(["stash.present"], support=["stash.present", "worktree.clean"])
    result = REPAIR.repair(store, argv, ["stash.present", "worktree.dirty"], False)
    assert result["repair"] == REPAIR.NARROWED
    assert result["required"] == ["stash.present", "worktree.clean"]
    assert STORE.choose(store, argv, ["worktree.clean"])["applies"] is False


def test_under_application_weakens_by_one_absent_required_fact():
    store, argv = _store(["a", "b"], support=["a", "b"])
    result = REPAIR.repair(store, argv, ["b"], True)
    assert result["repair"] == REPAIR.WEAKENED
    assert result["required"] == ["b"]
    assert STORE.choose(store, argv, ["b"])["applies"] is True


def test_matching_outcome_leaves_rule_untouched():
    store, argv = _store(["a"], support=["a", "b"])
    before = STORE.digest(store)
    result = REPAIR.repair(store, argv, ["a"], True)
    assert result["status"] == REPAIR.UNCHANGED
    assert STORE.digest(store) == before


def test_unknown_action_and_non_rule_status_fail_closed():
    store = STORE.new_store()
    argv = ("git", "stash", "pop")
    assert REPAIR.repair(store, argv, ["a"], True)["status"] == REPAIR.NO_RULE
    STORE.upsert_rule(store, argv, required=[], condition_status=STORE.ONE_SUCCESS,
                      source={})
    assert REPAIR.repair(store, argv, ["a"], True)["status"] == REPAIR.NO_RULE
