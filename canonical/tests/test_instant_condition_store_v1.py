"""Fail-closed tests for the external condition store and pure chooser."""
from __future__ import annotations

import json

import pytest

from canonical.runtime import applicability_v1 as APP
from canonical.runtime import instant_condition_store_v1 as STORE


def test_one_success_stores_program_but_no_condition():
    store = STORE.new_store()
    argv = ("git", "stash", "pop")
    STORE.record_one_success(store, argv, ["stash.present", "worktree.clean"],
                             source={"repo": "source"})
    decision = STORE.choose(store, argv, ["stash.present", "worktree.clean"])
    assert decision["decision"] == STORE.OPEN
    assert decision["status"] == STORE.ONE_SUCCESS
    entry = store["entries"][STORE.action_key(argv)]
    assert entry["required"] == []
    assert entry["program"] == list(argv)
    # "argv" would make the auditability scanner misread stored facts as
    # unverified execution declarations.
    assert "argv" not in entry


def test_contrast_bought_rule_is_applied_by_subset_test():
    store = STORE.new_store()
    argv = ("git", "stash", "pop")
    boundary = APP.learn([
        (["stash.present", "worktree.clean"], True),
        (["stash.present"], True),
        (["stash.absent", "worktree.clean"], False),
    ])
    assert boundary.identified is True
    STORE.upsert_condition(store, argv, boundary, source={"repo": "source"})
    assert STORE.choose(store, argv, ["stash.present", "worktree.clean"])["applies"] is True
    assert STORE.choose(store, argv, ["stash.absent"])["decision"] == STORE.DOES_NOT_APPLY


def test_store_is_external_editable_and_deletable(tmp_path):
    path = tmp_path / "store.json"
    store = STORE.new_store()
    argv = ("git", "stash", "pop")
    STORE.record_one_success(store, argv, ["stash.present"], source={"repo": "source"})
    STORE.save(store, path)
    raw = json.loads(path.read_text())
    assert raw["schema"] == STORE.SCHEMA
    loaded = STORE.load(path)
    assert STORE.choose(loaded, argv, ["stash.present"])["status"] == STORE.ONE_SUCCESS
    raw["entries"][STORE.action_key(argv)]["required"] = ["stash.present"]
    raw["entries"][STORE.action_key(argv)]["condition_status"] = STORE.IDENTIFIED
    path.write_text(json.dumps(raw))
    edited = STORE.load(path)
    assert STORE.choose(edited, argv, ["stash.present"])["applies"] is True
    assert STORE.delete(edited, argv) is True
    STORE.save(edited, path)
    assert STORE.choose(STORE.load(path), argv, ["stash.present"])["decision"] == STORE.OPEN


def test_unknown_action_and_provisional_rule_fail_closed():
    store = STORE.new_store()
    argv = ("git", "rebase", "--abort")
    assert STORE.choose(store, argv, ["rebase.in_progress"])["status"] == STORE.UNKNOWN
    STORE.upsert_rule(store, argv, required=["rebase.in_progress"],
                      condition_status=STORE.PROVISIONAL, source={"repo": "source"})
    assert STORE.choose(store, argv, ["rebase.in_progress"])["applies"] is True
    assert STORE.choose(store, argv, ["rebase.idle"])["applies"] is False


def test_identified_claim_cannot_be_invented():
    store = STORE.new_store()
    boundary = APP.learn([(["stash.present"], True)])
    with pytest.raises(STORE.ConditionStoreError):
        STORE.upsert_condition(store, ("git", "stash", "pop"), boundary,
                               source={}, condition_status=STORE.IDENTIFIED)
