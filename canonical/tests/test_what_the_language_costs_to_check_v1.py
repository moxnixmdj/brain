#!/usr/bin/env python3
"""Guards for the instrument that prices the term language at the site.

The failure modes these exist to catch are the ones that would turn a hard number into a soft one:
a size formula that only bounds instead of equalling, a decoy that cannot be parsed (a broken probe
posing as a candidate), a pruner that rejects the real fix (a bug posing as pruning), and a cost
that is assumed rather than timed.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

from what_the_language_costs_to_check_v1 import (  # noqa: E402
    decoy_probe,
    language_size,
    measure,
    read_basis,
    self_check,
)

CORPUS = str(ROOT / "canonical" / "corpus" / "real_fix_pairs_20261119_V1.json")
PRIOR = str(ROOT / "canonical" / "verification" / "WHERE_THE_MISSING_TERM_COMES_FROM_20261116_V1.json")
RECEIPT = ROOT / "canonical" / "verification" / "WHAT_THE_LANGUAGE_COSTS_TO_CHECK_20261116_V1.json"


def test_the_closed_form_equals_enumeration_by_level():
    basis = [{"operator": "Not", "arity": 1, "cls": ast.Not},
             {"operator": "Eq", "arity": 2, "cls": ast.Eq}]
    atoms = 2
    # exact by hand: level0=2, level1 = Not(2) + Eq(2*2) = 6, level2 = Not(6) + Eq(36) = 42
    assert language_size(atoms, basis, 1) == 2 + 6
    assert language_size(atoms, basis, 2) == 2 + 6 + 42
    assert self_check(basis)


def test_the_basis_is_read_from_the_census_not_written_here():
    basis = read_basis(PRIOR)
    assert 9 <= len(basis) <= 12
    for b in basis:
        assert b["arity"] in (1, 2)
        assert issubclass(b["cls"], (ast.operator, ast.cmpop, ast.boolop, ast.unaryop))


def test_a_decoy_is_never_unparsable():
    # a BoolOp swapped for a comparison would build an AST that cannot be unparsed: a broken probe
    before = "def f(a, b):\n    return a\n"
    after = "def f(a, b):\n    return a and b\n"
    post = ast.parse(after)
    from where_the_missing_term_comes_from_v1 import added_line_spans, terms_of
    spans = added_line_spans(before, after)
    term = terms_of(post, spans)[0]
    probe = decoy_probe(before, after, spans, term, read_basis(PRIOR))
    assert probe["hard_decoys"] >= 0  # generation must not raise on a BoolOp term
    assert probe["pruner_rejects_the_true_term"] is False


def test_a_pruner_that_rejects_the_true_term_is_never_shipped():
    rec = json.loads(RECEIPT.read_text())
    assert rec["free_pruners_reject_the_true_term"] == 0
    assert rec["broken"]["K3_no_free_pruner_rejects_the_true_term"]["MET"]


def test_arity_pruning_is_real_on_a_mismatched_decoy():
    before = "def helper(a, b):\n    return a\n\ndef f(x):\n    return x\n"
    after = "def helper(a, b):\n    return a\n\ndef f(x):\n    return helper(x)\n"
    post = ast.parse(after)
    from where_the_missing_term_comes_from_v1 import added_line_spans, terms_of
    spans = added_line_spans(before, after)
    term = terms_of(post, spans)[0]
    probe = decoy_probe(before, after, spans, term, read_basis(PRIOR))
    # the true term calls helper with one argument where it takes two: this is exactly what a naive
    # arity pruner rejects, and the gate exists to catch that class of unsoundness
    assert probe["pruner_rejects_the_true_term"] is True


def test_cost_is_timed_and_the_language_is_large():
    rec = json.loads(RECEIPT.read_text())
    assert rec["timed_checks_total"] >= 100_000
    assert 0 < rec["measurable_microseconds_per_check"] < 1000
    assert rec["median_language_size"] > 10**6
    assert rec["median_depth"] >= 2


def test_the_receipt_matches_a_fresh_run():
    rec = json.loads(RECEIPT.read_text())
    fresh = measure(CORPUS, PRIOR)
    for key in ("fixes_with_a_term", "median_depth", "basis", "hard_decoys",
                "hard_decoys_rejected_by_free_pruners", "malformed_decoys",
                "free_pruners_reject_the_true_term", "fixes_checkable_under_one_minute"):
        assert rec[key] == fresh[key], key
    assert rec["model_dependency_count"] == 0
    assert rec["network_calls_at_run_time"] == 0
    assert rec["test_suite_runs"] == 0
