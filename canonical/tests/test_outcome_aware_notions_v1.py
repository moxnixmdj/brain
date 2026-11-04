"""Value/exception/unknown controls for reviewed, bounded repair.

Fixture specifications and their labels are caller-authored, not authenticated
or independent verification. These tests do not establish general correctness.
"""
from __future__ import annotations

import ast
import hashlib
import itertools
import json
import operator

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime.creature_runtime_v1 import _publish_notion_candidate
from canonical.swe_kernel.expression_hypotheses_v1 import (
    OUTCOME_MODEL_VERSION,
    _constraint_result,
    _learned_compositions,
    _semantic_compositions,
    _signature,
    candidate_agrees_with_bounded_plan,
    evaluate_outcome,
    fitting_expression_candidates,
    function_models,
    investigate,
    matches_expected,
    target_expression_scope_sha256,
    validate_external_examples,
)
from canonical.swe_kernel.notion_feedback_cli_v1 import main as feedback_cli
from canonical.swe_kernel.notions_v1 import NotionStore, notions_for_source
from canonical.tests.test_experience_composition_v1 import (
    TRAIN, board, daemon, finding, load_function, make_workspace, provide_feedback, train_once,
)


SOURCE = """def unit(x):
    return x * x / x

def combine(a, b):
    return a + b
"""


def _prior_numeric_feedback(tmp_path):
    """Recreate a valid pre-upgrade snapshot with two agreeing nonzero answers."""
    root, workspace = tmp_path / "creature", tmp_path / "workspace"
    module = make_workspace(workspace, SOURCE)
    d = daemon(workspace, root)
    first = finding(d, "unit", "combine")
    store = NotionStore(d.notions_path)
    store.review(first["id"], decision="confirm", reviewer="fixture", basis="fixture contract",
                 trusted_function="unit")
    # This is the exact shape of a previously persisted feedback snapshot.
    # Neither row distinguishes the zero behavior of the two specifications.
    data = json.loads(d.notions_path.read_text())
    data["examples"][first["id"]] = [
        {"args": [2, 3], "expected": 2.0, "reviewer": "fixture", "basis": "fixture contract"},
        {"args": [-3, 11], "expected": -3.0, "reviewer": "fixture", "basis": "fixture contract"},
    ]
    d.notions_path.write_text(json.dumps(data))
    return root, workspace, module, d, first["id"]


def _actual_fixture_outcome(fn, args):
    try:
        return "value", fn(*args)
    except (ZeroDivisionError, OverflowError) as exc:
        return "raises", type(exc).__name__


@pytest.mark.parametrize("mode", ["numeric", "exception"])
@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_older_feedback_reopens_at_an_outcome_disagreement_before_board_publication(tmp_path, mode):
    root, workspace, module, d, fid = _prior_numeric_feedback(tmp_path)
    before = finding(d, "unit", "combine")
    plan = before["plan"]
    assert before["status"] == "needs_example" and plan["external_examples"] == 2
    assert {"a * a / a", "a * b / b"} <= set(plan["candidate_expressions"])
    query = plan["next_query"]
    assert query["reason"] == "models_disagree" and query["args"] == [0, 11]
    assert query["predictions"] == [0.0] and query["exception_predictions"] == ["ZeroDivisionError"]
    assert query["unknown_models"] == 0
    # Without a new external answer the board cannot author or publish a test.
    assert d._sense_failing_workspace_tests() == []
    assert not any(s.get("accepted_into_world") for s in board(root, workspace))
    assert module.read_text() == SOURCE and not list(workspace.rglob("test_*.py"))

    # Exact same source, review, and initial examples: the new caller outcome
    # selects a domain behavior rather than turning a model prediction into truth.
    if mode == "numeric":
        oracle = lambda a, b: a * b / b
        answer = 0.0
    else:
        oracle = lambda a, b: a * a / a
        answer = {"raises": "ZeroDivisionError"}
    store = NotionStore(d.notions_path)
    store.answer(fid, args=query["args"], expected=answer, reviewer="fixture", basis="fixture contract")
    after = finding(d, "unit", "combine")
    assert after["status"] == "bounded_agreement" and not after["plan"]["truncated"]
    assert after["plan"]["coverage"]["unknown_points"] == 0
    assert d._sense_failing_workspace_tests()
    test_file = workspace / "tests" / "test_example.py"
    authored = test_file.read_text()
    assert ("except ZeroDivisionError as captured:" in authored) == (mode == "exception")
    assert "import pytest" not in authored
    steps = board(root, workspace)
    accepted = next((s for s in steps if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted is not None and accepted["verified"] is False and accepted["correct"] is None
    assert accepted["structure_learning"]["status"] == "recorded_for_proposals"
    func = load_function(module, "combine")
    for args in ((0, 3), (3, 0), (-4, 3), (7, -2)):
        assert list(args) not in [[2, 3], [-3, 11], query["args"]]
        assert _actual_fixture_outcome(func, args) == _actual_fixture_outcome(oracle, args)


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_publication_rejects_a_candidate_outside_the_modelled_outcome_consensus(tmp_path):
    _, workspace, module, d, fid = _prior_numeric_feedback(tmp_path)
    query = finding(d, "unit", "combine")["plan"]["next_query"]
    store = NotionStore(d.notions_path)
    store.answer(fid, args=query["args"], expected=0, reviewer="fixture", basis="fixture contract")
    planned = finding(d, "unit", "combine")
    assert planned["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    # This candidate satisfies all three external answers and responds to input,
    # but does not raise at (3, 0) as the model-consensus expressions do.
    wrong = SOURCE.replace("return a + b", "return a + 0 * b")
    published, _, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": wrong}, notions_path=d.notions_path)
    assert not published and reason == "NOTION_CANDIDATE_DISAGREES" and module.read_text() == SOURCE
    right = SOURCE.replace("return a + b", "return a * b / b")
    published, probe, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": right}, notions_path=d.notions_path)
    assert published and probe["generalizes"] and reason is None
    with pytest.raises(ZeroDivisionError):
        load_function(module, "combine")(3, 0)


def test_candidate_grid_consistency_still_does_not_cover_other_inputs():
    notion = notions_for_source(SOURCE, "example.py")[0].evaluate()
    examples = [{"args": [2, 3], "expected": 2}, {"args": [-3, 11], "expected": -3},
                {"args": [0, 11], "expected": 0}]
    plan = investigate(SOURCE, target_name="combine", reference_name="unit",
                       observations=notion["observations"], examples=examples)
    assert plan["status"] == "bounded_agreement"
    # This nonzero polynomial vanishes at each first-argument grid value.
    factors = " * ".join(f"(a - {n})" for n in (2, 3, 4, 5, 6, 7, -3, 0, 11))
    candidate = SOURCE.replace("return a + b", f"return a * b / b + ({factors})")
    assert candidate_agrees_with_bounded_plan(SOURCE, candidate, target_name="combine",
                                              plan=plan, examples=examples)
    for bad in (None, {"coverage": ["not a mapping"]}, {**plan, "truncated": True},
                {**plan, "coverage": {**plan["coverage"], "unknown_points": 1}}):
        assert not candidate_agrees_with_bounded_plan(SOURCE, candidate, target_name="combine",
                                                      plan=bad, examples=examples)
    expression = function_models(candidate)["combine"].expression
    outcome = evaluate_outcome(expression, {"a": 8, "b": 3})
    assert outcome[0] == "value" and outcome[1] != 8


def test_interpreter_distinguishes_known_arithmetic_errors_from_its_own_limits():
    def outcome(text, **bindings):
        return evaluate_outcome(ast.parse(text, mode="eval").body, bindings)

    assert outcome("a / b", a=2, b=0) == ("raises", "ZeroDivisionError")
    assert outcome("a ** b", a=1e-30, b=-12) == ("raises", "OverflowError")
    assert outcome("a ** b", a=-2, b=0.5) == ("unknown", None)  # complex result outside the model
    assert outcome("(a ** b) / 0", a=2, b=13) == ("unknown", None)  # left operand is not modeled
    assert outcome("1 / 0 + (a ** b)", a=2, b=13) == ("raises", "ZeroDivisionError")
    assert _signature(("ZeroDivisionError",)) != _signature((None,))
    assert _signature(("ZeroDivisionError",)) != _signature(("OverflowError",))
    assert matches_expected(("unknown", None), {"raises": "ZeroDivisionError"}) is None
    assert matches_expected(("raises", "OverflowError"), {"raises": "ZeroDivisionError"}) is False
    # A real contradiction dominates an unknown, but unknown alone is not refutation.
    assert _constraint_result([("unknown", None), ("value", 3)], [5, 4]) is False
    assert _constraint_result([("unknown", None), ("value", 3)], [5, 3]) is None
    assert _constraint_result([("value", 3)], [3, 4]) is None


@pytest.mark.parametrize("symbol, operation", [
    ("+", operator.add), ("-", operator.sub), ("*", operator.mul), ("/", operator.truediv),
    ("//", operator.floordiv), ("%", operator.mod), ("**", operator.pow),
])
def test_modeled_primitive_outcomes_match_python_on_a_small_typed_grid(symbol, operation):
    expression = ast.parse(f"a {symbol} b", mode="eval").body
    for a, b in itertools.product((-3, -0.0, 0, 0.5, 2), repeat=2):
        try:
            actual = operation(a, b)
        except (ZeroDivisionError, OverflowError) as exc:
            expected = ("raises", type(exc).__name__)
        else:
            expected = ("value", actual) if type(actual) in (int, float) else ("unknown", None)
        modeled = evaluate_outcome(expression, {"a": a, "b": b})
        assert modeled[0] == expected[0]
        if modeled[0] == "value" and type(expected[1]) is float:
            assert type(modeled[1]) is float and modeled[1].hex() == expected[1].hex()
        else:
            assert modeled[1] == expected[1] and type(modeled[1]) is type(expected[1])


def test_unmodeled_result_neither_refutes_a_candidate_nor_authorizes_deepening():
    model = function_models("def target(a, b):\n    return a ** 13 // a ** 12\n")["target"]
    assert (2 ** 13 // 2 ** 12) == 2  # actual Python result, not a workspace import
    assert evaluate_outcome(model.expression, {"a": 2, "b": 3}) == ("unknown", None)
    survivors, truncated, search = fitting_expression_candidates(
        model, [], [((2, 3), 2)], learned_operators=["Add"])
    assert survivors and truncated
    assert search["indeterminate_candidates"] >= 1
    assert search["reason"] == "candidate_evaluation_unknown"
    assert not search["complete_through_depth"] and search["expansion_rounds"] == 0


def test_unknown_grid_is_queried_as_unknown_and_answer_does_not_become_false_refutation():
    source = "def ref(z):\n    return z ** (z * z)\n\ndef target(a,b):\n    return a + b\n"
    notion = notions_for_source(source, "example.py")[0].evaluate()
    assert notion["fired"] and len(notion["observations"]) == 2
    examples = [{"args": [2, 3], "expected": 16}, {"args": [-3, 11], "expected": -19683}]
    plan = investigate(source, target_name="target", reference_name="ref",
                       observations=notion["observations"], examples=examples)
    query = plan["next_query"]
    assert plan["status"] == "needs_example" and plan["coverage"]["unknown_points"] > 0
    assert query["reason"] == "model_unknown" and query["unknown_models"] == 1
    assert query["predictions"] == [] and query["exception_predictions"] == []
    assert query["args"] == [4, 2]
    examples.append({"args": query["args"], "expected": 4 ** 16})
    after = investigate(source, target_name="target", reference_name="ref",
                        observations=notion["observations"], examples=examples)
    assert after["status"] == "truncated_search" and after["truncated"]
    assert after["search"]["reason"] == "candidate_evaluation_unknown"
    assert "potentially fitting candidate unresolved" in after["reason"]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_unknown_outcome_cannot_author_or_publish_via_board(tmp_path):
    source = "def ref(z):\n    return z ** (z * z)\n\ndef target(a,b):\n    return a + b\n"
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    module = make_workspace(workspace, source)
    d = daemon(workspace, root)
    first = finding(d, "ref", "target")
    store = NotionStore(d.notions_path)
    store.review(first["id"], decision="confirm", reviewer="fixture", basis="fixture contract",
                 trusted_function="ref")
    saved = json.loads(d.notions_path.read_text())
    saved["examples"][first["id"]] = [
        {"args": [2, 3], "expected": 16, "reviewer": "fixture", "basis": "fixture contract"},
        {"args": [-3, 11], "expected": -19683, "reviewer": "fixture", "basis": "fixture contract"},
    ]
    d.notions_path.write_text(json.dumps(saved))
    query = finding(d, "ref", "target")["plan"]["next_query"]
    assert query["reason"] == "model_unknown" and query["args"] == [4, 2]
    store.answer(first["id"], args=query["args"], expected=4 ** 16,
                 reviewer="fixture", basis="fixture contract")
    assert finding(d, "ref", "target")["status"] == "truncated_search"
    assert d._sense_failing_workspace_tests() == []
    assert not any(step.get("accepted_into_world") for step in board(root, workspace))
    assert module.read_text() == source and not list(workspace.rglob("test_*.py"))


def test_feedback_cli_accepts_explicit_exception_outcome(tmp_path, capsys):
    _, _, _, d, fid = _prior_numeric_feedback(tmp_path)
    query = finding(d, "unit", "combine")["plan"]["next_query"]
    rc = feedback_cli(["--store", str(d.notions_path), "answer", fid, "--args", json.dumps(query["args"]),
                       "--expected", '{"raises":"ZeroDivisionError"}', "--reviewer", "fixture",
                       "--basis", "fixture contract"])
    assert rc == 0 and json.loads(capsys.readouterr().out)["expected"] == {"raises": "ZeroDivisionError"}
    assert NotionStore(d.notions_path).examples[fid][-1]["expected"] == {"raises": "ZeroDivisionError"}


@pytest.mark.parametrize("answer", [
    None, True, "ZeroDivisionError", {"raises": "ValueError"},
    {"raises": "__import__('os').getpid()"}, {"raises": "ZeroDivisionError", "extra": 1},
    {"raises": ["ZeroDivisionError"]}, {"raises": ""},
])
def test_unmodeled_or_malformed_outcomes_cannot_enter_feedback(tmp_path, answer):
    _, workspace, module, d, fid = _prior_numeric_feedback(tmp_path)
    query = finding(d, "unit", "combine")["plan"]["next_query"]
    store = NotionStore(d.notions_path)
    with pytest.raises(ValueError):
        store.answer(fid, args=query["args"], expected=answer, reviewer="fixture", basis="fixture")
    assert len(NotionStore(d.notions_path).examples[fid]) == 2
    assert module.read_text() == SOURCE and not list(workspace.rglob("test_*.py"))
    assert not validate_external_examples([{"args": query["args"], "expected": answer}], 2)[0]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_exception_evidence_must_match_before_operator_learning(tmp_path):
    _, workspace, module, d, fid = _prior_numeric_feedback(tmp_path)
    query = finding(d, "unit", "combine")["plan"]["next_query"]
    store = NotionStore(d.notions_path)
    store.answer(fid, args=query["args"], expected={"raises": "ZeroDivisionError"},
                 reviewer="fixture", basis="fixture contract")
    assert finding(d, "unit", "combine")["status"] == "bounded_agreement"
    assert d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_text().splitlines()[0][len("# brain-notion-v1 "):])
    # This source matches the two older numeric answers but not the exception.
    wrong = SOURCE.replace("return a + b", "return a * b / b")
    module.write_text(wrong)
    result = store.record_checked_repair(binding, wrong, workspace_root=workspace, test_file=test)
    assert result["status"] == "feedback_mismatch" and store.learned_operators() == []


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_direct_learning_rejects_an_out_of_consensus_candidate_but_still_cannot_prove_publication(tmp_path):
    _, workspace, module, d, fid = _prior_numeric_feedback(tmp_path)
    query = finding(d, "unit", "combine")["plan"]["next_query"]
    store = NotionStore(d.notions_path)
    store.answer(fid, args=query["args"], expected=0, reviewer="fixture", basis="fixture contract")
    assert finding(d, "unit", "combine")["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_text().splitlines()[0][len("# brain-notion-v1 "):])
    wrong = SOURCE.replace("return a + b", "return a + 0 * b")
    module.write_text(wrong)  # a direct write, not a board publication
    result = store.record_checked_repair(binding, wrong, workspace_root=workspace, test_file=test)
    assert result["status"] == "candidate_outcome_mismatch" and store.learned_operators() == []
    # Consistency still cannot authenticate provenance: a matching direct write
    # can create proposal experience without any board or independent verifier.
    matching = SOURCE.replace("return a + b", "return a * b / b")
    module.write_text(matching)
    result = store.record_checked_repair(binding, matching, workspace_root=workspace, test_file=test)
    assert result["status"] == "recorded_for_proposals" and result["operators"] == ["Div", "Mult"]
    assert store.experiences[fid]["observation"] == "workspace_matches_reviewed_examples_publication_not_authenticated"


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_old_origin_without_outcome_reference_cannot_create_new_experience(tmp_path):
    _, workspace, module, d, fid = _prior_numeric_feedback(tmp_path)
    query = finding(d, "unit", "combine")["plan"]["next_query"]
    store = NotionStore(d.notions_path)
    store.answer(fid, args=query["args"], expected=0, reviewer="fixture", basis="fixture contract")
    assert finding(d, "unit", "combine")["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_text().splitlines()[0][len("# brain-notion-v1 "):])
    saved = json.loads(d.notions_path.read_text())
    key = NotionStore._authored_test_key(workspace, "tests/test_example.py")
    saved["authored_tests"][key].pop("outcome_reference")
    d.notions_path.write_text(json.dumps(saved))
    matching = SOURCE.replace("return a + b", "return a * b / b")
    module.write_text(matching)
    result = store.record_checked_repair(binding, matching, workspace_root=workspace, test_file=test)
    assert result["status"] == "outcome_evidence_missing"
    assert store.learned_operators() == []


@pytest.mark.parametrize("legacy", [True, False], ids=["old-plan", "forged-current-plan"])
@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_stale_or_forged_plan_cannot_author_or_publish_without_replanning(tmp_path, legacy):
    root, workspace, module, d, fid = _prior_numeric_feedback(tmp_path)
    store = NotionStore(d.notions_path)
    feedback_hash = store._feedback_hash(store.reviews[fid], store.examples[fid])
    f = store.findings[fid]
    binding = {"module": f["module"], "source_sha256": f["source_sha256"], "target": "combine",
               "reference": "unit", "finding_id": fid, "feedback_sha256": feedback_hash}
    plan = {"status": "bounded_agreement", "external_examples": 2, "truncated": False,
            "outcome_model_version": OUTCOME_MODEL_VERSION}
    assert store.record_plan(fid, plan, expected_feedback_hash=feedback_hash)
    test = workspace / "tests" / "test_example.py"
    # A version string is not enough: rerunning the planner finds the missing query.
    assert not store.author_reviewed_test(binding, workspace, test)
    # Reconstruct a test/origin pair the older implementation could have left.
    text = store.render_reviewed_test(binding)
    key = store._authored_test_key(workspace, "tests/test_example.py")
    saved = json.loads(d.notions_path.read_text())
    saved["authored_tests"][key] = {"binding": binding, "test_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                     "non_target_sha256": target_expression_scope_sha256(SOURCE, "combine")}
    if legacy:
        saved["plans"][fid].pop("outcome_model_version")
    d.notions_path.write_text(json.dumps(saved))
    test.parent.mkdir()
    test.write_text(text)
    (test.parent / ".test_example.py.brain-origin").write_text("brain-generated-test-v1\n")
    store = NotionStore(d.notions_path)
    with store.hold_reviewed_feedback(binding) as valid:
        assert not valid  # workspace evidence is mandatory
    with store.hold_reviewed_feedback(binding, workspace_root=workspace) as valid:
        assert not valid
    steps = board(root, workspace)
    assert steps and not any(s.get("accepted_into_world") for s in steps)
    assert any(s.get("blocked") == "NOTION_FEEDBACK_STALE" for s in steps)
    assert module.read_text() == SOURCE
    replanned = finding(d, "unit", "combine")
    assert replanned["status"] == "needs_example"
    assert replanned["plan"]["next_query"]["exception_predictions"] == ["ZeroDivisionError"]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_legacy_test_with_unchanged_sufficient_feedback_can_be_requalified_at_publication_gate(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    before_test = test.read_bytes()
    saved = json.loads(d.notions_path.read_text())
    saved["plans"][f["id"]].pop("outcome_model_version")
    d.notions_path.write_text(json.dumps(saved))
    candidate = TRAIN.replace("return x * y", "return x + y")
    args = (workspace, test, {"pkg/example.py": candidate})
    opts = {"notions_path": d.notions_path}
    assert _publish_notion_candidate(*args, **opts)[2] == "NOTION_FEEDBACK_STALE"
    refreshed = finding(d, "narrow", "pair")
    assert refreshed["status"] == "bounded_agreement" and test.read_bytes() == before_test
    published, probe, reason = _publish_notion_candidate(*args, **opts)
    assert published and probe["generalizes"] and reason is None
    assert module.read_text() == candidate


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_new_real_experience_can_invalidate_an_old_plan_under_the_search_budget(tmp_path):
    root, trained, _ = train_once(tmp_path / "learn_add")
    assert NotionStore(trained.notions_path).learned_operators() == ["Add"]
    source = "def ref(z):\n    return 5*z\n\ndef target(a,b):\n    return a*b\n"
    workspace = tmp_path / "pending"
    module = make_workspace(workspace, source)
    d = daemon(workspace, root)
    original, _ = provide_feedback(d, "ref", "target", lambda v: 3 * v[0] + 2 * v[1])
    assert original["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_text().splitlines()[0][len("# brain-notion-v1 "):])
    with NotionStore(d.notions_path).hold_reviewed_feedback(binding, workspace_root=workspace) as valid:
        assert valid

    # The same creature actually learns another operator on a separate reviewed
    # board repair; no manually inserted operator or change of program code.
    product_ws = tmp_path / "product_training"
    product_source = "def square(s):\n    return s * s\n\ndef wider(a,b):\n    return a - b\n"
    make_workspace(product_ws, product_source)
    other = daemon(product_ws, root)
    product, _ = provide_feedback(other, "square", "wider", lambda v: v[0] * v[1])
    assert product["status"] == "bounded_agreement"
    steps = board(root, product_ws)
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] and
               (s.get("structure_learning") or {}).get("operators") == ["Mult"] for s in steps)
    store = NotionStore(d.notions_path)
    assert store.learned_operators() == ["Add", "Mult"]
    assert store.plans[original["id"]]["status"] == "bounded_agreement"  # old cached plan
    with store.hold_reviewed_feedback(binding, workspace_root=workspace) as valid:
        assert not valid
    candidate = source.replace("return a*b", "return a + (a + (a + (b + b)))")
    published, _, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not published and reason == "NOTION_FEEDBACK_STALE" and module.read_text() == source
    refreshed = finding(d, "ref", "target")
    assert refreshed["status"] == "truncated_search" and refreshed["plan"]["truncated"]


def test_exception_aware_semantic_compression_matches_exhaustive_small_grammar():
    target = function_models("def f(a,b):\n    return a+b\n")["f"]
    operators = ["Mod", "Sub"]
    constraints = [((2, 2), {"raises": "ZeroDivisionError"}), ((2, 3), -2)]
    compressed, truncated, search = _semantic_compositions(target, constraints, operators, limit=256)
    assert not truncated and search["learned_binary_nodes_explored"] == 3
    points = list(itertools.product((2, 3, 4, 5, 6, 7), repeat=2))
    points += list(itertools.product((-3, 0, 11), repeat=2))

    def vector(expression):
        outputs = []
        for point in points:
            kind, value = evaluate_outcome(expression, dict(zip(target.params, point)))
            if kind == "value":
                value = (type(value).__name__, value.hex() if type(value) is float else value)
            outputs.append((kind, value))
        return tuple(outputs)

    earliest = {}
    leaves = (ast.Name(id=p, ctx=ast.Load()) for p in target.params)
    syntax = itertools.chain(leaves, _learned_compositions(target.params, operators, max_nodes=3))
    for expression in syntax:
        depth = sum(isinstance(node, ast.BinOp) for node in ast.walk(expression))
        earliest.setdefault(vector(expression), (depth, expression))
    expected = {sig for sig, (depth, expression) in earliest.items() if depth == 3 and all(
        matches_expected(evaluate_outcome(expression, dict(zip(target.params, args))), value) is True
        for args, value in constraints)}
    assert len(expected) == 6
    assert {vector(expression) for expression in compressed} == expected
