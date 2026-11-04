"""Experience-guided questions, explicit labels, and safe test refresh controls.

Fixture answers, origins, and holdouts are caller-supplied and unauthenticated;
these are bounded behavior tests, not independent verification of intent.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime.creature_runtime_v1 import _publish_notion_candidate
from canonical.runtime.memory_policy_v1 import OFF, READ_ONLY, memory_policy_scope
from canonical.swe_kernel.expression_hypotheses_v1 import (
    MAX_EXTERNAL_EXAMPLES, OUTCOME_MODEL_VERSION, investigate, validate_transferred_inputs,
)
from canonical.swe_kernel.notion_feedback_cli_v1 import main as feedback_cli
from canonical.swe_kernel.notions_v1 import NotionStore, notions_for_source
from canonical.tests.test_adaptive_counterexample_search_v1 import QUADRUPLE
from canonical.tests.test_experience_composition_v1 import (
    TRAIN, board, daemon, finding, load_function, make_workspace, provide_feedback, train_once,
)


SECOND_ADD = "def repeat(s):\n    return s + s\n\ndef duo(a,b):\n    return a * b\n"


def _transfer_fixture(tmp_path, oracle, *, author_before=False, extras=((101, 2),)):
    root, trained, _ = train_once(tmp_path / "learn_add")
    workspace = tmp_path / "pending"
    module = make_workspace(workspace, QUADRUPLE)
    d = daemon(workspace, root)
    original, answers = provide_feedback(d, "ref", "target", oracle)
    assert original["status"] == "bounded_agreement"
    old_store = NotionStore(d.notions_path)
    old_examples = old_store.examples[original["id"]]
    old_review = old_store.reviews[original["id"]]
    test = workspace / "tests" / "test_example.py"
    old_test = old_binding = None
    if author_before:
        assert d._sense_failing_workspace_tests()
        old_test = test.read_bytes()
        old_binding = json.loads(old_test.splitlines()[0][len(b"# brain-notion-v1 "):])
    training_workspace = tmp_path / "another_repair"
    make_workspace(training_workspace, SECOND_ADD)
    trainer = daemon(training_workspace, root)
    train_finding, _ = provide_feedback(trainer, "repeat", "duo", sum)
    assert train_finding["status"] == "bounded_agreement"
    for args in extras:
        NotionStore(trainer.notions_path).provide_example(
            train_finding["id"], args=list(args), expected=sum(args), reviewer="fixture", basis="fixture contract")
    assert finding(trainer, "repeat", "duo")["status"] == "bounded_agreement"
    accepted = next((s for s in board(root, training_workspace) if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted is not None and accepted["structure_learning"]["operators"] == ["Add"]
    current = NotionStore(d.notions_path)
    assert current.learned_operators() == ["Add"]  # same operator set before and after
    assert current.examples[original["id"]] == old_examples and current.reviews[original["id"]] == old_review
    return root, workspace, module, d, original, answers, test, old_test, old_binding, trainer, train_finding


def _binding_with_current_feedback(store, old_binding):
    store.load()
    fid = old_binding["finding_id"]
    return {**old_binding, "feedback_sha256": store._feedback_hash(store.reviews[fid], store.examples[fid])}


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_prior_input_reopens_an_unchanged_task_without_reusing_the_old_output(tmp_path):
    oracle = lambda a: 2 * a[0] + 2 * a[1] + (1 if max(a) >= 100 and a[0] != a[1] else 0)
    root, workspace, module, d, original, answers, test, _, _, _, _ = _transfer_fixture(tmp_path, oracle)
    store = NotionStore(d.notions_path)
    assert store.learned_challenge_inputs(original["id"], 2) == [[101, 2]]
    assert store.learned_challenge_inputs(original["id"], 3) == []
    before = [dict(row) for row in store.examples[original["id"]]]
    planned = finding(d, "ref", "target")
    query = planned["plan"]["next_query"]
    assert planned["status"] == "needs_example" and query["args"] == [101, 2]
    assert query["reason"] == "experience_validation" and query["input_origin"] == "experience"
    assert query["predictions"] == [206] and "expected" not in query
    assert planned["plan"]["search"]["domain_points"] == 46
    assert NotionStore(d.notions_path).examples[original["id"]] == before  # no automatic label
    assert d._sense_failing_workspace_tests() == [] and not test.exists()
    assert module.read_text() == QUADRUPLE
    # The previous task's answer was 103; only this task's explicit 207 is used.
    store.answer(original["id"], args=query["args"], expected=207,
                 reviewer="fixture", basis="threshold fixture")
    after = finding(d, "ref", "target")
    assert after["status"] == "no_candidates" and after["plan"]["external_examples"] == 3
    assert d._sense_failing_workspace_tests() == []
    assert not any(step.get("accepted_into_world") for step in board(root, workspace))
    assert module.read_text() == QUADRUPLE and not test.exists()
    assert [101, 2] not in answers


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_answered_transfer_refreshes_only_the_unchanged_generated_test_then_board_repairs(tmp_path):
    oracle = lambda a: 2 * sum(a)
    root, workspace, module, d, original, answers, test, old_test, old_binding, _, _ = _transfer_fixture(
        tmp_path, oracle, author_before=True)
    sidecar = test.with_name("." + test.name + ".brain-origin")
    old_sidecar = sidecar.read_bytes()
    candidate = QUADRUPLE.replace("return a*b", "return a + (a + (b + b))")
    store = NotionStore(d.notions_path)
    assert store.plans[original["id"]]["status"] == "bounded_agreement"  # old cached plan
    with store.hold_reviewed_feedback(old_binding, workspace_root=workspace) as valid:
        assert not valid
    published, _, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not published and reason == "NOTION_FEEDBACK_STALE" and module.read_text() == QUADRUPLE
    query = finding(d, "ref", "target")["plan"]["next_query"]
    assert query["args"] == [101, 2] and query["predictions"] == [206]
    store.answer(original["id"], args=query["args"], expected=206,
                 reviewer="fixture", basis="linear fixture")
    assert finding(d, "ref", "target")["status"] == "bounded_agreement"
    # No manual test edit or refresh: the board's unscoped sensor refreshes it.
    accepted = next((s for s in board(root, workspace) if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted is not None and accepted["verified"] is False and accepted["correct"] is None
    assert accepted["structure_learning"]["status"] == "recorded_for_proposals"
    new_test = test.read_bytes()
    new_binding = json.loads(new_test.splitlines()[0][len(b"# brain-notion-v1 "):])
    assert new_test != old_test and new_binding["feedback_sha256"] != old_binding["feedback_sha256"]
    assert b"target(101, 2) == 206" in new_test and sidecar.read_bytes() == old_sidecar
    origin = NotionStore(d.notions_path).authored_tests[NotionStore._authored_test_key(workspace, "tests/test_example.py")]
    assert origin["binding"] == new_binding and origin["test_sha256"] == hashlib.sha256(new_test).hexdigest()
    fn = load_function(module, "target")
    for args in ((8, 3), (-2, 7), (0, 10)):
        assert list(args) not in answers and list(args) != query["args"]
        assert fn(*args) == oracle(args)


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_finite_transferred_points_do_not_prove_a_distant_threshold_fixture(tmp_path):
    oracle = lambda a: 2 * sum(a) + (1 if max(a) >= 1000 and a[0] != a[1] else 0)
    root, workspace, module, d, original, answers, test, _, _, _, _ = _transfer_fixture(
        tmp_path, oracle, author_before=True)
    query = finding(d, "ref", "target")["plan"]["next_query"]
    assert query["args"] == [101, 2] and query["input_origin"] == "experience"
    NotionStore(d.notions_path).answer(original["id"], args=query["args"], expected=oracle(query["args"]),
                                     reviewer="fixture", basis="threshold fixture")
    assert finding(d, "ref", "target")["status"] == "bounded_agreement"
    accepted = next((s for s in board(root, workspace) if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted is not None and accepted["verified"] is False and accepted["correct"] is None
    held_out = (1001, 2)
    assert list(held_out) not in answers and list(held_out) != query["args"]
    assert load_function(module, "target")(*held_out) == 2006
    assert oracle(held_out) == 2007  # a real remaining false acceptance, not a correctness claim
    assert test.exists()


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_new_experience_between_publication_and_recording_blocks_unanswered_learning(tmp_path):
    root, _, _ = train_once(tmp_path / "learn_add")
    workspace = tmp_path / "pending"
    module = make_workspace(workspace, QUADRUPLE)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "ref", "target", lambda a: 2 * sum(a))
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_bytes().splitlines()[0][len(b"# brain-notion-v1 "):])
    candidate = QUADRUPLE.replace("return a*b", "return a + (a + (b + b))")
    published, _, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert published and reason is None and module.read_text() == candidate
    assert f["id"] not in NotionStore(d.notions_path).experiences
    other_ws = tmp_path / "other"
    make_workspace(other_ws, SECOND_ADD)
    other = daemon(other_ws, root)
    other_f, _ = provide_feedback(other, "repeat", "duo", sum)
    NotionStore(other.notions_path).provide_example(other_f["id"], args=[101, 2], expected=103,
                                                   reviewer="fixture", basis="fixture")
    assert finding(other, "repeat", "duo")["status"] == "bounded_agreement"
    assert any(s.get("accepted_into_world") for s in board(root, other_ws))
    store = NotionStore(d.notions_path)
    result = store.record_checked_repair(binding, candidate, workspace_root=workspace, test_file=test)
    assert result["status"] == "experience_validation_pending" and result["operators"] == []
    assert f["id"] not in NotionStore(d.notions_path).experiences


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_real_experience_can_make_a_task_unanswerable_under_the_model_budget(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "pending"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    original, answers = provide_feedback(d, "narrow", "pair", sum)
    assert original["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    binding = json.loads(test.read_bytes().splitlines()[0][len(b"# brain-notion-v1 "):])
    training = tmp_path / "subtract"
    make_workspace(training, "def subtract_self(q):\n    return q - q\n\ndef difference(a,b):\n    return a + b\n")
    trainer = daemon(training, root)
    f, _ = provide_feedback(trainer, "subtract_self", "difference", lambda a: a[0] - a[1])
    assert f["status"] == "bounded_agreement"
    NotionStore(trainer.notions_path).provide_example(
        f["id"], args=[1e20, 1e20], expected=0.0, reviewer="fixture", basis="subtraction fixture")
    assert finding(trainer, "subtract_self", "difference")["status"] == "bounded_agreement"
    assert any((s.get("structure_learning") or {}).get("operators") == ["Sub"] for s in board(root, training))
    store = NotionStore(d.notions_path)
    assert store.learned_challenge_inputs(original["id"], 2) == [[1e20, 1e20]]
    current = finding(d, "narrow", "pair")
    query = current["plan"]["next_query"]
    assert current["status"] == "needs_example" and query["reason"] == "model_unknown"
    assert query["input_origin"] == "experience" and query["unknown_models"] > 0 and query["predictions"] == []
    with pytest.raises(ValueError, match="supported external outcome"):
        store.answer(original["id"], args=query["args"], expected=2e20, reviewer="fixture", basis="sum fixture")
    candidate = TRAIN.replace("return x * y", "return x + y")
    published, _, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not published and reason == "NOTION_FEEDBACK_STALE" and module.read_text() == TRAIN
    # Revoking that prior review removes its proposal; it does not edit the pending feedback.
    store.review(f["id"], decision="reject", reviewer="fixture", basis="retracted")
    assert finding(d, "narrow", "pair")["status"] == "bounded_agreement"
    assert [row["args"] for row in NotionStore(d.notions_path).examples[original["id"]]] == answers
    with store.hold_reviewed_feedback(binding, workspace_root=workspace) as valid:
        assert valid


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_retracting_the_source_review_removes_the_transferred_question(tmp_path):
    root, workspace, module, d, original, _, test, _, _, trainer, train_finding = _transfer_fixture(
        tmp_path, lambda a: 2 * sum(a))
    assert finding(d, "ref", "target")["plan"]["next_query"]["args"] == [101, 2]
    NotionStore(trainer.notions_path).review(train_finding["id"], decision="reject",
                                             reviewer="fixture", basis="retracted")
    store = NotionStore(d.notions_path)
    assert store.learned_operators() == ["Add"]  # the separate first repair remains
    assert store.learned_challenge_inputs(original["id"], 2) == []
    current = finding(d, "ref", "target")
    assert current["status"] == "bounded_agreement" and current["plan"]["next_query"] is None
    assert module.read_text() == QUADRUPLE and not test.exists()


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_transferred_input_pool_is_bounded_and_respects_memory_policy(tmp_path):
    extras = ((20, 2), (30, 2), (40, 2), (50, 2), (60, 2))
    _, _, _, d, original, _, _, _, _, _, train_finding = _transfer_fixture(
        tmp_path, lambda a: 2 * sum(a), extras=extras)
    store = NotionStore(d.notions_path)
    selected = [[60, 2], [50, 2], [40, 2], [30, 2]]
    assert store.learned_challenge_inputs(original["id"], 2) == selected
    assert store.learned_challenge_inputs(train_finding["id"], 2) == []  # same source is not its own experience
    for args in selected:
        query = finding(d, "ref", "target")["plan"]["next_query"]
        assert query["args"] == args and query["input_origin"] == "experience"
        store.answer(original["id"], args=args, expected=2 * sum(args), reviewer="fixture", basis="fixture")
    assert finding(d, "ref", "target")["status"] == "bounded_agreement"
    with memory_policy_scope(READ_ONLY):
        assert store.learned_challenge_inputs(original["id"], 2) == [[60, 2], [50, 2], [40, 2], [30, 2]]
        with pytest.raises(PermissionError):
            store.provide_example(original["id"], args=[70, 2], expected=144, reviewer="fixture", basis="fixture")
    with memory_policy_scope(OFF):
        assert store.learned_challenge_inputs(original["id"], 2) == []


def test_explicit_additional_examples_are_validated_attributed_and_invalidate_plans(tmp_path, capsys):
    workspace, root = tmp_path / "workspace", tmp_path / "root"
    make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f = finding(d, "narrow", "pair")
    store = NotionStore(d.notions_path)
    with pytest.raises(ValueError):
        store.provide_example(f["id"], args=[101, 2], expected=103, reviewer="fixture", basis="fixture")
    store.review(f["id"], decision="confirm", reviewer="fixture", basis="fixture", trusted_function="narrow")
    assert finding(d, "narrow", "pair")["plan"]["next_query"] is not None
    row = store.provide_example(f["id"], args=[101, 2], expected=103, reviewer="fixture", basis="fixture")
    assert row["args"] == [101, 2] and f["id"] not in NotionStore(d.notions_path).plans
    invalid = [
        ([101], 1, "r", "b"), ([True, 2], 1, "r", "b"), ([float("nan"), 2], 1, "r", "b"),
        ([2 ** 81, 2], 1, "r", "b"), ([101, 2], 1, "r", "b"),
        ([102, 2], True, "r", "b"), ([102, 2], {"raises": "RuntimeError"}, "r", "b"),
        ([102, 2], 104, " ", "b"), ([102, 2], 104, "r", " "),
    ]
    for args, expected, reviewer, basis in invalid:
        with pytest.raises(ValueError):
            store.provide_example(f["id"], args=args, expected=expected, reviewer=reviewer, basis=basis)
    assert feedback_cli(["--store", str(d.notions_path), "example", f["id"], "--args", "[99, 0]",
                         "--expected", '{"raises":"ZeroDivisionError"}', "--reviewer", "fixture", "--basis", "contract"]) == 0
    assert json.loads(capsys.readouterr().out)["expected"] == {"raises": "ZeroDivisionError"}
    returned = store.provide_example(f["id"], args=[102, 0], expected={"raises": "OverflowError"},
                                     reviewer="fixture", basis="contract")
    returned["expected"]["raises"] = "ZeroDivisionError"
    assert NotionStore(d.notions_path).examples[f["id"]][-1]["expected"] == {"raises": "OverflowError"}


def test_transferred_input_validation_rejects_wrong_types_and_limits():
    valid, points = validate_transferred_inputs([[101, 2], [101.0, 2], [0.0, 2], [-0.0, 2]], 2)
    assert valid and len(points) == 4
    assert type(points[0][0]) is int and type(points[1][0]) is float
    assert points[2][0].hex() != points[3][0].hex()
    for bad in (None, [[True, 2]], [[float("inf"), 2]], [[2 ** 81, 2]], [[1]], [[1, 2]] * 5):
        assert validate_transferred_inputs(bad, 2) == (False, [])
    notion = notions_for_source(TRAIN, "pkg/example.py")[0].evaluate()
    plan = investigate(TRAIN, target_name="pair", reference_name="narrow", observations=notion["observations"],
                       examples=[], experience_inputs=[[True, 2]])
    assert plan["status"] == "invalid_experience_inputs" and plan["next_query"] is None


def test_extra_examples_follow_the_target_arity_when_the_wide_function_is_trusted(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f = finding(d, "narrow", "pair")
    # With the wide function as the reference, the target takes one argument.
    store = NotionStore(d.notions_path)
    store.review(f["id"], decision="confirm", reviewer="fixture", basis="wide reference", trusted_function="pair")
    for _ in range(6):
        current = finding(d, "narrow", "pair")
        query = current["plan"].get("next_query")
        if query is None:
            break
        assert len(query["args"]) == 1
        store.answer(f["id"], args=query["args"], expected=query["args"][0] ** 2,
                     reviewer="fixture", basis="fixture")
    assert current["status"] == "bounded_agreement"
    with pytest.raises(ValueError):
        store.provide_example(f["id"], args=[101, 2], expected=10201, reviewer="fixture", basis="fixture")
    store.provide_example(f["id"], args=[101], expected=10201, reviewer="fixture", basis="fixture")
    assert finding(d, "narrow", "pair")["status"] == "bounded_agreement"


def test_extra_examples_are_attributed_bounded_and_may_describe_exceptions(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    store = NotionStore(d.notions_path)
    example = store.provide_example(f["id"], args=[0, 11], expected={"raises": "ZeroDivisionError"},
                                    reviewer="reviewer", basis="caller fixture")
    assert example["expected"] == {"raises": "ZeroDivisionError"}
    example["expected"]["raises"] = "OverflowError"
    assert NotionStore(d.notions_path).examples[f["id"]][-1]["expected"] == {"raises": "ZeroDivisionError"}
    for args, expected in [([1], 1), ([True, 1], 2), ([1, 2], {"raises": "RuntimeError"})]:
        with pytest.raises(ValueError):
            store.provide_example(f["id"], args=args, expected=expected, reviewer="reviewer", basis="fixture")


def test_example_budget_is_enforced_for_explicit_and_active_answers(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    store = NotionStore(d.notions_path)
    # Seed a near-full attributed store to exercise the limit without 253 filesystem writes.
    rows = list(store.examples[f["id"]])
    rows.extend({"args": [1000 + i, 1], "expected": 1001 + i, "reviewer": "fixture", "basis": "fixture"}
                for i in range(MAX_EXTERNAL_EXAMPLES - len(rows) - 1))
    store.examples[f["id"]] = rows
    store.save()
    store.provide_example(f["id"], args=[9999, 1], expected=10000, reviewer="fixture", basis="fixture")
    assert len(NotionStore(d.notions_path).examples[f["id"]]) == MAX_EXTERNAL_EXAMPLES
    with pytest.raises(ValueError, match="budget"):
        store.provide_example(f["id"], args=[8888, 1], expected=8889, reviewer="fixture", basis="fixture")
    notion = notions_for_source(TRAIN, "pkg/example.py")[0].evaluate()
    full = NotionStore(d.notions_path).examples[f["id"]]
    plan = investigate(TRAIN, target_name="pair", reference_name="narrow", observations=notion["observations"],
                       examples=full, experience_inputs=[[8888, 1]])
    assert plan["status"] == "example_budget_exhausted" and plan["truncated"]
    assert plan["next_query"]["args"] == [8888, 1] and "budget" in plan["reason"]
    assert store.record_plan(f["id"], plan)
    with pytest.raises(ValueError):
        store.answer(f["id"], args=[8888, 1], expected=8889, reviewer="fixture", basis="fixture")
    # Even a forged stale plan marked as active cannot push stored examples past the cap.
    assert store.record_plan(f["id"], {**plan, "status": "needs_example"})
    before = d.notions_path.read_bytes()
    with pytest.raises(ValueError, match="budget"):
        store.answer(f["id"], args=[8888, 1], expected=8889, reviewer="fixture", basis="fixture")
    assert d.notions_path.read_bytes() == before


@pytest.mark.parametrize("first, second", [([2, 3], [2.0, 3.0]), ([0, 3], [-0.0, 3.0])])
def test_typed_aliases_are_constraints_but_not_two_distinct_example_locations(tmp_path, first, second):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f = finding(d, "narrow", "pair")
    store = NotionStore(d.notions_path)
    store.review(f["id"], decision="confirm", reviewer="fixture", basis="fixture", trusted_function="narrow")
    for args in (first, second):
        store.provide_example(f["id"], args=args, expected=sum(args), reviewer="fixture", basis="fixture")
    current = finding(d, "narrow", "pair")
    plan = current["plan"]
    assert plan["external_examples"] == 2 and plan["distinct_numeric_example_inputs"] == 1
    assert current["status"] == "needs_example" and plan["next_query"]["reason"] == "independent_validation"
    assert tuple(plan["next_query"]["args"]) != tuple(first)
    store.load()
    feedback_hash = store._feedback_hash(store.reviews[f["id"]], store.examples[f["id"]])
    forged = {**plan, "status": "bounded_agreement", "truncated": False,
              "outcome_model_version": OUTCOME_MODEL_VERSION}
    assert store.record_plan(f["id"], forged, expected_feedback_hash=feedback_hash)
    binding = {"module": f["module"], "source_sha256": f["source_sha256"], "target": "pair",
               "reference": "narrow", "finding_id": f["id"], "feedback_sha256": feedback_hash}
    test = workspace / "tests" / "test_example.py"
    assert not store.author_reviewed_test(binding, workspace, test) and not test.exists()
    # A forged experience bound to those same aliases cannot supply operators.
    store.load()
    store.experiences[f["id"]] = {"source_sha256": f["source_sha256"], "target": "pair", "reference": "narrow",
                                   "feedback_sha256": feedback_hash, "operators": ["Add"]}
    store.save()
    assert NotionStore(d.notions_path).learned_operators() == []


def test_plan_updates_preserve_typed_and_signed_zero_query_coordinates(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f = finding(d, "narrow", "pair")
    store = NotionStore(d.notions_path)
    for first in (0, 0.0, -0.0):
        plan = {"status": "needs_example", "next_query": {"args": [first, 2]}}
        assert store.record_plan(f["id"], plan)
        saved = NotionStore(d.notions_path).plans[f["id"]]["next_query"]["args"][0]
        assert type(saved) is type(first)
        if type(first) is float:
            assert saved.hex() == first.hex()


def test_float_challenge_is_not_suppressed_by_an_equal_integer_example():
    source = "def ref(q):\n    return (q + q) - q\n\ndef target(a,b):\n    return a * b\n"
    notion = notions_for_source(source, "pkg/example.py")[0].evaluate()
    assert notion["fired"]
    examples = [{"args": [2, 3], "expected": 3}, {"args": [-3, 11], "expected": 11},
                {"args": [10 ** 16, 1], "expected": 1}]
    plan = investigate(source, target_name="target", reference_name="ref", observations=notion["observations"],
                       examples=examples, experience_inputs=[[1e16, 1.0]])
    query = plan["next_query"]
    assert plan["status"] == "needs_example" and query["input_origin"] == "experience"
    assert query["reason"] == "models_disagree" and set(query["predictions"]) == {0.0, 1.0}
    assert (1e16 + 1.0) - 1e16 == 0.0 and (1.0 + 1.0) - 1.0 == 1.0


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_exception_from_real_experience_transfers_only_the_input(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "division"
    source = "def unit(x):\n    return x / x\n\ndef quotient(a, b):\n    return a + b\n"
    make_workspace(workspace, source)
    trainer = daemon(workspace, root)
    oracle = lambda args: {"raises": "ZeroDivisionError"} if args[1] == 0 else args[0] / args[1]
    f, _ = provide_feedback(trainer, "unit", "quotient", oracle)
    assert f["status"] == "bounded_agreement"
    NotionStore(trainer.notions_path).provide_example(
        f["id"], args=[101, 0], expected={"raises": "ZeroDivisionError"}, reviewer="fixture", basis="fixture")
    assert finding(trainer, "unit", "quotient")["status"] == "bounded_agreement"
    assert any((s.get("structure_learning") or {}).get("operators") == ["Div"] for s in board(root, workspace))
    pending = tmp_path / "sum"
    module = make_workspace(pending, TRAIN)
    d = daemon(pending, root)
    current = finding(d, "narrow", "pair")
    store = NotionStore(d.notions_path)
    store.review(current["id"], decision="confirm", reviewer="fixture", basis="fixture", trusted_function="narrow")
    for _ in range(6):
        current = finding(d, "narrow", "pair")
        query = current["plan"]["next_query"]
        assert query is not None
        if query["input_origin"] == "experience":
            break
        store.answer(current["id"], args=query["args"], expected=sum(query["args"]),
                     reviewer="fixture", basis="sum fixture")
    else:
        pytest.fail("experience input was never proposed")
    assert query["args"] == [101, 0] and query["predictions"] == [101]
    assert "expected" not in query and all(row["args"] != [101, 0]
                                          for row in NotionStore(d.notions_path).examples[current["id"]])
    assert module.read_text() == TRAIN  # the old exception is not used as a label
    store.answer(current["id"], args=query["args"], expected=101, reviewer="fixture", basis="sum fixture")
    assert finding(d, "narrow", "pair")["status"] == "bounded_agreement"
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in board(root, pending))


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_typed_point_from_real_experience_needs_a_matching_typed_answer(tmp_path):
    _, _, _, d, original, _, _, _, _, _, _ = _transfer_fixture(
        tmp_path, lambda a: 2 * sum(a), extras=((2.0, 3.0),))
    store = NotionStore(d.notions_path)
    points = store.learned_challenge_inputs(original["id"], 2)
    assert len(points) == 1 and all(type(x) is float for x in points[0])
    query = finding(d, "ref", "target")["plan"]["next_query"]
    assert query["args"] == [2.0, 3.0] and all(type(x) is float for x in query["args"])
    assert query["input_origin"] == "experience"
    with pytest.raises(ValueError, match="active, reviewed query"):
        store.answer(original["id"], args=[2, 3], expected=10, reviewer="fixture", basis="fixture")
    store.answer(original["id"], args=[2.0, 3.0], expected=10.0, reviewer="fixture", basis="fixture")
    assert finding(d, "ref", "target")["status"] == "bounded_agreement"
    rows = NotionStore(d.notions_path).examples[original["id"]]
    assert any(row["args"] == [2, 3] and type(row["args"][0]) is int for row in rows)
    assert any(row["args"] == [2.0, 3.0] and type(row["args"][0]) is float for row in rows)


def test_transferred_input_with_unknown_outcomes_never_authorizes_agreement():
    notion = notions_for_source(TRAIN, "pkg/example.py")[0].evaluate()
    examples = [{"args": [2, 3], "expected": 5}, {"args": [-3, 11], "expected": 8}]
    large = [[1e20, 1e20]]
    plan = investigate(TRAIN, target_name="pair", reference_name="narrow", observations=notion["observations"],
                       examples=examples, experience_inputs=large)
    query = plan["next_query"]
    assert plan["status"] == "needs_example" and query["input_origin"] == "experience"
    assert query["reason"] == "model_unknown" and query["unknown_models"] > 0
    assert query["predictions"] == [] and query["exception_predictions"] == []
    examples.append({"args": large[0], "expected": 0})
    after = investigate(TRAIN, target_name="pair", reference_name="narrow", observations=notion["observations"],
                        examples=examples, experience_inputs=large)
    assert after["status"] == "truncated_search" and after["truncated"]
    assert after["search"]["reason"] == "candidate_evaluation_unknown"


def _refresh_fixture(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    old = test.read_bytes()
    binding = json.loads(old.splitlines()[0][len(b"# brain-notion-v1 "):])
    store = NotionStore(d.notions_path)
    store.provide_example(f["id"], args=[101, 2], expected=103, reviewer="fixture", basis="fixture")
    assert finding(d, "narrow", "pair")["status"] == "bounded_agreement"
    return root, workspace, module, d, f, test, old, binding


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("tampering", ["edited-test", "missing-sidecar", "changed-sidecar", "symlink-sidecar",
                                       "unregistered", "ordinary-test", "changed-source", "bad-scope", "edited-header"])
def test_refresh_refuses_changed_or_unregistered_test_evidence(tmp_path, tampering):
    _, workspace, module, d, _, test, old, old_binding = _refresh_fixture(tmp_path)
    sidecar = test.with_name("." + test.name + ".brain-origin")
    key = NotionStore._authored_test_key(workspace, "tests/test_example.py")
    data = json.loads(d.notions_path.read_text())
    if tampering == "edited-test":
        test.write_bytes(old + b"\n# user edit\n")
    elif tampering == "missing-sidecar":
        sidecar.unlink()
    elif tampering == "changed-sidecar":
        sidecar.write_text("different marker\n")
    elif tampering == "symlink-sidecar":
        sidecar.unlink()
        marker = test.parent / "marker-copy"
        marker.write_bytes(b"brain-generated-test-v1\n")
        sidecar.symlink_to(marker.name)
    elif tampering == "unregistered":
        data["authored_tests"].pop(key)
        d.notions_path.write_text(json.dumps(data))
    elif tampering == "ordinary-test":
        data["authored_tests"].pop(key)
        d.notions_path.write_text(json.dumps(data))
        sidecar.unlink()
        test.write_text("def test_owned_by_user():\n    assert 2 + 2 == 4\n")
    elif tampering == "changed-source":
        module.write_text(TRAIN + "\n# a different source outside the target\n")
    elif tampering == "bad-scope":
        data["authored_tests"][key]["non_target_sha256"] = "0" * 64
        d.notions_path.write_text(json.dumps(data))
    elif tampering == "edited-header":
        test.write_bytes(old.split(b"\n", 1)[1])
        data["authored_tests"][key]["test_sha256"] = hashlib.sha256(test.read_bytes()).hexdigest()
        d.notions_path.write_text(json.dumps(data))
    store = NotionStore(d.notions_path)
    binding = _binding_with_current_feedback(store, old_binding)
    before_test, before_store, before_source = test.read_bytes(), d.notions_path.read_bytes(), module.read_bytes()
    before_sidecar = ("link", sidecar.readlink()) if sidecar.is_symlink() else (
        ("file", sidecar.read_bytes()) if sidecar.exists() else None)
    assert not store.author_reviewed_test(binding, workspace, test)
    assert test.read_bytes() == before_test and d.notions_path.read_bytes() == before_store
    assert module.read_bytes() == before_source
    if before_sidecar is None:
        assert not sidecar.exists() and not sidecar.is_symlink()
    elif before_sidecar[0] == "link":
        assert sidecar.is_symlink() and sidecar.readlink() == before_sidecar[1]
    else:
        assert not sidecar.is_symlink() and sidecar.read_bytes() == before_sidecar[1]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_contradictory_new_feedback_neither_refreshes_nor_publishes_the_old_test(tmp_path):
    root, workspace = tmp_path / "root", tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    old = test.read_bytes()
    binding = json.loads(old.splitlines()[0][len(b"# brain-notion-v1 "):])
    store = NotionStore(d.notions_path)
    store.provide_example(f["id"], args=[101, 2], expected=104, reviewer="fixture", basis="counterexample")
    assert finding(d, "narrow", "pair")["status"] == "no_candidates"
    new_binding = _binding_with_current_feedback(store, binding)
    assert not store.author_reviewed_test(new_binding, workspace, test)
    d._sense_failing_workspace_tests()
    assert test.read_bytes() == old and module.read_text() == TRAIN
    candidate = TRAIN.replace("return x * y", "return x + y")
    published, _, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not published and reason == "NOTION_FEEDBACK_STALE" and module.read_text() == TRAIN


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_test_refresh_respects_memory_policy_and_is_not_triggered_by_scoped_sensing(tmp_path):
    _, workspace, module, d, _, test, old, old_binding = _refresh_fixture(tmp_path)
    store = NotionStore(d.notions_path)
    binding = _binding_with_current_feedback(store, old_binding)
    for policy in (READ_ONLY, OFF):
        with memory_policy_scope(policy):
            assert not store.author_reviewed_test(binding, workspace, test)
            d._sense_failing_workspace_tests()
            assert test.read_bytes() == old and module.read_text() == TRAIN
    # A scoped scan does not implicitly refresh even a safely refreshable test.
    d._sense_failing_workspace_tests(within=["tests/test_example.py"])
    assert test.read_bytes() == old
    d._sense_failing_workspace_tests()
    assert test.read_bytes() != old and module.read_text() == TRAIN


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_interrupted_refresh_leaves_a_mismatch_that_cannot_publish(tmp_path):
    _, workspace, module, d, _, test, old, old_binding = _refresh_fixture(tmp_path)
    store = NotionStore(d.notions_path)
    binding = _binding_with_current_feedback(store, old_binding)
    old_mode = test.parent.stat().st_mode & 0o777
    test.parent.chmod(0o555)
    try:
        with pytest.raises(PermissionError):
            store.author_reviewed_test(binding, workspace, test)
    finally:
        test.parent.chmod(old_mode)
    assert test.read_bytes() == old and module.read_text() == TRAIN
    current = NotionStore(d.notions_path).authored_test_binding(workspace, "tests/test_example.py")
    assert current == binding and current != old_binding
    candidate = TRAIN.replace("return x * y", "return x + y")
    published, _, reason = _publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not published and reason == "NOTION_TEST_CHANGED" and module.read_text() == TRAIN
    # Mismatch needs manual recovery; automatic refresh must not overwrite it.
    assert not NotionStore(d.notions_path).author_reviewed_test(binding, workspace, test)
    assert test.read_bytes() == old


def test_challenge_ranking_counts_distinct_source_bytes_and_excludes_same_source(tmp_path):
    # Synthetic serialized records test the selector only; no publication or
    # independent verification is asserted here.
    store = NotionStore(tmp_path / "notions.json")
    store.findings["current"] = {"source_sha256": "same-as-current"}
    for fid, source_hash, point in (("a1", "a", [100, 2]), ("a2", "a", [100, 2]),
                                    ("a3", "a", [100, 2]), ("b1", "b", [50, 2]),
                                    ("b2", "c", [50, 2]), ("self", "same-as-current", [999, 2])):
        store.findings[fid] = {"source_sha256": source_hash, "left": "r", "right": "t",
                               "arity": 2, "fired": True, "declined": False}
        store.reviews[fid] = {"decision": "confirm", "trusted_function": "r", "reviewer": "r", "basis": "b"}
        store.examples[fid] = [{"args": [2, 3], "expected": 5, "reviewer": "r", "basis": "b"},
                               {"args": point, "expected": 1, "reviewer": "r", "basis": "b"}]
        store.experiences[fid] = {"source_sha256": source_hash, "target": "t", "reference": "r",
                                  "feedback_sha256": store._feedback_hash(store.reviews[fid], store.examples[fid])}
    store.save()
    assert store.learned_challenge_inputs("current", 2) == [[50, 2], [100, 2]]
    data = json.loads(store.path.read_text())
    data["examples"]["b2"][1]["expected"] = 2  # old experience no longer matches its feedback
    store.path.write_text(json.dumps(data))
    assert store.learned_challenge_inputs("current", 2) == [[100, 2], [50, 2]]
