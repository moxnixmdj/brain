#!/usr/bin/env python3
"""Tests for name-addressed interface control.

Every test here pins a bug that this build actually hit against a real Chromium
driving real apps. None of them needs a browser: they exercise the parts that
were wrong, with the snapshot shapes the driver really produced.
"""
from __future__ import annotations

import importlib
from typing import Any

M = importlib.import_module("canonical.runtime.interface_is_its_own_declaration_v1")


def _snap(elements: list[dict[str, Any]], *, url="http://x/", title="t") -> dict:
    return {"pages": [{"url": url, "title": title, "elements": elements}]}


# --- the name is a list, not a string ------------------------------------- #
def test_a_control_is_addressed_by_every_name_the_interface_publishes() -> None:
    """Pinned bug: preferring one name absolutely broke 8 of 11 real apps.

    Measured across three implementations of the same interface, the accessibility
    name and the placeholder disagree and either may be absent:

        backbone      name: (none)                placeholder: "What needs to be done?"
        react-redux   name: "New todo"            placeholder: "What needs to be done?"
        web-components name: "Enter a new todo."   placeholder: "What needs to be done?"

    Choosing aria_name first emptied backbone's address and cost 8 apps; choosing
    placeholder first broke the 3 that carry a real label. The address must be all
    of them, in the order the interface publishes them.
    """
    snap = _snap([{"i": 0, "tag": "input", "placeholder": "What needs to be done?",
                   "aria_name": "Enter a new todo."}])
    ctl = M.declared_names(snap)[0]
    assert ctl["names"] == ["Enter a new todo.", "What needs to be done?"], ctl["names"]
    assert ctl["name"] == "Enter a new todo."

    # a control with no label at all still has an address: its placeholder
    snap2 = _snap([{"i": 0, "tag": "input", "placeholder": "What needs to be done?",
                    "aria_name": ""}])
    assert M.declared_names(snap2)[0]["names"] == ["What needs to be done?"]


def test_an_unlabelled_unplaced_control_is_reported_not_invented() -> None:
    snap = _snap([{"i": 0, "tag": "input", "aria_name": "", "placeholder": "", "text": ""}])
    ctl = M.declared_names(snap)[0]
    assert ctl["name"] == ""
    assert ctl["names"] == []
    # and it must not be rankable, so the loop cannot act on a nameless thing
    assert M.rank_actions([ctl], goal=["x"]) == []


def test_the_name_list_deduplicates_without_reordering() -> None:
    snap = _snap([{"i": 0, "tag": "input", "aria_name": "Same",
                   "placeholder": "same", "text": "Other"}])
    assert M.declared_names(snap)[0]["names"] == ["Same", "Other"]


# --- the goal is a statement about the environment ------------------------ #
def test_the_goal_is_satisfied_only_by_the_interface_declaring_it() -> None:
    obs = {"url": "http://x/#/active", "text": "buy milk 1 item left", "values": {}, "title": "t"}
    assert M.goal_holds(obs, ["buy milk"])["holds"] is True
    assert M.goal_holds(obs, ["1 item left"])["holds"] is True
    miss = M.goal_holds(obs, ["buy bread"])
    assert miss["holds"] is False and miss["missing"] == ["buy bread"]


def test_a_goal_naming_the_url_is_checked_against_the_url() -> None:
    """The postcondition after filtering is routing, not text: 11 of 11 apps moved
    to #/completed, and no text on the page changed."""
    obs = {"url": "http://x/#/completed", "text": "", "values": {}, "title": "t"}
    assert M.goal_holds(obs, ["#/completed"])["holds"] is True


def test_a_typed_value_counts_as_the_interface_declaring_it() -> None:
    """A filled textbox holds the value in `value`, not in its text node."""
    obs = {"url": "", "text": "", "values": {"What needs to be done?": "buy milk"}, "title": ""}
    assert M.goal_holds(obs, ["buy milk"])["holds"] is True


# --- ranking is a computation over the declaration ------------------------ #
def test_a_destructive_control_is_ranked_below_everything_useful() -> None:
    ctl = M.declared_names(_snap([
        {"i": 0, "tag": "button", "text": "Clear completed"},
        {"i": 1, "tag": "input", "placeholder": "What needs to be done?"},
    ]))
    ranked = M.rank_actions(ctl, goal=["buy milk"], want_typed="buy milk")
    assert ranked[0]["control"]["name"] == "What needs to be done?"
    assert ranked[-1]["control"]["name"] == "Clear completed"
    assert ranked[-1]["score"] < 0


def test_a_control_the_goal_already_names_ranks_first() -> None:
    ctl = M.declared_names(_snap([
        {"i": 0, "tag": "input", "placeholder": "What needs to be done?"},
        {"i": 1, "tag": "a", "text": "Completed"},
    ]))
    ranked = M.rank_actions(ctl, goal=["Completed"])
    assert ranked[0]["control"]["name"] == "Completed"


def test_a_type_role_with_nothing_to_type_is_not_ranked_first() -> None:
    """A textbox is only useful when the goal supplies text for it. Otherwise it
    burns a step proving the obvious, which is what happened on app 11."""
    ctl = M.declared_names(_snap([{"i": 0, "tag": "input", "placeholder": "Box"}]))
    ranked = M.rank_actions(ctl, goal=["x"], want_typed=None)
    assert ranked[0]["score"] < 6.0


def test_a_control_proved_unhelpful_twice_is_vetoed_by_memory() -> None:
    ctl = M.declared_names(_snap([{"i": 0, "tag": "button", "text": "Add"}]))
    plain = M.rank_actions(ctl, goal=["x"])[0]["score"]
    vetoed = M.rank_actions(ctl, goal=["x"],
                            memory={"controls": {"button|Add": {"helped": False}}})[0]["score"]
    assert vetoed < plain - 10


def test_one_silent_run_does_not_condemn_a_control() -> None:
    """A render delay is not a refusal. The recorder needs two samples, because an
    earlier instrument in this project talked itself out of working names."""
    mem: dict = {"controls": {}}
    M._remember(mem, "button|Add", False)
    assert mem["controls"]["button|Add"]["helped"] is None
    M._remember(mem, "button|Add", False)
    assert mem["controls"]["button|Add"]["helped"] is False
    M._remember(mem, "button|Add", True)
    assert mem["controls"]["button|Add"]["helped"] is True


# --- the generalisation is computed, not hoped for ------------------------ #
def test_the_invariant_is_what_every_interface_says_not_the_commonest() -> None:
    rows = [{"roles": ["link", "textbox"]},
            {"roles": ["link", "textbox", "checkbox"]},
            {"roles": ["link", "textbox", "button"]}]
    inv = M.declarative_invariant(rows)
    assert inv["roles"] == ["link", "textbox"], inv["roles"]
    # checkbox and button are each true of one app, so neither is in the invariant
    assert "checkbox" not in inv["roles"] and "button" not in inv["roles"]


def test_the_memory_decision_names_what_it_keeps_and_what_it_refuses() -> None:
    d = M.what_to_remember({"roles": ["link", "textbox"]}, per_app_names_are_unique=True)
    assert "declarative_invariant" in d["keep"] and "refusals" in d["keep"]
    for never in ("names", "coordinates", "step_sequence", "pixels"):
        assert never in d["never"], never
    assert d["per_app_names_are_unique"] is True


# --- the loop is one organ, and it reports rather than guesses ------------ #
class _FakeDriver:
    """A driver that answers from a script, so the loop is testable without a browser."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self.pages = pages
        self.index = -1
        self.ops: list[dict[str, Any]] = []

    def act(self, op):
        self.ops.append(op)
        if op["type"] == "NAVIGATE":
            self.index = 0
            return {"status": "PASS"}
        if op["type"] == "FILL_NAME":
            # the app now declares the typed value
            self.index = min(self.index + 1, len(self.pages) - 1)
            return {"status": "PASS"}
        self.index = min(self.index + 1, len(self.pages) - 1)
        return {"status": "PASS"}

    def bind(self):
        outer = self

        class _B:
            def snapshot(self_inner):
                return outer.pages[max(outer.index, 0)]
        return _B()


def test_the_loop_stops_the_moment_the_interface_declares_the_goal() -> None:
    empty = _snap([{"i": 0, "tag": "input", "placeholder": "What needs to be done?"}],
                  url="http://x/")
    typed = _snap([{"i": 0, "tag": "input", "placeholder": "What needs to be done?",
                    "value": "buy milk"}], url="http://x/")
    d = _FakeDriver([empty, typed, typed])
    r = M.run_goal("http://x/", ["buy milk"], want_typed="buy milk", driver=d)
    assert r["status"] == "GOAL_DECLARED", r
    assert len(r["steps"]) == 1
    assert r["model_calls"] == 0 and r["network_calls"] == 0


def test_a_goal_the_interface_never_declares_is_reported_not_retried_forever() -> None:
    empty = _snap([{"i": 0, "tag": "a", "text": "nowhere"}], url="http://x/")
    d = _FakeDriver([empty] * 20)
    r = M.run_goal("http://x/", ["impossible string"], driver=d, max_steps=3)
    assert r["status"] in ("NOT_REACHED", "REFUSE__NO_ADDRESSABLE_CONTROL"), r["status"]
    assert len(r["steps"]) <= 3


def test_a_navigation_that_fails_is_a_refusal_not_an_attempt() -> None:
    class _Dead:
        def act(self, op):
            return {"status": "REFUSED"}

        def bind(self):
            raise AssertionError("must not read a page that never loaded")

    r = M.run_goal("http://x/", ["anything"], driver=_Dead())
    assert r["status"] == "REFUSE__NAVIGATE_FAILED"


def test_an_already_satisfied_goal_cost_zero_actions() -> None:
    ready = _snap([{"i": 0, "tag": "a", "text": "buy milk"}], url="http://x/")
    d = _FakeDriver([ready])
    r = M.run_goal("http://x/", ["buy milk"], driver=d)
    assert r["status"] == "ALREADY_SATISFIED"
    assert r["steps"] == []
