#!/usr/bin/env python3
"""Provenance of branch tests roughly doubles coverage on real code -- and the first version of this file
was a leak that made it look solved.

WITH THE LEAK (features computed from Return nodes, target class defined by Return nodes):

    SHAPE_ONLY      174 pred, 0 wrong, coverage 0.047
    PROVENANCE_ONLY 365 pred, 0 wrong, coverage 0.099
    BOTH            692 pred, 0 wrong, coverage 0.188   <- "solved", and meaningless
    best at price 1: 3621 pred, 4 wrong, coverage 0.984

`RET_ORIGINS_COUNT_0` IS "no return carries a value". The label was handed to the predictor: the V14 defect,
committed again four rounds later, by me.

WITHOUT IT (branch-test provenance only), 7,812 trained / 3,679 held out, equal vocabulary budget:

    SHAPE_ONLY      211 pred,  4 wrong, accuracy 0.9814, coverage 0.0574
    PROVENANCE_ONLY  20 pred,  3 wrong, accuracy 0.8696, coverage 0.0054   <- near-useless alone
    BOTH            395 pred, 22 wrong, accuracy 0.9472, coverage 0.1074   <- doubles coverage

The union wins at every price (1, 10, 100) under the cost objective, and its extra coverage is bought with
18 more errors -- which is exactly what the dial says should happen.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import provenance_not_shape_v1 as prov  # noqa: E402

ARTIFACT = REPO / "canonical" / "verification" / "PROVENANCE_NOT_SHAPE_20261124_V1.json"


def test_no_provenance_feature_is_computed_from_a_return_node():
    """The anti-leak assertion. A function whose ONLY distinguishing feature is its return value must look
    identical to a function with no return, in the provenance feature set."""
    with_return = ast.parse("def f(a):\n if a:\n  return a\n").body[0]
    no_return = ast.parse("def f(a):\n if a:\n  pass\n").body[0]
    assert prov.provenance_features(with_return) == prov.provenance_features(no_return)
    # and nothing in the vocabulary is named after returns
    assert all("RET" not in name for name in prov.PROVENANCE_FEATURES)


def test_branch_provenance_is_still_computed():
    """Removing the leak must not have removed the mechanism: a branch on a call and a branch on an
    attribute must differ."""
    on_call = ast.parse("def f():\n if g():\n  return 1\n").body[0]
    on_attr = ast.parse("def f(o):\n if o.flag:\n  return 1\n").body[0]
    call_features = prov.provenance_features(on_call)
    attr_features = prov.provenance_features(on_attr)
    assert "BRANCH_ON_CALL" in call_features
    assert "BRANCH_ON_ATTRIBUTE" in attr_features
    assert call_features != attr_features


def test_the_union_doubles_coverage_over_shape_alone():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    arms = json.loads(ARTIFACT.read_text())["summary"]["arms"]
    assert arms["BOTH"]["coverage"] > 1.7 * arms["SHAPE_ONLY"]["coverage"]
    # and the honesty half: it costs accuracy
    assert arms["BOTH"]["accuracy"] < arms["SHAPE_ONLY"]["accuracy"]


def test_provenance_alone_is_not_a_win():
    """The pre-registered claim was that provenance is the answer. Alone, it is the worst arm."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    arms = summary["arms"]
    assert arms["PROVENANCE_ONLY"]["coverage"] < arms["SHAPE_ONLY"]["coverage"]
    assert summary["verdicts"]["provenance_beats_shape_at_equal_budget"] is False
    assert summary["verdicts"]["provenance_lifts_coverage_out_of_single_digits"] is False


def test_the_arms_are_selected_by_the_same_objective_as_the_price_table():
    """A second defect caught while fixing the first: `sweep` minimised errors while the price table
    minimised cost, so the two tables could disagree while both claiming equal budget."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    # the two tables must agree on the same objective: at price 1, cost == wrong + refused exactly, and
    # the price-1 winner must be the same arm the arms table selects
    price_one = summary["by_price"]["1"]
    assert price_one["cost"] == price_one["wrong"] + price_one["refused"]
    assert price_one["arm"] in summary["arms"]
    assert price_one["predictions"] == summary["arms"][price_one["arm"]]["predictions"], (
        "the price table and the arms table must be selecting the same subset")
    for price, cell in summary["by_price"].items():
        assert cell["cost"] >= cell["wrong"] * int(price) + cell["refused"]
