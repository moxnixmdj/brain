"""r87 -- the binder, and two bugs that made a fix look like a non-fix.

r86 measured that the executor's model of a task was ONE literal into ONE control, that
this covered 32/130 goals, and that all the SOLVED-but-lost tasks were arity>=2, spread
across fields, or transformed. `multi_bind_v1` binds every literal in the goal to a field
from the page's own control list, in order, applying only transforms the goal names.

Measured live: 6 of 8 binder tasks won (75%), against 0 of 6 for the old single binding.

TWO BUGS sat between the module and the benchmark, and both were invisible:

  1. `_RD.__init__` ran but `self.SR` was only assigned inside it, while the first `ask`
     happened before RDC existed. `except Exception: mb_state = []` swallowed it, and an
     empty list is indistinguishable from "this page has no controls". A silent except
     bought one full round.
  2. `centre_of` prefixed '#' unconditionally, so a caller passing "#tt" got "##tt"; an
     invalid selector makes querySelector throw, the read returned None, and the click
     never happened.
"""
import pathlib

import pytest

from canonical.runtime import multi_bind_v1 as MB

TWO = [{"tag": "INPUT", "id": "f1", "vis": True, "text": ""},
       {"tag": "INPUT", "id": "f2", "vis": True, "text": ""}]


def test_one_literal_spread_over_both_fields():
    p = MB.plan_multi_bind('Enter the password "0xMq" into both text fields', TWO)
    assert p["status"] == "SOLVED"
    assert p["writes"] == [("f1", "0xMq"), ("f2", "0xMq")]


def test_two_literals_bind_in_order_one_per_field():
    p = MB.plan_multi_bind('Login with username "dolores" and password "xGta"', TWO)
    assert p["status"] == "SOLVED"
    assert p["writes"] == [("f1", "dolores"), ("f2", "xGta")]


def test_a_named_single_field_is_not_ambiguous_on_a_two_field_page():
    p = MB.plan_multi_bind('Enter "Annis" in the text field and press Submit.', TWO)
    assert p["status"] == "SOLVED"
    assert p["writes"] == [("f1", "Annis")]


def test_a_transform_named_by_the_goal_is_applied():
    """Uses the REAL MiniWob goal text. My first version dropped the "text input" clause,
    so the goal no longer named a field, the module correctly refused as ambiguous, and
    the test failed for a reason that had nothing to do with transforms."""
    p = MB.plan_multi_bind(
        'Type "leonie" in all upper case letters in the text input and press Submit.', TWO)
    assert p["status"] == "SOLVED"
    assert p["writes"] == [("f1", "LEONIE")]
    assert MB.detect_transform('all upper case') == "upper"
    assert MB.apply_transform("leonie", "upper") == "LEONIE"


def test_a_transform_without_a_named_field_is_refused():
    """The honest boundary: a transform does not tell you WHICH field."""
    p = MB.plan_multi_bind('Type "leonie" in all upper case letters', TWO)
    assert p["status"] == "AMBIGUOUS" and p["writes"] == []


def test_ambiguity_is_refused_not_guessed():
    """One literal, two fields, no spread wording, no named field -> refuse."""
    p = MB.plan_multi_bind('Enter "x" somewhere', TWO)
    assert p["status"] == "AMBIGUOUS"
    assert p["writes"] == []


def test_centre_of_tolerates_a_leading_hash():
    """'##tt' is an invalid selector; the read returned None and the click never ran."""
    src = pathlib.Path("canonical/runtime/state_read_v1.py").read_text()
    assert 'element_id if element_id.startswith("#") else "#" + element_id' in src


def test_a_read_failure_is_recorded_not_swallowed():
    runner = pathlib.Path("canonical/evaluation/bench/run_planned_v1.py").read_text()
    assert 'r["read_error"]' in runner
    assert "mb_state = RD.ask(None" in runner
