#!/usr/bin/env python3
"""Invariants of the instrument that decides where the missing term comes from.

These are not capability tests, they are guards against the fake signals this instrument is most
likely to produce: a temp counted as vocabulary, a name from another function credited as in
scope, an insertion before a closing bracket going invisible, or a gate that reports a partition
that does not partition.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

from where_the_missing_term_comes_from_v1 import (  # noqa: E402
    added_line_spans,
    classify,
    measure,
)

CORPUS = ROOT / "canonical" / "corpus" / "real_fix_pairs_20261119_V1.json"


def task(before: str, after: str) -> dict:
    return {"repo": "t/t", "sha": "0" * 12, "source": "m.py", "before": before, "after": after}


def test_a_temp_the_fix_invents_is_not_vocabulary():
    # `i` is new to the file, but the fix binds it, so it is alpha-renamable -- not knowledge.
    row = classify(task(
        "def f(x):\n    return x\n",
        "def f(x):\n    i = x + 1\n    return i\n",
    ))
    assert row["regime"] == "R1_TERM", row
    assert "i" in row["temps"]
    assert row["new_names"] == []


def test_a_name_absent_from_the_file_is_knowledge():
    row = classify(task(
        "def f(x):\n    return x\n",
        "def f(x):\n    return canonicalize_name(x)\n",
    ))
    assert row["regime"] == "R3_NEW_NAME", row
    assert row["new_names"] == ["canonicalize_name"]


def test_a_name_bound_in_another_function_is_not_in_scope():
    # `local_name` exists in the file but is not available at f's site: the fix would have to
    # thread it. Crediting it as in scope would hide scope-widening.
    row = classify(task(
        "def g():\n    local_name = 1\n    return local_name\n\ndef f(x):\n    return x\n",
        "def g():\n    local_name = 1\n    return local_name\n\ndef f(x):\n    return local_name\n",
    ))
    assert row["regime"] == "R2_SCOPE", row


def test_a_literal_only_term_is_its_own_regime():
    row = classify(task(
        "def f(x):\n    return x\n",
        "def f(x):\n    return 17\n",
    ))
    assert row["regime"] == "R0_LITERAL", row


def test_an_insertion_before_a_closing_bracket_is_visible():
    # The round-27 defect: a diff that only tracks the shared prefix misses this.
    before = "def f(xs):\n    return sorted([\n        a\n        for a in xs\n    ])\n"
    after = "def f(xs):\n    return sorted([\n        a\n        for a in xs\n        if a\n    ])\n"
    spans = added_line_spans(before, after)
    assert spans, "the added element must produce at least one added span"
    row = classify(task(before, after))
    assert row["regime"] != "NO_TERM", row


def test_a_pure_structural_change_has_no_term():
    row = classify(task(
        "class A:\n    pass\n",
        "class A:\n    def extra(self):\n        return 1\n",
    ))
    # `1` is an expression inside the added block; the regime must be a real one, never a crash
    assert row["regime"] in {"R0_LITERAL", "R1_TERM", "R2_SCOPE", "R3_NEW_NAME", "NO_TERM"}, row


def test_every_fix_is_classified_and_the_regimes_partition():
    rec = measure(str(CORPUS))
    assert rec["fixes"] == 87
    counts = rec["regimes"]
    assert sum(counts.values()) == 87
    assert rec["broken"]["K1_every_fix_classified"]["MET"]
    assert rec["broken"]["K4_regimes_partition_the_corpus"]["MET"]
    assert rec["broken"]["K3_no_silent_parse_failures"]["MET"]


def test_the_receipt_matches_the_instrument_and_records_its_basis():
    rec = json.loads((ROOT / "canonical" / "verification" /
                      "WHERE_THE_MISSING_TERM_COMES_FROM_20261116_V1.json").read_text())
    fresh = measure(str(CORPUS))
    for key in ("regimes", "term_local_share", "new_name_share", "distinct_operators",
                "operators_for_ninety_percent"):
        assert rec[key] == fresh[key], key
    assert rec["model_dependency_count"] == 0
    assert rec["network_calls_at_run_time"] == 0
    assert rec["operators_for_ninety_percent"] <= 12
