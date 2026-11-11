"""A library's value is not what it contains. It is what can be FOUND in it.

Measured before this file was written, and the reason it exists:

    ten skills, goals phrased in the library's own words        10/10, no model
    the SAME ten tasks, phrased the way a person asks            0/10, no model
    ... with a mechanical router (stems, rarity weights)         3/10, no model
    ... with a model filling only the router's refusals         10/10, 3 of them free

That is the whole shape of the problem, and it is the opposite of the flattering version.
Learning fast is not the bottleneck. FINDING what was learned is, and the faster you learn
the sooner you hit it: r52 already measured that teaching more near-duplicates makes
selection worse.

The tests below hold the numbers and, more importantly, hold the refusals: a router that
guesses silently is worse than one that says it does not know.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import compose_skills_v1 as C
from canonical.runtime import route_with_model_v1 as R

LIB = {n: {"trigger": t, "binding": "present"} for n, t in [
    ("search", "search for <query>"), ("sort", "sort the list"),
    ("rename", "rename the file"), ("delete", "delete the file"),
    ("copy", "copy the text"), ("paste", "paste it"), ("open", "open the report"),
    ("save", "save the work"), ("upload", "upload the photo"), ("email", "send the email")]}

NATURAL = ["find me papers about eigenvalues", "put the list in alphabetical order",
           "give this file a different name", "get rid of the file", "grab that paragraph",
           "show me the report", "don't lose what I did", "put the photo on the server",
           "mail this to the team", "find eigenvalues then alphabetise"]
WANT = ["search", "sort", "rename", "delete", "copy", "open", "save", "upload", "email",
        "search+sort"]
ROUTES = R.load_routes(
    pathlib.Path(__file__).resolve().parents[2]
    / "canonical/evaluation/routing/routes_20261109_v1.json")["routes"]


# ------------------------------------------------------------------ the collapse

def test_literal_triggers_collapse_when_the_user_does_not_speak_library():
    literal = sum(1 for g in NATURAL if C.find_plan(g, LIB)["verdict"] == "PLANNED")
    assert literal == 0, f"{literal}/10 -- the literal planner found something"


def test_a_mechanical_router_recovers_some_but_not_enough():
    routed = sum(1 for g in NATURAL if C.route(g, LIB)["verdict"] == "ROUTED")
    assert routed == 3, f"{routed}/10 by word overlap alone"


def test_a_model_route_file_closes_the_gap():
    ok = 0
    for g, w in zip(NATURAL, WANT):
        r = R.route_goal(g, LIB, ROUTES)
        got = [p["skill"] for p in r.get("plan", {}).get("plan", [])]
        ok += got == w.split("+")
    assert ok == 10, f"{ok}/10 with the model"


def test_the_model_is_only_called_where_the_router_refused():
    """If the model were doing all the work, routing would be as expensive as before --
    and this whole mechanism would be worth nothing."""
    mech = sum(1 for g in NATURAL if C.route(g, LIB)["verdict"] == "ROUTED")
    by_model = sum(1 for g in NATURAL
                   if R.route_goal(g, LIB, ROUTES)["verdict"] == "ROUTED_BY_MODEL")
    assert (mech, by_model) == (3, 7)


# ------------------------------------------------------------------ the refusals

def test_a_router_that_does_not_know_says_so():
    r = C.route("reconcile the ledger", LIB)
    assert r["verdict"] == "NO_ROUTE"
    assert r["unrouted"]


def test_a_genuinely_ambiguous_request_is_not_guessed():
    """Two triggers share only the word 'file', so neither wins on meaning."""
    r = C.route("get rid of the file", LIB)
    assert r["verdict"] == "AMBIGUOUS"
    assert set(r["between"]) == {"rename", "delete"}


def test_a_model_route_cannot_name_a_skill_that_does_not_exist():
    ok, why = R.check_route("g", {"skills": ["teleport"], "because": "x", "confidence": 1.0}, LIB)
    assert not ok and why == "ROUTED_A_SKILL_THAT_DOES_NOT_EXIST__teleport"


def test_a_model_route_cannot_name_a_skill_with_nothing_to_run():
    lib = dict(LIB); lib["paste"] = {"trigger": "paste it", "binding": None}
    ok, why = R.check_route("g", {"skills": ["paste"], "because": "x"}, lib)
    assert not ok and why == "SKILL_HAS_NO_BINDING_TO_RUN__paste"


def test_a_route_that_admits_a_gap_is_refused():
    """Admitting the gap is required; it does not make the route runnable."""
    ok, why = R.check_route("g", {"skills": ["search"], "uncovered": "pay the invoice",
                                  "because": "x"}, LIB)
    assert not ok and "UNCOVERED" in why


def test_an_empty_or_abstaining_route_is_refused():
    assert not R.check_route("g", {"skills": [], "because": "x"}, LIB)[0]
    assert not R.check_route("g", {"abstain": True, "because": "x"}, LIB)[0]


def test_confidence_is_not_a_licence():
    a, _ = R.check_route("g", {"skills": ["teleport"], "because": "x", "confidence": 1.0}, LIB)
    b, _ = R.check_route("g", {"skills": ["teleport"], "because": "x", "confidence": 0.01}, LIB)
    assert a is False and b is False
