#!/usr/bin/env python3
"""The synthesizer builds the fix at the site the failure points to, and refuses what it cannot.

MEASURED 2026-11-17 on the four example-searchable hard-open QuixBugs tasks, with the corpus's
own published examples and its own pytest as the only verdict (answer key absent, $0, no model):

    kheapsort        for iterable   `arr`        ->  `arr[k:]`              corpus pytest rc 0
    possible_change  guard          `total < 0`  ->  `(total < 0) or (not coins)`  rc 0
    powerset         return         `[[first]+s]`->  `rest_subsets + [[first]+s for s in rest_subsets]`  rc 0
    subsequences     early return   `[]`         ->  `[[]]`                 rc 0

These tests pin the mechanism on constructed functions so a regression is caught without the
corpus, and pin the two honesty rules: a candidate that passes the examples but fails the
corpus test is NOT a repair, and exhausting a bounded search is not treated as success.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from canonical.tools import site_general_expression_synthesis_v1 as S


# --------------------------------------------------------------------------- #
# sites and scopes
# --------------------------------------------------------------------------- #
def test_sites_are_read_from_the_ast_in_document_order():
    # An early return must come before a later `if`, which must come before a later loop: the
    # order is the program's own, not a type grouping.
    source = "def f(a):\n    if a:\n        return 1\n    for x in a:\n        if x:\n            return x\n    return a\n"
    function = ast.parse(source).body[0]
    kinds = [kind for kind, _ in S.iter_sites(function)]
    assert kinds == ["if_test", "return", "for_iter", "if_test", "return", "return"]


def test_guard_scope_is_observable_even_when_the_next_line_raises():
    source = "def f(coins, total):\n    if total < 0:\n        return 0\n    first, *rest = coins\n    return total * first\n"
    tree = ast.parse(source)
    function = tree.body[0]
    site = next(node for kind, node in S.iter_sites(function) if kind == "if_test")
    scope = S.scope_at_site(source, "f", "if_test", site, [[], 5], 0.05)
    assert scope is not None
    assert scope["coins"] == []
    assert scope["total"] == 5


def test_generator_for_iterable_scope_is_captured_after_consumption():
    source = "def f(arr, k):\n    for x in arr:\n        yield x\n"
    tree = ast.parse(source)
    function = tree.body[0]
    site = next(node for kind, node in S.iter_sites(function) if kind == "for_iter")
    scope = S.scope_at_site(source, "f", "for_iter", site, [[1, 2, 3], 2], 0.05)
    assert scope is not None
    assert scope["arr"] == [1, 2, 3]
    assert scope["k"] == 2


# --------------------------------------------------------------------------- #
# the grammar reaches the shapes the refusals named
# --------------------------------------------------------------------------- #
def test_grammar_contains_the_four_shapes():
    texts = S.expression_texts([{"arr": [1], "k": 1, "total": 1, "coins": [1],
                                 "first": 1, "rest_subsets": [1], "a": 1, "b": 1}])
    assert "[[]]" in texts
    assert "arr[k:]" in texts
    assert "((total < 0) or (not coins))" in texts
    assert "(rest_subsets + [([first] + _v) for _v in rest_subsets])" in texts


def test_score_materialises_a_generator_like_the_corpus_test_does():
    source = "def f(arr):\n    for x in arr:\n        yield x\n"
    assert S.score(source, "f", [([[1, 2]], [1, 2])], 0.05) == 1


# --------------------------------------------------------------------------- #
# the four closures, on constructed functions
# --------------------------------------------------------------------------- #
def test_early_return_literal_is_synthesized():
    source = "def f(k):\n    if k == 0:\n        return []\n    return [k]\n"
    found = S.synthesize(source, "f", [([0], [[]]), ([1], [1])], 0.05)
    assert found["status"] == "FOUND"
    assert any(h["expression"] == "[[]]" for h in found["hits"])


def test_guard_is_synthesized():
    source = ("def f(coins, total):\n    if total < 0:\n        return 0\n"
              "    first, *rest = coins\n    return total * first\n")
    found = S.synthesize(source, "f", [([[2, 3], 5], 10), ([[], 5], 0), ([[2], -1], 0), ([[3], 4], 12)], 0.05)
    assert found["status"] == "FOUND"
    assert any("or" in h["expression"] and "not coins" in h["expression"] for h in found["hits"])


def test_for_iterable_slice_is_synthesized():
    source = "def f(arr, k):\n    out = []\n    for x in arr:\n        out.append(x)\n    return out\n"
    found = S.synthesize(source, "f", [([[1, 2, 3, 4], 2], [3, 4])], 0.05)
    assert found["status"] == "FOUND"
    assert any(h["expression"] == "arr[k:]" for h in found["hits"])


def test_comprehension_return_is_synthesized():
    source = ("def f(arr):\n    if arr:\n        first, *rest = arr\n"
              "        rest_subsets = f(rest)\n"
              "        return [[first] + s for s in rest_subsets]\n    return [[]]\n")
    found = S.synthesize(source, "f", [([["a", "b"]], [[], ["b"], ["a"], ["a", "b"]])], 0.05)
    assert found["status"] == "FOUND"
    assert any("for _v in rest_subsets" in h["expression"] for h in found["hits"])


def test_bounded_search_refuses_when_no_candidate_matches():
    # The bounded grammar does not construct dictionaries with arbitrary string keys.
    source = "def f(x):\n    return x\n"
    found = S.synthesize(source, "f", [([1], {"unseen-key": 7})], 0.05, max_texts=500)
    assert found["status"] == "NO_EXPRESSION"
    assert found["hits"] == []


# --------------------------------------------------------------------------- #
# the verdict is the corpus's own pytest, never the examples alone
# --------------------------------------------------------------------------- #
def test_a_candidate_that_fails_the_corpus_test_is_not_a_repair(monkeypatch, tmp_path):
    root = tmp_path / "quixbugs"
    (root / "python_programs").mkdir(parents=True)
    (root / "python_testcases").mkdir(parents=True)
    (root / "json_testcases").mkdir(parents=True)
    (root / "python_programs" / "f.py").write_text("def f(k):\n    if k == 0:\n        return []\n    return [k]\n")
    (root / "python_testcases" / "test_f.py").write_text("def test_f():\n    assert 1 == 2\n")
    (root / "json_testcases" / "f.json").write_text("[[0], [[]]]\n")

    # The candidate passes the published examples; the corpus test says no. The stage must be
    # the corpus failure, never REPAIRED.
    monkeypatch.setattr(S.gen, "verify_with_corpus_test",
                        lambda *a, **k: {"returncode": 1, "tail": ["1 failed"], "timed_out": False})
    row = S.measure_task(root, "f", per_example_timeout=0.05, verify_timeout=10, max_texts=20000)
    assert row["synthesis_status"] == "FOUND"
    assert row["stage"] == "SYNTHESIZED__CORPUS_TEST_FAILS"


def test_measure_task_reports_no_examples_honestly(tmp_path):
    root = tmp_path / "quixbugs"
    (root / "python_programs").mkdir(parents=True)
    (root / "python_testcases").mkdir(parents=True)
    (root / "json_testcases").mkdir(parents=True)
    (root / "python_programs" / "f.py").write_text("def f():\n    return 1\n")
    row = S.measure_task(root, "f", per_example_timeout=0.05, verify_timeout=10, max_texts=100)
    assert row["stage"] == "NO_EXAMPLES"


def test_timeout_does_not_kill_the_process_or_change_the_alarm_handler():
    import signal
    previous = signal.getsignal(signal.SIGALRM)
    assert S.score("def f():\n    while True:\n        pass\n", "f", [([], 1)], 0.01) == -1
    assert signal.getsignal(signal.SIGALRM) == previous
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


def test_empty_examples_are_not_vacuous_success():
    result = S.synthesize("def f():\n    return 1\n", "f", [], 0.05)
    assert result["status"] == "NO_EXAMPLES"
    assert result["hits"] == []


def test_zero_budget_is_rejected():
    with pytest.raises(ValueError, match="max_texts"):
        S.expression_texts([{"x": 1}], max_texts=0)
