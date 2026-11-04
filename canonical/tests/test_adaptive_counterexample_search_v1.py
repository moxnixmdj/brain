"""Counterexample-guided composition and local experience-evidence boundaries.

Fixture oracles here are author-supplied, not independently authenticated.
The bounded grammar and probes cannot establish a complete specification.
"""
from __future__ import annotations

import ast
import itertools
import json

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.swe_kernel.expression_hypotheses_v1 import (
    _learned_compositions,
    _signature,
    evaluate_expression,
    fitting_expression_candidates,
    function_models,
    investigate,
    supported_binary_operator_names,
    validate_external_examples,
)
from canonical.swe_kernel.notions_v1 import NotionStore, notions_for_source
from canonical.tests.test_experience_composition_v1 import (
    TRAIN,
    active_plan,
    board,
    daemon,
    finding,
    load_function,
    make_workspace,
    provide_feedback,
)


QUADRUPLE = "def ref(z):\n    return 4*z\n\ndef target(a,b):\n    return a*b\n"
QUINTUPLE = "def ref(z):\n    return 5*z\n\ndef target(a,b):\n    return a*b\n"


def _observations():
    return next(n.evaluate()["observations"] for n in notions_for_source(QUADRUPLE, "pkg/example.py")
                if n.left == "ref" and n.right == "target")


def test_search_deepens_only_after_a_complete_smaller_search_is_refuted():
    observations = _observations()
    first = investigate(QUADRUPLE, target_name="target", reference_name="ref",
                        observations=observations, examples=[], learned_operators=["Add"])
    assert first["status"] == "needs_example" and first["search"]["expansion_rounds"] == 0
    assert first["search"]["learned_binary_nodes_explored"] == 2
    args = first["next_query"]["args"]
    examples = [{"args": args, "expected": 2 * sum(args)}]
    after = investigate(QUADRUPLE, target_name="target", reference_name="ref",
                        observations=observations, examples=examples, learned_operators=["Add"])
    assert after["status"] == "needs_example"
    assert after["search"]["learned_binary_nodes_explored"] == 3
    assert after["search"]["expansion_rounds"] == 1 and after["search"]["complete_through_depth"]
    assert after["search"]["more_complex_learned_models_unexamined"]
    args = after["next_query"]["args"]
    examples.append({"args": args, "expected": 2 * sum(args)})
    done = investigate(QUADRUPLE, target_name="target", reference_name="ref",
                       observations=observations, examples=examples, learned_operators=["Add"])
    assert done["status"] == "bounded_agreement" and not done["truncated"]
    assert done["search"]["method"] == "finite_domain_signature"
    assert done["search"]["domain_points"] == 45
    assert done["search"]["candidates_examined"] == 14  # semantic representatives, not syntax count


@pytest.mark.parametrize("operators", [["Add"], ["Add", "Sub"], ["Add", "Mult"], ["Add", "FloorDiv"]])
def test_behavioral_compression_matches_exhaustive_syntax_on_the_finite_domain(operators):
    target = function_models(QUADRUPLE)["target"]
    constraints = [((2, 2), 8), ((3, 3), 12)]
    compressed, truncated, search = fitting_expression_candidates(
        target, [], constraints, learned_operators=operators)
    assert not truncated and search["learned_binary_nodes_explored"] == 3
    points = list(itertools.product((2, 3, 4, 5, 6, 7), repeat=2))
    points += list(itertools.product((-3, 0, 11), repeat=2))

    def vector(expression):
        values = [evaluate_expression(expression, dict(zip(target.params, point))) for point in points]
        return tuple(("undefined",) if not ok else
                     (type(value).__name__, value.hex() if type(value) is float else value)
                     for ok, value in values)

    exhaustive = []
    for expression in _learned_compositions(target.params, operators, max_nodes=3):
        if all(evaluate_expression(expression, dict(zip(target.params, args))) == (True, expected)
               for args, expected in constraints):
            exhaustive.append(expression)
    assert len(exhaustive) > len(compressed)
    assert {vector(expression) for expression in exhaustive} == {vector(expression) for expression in compressed}


def test_finite_signature_domain_includes_out_of_grid_feedback():
    target = function_models(QUADRUPLE)["target"]
    constraints = [((2, 2), 8), ((3, 3), 12), ((101, -47), 108)]
    candidates, truncated, search = fitting_expression_candidates(target, [], constraints, learned_operators=["Add"])
    assert not truncated and search["domain_points"] == 46
    assert candidates
    for candidate in candidates:
        assert evaluate_expression(candidate, {"a": 101, "b": -47}) == (True, 108)


def test_behavioral_signatures_preserve_numeric_type_and_signed_zero():
    assert _signature((0,)) != _signature((0.0,))
    assert _signature((0.0,)) != _signature((-0.0,))
    assert _signature((None,)) != _signature((0,))


@pytest.mark.parametrize("weights, depth", [((3, 2), 4), ((4, 2), 5)])
def test_one_observed_operator_can_be_recombined_beyond_three_nodes(weights, depth):
    a, b = weights
    source = f"def ref(z):\n    return {a + b}*z\n\ndef target(a,b):\n    return a*b\n"
    oracle = lambda values: a * values[0] + b * values[1]
    cold, _ = active_plan(source, "ref", "target", oracle, [])
    warm, answers = active_plan(source, "ref", "target", oracle, ["Add"])
    assert cold["status"] == "no_candidates" and warm["status"] == "bounded_agreement"
    assert warm["search"]["learned_binary_nodes_explored"] == depth
    for text in warm["candidate_expressions"]:
        expr = ast.parse(text, mode="eval").body
        for values in ((8, 3), (-2, 7), (101, -47)):
            assert list(values) not in [e["args"] for e in answers]
            valid, prediction = evaluate_expression(expr, dict(zip(("a", "b"), values)))
            assert valid and prediction == oracle(values)


def test_incomplete_smaller_search_is_not_treated_as_refutation():
    models = function_models(QUADRUPLE)
    survivors, truncated, search = fitting_expression_candidates(
        models["target"], [models["ref"]], [((2, 2), 999)],
        learned_operators=sorted(supported_binary_operator_names()))
    assert survivors == [] and truncated
    assert not search["complete_through_depth"]
    assert search["learned_binary_nodes_explored"] == 2 and search["expansion_rounds"] == 0


def test_deeper_search_that_exceeds_budget_cannot_claim_agreement():
    plan, examples = active_plan(QUADRUPLE, "ref", "target", lambda v: 2 * sum(v), ["Add", "Div", "Pow"])
    assert len(examples) >= 2 and plan["truncated"]
    assert plan["status"] == "truncated_search"
    assert plan["search"]["expansion_rounds"] == 1 and not plan["search"]["complete_through_depth"]


def test_deeper_finite_search_still_misses_a_distant_counterexample():
    oracle = lambda v: 2 * sum(v) + (1 if max(v) >= 100 and v[0] != v[1] else 0)
    plan, examples = active_plan(QUADRUPLE, "ref", "target", oracle, ["Add"])
    assert plan["status"] == "bounded_agreement" and all(max(e["args"]) < 100 for e in examples)
    expression = ast.parse(plan["candidate_expressions"][0], mode="eval").body
    good, value = evaluate_expression(expression, {"a": 101, "b": 2})
    assert good and value != oracle([101, 2])


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("source,weights,depth", [(QUADRUPLE, (2, 2), 3), (QUINTUPLE, (3, 2), 4)])
def test_real_experience_reopens_a_shallow_search_and_enables_a_deeper_board_repair(tmp_path, source, weights, depth):
    root, workspace = tmp_path / "creature", tmp_path / "held"
    module = make_workspace(workspace, source)
    d = daemon(workspace, root)
    oracle = lambda v: weights[0] * v[0] + weights[1] * v[1]
    cold, answers = provide_feedback(d, "ref", "target", oracle)
    assert cold["status"] == "no_candidates" and len(answers) == 1
    before_examples = NotionStore(d.notions_path).examples[cold["id"]]
    assert d._sense_failing_workspace_tests() == [] and module.read_text() == source

    # Use the same creature root for a real reviewed/local training repair.
    train_ws = tmp_path / "training"
    make_workspace(train_ws, TRAIN)
    training = daemon(train_ws, root)
    trained, _ = provide_feedback(training, "narrow", "pair", sum)
    assert trained["status"] == "bounded_agreement"
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in board(root, train_ws))
    assert NotionStore(d.notions_path).learned_operators() == ["Add"]

    resumed = finding(d, "ref", "target")
    assert resumed["id"] == cold["id"] and resumed["status"] == "needs_example"
    assert resumed["plan"]["search"]["expansion_rounds"] == depth - 2
    assert NotionStore(d.notions_path).examples[cold["id"]] == before_examples
    args = resumed["plan"]["next_query"]["args"]
    NotionStore(d.notions_path).answer(cold["id"], args=args, expected=oracle(args),
                                      reviewer="fixture", basis="fixture oracle")
    final = finding(d, "ref", "target")
    assert final["status"] == "bounded_agreement" and final["plan"]["search"]["expansion_rounds"] == depth - 2
    steps = board(root, workspace)
    accepted = next((s for s in steps if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted and accepted["verified"] is False and accepted["correct"] is None
    experience = NotionStore(d.notions_path).experiences[cold["id"]]
    assert experience["observation"] == "workspace_matches_reviewed_examples_publication_not_authenticated"
    assert experience["test_origin_key"] and len(experience["non_target_sha256"]) == 64
    rewritten = ast.parse(module.read_text())
    target = next(n for n in rewritten.body if isinstance(n, ast.FunctionDef) and n.name == "target")
    assert sum(isinstance(n, ast.Add) for n in ast.walk(target)) == depth
    func = load_function(module, "target")
    for values in ((8, 3), (-2, 7), (0, 10), (101, -47)):
        assert list(values) not in answers + [args]
        assert func(*values) == oracle(values)


@pytest.mark.parametrize("examples", [
    [{"args": [2, 3], "expected": 5}, {"args": [2.0, 3], "expected": 5}],
    [{"args": [2, 3], "expected": True}],
    [{"args": [2, 3], "expected": float("nan")}],
    [{"args": [2], "expected": 5}],
    [None],
])
def test_malformed_or_duplicate_external_examples_cannot_count_as_evidence(examples):
    valid, _ = validate_external_examples(examples, 2)
    assert not valid
    plan = investigate(QUADRUPLE, target_name="target", reference_name="ref",
                       observations=_observations(), examples=examples, learned_operators=["Add"])
    assert plan["status"] == "invalid_external_examples" and plan["next_query"] is None


def test_attribution_fields_are_required_but_do_not_authenticate_the_source():
    row = {"args": [2, 3], "expected": 5}
    assert validate_external_examples([row], 2)[0]
    assert not validate_external_examples([row], 2, require_attribution=True)[0]
    row.update(reviewer="fixture", basis="unverified claim")
    assert validate_external_examples([row], 2, require_attribution=True)[0]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_duplicated_feedback_cannot_author_a_test_even_with_a_forged_plan(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    data = json.loads(d.notions_path.read_text())
    first = data["examples"][f["id"]][0]
    data["examples"][f["id"]] = [first, first]
    d.notions_path.write_text(json.dumps(data))
    observed = finding(d, "narrow", "pair")
    assert observed["status"] == "invalid_external_examples" and d._sense_failing_workspace_tests() == []
    store = NotionStore(d.notions_path)
    feedback_hash = store._feedback_hash(store.reviews[f["id"]], store.examples[f["id"]])
    assert store.record_plan(f["id"], {"status": "bounded_agreement", "truncated": False,
                                       "external_examples": 2}, expected_feedback_hash=feedback_hash)
    binding = {"module": f["module"], "source_sha256": f["source_sha256"],
               "target": "pair", "reference": "narrow", "finding_id": f["id"],
               "feedback_sha256": feedback_hash}
    assert not store.author_reviewed_test(binding, workspace, workspace / "tests" / "test_example.py")
    assert module.read_text() == TRAIN and not (workspace / "tests" / "test_example.py").exists()


def _prepared_authored_test(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_text().splitlines()[0][len("# brain-notion-v1 "):])
    return workspace, module, d, test, binding


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_unpublished_candidate_cannot_become_experience_via_store_api(tmp_path):
    workspace, module, d, test, binding = _prepared_authored_test(tmp_path)
    candidate = TRAIN.replace("return x * y", "return x + y")
    store = NotionStore(d.notions_path)
    assert store.record_checked_repair(binding, candidate)["status"] == "workspace_evidence_missing"
    result = store.record_checked_repair(binding, candidate, workspace_root=workspace, test_file=test)
    assert result["status"] == "candidate_not_current"
    assert module.read_text() == TRAIN and store.learned_operators() == []


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_workspace_learning_rechecks_target_scope_and_authored_test(tmp_path):
    workspace, module, d, test, binding = _prepared_authored_test(tmp_path)
    candidate = TRAIN.replace("return x * y", "return x + y")
    altered_reference = candidate.replace("return t + t", "return 2 * t")
    module.write_text(altered_reference)
    store = NotionStore(d.notions_path)
    out = store.record_checked_repair(binding, altered_reference, workspace_root=workspace, test_file=test)
    assert out["status"] == "candidate_scope_changed" and store.learned_operators() == []
    module.write_text(candidate)
    test.write_text(test.read_text() + "\n# modified\n")
    out = store.record_checked_repair(binding, candidate, workspace_root=workspace, test_file=test)
    assert out["status"] == "test_origin_mismatch" and store.learned_operators() == []


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_older_origin_without_target_scope_fingerprint_cannot_train(tmp_path):
    workspace, module, d, test, binding = _prepared_authored_test(tmp_path)
    candidate = TRAIN.replace("return x * y", "return x + y")
    module.write_text(candidate)
    data = json.loads(d.notions_path.read_text())
    key = NotionStore._authored_test_key(workspace, "tests/test_example.py")
    data["authored_tests"][key].pop("non_target_sha256")
    d.notions_path.write_text(json.dumps(data))
    store = NotionStore(d.notions_path)
    out = store.record_checked_repair(binding, candidate, workspace_root=workspace, test_file=test)
    assert out["status"] == "scope_evidence_missing" and store.learned_operators() == []
