"""Bounded streaming search and real experience controls, not a general verifier.

Fixture labels and holdouts are supplied by the test author, not independent
proofs of intent. Exhaustive comparisons cover only the stated small grammars.
"""
from __future__ import annotations

import ast
import itertools
import json
import random

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.swe_kernel.expression_hypotheses_v1 import (
    _learned_compositions,
    _semantic_compositions,
    _signature,
    evaluate_outcome,
    function_models,
    matches_expected,
)
from canonical.swe_kernel.notions_v1 import NotionStore
from canonical.tests.test_adaptive_counterexample_search_v1 import QUINTUPLE
from canonical.tests.test_experience_composition_v1 import (
    board, daemon, finding, load_function, make_workspace, provide_feedback, train_once,
)


def _target():
    return function_models("def target(a,b):\n    return a*b\n")["target"]


def _points(constraints):
    points = list(itertools.product((2, 3, 4, 5, 6, 7), repeat=2))
    points += list(itertools.product((-3, 0, 11), repeat=2))

    def key(point):
        return tuple((type(value).__name__, value.hex() if type(value) is float else value) for value in point)

    seen = {key(point) for point in points}
    for args, _ in constraints:
        if key(args) not in seen:
            points.append(tuple(args))
            seen.add(key(args))
    return points


def _vector(expression, points):
    outcomes = [evaluate_outcome(expression, dict(zip(("a", "b"), point))) for point in points]
    return _signature([None if kind == "unknown" else value for kind, value in outcomes])


def _exhaustive_survivor_vectors(operators, constraints, depth):
    """Enumerate syntax separately from the compressed bottom-up search."""
    expressions = itertools.chain(
        (ast.Name(id=name, ctx=ast.Load()) for name in ("a", "b")),
        _learned_compositions(("a", "b"), operators, max_nodes=depth),
    )
    points = _points(constraints)
    survivors = set()
    for expression in expressions:
        results = [matches_expected(evaluate_outcome(expression, dict(zip(("a", "b"), args))), expected)
                   for args, expected in constraints]
        assert None not in results  # these comparisons deliberately avoid model-unknown constraints
        if all(results):
            nodes = sum(isinstance(node, ast.BinOp) for node in ast.walk(expression))
            assert nodes == depth  # no lower-depth expression satisfies this fixture
            survivors.add(_vector(expression, points))
    return survivors


def _weighted_constraints():
    return [((x, x), 5 * x) for x in (2, 3, 4, 5)] + [((2, 3), 12), ((-3, 11), 13)]


def test_streamed_terminal_refutations_preserve_every_small_grammar_survivor():
    target, constraints = _target(), _weighted_constraints()
    result, truncated, info = _semantic_compositions(target, constraints, ["Add", "Mult"], limit=256)
    unfiltered, high_truncated, high = _semantic_compositions(target, constraints, ["Add", "Mult"], limit=512)
    assert not truncated and not high_truncated
    assert info["learned_binary_nodes_explored"] == high["learned_binary_nodes_explored"] == 4
    assert info["terminal_refutation_filtering"] and not high["terminal_refutation_filtering"]
    assert info["peak_retained_signatures"] == 256 and info["retained_signatures"] == 96
    assert info["candidates_examined_is_lower_bound"] and info["semantic_combinations"] == 1280
    assert info["full_domain_combinations"] == 472 and info["constraint_first_refutations"] == 808
    assert high["full_domain_combinations"] == 1280 and high["constraint_first_refutations"] == 0
    assert high["retained_signatures"] == 344  # diagnostic only; production cap remains 256
    points = _points(constraints)
    expected = _exhaustive_survivor_vectors(["Add", "Mult"], constraints, depth=4)
    assert len(expected) == 1
    assert {_vector(e, points) for e in result} == expected == {_vector(e, points) for e in unfiltered}


def test_leaf_overflow_also_respects_the_signature_limit():
    result, truncated, info = _semantic_compositions(_target(), _weighted_constraints(), ["Add"], limit=1)
    assert result == [] and truncated and not info["complete_through_depth"]
    assert info["learned_binary_nodes_explored"] == 0 and info["reason"] == "semantic_signature_budget"
    assert info["peak_retained_signatures"] == 1 and info["semantic_combinations"] == 0


def test_refuted_intermediates_cannot_be_discarded_then_used_to_claim_deeper_search():
    target, constraints = _target(), _weighted_constraints()
    result, truncated, info = _semantic_compositions(target, constraints, ["Add", "Mult"], limit=50)
    assert result == [] and truncated and not info["complete_through_depth"]
    assert info["reason"] == "intermediate_signature_budget"
    assert info["terminal_refutation_filtering"] and info["learned_binary_nodes_explored"] == 3
    assert info["peak_retained_signatures"] == 50
    # With enough intermediate space the next depth really does contain a fit.
    larger, larger_truncated, larger_info = _semantic_compositions(target, constraints, ["Add", "Mult"], limit=256)
    assert larger and not larger_truncated and larger_info["learned_binary_nodes_explored"] == 4


def test_streaming_keeps_all_divergent_survivors_or_reports_a_full_survivor_budget():
    target = _target()
    constraints = [((x, x), 5 * x) for x in (2, 3, 4, 5)]
    complete, truncated, info = _semantic_compositions(target, constraints, ["Add", "Mult"], limit=101)
    reference, ref_truncated, _ = _semantic_compositions(target, constraints, ["Add", "Mult"], limit=512)
    assert not truncated and not ref_truncated and info["terminal_refutation_filtering"]
    assert len(complete) == 6 and info["peak_retained_signatures"] == 101
    assert {_vector(e, _points(constraints)) for e in complete} == {
        _vector(e, _points(constraints)) for e in reference}
    predictions = {evaluate_outcome(e, {"a": 2, "b": 3}) for e in complete}
    assert predictions == {("value", n) for n in range(10, 16)}
    partial, truncated, info = _semantic_compositions(target, constraints, ["Add", "Mult"], limit=100)
    assert len(partial) == 5 and truncated and not info["complete_through_depth"]
    assert info["reason"] == "semantic_signature_budget"
    assert info["peak_retained_signatures"] == 100


@pytest.mark.parametrize("operators, constraints, limit, count", [
    (["Add", "Div"], [((2, 0), {"raises": "ZeroDivisionError"}), ((2, 2), 2.5)], 64, 12),
    (["Add", "Div"], [((2, -0.0), {"raises": "ZeroDivisionError"}), ((2, 2), 2.5),
                       ((2.0, 0.5), 4.0)], 64, 3),
    (["Mod", "Sub"], [((2, 2), {"raises": "ZeroDivisionError"}), ((2, 3), -2)], 50, 6),
])
def test_exception_survivors_are_not_filtered_as_missing_values(operators, constraints, limit, count):
    target = _target()
    result, truncated, info = _semantic_compositions(target, constraints, operators, limit=limit)
    high, high_truncated, high_info = _semantic_compositions(target, constraints, operators, limit=512)
    assert not truncated and not high_truncated
    assert info["terminal_refutation_filtering"] and not high_info["terminal_refutation_filtering"]
    assert info["peak_retained_signatures"] == limit
    expected = _exhaustive_survivor_vectors(operators, constraints, depth=3)
    assert len(expected) == count
    assert {_vector(e, _points(constraints)) for e in result} == expected == {
        _vector(e, _points(constraints)) for e in high}


def test_streaming_still_stops_at_the_global_combination_budget():
    constraints = [((2, 2), 999), ((3, 3), 1234)]
    result, truncated, info = _semantic_compositions(_target(), constraints, ["Add", "Sub", "Mult"], limit=256)
    assert result == [] and truncated and not info["complete_through_depth"]
    assert info["terminal_refutation_filtering"] and info["reason"] == "semantic_combination_budget"
    assert info["semantic_combinations"] == 4096 and info["peak_retained_signatures"] <= 256
    assert info["full_domain_combinations"] + info["constraint_first_refutations"] == 4096


def test_unknown_candidates_remain_unresolved_during_streaming():
    constraints = [((2, 13), 2), ((2, 2), 10)]
    _, truncated, info = _semantic_compositions(_target(), constraints, ["Add", "Pow"], limit=128)
    assert truncated and not info["complete_through_depth"] and info["terminal_refutation_filtering"]
    assert info["indeterminate_candidates"] > 0 and info["reason"] == "candidate_evaluation_unknown"
    assert info["peak_retained_signatures"] <= 128


def test_filtered_and_larger_cap_agree_on_generated_finite_grammar_cases():
    rng = random.Random(29)
    target = _target()
    compared = streamed = 0
    for operators in (["Add", "Mult"], ["Add", "Div"], ["Mod", "Sub"], ["Add", "Sub"]):
        syntax = list(_learned_compositions(("a", "b"), operators, max_nodes=3))
        for _ in range(25):
            expression = rng.choice(syntax)
            constraints = []
            for args in ((2, 2), (3, 3), (2, 3), (-3, 11), (0, 3)):
                kind, value = evaluate_outcome(expression, dict(zip(("a", "b"), args)))
                assert kind != "unknown"  # these generated fixtures use bounded primitive outcomes
                constraints.append((args, {"raises": value} if kind == "raises" else value))
            filtered, ft, fi = _semantic_compositions(target, constraints, operators, limit=128)
            larger, lt, li = _semantic_compositions(target, constraints, operators, limit=512)
            if not ft and not lt:
                compared += 1
                streamed += int(fi["terminal_refutation_filtering"])
                assert fi["learned_binary_nodes_explored"] == li["learned_binary_nodes_explored"]
                assert {_vector(e, _points(constraints)) for e in filtered} == {
                    _vector(e, _points(constraints)) for e in larger}
    # These are coverage guards for the differential test, not accuracy claims.
    assert compared >= 80 and streamed >= 30


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_real_added_experience_no_longer_blocks_the_four_addition_fixture(tmp_path):
    root, trained, _ = train_once(tmp_path / "learn_add")
    assert NotionStore(trained.notions_path).learned_operators() == ["Add"]
    workspace = tmp_path / "pending"
    module = make_workspace(workspace, QUINTUPLE)
    d = daemon(workspace, root)
    original, answers = provide_feedback(d, "ref", "target", lambda v: 3 * v[0] + 2 * v[1])
    assert original["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_text().splitlines()[0][len("# brain-notion-v1 "):])
    saved_test = test.read_bytes()
    store = NotionStore(d.notions_path)
    old_examples, old_review = store.examples[original["id"]], store.reviews[original["id"]]
    assert store.plans[original["id"]]["learned_operators_considered"] == ["Add"]

    # Actually acquire Mult from a separate reviewed board repair; do not insert
    # an operator directly or change code/feedback during the experiment.
    product_ws = tmp_path / "product_training"
    make_workspace(product_ws, "def square(s):\n    return s * s\n\ndef wider(a,b):\n    return a - b\n")
    other = daemon(product_ws, root)
    product, _ = provide_feedback(other, "square", "wider", lambda v: v[0] * v[1])
    assert product["status"] == "bounded_agreement"
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] and
               (s.get("structure_learning") or {}).get("operators") == ["Mult"] for s in board(root, product_ws))
    store = NotionStore(d.notions_path)
    assert store.learned_operators() == ["Add", "Mult"]
    assert store.examples[original["id"]] == old_examples and store.reviews[original["id"]] == old_review
    assert store.plans[original["id"]]["learned_operators_considered"] == ["Add"]  # cached old plan
    # Revalidation uses the enlarged grammar even before the stored plan refresh.
    with store.hold_reviewed_feedback(binding, workspace_root=workspace) as valid:
        assert valid
    refreshed = finding(d, "ref", "target")
    plan = refreshed["plan"]
    assert refreshed["status"] == "bounded_agreement" and not plan["truncated"]
    assert plan["learned_operators_considered"] == ["Add", "Mult"]
    assert plan["search"]["terminal_refutation_filtering"]
    assert plan["search"]["peak_retained_signatures"] == 256
    assert plan["search"]["semantic_combinations"] == 1280
    assert test.read_bytes() == saved_test and module.read_text() == QUINTUPLE
    steps = board(root, workspace)
    accepted = next((s for s in steps if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted is not None and accepted["verified"] is False and accepted["correct"] is None
    assert accepted["structure_learning"]["status"] == "recorded_for_proposals"
    fn = load_function(module, "target")
    for args in ((8, 3), (-2, 7), (0, 10), (101, -47)):
        assert list(args) not in answers
        assert fn(*args) == 3 * args[0] + 2 * args[1]
