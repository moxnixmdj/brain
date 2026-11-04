"""Real feedback/experience controls for bounded compositional transfer.

The fixture oracles below are deliberately authored evaluation specifications,
not runtime repair tables or independently authenticated verification.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import multiprocessing
import pathlib

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import creature_runtime_v1 as creature
from canonical.runtime.memory_policy_v1 import OFF, READ_ONLY, READ_WRITE, memory_policy_scope
from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
from canonical.swe_kernel.expression_hypotheses_v1 import evaluate_expression, investigate, supported_binary_operator_names
from canonical.swe_kernel.notions_v1 import NotionStore, notions_for_source
from canonical.swe_kernel.probe_syntax_guard_v1 import probe_source_supported


TRAIN = """def narrow(t):
    return t + t

def pair(x, y):
    return x * y
"""

TRIPLE = """def diagonal(q):
    return 3 * q

def bundle(a, b, c):
    return a * b * c
"""

WEIGHTED = """def compact(q):
    return 3 * q

def combine(p, q):
    return p * q
"""


def make_workspace(path: pathlib.Path, source: str):
    (path / "pkg").mkdir(parents=True)
    (path / "pkg" / "__init__.py").write_text("")
    module = path / "pkg" / "example.py"
    module.write_text(source)
    return module


def daemon(workspace: pathlib.Path, root: pathlib.Path):
    return AwakeAgencyDaemon(workspace, ledger_path=root / "awake_sense" / "ledger.json",
                             skill_store_path=root / "awake_sense" / "skills.sqlite")


def finding(d, reference: str, target: str):
    return next(f for f in d.investigate_workspace() if f["left"] == reference and f["right"] == target)


def provide_feedback(d, reference: str, target: str, oracle):
    f = finding(d, reference, target)
    store = NotionStore(d.notions_path)
    store.review(f["id"], decision="confirm", reviewer="evaluation fixture",
                 basis="fixture contract", trusted_function=reference)
    answers = []
    for _ in range(12):
        f = finding(d, reference, target)
        plan = f["plan"]
        query = plan.get("next_query")
        if not query:
            return f, answers
        args = list(query["args"])
        expected = oracle(args)
        store.answer(f["id"], args=args, expected=expected,
                     reviewer="evaluation fixture", basis="fixture oracle")
        answers.append(args)
    pytest.fail("bounded active-query loop did not settle within its test budget")


def board(root: pathlib.Path, workspace: pathlib.Path):
    report = creature.run_sovereign_board(root, cycles=6, identity="experience-fixture",
                                           life=480, slice_size=480, workspace=workspace)
    return [s for s in report["run"].get("steps", []) if str(s.get("work", "")).startswith("repair:")]


def load_function(module: pathlib.Path, name: str):
    # This module is a locally authored test fixture; it is not an arbitrary
    # workspace program. Values supplied here are held out from the repair.
    spec = importlib.util.spec_from_file_location("experience_fixture", module)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return getattr(loaded, name)


def train_once(tmp_path: pathlib.Path):
    root = tmp_path / "creature"
    workspace = tmp_path / "training"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, queries = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and len(queries) >= 2
    steps = board(root, workspace)
    accepted = next((s for s in steps if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted is not None, steps
    assert accepted["verified"] is False and accepted["correct"] is None
    assert accepted["prediction_features"]["strong_verifier"] == 0.0
    assert accepted["prediction_features"]["grounding_complete"] == 0.0
    assert accepted["independent_calibration_recorded"] is False
    ledger = root / "self_prediction_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    assert not any(str(row.get("capability_id", "")).startswith("repair:") for row in rows)
    assert accepted["structure_learning"]["status"] == "recorded_for_proposals"
    assert accepted["structure_learning"]["operators"] == ["Add"]
    assert load_function(module, "pair")(9, -4) == 5
    return root, d, f


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_actual_experience_enables_new_composition_without_authorizing_it(tmp_path):
    # The same unseen task with a fresh creature cannot represent its spec.
    cold_root = tmp_path / "cold_creature"
    cold_workspace = tmp_path / "cold_workspace"
    cold_module = make_workspace(cold_workspace, TRIPLE)
    cold = daemon(cold_workspace, cold_root)
    cold_result, cold_queries = provide_feedback(cold, "diagonal", "bundle", sum)
    assert cold_result["status"] == "no_candidates" and len(cold_queries) >= 2
    assert cold._sense_failing_workspace_tests() == []
    assert cold_module.read_text() == TRIPLE and not list(cold_workspace.rglob("test_*.py"))

    # Experience comes from a real reviewed board repair, not manually inserted
    # memory. The source in the new task has multiplication but no addition.
    root, trained, training_finding = train_once(tmp_path / "warm")
    store = NotionStore(trained.notions_path)
    assert store.learned_operators() == ["Add"] and len(store.experiences) == 1
    warm_workspace = tmp_path / "warm_workspace"
    warm_module = make_workspace(warm_workspace, TRIPLE)
    warm = daemon(warm_workspace, root)
    pending = finding(warm, "diagonal", "bundle")
    assert pending["status"] == "needs_review"
    assert warm._sense_failing_workspace_tests() == []
    assert warm_module.read_text() == TRIPLE and not list(warm_workspace.rglob("test_*.py"))

    planned, queries = provide_feedback(warm, "diagonal", "bundle", sum)
    assert planned["status"] == "bounded_agreement"
    assert planned["plan"]["learned_operators_considered"] == ["Add"]
    assert len(queries) >= 2 and any(any(x < 0 or x > 7 for x in args) for args in queries)
    steps = board(root, warm_workspace)
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in steps), steps
    after = warm_module.read_text()
    assert "return 3 * q" in after and "a +" in after
    func = load_function(warm_module, "bundle")
    for args in ((8, 3, 5), (-2, 7, 4), (0, 10, -4)):
        assert list(args) not in queries
        assert func(*args) == sum(args)
    # No authority or general verification is conferred by learned grammar.
    assert next(s for s in steps if s.get("accepted_into_world"))["verified"] is False
    assert training_finding["id"] in NotionStore(trained.notions_path).experiences


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_previously_unresolved_case_reopens_after_new_experience(tmp_path):
    root = tmp_path / "creature"
    old_workspace = tmp_path / "unresolved"
    old_module = make_workspace(old_workspace, TRIPLE)
    old_daemon = daemon(old_workspace, root)
    old, answers = provide_feedback(old_daemon, "diagonal", "bundle", sum)
    assert old["status"] == "no_candidates" and old_module.read_text() == TRIPLE
    original_examples = NotionStore(old_daemon.notions_path).examples[old["id"]]

    train_workspace = tmp_path / "later_experience"
    make_workspace(train_workspace, TRAIN)
    train_daemon = daemon(train_workspace, root)
    plan, _ = provide_feedback(train_daemon, "narrow", "pair", sum)
    assert plan["status"] == "bounded_agreement"
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in board(root, train_workspace))
    assert NotionStore(old_daemon.notions_path).learned_operators() == ["Add"]

    # Re-observe the old source with the same reviewed examples, not new labels.
    revised = finding(old_daemon, "diagonal", "bundle")
    assert revised["id"] == old["id"] and revised["status"] == "bounded_agreement"
    assert NotionStore(old_daemon.notions_path).examples[old["id"]] == original_examples
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in board(root, old_workspace))
    func = load_function(old_module, "bundle")
    for args in ((8, 3, 5), (-2, 7, 4)):
        assert list(args) not in answers
        assert func(*args) == sum(args)


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_repeated_learned_primitive_composes_a_new_weighted_expression(tmp_path):
    root, trained, _ = train_once(tmp_path / "training")
    workspace = tmp_path / "weighted"
    module = make_workspace(workspace, WEIGHTED)
    d = daemon(workspace, root)
    oracle = lambda a: a[0] + a[0] + a[1]
    f, queries = provide_feedback(d, "compact", "combine", oracle)
    assert f["status"] == "bounded_agreement", f
    steps = board(root, workspace)
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in steps), steps
    func = load_function(module, "combine")
    for args in ((8, 3), (-2, 7), (0, 10)):
        assert list(args) not in queries
        assert func(*args) == oracle(args)
    # The training repair was x+y, while this function needs two Add nodes.
    after = ast.parse(module.read_text())
    target = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == "combine")
    assert sum(isinstance(n, ast.Add) for n in ast.walk(target)) == 2
    assert NotionStore(trained.notions_path).learned_operators() == ["Add"]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_prior_addition_does_not_force_an_unrelated_product_specification(tmp_path):
    root, trained, _ = train_once(tmp_path / "training")
    source = "def square(s):\n    return s * s\n\ndef wider(a, b):\n    return a - b\n"
    workspace = tmp_path / "product"
    module = make_workspace(workspace, source)
    d = daemon(workspace, root)
    oracle = lambda a: a[0] * a[1]
    f, queries = provide_feedback(d, "square", "wider", oracle)
    assert f["status"] == "bounded_agreement" and f["plan"]["learned_operators_considered"] == ["Add"]
    steps = board(root, workspace)
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in steps), steps
    func = load_function(module, "wider")
    for args in ((8, 3), (-2, 7), (0, 10)):
        assert list(args) not in queries
        assert func(*args) == oracle(args)
    assert NotionStore(trained.notions_path).learned_operators() == ["Add", "Mult"]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_separate_subtraction_experience_transfers_without_addition_rules(tmp_path):
    root = tmp_path / "creature"
    workspace = tmp_path / "training_sub"
    source = "def single(t):\n    return t - t\n\ndef pair(x, y):\n    return x + y\n"
    module = make_workspace(workspace, source)
    d = daemon(workspace, root)
    f, queries = provide_feedback(d, "single", "pair", lambda a: a[0] - a[1])
    assert f["status"] == "bounded_agreement" and len(queries) >= 2
    steps = board(root, workspace)
    accepted = next((s for s in steps if s.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted and accepted["structure_learning"]["operators"] == ["Sub"]
    assert load_function(module, "pair")(9, 4) == 5
    assert NotionStore(d.notions_path).learned_operators() == ["Sub"]

    novel = "def unary(q):\n    return -q\n\ndef combine(a, b, c):\n    return a * b * c\n"
    cold_plan, _ = active_plan(novel, "unary", "combine", lambda a: a[0] - a[1] - a[2], [])
    assert cold_plan["status"] == "no_candidates"
    held_workspace = tmp_path / "held_sub"
    held_module = make_workspace(held_workspace, novel)
    held_daemon = daemon(held_workspace, root)
    oracle = lambda a: a[0] - a[1] - a[2]
    planned, held_queries = provide_feedback(held_daemon, "unary", "combine", oracle)
    assert planned["status"] == "bounded_agreement"
    assert planned["plan"]["learned_operators_considered"] == ["Sub"]
    steps = board(root, held_workspace)
    assert any(s.get("accepted_into_world") == ["pkg/example.py"] for s in steps), steps
    func = load_function(held_module, "combine")
    for args in ((8, 3, 2), (-2, 7, 4), (0, 10, -4)):
        assert list(args) not in held_queries
        assert func(*args) == oracle(args)


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_retracting_source_feedback_retracts_its_learned_operator(tmp_path):
    root, trained, f = train_once(tmp_path)
    store = NotionStore(trained.notions_path)
    assert store.learned_operators() == ["Add"]
    before = pathlib.Path(trained.notions_path).read_bytes()
    with memory_policy_scope(READ_ONLY):
        assert store.learned_operators() == ["Add"]
        with pytest.raises(PermissionError):
            store.review(f["id"], decision="reject", reviewer="fixture", basis="retracted")
    with memory_policy_scope(OFF):
        assert store.learned_operators() == []
    assert pathlib.Path(trained.notions_path).read_bytes() == before
    stale_reader = NotionStore(trained.notions_path)
    store.review(f["id"], decision="reject", reviewer="fixture", basis="retracted")
    assert stale_reader.learned_operators() == []  # reloads instead of trusting cached approval
    assert NotionStore(trained.notions_path).learned_operators() == []
    workspace = tmp_path / "after_retraction"
    make_workspace(workspace, TRIPLE)
    d = daemon(workspace, root)
    result, _ = provide_feedback(d, "diagonal", "bundle", sum)
    assert result["status"] == "no_candidates"


def active_plan(source, reference, target, oracle, operators):
    result = next(n.evaluate() for n in notions_for_source(source, "fixture.py")
                  if n.left == reference and n.right == target)
    examples = []
    for _ in range(12):
        plan = investigate(source, target_name=target, reference_name=reference,
                           observations=result["observations"], examples=examples,
                           learned_operators=operators)
        query = plan.get("next_query")
        if not query:
            return plan, examples
        args = query["args"]
        examples.append({"args": args, "expected": oracle(args)})
    pytest.fail("active plan did not settle within its test budget")


@pytest.fixture(scope="module")
def one_add_experience(tmp_path_factory):
    if not broker.namespace_broker_available():
        pytest.skip("confined execution unavailable")
    _, d, _ = train_once(tmp_path_factory.mktemp("one_observed_add"))
    return NotionStore(d.notions_path).learned_operators()


@pytest.mark.parametrize("source,oracle,heldout", [
    ("def ref(z):\n    return 3*z\ndef target(a,b,c):\n    return a*b*c\n",
     lambda v: sum(v), [(8, 3, 5), (-2, 7, 4)]),
    ("def ref(z):\n    return 2*z\ndef target(a,b):\n    return a-b\n",
     lambda v: sum(v), [(8, 3), (-2, 7)]),
    ("def ref(z):\n    return 3*z\ndef target(a,b):\n    return a*b\n",
     lambda v: 2*v[0] + v[1], [(8, 3), (-2, 7)]),
    ("def ref(z):\n    return z*3\ndef target(a,b):\n    return a//b\n",
     lambda v: v[0] + 2*v[1], [(8, 3), (-2, 7)]),
    ("def ref(z):\n    return z*3\ndef target(a,b,c):\n    return a*b+c\n",
     lambda v: sum(v), [(8, 3, 5), (-2, 7, 4)]),
], ids=["three-input", "two-input", "weighted-left", "weighted-right", "mixed-source"])
def test_held_out_compositions_change_with_one_real_experience(one_add_experience, source, oracle, heldout):
    assert one_add_experience == ["Add"]
    cold, _ = active_plan(source, "ref", "target", oracle, [])
    warm, examples = active_plan(source, "ref", "target", oracle, one_add_experience)
    assert cold["status"] == "no_candidates"
    assert warm["status"] == "bounded_agreement" and not warm["truncated"]
    for text in warm["candidate_expressions"]:
        expr = ast.parse(text, mode="eval").body
        for args in heldout:
            assert list(args) not in [e["args"] for e in examples]
            valid, prediction = evaluate_expression(expr, dict(zip(("a", "b", "c"), args)))
            assert valid and prediction == oracle(args)


def test_truncated_learned_grammar_does_not_claim_agreement():
    result = next(n.evaluate() for n in notions_for_source(TRIPLE, "fixture.py")
                  if n.left == "diagonal" and n.right == "bundle")
    plan = investigate(TRIPLE, target_name="bundle", reference_name="diagonal",
                       observations=result["observations"],
                       examples=[{"args": [2, 3, 6], "expected": 11},
                                 {"args": [-3, -3, 11], "expected": 5}],
                       learned_operators=sorted(supported_binary_operator_names()))
    assert plan["truncated"] is True
    assert plan["status"] != "bounded_agreement"


def test_expression_budget_refuses_a_more_complex_unseen_specification():
    source = "def ref(z):\n    return 4*z\ndef target(a,b):\n    return a*b\n"
    oracle = lambda v: 2*v[0] + 2*v[1]
    plan, _ = active_plan(source, "ref", "target", oracle, ["Add"])
    assert plan["status"] == "no_candidates"  # three additions exceed the two-node budget


def test_stress_query_catches_one_out_of_range_specification_change():
    # The diagonal relationship holds even outside the main grid. One truthful
    # specification differs only off-diagonal at a large input.
    oracle = lambda a: sum(a) + (1 if max(a) >= 10 and len(set(a)) > 1 else 0)
    plan, examples = active_plan(TRIPLE, "diagonal", "bundle", oracle, ["Add"])
    assert any(max(e["args"]) >= 10 for e in examples)
    assert plan["status"] == "no_candidates"


def test_bounded_questions_still_cannot_rule_out_a_more_distant_specification():
    # Honest answers on both finite grids cannot prove a behavior at 100+.
    oracle = lambda a: sum(a) + (1 if max(a) >= 100 and len(set(a)) > 1 else 0)
    plan, examples = active_plan(TRIPLE, "diagonal", "bundle", oracle, ["Add"])
    assert plan["status"] == "bounded_agreement" and all(max(e["args"]) < 100 for e in examples)
    args = (101, 2, 3)
    candidate = ast.parse(plan["candidate_expressions"][0], mode="eval").body
    valid, prediction = evaluate_expression(candidate, dict(zip(("a", "b", "c"), args)))
    assert valid and prediction != oracle(args)  # a surviving model fails the held-out contract


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("change", ["rejected", "changed_basis"])
def test_retracted_feedback_cannot_publish_a_previously_authored_test(tmp_path, change):
    root = tmp_path / "creature"
    workspace = tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    assert (workspace / "tests" / "test_example.py").exists()
    store = NotionStore(d.notions_path)
    if change == "rejected":
        store.review(f["id"], decision="reject", reviewer="fixture", basis="retracted before publication")
    else:
        store.review(f["id"], decision="confirm", reviewer="fixture", basis="changed basis",
                     trusted_function="narrow")
    steps = board(root, workspace)
    assert steps and all(not s.get("accepted_into_world") for s in steps)
    assert all(s.get("blocked") == "NOTION_FEEDBACK_STALE" for s in steps)
    assert module.read_text() == TRAIN and NotionStore(d.notions_path).learned_operators() == []


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("memory_mode", [READ_WRITE, OFF])
def test_removing_generated_test_marker_does_not_bypass_withdrawal(tmp_path, memory_mode):
    root = tmp_path / "creature"
    workspace = tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    NotionStore(d.notions_path).review(f["id"], decision="reject", reviewer="fixture", basis="withdrawn")
    test = workspace / "tests" / "test_example.py"
    assert test.with_name("." + test.name + ".brain-origin").is_file()
    test.write_text(test.read_text().split("\n", 1)[1])
    with memory_policy_scope(memory_mode):
        steps = board(root, workspace)
    assert steps and all(not s.get("accepted_into_world") for s in steps)
    assert all(s.get("blocked") == "NOTION_TEST_CHANGED" for s in steps)
    assert module.read_text() == TRAIN


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_rejected_reviewed_candidate_does_not_train_legacy_memory_or_global_caches(tmp_path):
    from canonical.swe_kernel import (grammar_growth_v1, interpretive_repair_v1,
        learned_edit_habits_v1, synthesized_edit_grammar_v1, tool_competence_v1)
    modules = (grammar_growth_v1, interpretive_repair_v1, learned_edit_habits_v1,
               synthesized_edit_grammar_v1, tool_competence_v1)
    root, ws = tmp_path / "root", tmp_path / "world"
    make_workspace(ws, TRAIN)
    d = daemon(ws, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    d._sense_failing_workspace_tests()
    NotionStore(d.notions_path).review(f["id"], decision="reject", reviewer="fixture", basis="withdrawn")
    folder = root / "awake_repair"
    folder.mkdir(parents=True)
    habits = folder / "learned_edit_habits.json"
    old_memory = json.dumps({"schema": "BRAIN_LEARNED_EDIT_HABITS_V1",
                             "observed": [["-", "+"]], "inferred": []})
    habits.write_text(old_memory)
    old_caches = [m._LIVE for m in modules]
    steps = board(root, ws)
    assert not any(s.get("accepted_into_world") for s in steps)
    assert habits.read_text() == old_memory
    assert sorted(p.name for p in folder.iterdir()) == [habits.name]
    assert all(m._LIVE is old for m, old in zip(modules, old_caches))
    assert (ws / "pkg" / "example.py").read_text() == TRAIN


def test_repair_memory_snapshot_copies_sqlite_wal_and_respects_off(tmp_path):
    import sqlite3
    from canonical.runtime.creature_runtime_v1 import _snapshot_repair_memory
    source, copied, cold = tmp_path / "source", tmp_path / "copied", tmp_path / "cold"
    source.mkdir()
    (source / "learned_edit_habits.json").write_text('{"observed": []}')
    with sqlite3.connect(source / "skills.sqlite") as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE evidence (value TEXT)")
        db.execute("INSERT INTO evidence VALUES ('committed')")
        db.commit()
        _snapshot_repair_memory(source, copied)
        with sqlite3.connect(copied / "skills.sqlite") as snapshot:
            assert snapshot.execute("SELECT value FROM evidence").fetchall() == [("committed",)]
    assert (copied / "learned_edit_habits.json").read_text() == '{"observed": []}'
    with memory_policy_scope("OFF"):
        _snapshot_repair_memory(source, cold)
    assert list(cold.iterdir()) == []


def test_symlink_alias_cannot_hide_a_generated_test_sidecar_when_memory_is_off(tmp_path):
    root, ws = tmp_path / "root", tmp_path / "world"
    module = make_workspace(ws, TRAIN)
    d = daemon(ws, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = ws / "tests" / "test_example.py"
    assert test.with_name("." + test.name + ".brain-origin").is_file()
    test.write_text(test.read_text().split("\n", 1)[1])
    alias = test.with_name("test_alias.py")
    alias.symlink_to(test.name)
    candidate = TRAIN.replace("return x * y", "return x + y")
    with memory_policy_scope(OFF):
        ok, _, reason = creature._publish_candidate(ws, alias, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not ok and reason == "NOTION_TEST_CHANGED" and module.read_text() == TRAIN


@pytest.mark.parametrize("broken_entry", [None, {}, {"binding": {}},
    {"binding": {"module": "pkg/example.py"}, "test_sha256": "invalid"}])
def test_corrupt_registered_origin_is_not_treated_as_an_ordinary_test(tmp_path, broken_entry):
    root, ws = tmp_path / "root", tmp_path / "world"
    module = make_workspace(ws, TRAIN)
    d = daemon(ws, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = ws / "tests" / "test_example.py"
    test.with_name("." + test.name + ".brain-origin").unlink()
    test.write_text(test.read_text().split("\n", 1)[1])
    data = json.loads(d.notions_path.read_text())
    key = NotionStore._authored_test_key(ws, "tests/test_example.py")
    # The top-level schema also rejects non-dict entries; nested corruption must
    # not collapse to the same value as an absent registry entry either.
    data["authored_tests"][key] = broken_entry
    d.notions_path.write_text(json.dumps(data))
    candidate = TRAIN.replace("return x * y", "return x + y")
    ok, _, reason = creature._publish_candidate(ws, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not ok and reason == "NOTION_FEEDBACK_UNAVAILABLE"
    assert module.read_text() == TRAIN


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_read_only_can_use_current_feedback_without_learning(tmp_path):
    root, ws = tmp_path / "root", tmp_path / "world"
    module = make_workspace(ws, TRAIN)
    d = daemon(ws, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    before = d.notions_path.read_bytes()
    with memory_policy_scope(READ_ONLY):
        steps = board(root, ws)
    accepted = [s for s in steps if s.get("accepted_into_world")]
    assert accepted and accepted[0]["structure_learning"]["status"] == "memory_policy_blocks_learning"
    assert module.read_text() == TRAIN.replace("return x * y", "return x + y")
    assert d.notions_path.read_bytes() == before


@pytest.mark.parametrize("missing", ["store", "lock"])
def test_missing_feedback_store_or_read_only_lock_refuses_publication(tmp_path, missing):
    root, ws = tmp_path / "root", tmp_path / "world"
    module = make_workspace(ws, TRAIN)
    d = daemon(ws, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = ws / "tests" / "test_example.py"
    if missing == "store":
        d.notions_path.unlink()
    else:
        d.notions_path.with_name("." + d.notions_path.name + ".lock").unlink()
    candidate = TRAIN.replace("return x * y", "return x + y")
    with memory_policy_scope(READ_ONLY):
        ok, _, reason = creature._publish_notion_candidate(
            ws, test, {"pkg/example.py": candidate}, notions_path=d.notions_path)
    assert not ok and reason == "NOTION_FEEDBACK_STALE"
    assert module.read_text() == TRAIN


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_reviewed_test_content_is_bound_to_the_feedback_snapshot(tmp_path):
    root = tmp_path / "creature"
    workspace = tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    test.write_text(test.read_text() + "\n# modified after review\n")
    candidate = TRAIN.replace("return x * y", "return x + y")
    ok, _, reason = creature._publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path
    )
    assert not ok and reason == "NOTION_TEST_CHANGED" and module.read_text() == TRAIN


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_older_review_marker_without_feedback_hash_is_not_authority(tmp_path):
    root = tmp_path / "creature"
    workspace = tmp_path / "workspace"
    module = make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    first, body = test.read_text().split("\n", 1)
    binding = json.loads(first[len("# brain-notion-v1 "):])
    binding.pop("feedback_sha256")
    test.write_text("# brain-notion-v1 " + json.dumps(binding, sort_keys=True) + "\n" + body)
    candidate = TRAIN.replace("return x * y", "return x + y")
    ok, _, reason = creature._publish_notion_candidate(
        workspace, test, {"pkg/example.py": candidate}, notions_path=d.notions_path
    )
    assert not ok and reason == "NOTION_TEST_CHANGED" and module.read_text() == TRAIN


def _retract_concurrently(path: str, finding_id: str, started, finished):
    store = NotionStore(path)
    started.set()
    store.review(finding_id, decision="reject", reviewer="second process", basis="retracted")
    finished.set()


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_feedback_retraction_waits_for_the_publication_read_lock(tmp_path):
    root = tmp_path / "creature"
    workspace = tmp_path / "workspace"
    make_workspace(workspace, TRAIN)
    d = daemon(workspace, root)
    f, _ = provide_feedback(d, "narrow", "pair", sum)
    assert f["status"] == "bounded_agreement" and d._sense_failing_workspace_tests()
    first = (workspace / "tests" / "test_example.py").read_text().splitlines()[0]
    binding = json.loads(first[len("# brain-notion-v1 "):])
    store = NotionStore(d.notions_path)
    ctx = multiprocessing.get_context("fork")
    started, finished = ctx.Event(), ctx.Event()
    with store.hold_reviewed_feedback(binding) as valid:
        assert valid
        process = ctx.Process(target=_retract_concurrently, args=(str(d.notions_path), f["id"], started, finished))
        process.start()
        assert started.wait(5)
        assert not finished.wait(0.2)
    assert finished.wait(5)
    process.join(5)
    assert process.exitcode == 0
    assert NotionStore(d.notions_path).reviews[f["id"]]["decision"] == "reject"


def test_candidate_alone_does_not_create_experience_without_reviewed_feedback(tmp_path):
    store = NotionStore(tmp_path / "memory.json")
    result = store.record_checked_repair(
        {"finding_id": "unreviewed", "module": "m.py", "target": "pair", "reference": "narrow"}, TRAIN
    )
    assert result["status"] == "missing_attributed_feedback"
    assert store.learned_operators() == [] and store.experiences == {}


def test_corrupt_memory_is_reported_and_does_not_keep_stale_findings(tmp_path):
    path = tmp_path / "memory.json"
    store = NotionStore(path)
    store.record([{"id": "one", "kind": "IDENTITY", "subject": "x", "fired": True, "declined": False}])
    assert "one" in store.findings
    path.write_text("{broken")
    with pytest.raises(ValueError, match="corrupt or incompatible"):
        store.load()
    assert store.findings == {} and path.read_text() == "{broken"
    with pytest.raises(ValueError, match="corrupt or incompatible"):
        NotionStore(path)


def _record_concurrently(path: str, index: int, start):
    store = NotionStore(path)
    start.wait()
    store.record([{"id": str(index), "kind": "IDENTITY", "subject": f"case{index}",
                   "fired": True, "declined": False}])


def test_memory_preserves_concurrent_process_updates(tmp_path):
    context = multiprocessing.get_context("fork")
    start = context.Event()
    path = str(tmp_path / "memory.json")
    processes = [context.Process(target=_record_concurrently, args=(path, i, start)) for i in range(16)]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0
    store = NotionStore(path)
    assert set(store.findings) == {str(i) for i in range(16)}


def test_probe_syntax_gate_abstains_instead_of_running_unsafe_python():
    safe = "def total(xs, ys):\n    return [a + b for a, b in zip(xs, ys)]\n"
    assert probe_source_supported(safe)[0] is True
    unsafe = [
        "import sys\ndef f(x):\n    return x\n",
        "def f(x):\n    return x.__class__\n",
        "def f(x):\n    return eval(x)\n",
        "def f(x):\n    return min([x], key=eval)\n",
        "def f(x):\n    zip = min([eval])\n    return zip(x)\n",
        "def f(x):\n    return min([eval])\n",
        "def f(x: print('effect')):\n    return x\n",
        "def f(x=print('effect')):\n    return x\n",
        "x = print('effect')\ndef f(x):\n    return x\n",
    ]
    assert all(probe_source_supported(src)[0] is False for src in unsafe)
    benign_but_unsupported = "import math\ndef f(x):\n    return math.sqrt(x)\n"
    assert probe_source_supported(benign_but_unsupported)[0] is False


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("expression, generalizes, reason", [
    ("True", False, "BOOLEAN_RESULT_INPUT_SENSITIVITY_UNPROBED"),
    ("x < 10", True, "RESPONDS_TO_INPUT"),
])
def test_boolean_probe_abstains_when_perturbations_do_not_show_sensitivity(tmp_path, expression, generalizes, reason):
    ws = tmp_path / "world"
    (ws / "pkg").mkdir(parents=True)
    (ws / "pkg" / "__init__.py").write_text("")
    (ws / "pkg" / "m.py").write_text(f"def f(x):\n    return {expression}\n")
    test = ws / "test_m.py"
    test.write_text("from pkg.m import f\ndef test_f():\n    assert f(2) is True\n")
    result = creature._generalization_probe(test, ws)
    assert result["generalizes"] is generalizes and result["reason"] == reason
    assert result["proves_correctness"] is False


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("memory_mode", [READ_WRITE, READ_ONLY, OFF])
def test_ordinary_user_test_does_not_require_a_notion_store(tmp_path, memory_mode):
    ws = tmp_path / "world"
    (ws / "pkg").mkdir(parents=True)
    (ws / "pkg" / "__init__.py").write_text("")
    module = ws / "pkg" / "m.py"
    module.write_text("def f(x):\n    return x - 1\n")
    (ws / "tests").mkdir()
    test = ws / "tests" / "test_m.py"
    test.write_text("from pkg.m import f\ndef test_f():\n    assert f(2) == 3\n    assert f(5) == 6\n")
    candidate = "def f(x):\n    return x + 1\n"
    with memory_policy_scope(memory_mode):
        ok, _, reason = creature._publish_candidate(
            ws, test, {"pkg/m.py": candidate}, notions_path=tmp_path / "missing.json")
    assert ok and reason is None and module.read_text() == candidate


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_ordinary_repairs_are_staged_and_multifile_repairs_are_refused(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "pkg").mkdir(parents=True)
    (workspace / "pkg" / "__init__.py").write_text("")
    module = workspace / "pkg" / "m.py"
    before = "def f(x):\n    return x - 1\n"
    module.write_text(before)
    other = workspace / "pkg" / "other.py"
    other.write_text("VALUE = 1\n")
    (workspace / "tests").mkdir()
    test = workspace / "tests" / "test_m.py"
    test.write_text("from pkg.m import f\ndef test_f():\n    assert f(2) == 3\n    assert f(5) == 6\n")
    ok, _, reason = creature._publish_candidate(workspace, test,
        {"pkg/m.py": "def f(x):\n    return x + 1\n", "pkg/other.py": "VALUE = 2\n"})
    assert not ok and reason == "MULTIFILE_PUBLICATION_UNSUPPORTED"
    assert module.read_text() == before and other.read_text() == "VALUE = 1\n"
    ok, _, _ = creature._publish_candidate(workspace, test,
        {"pkg/m.py": "def f(x):\n    return x * 2\n"})
    assert not ok and module.read_text() == before
    good = "def f(x):\n    return x + 1\n"
    ok, probe, reason = creature._publish_candidate(workspace, test, {"pkg/m.py": good})
    assert ok and reason is None and probe["generalizes"]
    assert module.read_text() == good and other.read_text() == "VALUE = 1\n"
