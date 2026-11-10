"""r88 -- the router, and the two ways I got it wrong before it was right.

The instruments existed but nothing decided between them. `task_class_router_v1` does,
and building it exposed two conceptual errors worth keeping:

  1. It tested ADDRESSABILITY before testing whether a literal exists, so it returned
     REFUSE for all 130 MiniWob tasks -- including the eight the executor actually wins.
     A gate that refuses everything is not a decision, it is a stub wearing a verdict.
  2. It collapsed two orthogonal questions into one verdict: "can a reusable skill be
     compiled?" and "how should the agent attempt this now?". Answering the first with
     REFUSE must never imply refusing the second.

And the measurement that came out of fixing it, which is the useful part:

    has_literal              37 tasks  ->  8 won  (22%)
    predicate_referent        7 tasks  ->  0 won  (0%)
    no_literal_no_predicate  86 tasks  ->  0 won  (0%)

A literal in the goal is a near-perfect predictor of where this system can win, and the
other two classes are currently zero -- not because they are impossible, but because
nothing here can name their target.
"""
import pathlib

import pytest

from canonical.runtime.task_class_router_v1 import (
    ATTEMPT_BINDER, ATTEMPT_DEMONSTRATE, ATTEMPT_EXECUTE, ATTEMPT_PIXEL, ATTEMPT_REFUSE,
    EXECUTE_BINDER, EXECUTE_SIMPLE, REFUSE, SKILL_NO, SKILL_YES, route,
)

FORM = "<form><input name=a></form>"
TWO = [{"tag": "INPUT", "id": "a", "vis": True, "text": ""},
       {"tag": "INPUT", "id": "b", "vis": True, "text": ""}]


def test_one_literal_one_field_is_a_simple_execute():
    r = route('Enter "Annis" in the text field and press Submit.', FORM,
              [{"tag": "INPUT", "id": "tt", "vis": True, "text": ""}])
    assert r["decision"] == EXECUTE_SIMPLE and r["attempt"] == ATTEMPT_EXECUTE
    assert r["skill"] == SKILL_YES


def test_several_writes_route_to_the_binder():
    r = route('Enter the password "0xMq" into both text fields', FORM, TWO)
    assert r["decision"] == EXECUTE_BINDER and r["attempt"] == ATTEMPT_BINDER


def test_a_predicate_referent_needs_a_demonstration():
    r = route("Buy the ticket with the shortest duration.", FORM, TWO)
    assert r["attempt"] == ATTEMPT_DEMONSTRATE
    assert r["skill"] == SKILL_NO


def test_skill_compilability_and_attempt_route_are_orthogonal():
    """The bug that refused 114/130: one verdict standing in for two questions."""
    r = route("Click on the numbers in ascending order.", "<div>x</div>", [])
    assert r["skill"] == SKILL_NO              # cannot become a verified skill
    assert r["attempt"] in (ATTEMPT_PIXEL, ATTEMPT_DEMONSTRATE)  # but still attemptable
    assert r["attempt"] != ATTEMPT_REFUSE


def test_the_router_does_not_refuse_everything():
    """The first version returned REFUSE for all 130 tasks."""
    d = pathlib.Path("canonical/evaluation/bench/result_planned_v1.json")
    if not d.exists():
        pytest.skip("no recorded run")
    import json
    miniwob = pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob")
    if not miniwob.exists():
        pytest.skip("MiniWob not present")
    import collections
    c = collections.Counter()
    for t in json.loads(d.read_text())["tasks"]:
        f = miniwob / (t["task"] + ".html")
        r = route(t.get("goal", ""), f.read_text(errors="replace") if f.exists() else "", [])
        c[r["attempt"]] += 1
    assert c[ATTEMPT_REFUSE] < 130, "the router refused everything"
    assert sum(c.values()) == 130
