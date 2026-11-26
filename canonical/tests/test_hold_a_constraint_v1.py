#!/usr/bin/env python3
"""Tests for holding a constraint across many steps.

Every test pins a bug this build hit against real apps in a real browser. None
needs a browser: the parts that were wrong are the clause reader and the scorer,
and both are pure functions of what the interface declared.
"""
from __future__ import annotations

import importlib

H = importlib.import_module("canonical.runtime.hold_a_constraint_v1")


def _row(text: str, checked: bool = False) -> dict:
    return {"text": text, "role": "li",
            "control": {"role": "checkbox", "checked": checked, "name": ""}, "index": 0}


# --- the postcondition is clauses, not a string ---------------------------- #
def test_a_goal_is_a_clause_per_item_with_its_own_polarity() -> None:
    """"mark beta complete but leave alpha and gamma uncompleted" is ONE positive
    and TWO negatives. A string goal cannot express that, which is why the two-action
    loop ranked "Toggle All Input" first and would have completed all three."""
    post = H.read_postcondition(
        "mark beta complete but leave alpha and gamma uncompleted",
        ["alpha", "beta", "gamma"])
    got = {c["item"]: (c["polarity"], c["wanted"]) for c in post["clauses"]}
    assert got["beta"] == ("positive", "complete"), got
    assert got["alpha"] == ("negative", "incomplete"), got
    assert got["gamma"] == ("negative", "incomplete"), got
    assert post["has_negative"] is True


def test_leave_is_a_scope_and_not_an_adjacent_word() -> None:
    """Pinned bug: "uncompleted" sits after gamma only, so an adjacency rule called
    alpha a mere invariant -- a WEAKER clause -- and the loop checked alpha twelve
    times in a row, changing a state the task said to leave alone."""
    post = H.read_postcondition("leave alpha and gamma uncompleted", ["alpha", "gamma"])
    assert all(c["polarity"] == "negative" for c in post["clauses"]), post["clauses"]


def test_a_completion_verb_attached_to_one_item_beats_the_leave_scope() -> None:
    post = H.read_postcondition(
        "leave alpha alone but mark beta complete", ["alpha", "beta"])
    got = {c["item"]: c["polarity"] for c in post["clauses"]}
    assert got["beta"] == "positive", got
    assert got["alpha"] == "negative", got


def test_an_item_the_task_does_not_name_gets_no_clause() -> None:
    post = H.read_postcondition("mark beta complete", ["alpha", "beta", "gamma"])
    assert [c["item"] for c in post["clauses"]] == ["beta"]


# --- reading the state ----------------------------------------------------- #
def test_a_row_is_matched_by_the_word_it_publishes() -> None:
    """Pinned bug: one implementation reports the row as "Toggle Todo beta" because
    the row contains its own control's aria-label. An equality test found no clause,
    so the row scored 0.0 and the planner fell through to a global control."""
    post = H.read_postcondition("mark beta complete", ["beta"])
    state = H.observe_clauses([_row("Toggle Todo beta")], post)
    assert state["beta"] is False          # declared, and not complete


def test_a_substring_is_not_a_word() -> None:
    """"alpha" must not match "alphabet", or a clause fires on an unrelated row."""
    post = H.read_postcondition("mark alpha complete", ["alpha"])
    state = H.observe_clauses([_row("alphabet soup"), _row("alpha")], post)
    assert state["alpha"] is False


def test_an_item_the_interface_does_not_declare_is_reported_not_assumed() -> None:
    post = H.read_postcondition("mark beta complete", ["beta"])
    assert H.observe_clauses([_row("alpha")], post)["beta"] is None
    ok, missing = H.satisfied({"beta": None}, post)
    assert ok is False and "not declared" in missing[0]


# --- choosing the action --------------------------------------------------- #
def _controls():
    return [
        {"role": "textbox", "name": "What needs to be done?", "row_text": None},
        {"role": "checkbox", "name": "Mark all as complete", "row_text": None},
        {"role": "checkbox", "name": "Toggle Todo", "row_text": "Toggle Todo alpha"},
        {"role": "checkbox", "name": "Toggle Todo", "row_text": "Toggle Todo beta"},
        {"role": "checkbox", "name": "Toggle Todo", "row_text": "Toggle Todo gamma"},
    ]


def test_the_global_toggle_is_never_chosen_when_a_constraint_is_protected() -> None:
    """The measured fatal action. On every one of 11 apps the blind loop's global
    toggle satisfied nothing: it either completed the protected rows or none. The
    planner must score it below the row control it would destroy."""
    post = H.read_postcondition(
        "mark beta complete but leave alpha and gamma uncompleted",
        ["alpha", "beta", "gamma"])
    rows = [_row("alpha"), _row("beta"), _row("gamma")]
    state = H.observe_clauses(rows, post)
    plan = H.plan_step(_controls(), rows, post, state)
    assert plan["best"]["scope"] == "row", plan["best"]
    assert "beta" in (plan["best"]["control"]["row_text"] or "")
    glob = [r for r in plan["ranking"]
            if r["control"]["name"] == "Mark all as complete"]
    assert glob and glob[0]["score"] < 0, glob


def test_a_clause_that_already_holds_is_not_acted_on() -> None:
    """Pinned bug: every named row scored 6.0, so the loop checked alpha -- the item
    the task protected -- over and over instead of reaching the open clause."""
    post = H.read_postcondition(
        "mark beta complete but leave alpha and gamma uncompleted",
        ["alpha", "beta", "gamma"])
    rows = [_row("alpha"), _row("beta"), _row("gamma")]     # all incomplete
    state = H.observe_clauses(rows, post)
    plan = H.plan_step(_controls(), rows, post, state)
    alpha = [r for r in plan["ranking"]
             if "alpha" in (r["control"]["row_text"] or "")]
    # alpha's clause already holds, so acting on it can only break it
    assert alpha and alpha[0]["score"] < 0, alpha


def test_the_open_positive_clause_outranks_a_closed_negative() -> None:
    post = H.read_postcondition(
        "mark beta complete but leave alpha and gamma uncompleted",
        ["alpha", "beta", "gamma"])
    rows = [_row("alpha"), _row("beta"), _row("gamma")]
    state = H.observe_clauses(rows, post)
    plan = H.plan_step(_controls(), rows, post, state)
    assert plan["best"]["score"] > 0
    assert "beta" in plan["best"]["control"]["row_text"]


# --- the constraint must be re-checked, not assumed ------------------------ #
def test_an_invariant_that_moves_is_reported_with_its_name() -> None:
    baseline = {"alpha": ("baseline", False), "gamma": ("baseline", False)}
    now = {"alpha": ("baseline", True), "gamma": ("baseline", False)}
    assert H.violations_vs_baseline(baseline, now) == ["alpha"]


def test_a_satisfied_postcondition_reports_no_missing_clause() -> None:
    post = H.read_postcondition(
        "mark beta complete but leave alpha and gamma uncompleted",
        ["alpha", "beta", "gamma"])
    rows = [_row("alpha", False), _row("beta", True), _row("gamma", False)]
    state = H.observe_clauses(rows, post)
    ok, missing = H.satisfied(state, post)
    assert ok is True and missing == []


def test_a_violated_negative_names_the_clause_it_broke() -> None:
    post = H.read_postcondition(
        "mark beta complete but leave alpha and gamma uncompleted",
        ["alpha", "beta", "gamma"])
    rows = [_row("alpha", True), _row("beta", True), _row("gamma", False)]
    ok, missing = H.satisfied(H.observe_clauses(rows, post), post)
    assert ok is False
    assert any("alpha" in m and "negative" in m for m in missing), missing
