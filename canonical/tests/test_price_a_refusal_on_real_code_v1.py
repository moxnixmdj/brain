#!/usr/bin/env python3
"""The dial cannot be fixed externally: real code refuses almost everything and the price barely matters.

Corpus: 1,200 files of this repo, 7,282 functions to train on, 3,538 held out split by FILE (no held-out
function shares a file with a trained one). Every subset of the 9 candidate features, sizes 1-6.

    price   cost  pred  wrong  refused   accuracy  coverage   winning subset
        1   3282   268     12     3270     0.9571    0.0757   6 features
       10   3354   224      4     3314     0.9825    0.0633   6
       50   3472   116      1     3422     0.9915    0.0328   5
      100   3477    61      0     3477     1.0000    0.0172   4

The headline is not which subset wins. It is that **a 100x sweep in the price of an error changes the total
cost by 5.9%**, because at most 268 of 3,538 functions are ever predicted at all. Accuracy and coverage
trade strictly (0.957 -> 1.000 while 0.076 -> 0.017): the dial is real, but it sits inside a 7% coverage
band and the cost model has almost nothing to choose between.

So the hope from last round -- that a real corpus would fix the setting of the dial from outside -- is
refuted. On real code the vocabulary covers under 8% of what it is pointed at, and no price rescues that.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import price_a_refusal_on_real_code_v1 as price  # noqa: E402

ARTIFACT = (REPO / "canonical" / "verification" /
            "PRICE_A_REFUSAL_ON_REAL_CODE_20261124_V1.json")


def test_features_carry_no_names_or_literals():
    """The discipline the lifted vocabulary follows, applied to real code: a feature may describe shape
    and never content, or the corpus would be reported not modelled."""
    import ast
    node = ast.parse("def f(a):\n if a:\n  return secret_name\n return None\n").body[0]
    feats = price.features_of(node)
    joined = " ".join(feats)
    assert "secret_name" not in joined and "return" not in joined
    assert all(f.split("_")[0] in {"LINES", "BODY", "DEPTH", "HAS"} for f in feats)


def test_return_shape_does_not_descend_into_inner_functions():
    """A nested def's returns are its own; counting them would mislabel the outer shape."""
    import ast
    node = ast.parse("def f():\n def g():\n  return 1\n return\n").body[0]
    with_value, without = price.returns_of(node)
    assert (with_value, without) == (0, 1)
    assert price.shape_of(with_value, without) == "NO_RETURN"


def test_the_cost_spread_is_small_across_a_100x_price_sweep():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["verdicts"]["the_cost_spread_across_a_100x_price_sweep_is_under_10_percent"] is True
    costs = [summary["by_price"][k]["cost"] for k in
             ("1", "2", "5", "10", "20", "50", "100")]
    assert max(costs) / min(costs) < 1.10


def test_the_corpus_resists_and_that_is_the_finding():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["verdicts"]["the_corpus_resists_rather_than_informing"] is True
    assert summary["by_price"]["100"]["coverage"] < 0.02
    assert summary["by_price"]["1"]["coverage"] < 0.10


def test_accuracy_and_coverage_trade_strictly():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["verdicts"]["accuracy_and_coverage_trade_strictly"] is True
    assert summary["by_price"]["100"]["accuracy"] > summary["by_price"]["1"]["accuracy"]
    assert summary["by_price"]["100"]["coverage"] < summary["by_price"]["1"]["coverage"]
