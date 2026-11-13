"""Tests for the neuro-symbolic compositional & causal generalization engine.

Coverage map (four pillars + integration + honesty gates):

  Pillar 1 — online parametric policy: learning reduces loss, receipts carry
             pre/post loss and ||dW||2, weights persist and reload.
  Pillar 2 — typed parser + compositional synthesizer: operation x concept x
             domain x qualifier compose; answers are structured (int/list/dict);
             hand-computed ground truth is reproduced on independent fixtures.
  Pillar 3 — cross-domain schema transfer: python AST, Markdown (incl. fenced
             python blocks), JSON, CSV, plain text.
  Pillar 4 — causal verifier: probes run and pass on the happy path; the
             verifier *fails closed* when the mechanism is sabotaged; probe
             receipts are present in every successful answer.

Honesty gates: unrecognized operation/concept, missing target, mixed domains,
negation, inapplicable/infeasible qualifiers, unparsed qualifier markers,
whole-file breakdown with qualifiers.

Integration: solve_or_learn honours a Mapping request-level `learn` flag;
the read-only door path answers with bound capabilities again (regression
for the "Found 1 classes" string-typed answer bug).
"""
from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest

from canonical.swe_kernel import semantic_generalization_engine_v1 as eng
from canonical.swe_kernel.semantic_generalization_engine_v1 import (
    CausalVerificationFailure,
    GeneralizationEngine,
    OnlineParametricPolicyModel,
    SemanticTaskAST,
    build_qualified_python_fixture,
    parse_task,
    verify_postconditions,
    _select_concept_in_source,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

PY_SAMPLE = '''"""Module docstring (not counted by the docstring concept)."""

import os
from pathlib import Path


class Widget:
    """Widget docstring."""

    def public_method(self, x):
        return x


def public_alpha(a, b):
    """Alpha docstring."""
    if a:
        for i in range(b):
            print(i)
    return a


def _private_beta(x):
    return x * 2


async def public_gamma():
    try:
        raise ValueError("boom")
    except ValueError:
        pass


assert public_alpha(1, 2) is not None
'''

DOCUMENTED_MD = (
    "# Title\n\n"
    "Some intro words here.\n\n"
    "## Section A\n\n"
    "A [link](https://example.com) here.\n\n"
    "- one\n- two\n\n"
    "```python\n"
    "def md_func_a():\n    return 1\n\n"
    "def md_func_b(x):\n    return x\n"
    "```\n"
)

DATA_JSON = '{"alpha": 1, "beta": [1, 2], "gamma": {"a": "s", "b": true, "c": null}}'

DATA_CSV = "name,size\nalpha,3\nbeta,5\n"

PLAIN_TXT = "one two three\nfour five\n"


def _independent_python_counts(source: str) -> dict[str, int]:
    tree = ast.parse(source)
    counts = {k: 0 for k in eng.PY_CONCEPTS}
    parents: dict[int, object] = {}

    def visit(node, parent):
        parents[id(node)] = parent
        for child in ast.iter_child_nodes(node):
            visit(child, node)

    visit(tree, None)
    defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    counts["function"] = len(defs)
    counts["async_function"] = sum(1 for n in defs if isinstance(n, ast.AsyncFunctionDef))
    counts["class"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    counts["method"] = sum(1 for n in defs if isinstance(parents.get(id(n)), ast.ClassDef))
    counts["if_statement"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.If))
    counts["for_loop"] = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.For, ast.AsyncFor)))
    counts["while_loop"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.While))
    counts["loop"] = counts["for_loop"] + counts["while_loop"]
    counts["import"] = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)))
    counts["return_statement"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Return))
    try_types = tuple(t for t in (getattr(ast, "Try", None), getattr(ast, "TryStar", None)) if t is not None)
    counts["try_block"] = sum(1 for n in ast.walk(tree) if isinstance(n, try_types))
    counts["raise_statement"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Raise))
    counts["call"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call))
    counts["assignment"] = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)))
    counts["assertion"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Assert))
    counts["comprehension"] = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)))
    counts["decorator"] = sum(
        len(getattr(n, "decorator_list", []))
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    counts["docstring"] = sum(
        1 for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and ast.get_docstring(n) is not None
    )
    counts["parameter"] = sum(
        len(n.args.posonlyargs) + len(n.args.args) + len(n.args.kwonlyargs)
        + (1 if n.args.vararg else 0) + (1 if n.args.kwarg else 0)
        for n in defs
    )
    return counts


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "sample.py").write_text(PY_SAMPLE, encoding="utf-8")
    (tmp_path / "notes.md").write_text(DOCUMENTED_MD, encoding="utf-8")
    (tmp_path / "data.json").write_text(DATA_JSON, encoding="utf-8")
    (tmp_path / "data.csv").write_text(DATA_CSV, encoding="utf-8")
    (tmp_path / "plain.txt").write_text(PLAIN_TXT, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def engine(tmp_path: Path) -> GeneralizationEngine:
    state = tmp_path / "genstate"
    state.mkdir()
    return GeneralizationEngine(
        experiences_path=state / "exp.json",
        embeddings_path=state / "emb.json",
        policy_path=state / "policy.json",
    )


# ---------------------------------------------------------------------------
# Pillar 2 — the parser
# ---------------------------------------------------------------------------

def test_parse_basic_count_request():
    task = parse_task("count functions in canonical/runtime/solve_v1.py")
    assert task.operation == "count"
    assert task.concept == "function"
    assert task.domain == "python_ast"
    assert task.targets == ["canonical/runtime/solve_v1.py"]
    assert task.confidence >= 0.9


def test_parse_absolute_and_relative_targets():
    task = parse_task("how many classes does /tmp/x/y.py contain?")
    assert task.targets == ["/tmp/x/y.py"]
    assert task.domain == "python_ast"


def test_parse_multi_file_compare_request():
    task = parse_task("Compare the function count in a.py and b.py")
    assert task.operation == "compare"
    assert task.concept == "function"
    assert task.targets == ["a.py", "b.py"]


@pytest.mark.parametrize("goal,concept", [
    ("count if statements in x.py", "if_statement"),
    ("count for loops in x.py", "for_loop"),
    ("count while loops in x.py", "while_loop"),
    ("count loops in x.py", "loop"),
    ("count import statements in x.py", "import"),
    ("count return statements in x.py", "return_statement"),
    ("count try blocks in x.py", "try_block"),
    ("count raise statements in x.py", "raise_statement"),
    ("count function calls in x.py", "call"),
    ("count assignments in x.py", "assignment"),
    ("count assertions in x.py", "assertion"),
    ("count comprehensions in x.py", "comprehension"),
    ("count decorators in x.py", "decorator"),
    ("count docstrings in x.py", "docstring"),
    ("count parameters in x.py", "parameter"),
    ("count async functions in x.py", "async_function"),
    ("identify methods in x.py", "method"),
    ("enumerate subroutines in x.py", "function"),
])
def test_parse_concept_lexicon(goal, concept):
    assert parse_task(goal).concept == concept


@pytest.mark.parametrize("goal,domain", [
    ("count headings in notes.md", "markdown"),
    ("count keys in data.json", "json"),
    ("count rows in data.csv", "csv"),
    ("count words in plain.txt", "text"),
])
def test_parse_domain_by_extension(goal, domain):
    assert parse_task(goal).domain == domain


def test_parse_qualifiers_compose():
    task = parse_task("Count public functions with at least 2 parameters and a docstring in x.py")
    assert task.qualifiers == {"public": True, "min_args": 2, "has_docstring": True}
    task = parse_task("Count private methods with at most 1 parameter in x.py")
    assert task.qualifiers == {"private": True, "max_args": 1}


def test_parse_name_prefix_and_suffix():
    task = parse_task("Count functions named fix_helper in x.py")
    assert task.qualifiers.get("name_prefix") == "fix_helper"
    task = parse_task("Count functions ending with _test in x.py")
    assert task.qualifiers.get("name_suffix") == "_test"


def test_unparsed_argument_marker_is_flagged_not_dropped():
    task = parse_task("Count parameters with at least 2 in x.py")
    assert "argument_count" in task.unparsed_qualifiers


def test_function_calls_phrase_is_calls_not_functions():
    assert parse_task("count function calls in x.py").concept == "call"


# ---------------------------------------------------------------------------
# Engine — python ground truth
# ---------------------------------------------------------------------------

CONCEPT_PHRASES = {
    "function": "functions",
    "async_function": "async functions",
    "class": "classes",
    "method": "methods",
    "if_statement": "if statements",
    "for_loop": "for loops",
    "while_loop": "while loops",
    "loop": "loops",
    "import": "import statements",
    "return_statement": "return statements",
    "try_block": "try blocks",
    "raise_statement": "raise statements",
    "call": "calls",
    "assignment": "assignments",
    "assertion": "assertions",
    "comprehension": "comprehensions",
    "decorator": "decorators",
    "docstring": "docstrings",
    "parameter": "parameters",
}


def test_python_counts_match_independent_ast_walk(workspace, engine):
    for concept, expected in _independent_python_counts(PY_SAMPLE).items():
        result = engine.solve_task(
            f"Count {CONCEPT_PHRASES[concept]} in sample.py", work_cwd=workspace,
            learn_update=False, persist_policy=False, store_experience=False,
        )
        if not result["pass"]:
            pytest.fail(f"engine failed on concept {concept}: {result.get('status')} {result.get('detail')}")
        assert result["answer"] == expected, f"{concept}: expected {expected}, got {result['answer']}"


def test_python_count_goal_matches_fixture_expect(workspace, engine):
    result = engine.solve_task(
        "How many functions does sample.py contain?", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["pass"] is True
    assert result["answer"] == 4
    assert result["answer_kind"] == "count"


def test_list_functions_returns_names_in_definition_order(workspace, engine):
    result = engine.solve_task(
        "List the function names in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["pass"] is True
    assert result["answer"] == ["public_method", "public_alpha", "_private_beta", "public_gamma"]


def test_class_list_and_method_list(workspace, engine):
    result = engine.solve_task(
        "List the class names in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == ["Widget"]
    result = engine.solve_task(
        "List the methods in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == ["public_method"]


def test_breakdown_matches_independent_walk(workspace, engine):
    result = engine.solve_task(
        "breakdown of sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["pass"] is True
    assert result["answer"] == _independent_python_counts(PY_SAMPLE)


def test_compare_two_files_delta_identity(workspace, engine):
    (workspace / "other.py").write_text("def one():\n    return 1\n\ndef two():\n    return 2\n", encoding="utf-8")
    result = engine.solve_task(
        "Compare the function count in sample.py and other.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["pass"] is True
    assert result["answer"]["left"] == 4
    assert result["answer"]["right"] == 2
    assert result["answer"]["delta"] == 2


def test_exists_answer_is_boolean(workspace, engine):
    result = engine.solve_task(
        "Are there any functions in sample.py?", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] is True
    (workspace / "empty.py").write_text("pass\n", encoding="utf-8")
    result = engine.solve_task(
        "Are there any functions in empty.py?", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] is False


def test_public_private_qualifier_split(workspace, engine):
    result = engine.solve_task(
        "Count public functions in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 3
    result = engine.solve_task(
        "Count private functions in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 1


def test_argument_window_qualifier(workspace, engine):
    result = engine.solve_task(
        "Count functions with at least 2 parameters in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 2   # public_method(self, x), public_alpha(a, b)
    result = engine.solve_task(
        "Count functions with at most 1 parameter in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 2   # _private_beta(x), public_gamma()


def test_docstring_qualifier(workspace, engine):
    result = engine.solve_task(
        "Count functions with a docstring in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 1   # public_alpha only


# ---------------------------------------------------------------------------
# Pillar 3 — cross-domain schema transfer
# ---------------------------------------------------------------------------

def test_markdown_counts_and_list(workspace, engine):
    result = engine.solve_task(
        "Count headings in notes.md", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 2
    result = engine.solve_task(
        "Count bullets in notes.md", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 2
    result = engine.solve_task(
        "Count links in notes.md", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 1
    result = engine.solve_task(
        "List the headings in notes.md", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == ["Title", "Section A"]


def test_markdown_fenced_python_block_transfers_python_concepts(workspace, engine):
    """LOAD -> PARSE_markdown -> EXTRACT fenced python -> PARSE_python -> SELECT -> REDUCE."""
    result = engine.solve_task(
        "Count functions in notes.md", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == 2
    result = engine.solve_task(
        "List the functions in notes.md", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == ["md_func_a", "md_func_b"]
    assert result["plan"]["pipeline"][:4] == ["LOAD", "PARSE_MARKDOWN", "EXTRACT_FENCED_CODE_BLOCKS", "PARSE_PYTHON_AST"]


def test_json_counts(workspace, engine):
    expected = {"key": 6, "entry": 3, "object": 2, "array": 1, "number": 3, "string": 1, "boolean": 1, "null": 1}
    for concept, count in expected.items():
        plural = {"entry": "entries", "boolean": "booleans", "null": "null values"}.get(concept, f"{concept}s")
        result = engine.solve_task(
            f"Count {plural} in data.json", work_cwd=workspace,
            learn_update=False, persist_policy=False, store_experience=False,
        )
        assert result["pass"] is True and result["answer"] == count, f"{concept}: {result.get('answer')}"


def test_csv_counts(workspace, engine):
    for goal, expected in [("Count rows in data.csv", 2), ("Count columns in data.csv", 2), ("Count cells in data.csv", 4)]:
        result = engine.solve_task(goal, work_cwd=workspace,
                                   learn_update=False, persist_policy=False, store_experience=False)
        assert result["answer"] == expected


def test_text_counts(workspace, engine):
    for goal, expected in [
        ("Count lines in plain.txt", 2),
        ("Count words in plain.txt", 5),
        ("Count characters in plain.txt", len(PLAIN_TXT)),
    ]:
        result = engine.solve_task(goal, work_cwd=workspace,
                                   learn_update=False, persist_policy=False, store_experience=False)
        assert result["answer"] == expected


def test_breakdown_json_and_text(workspace, engine):
    result = engine.solve_task(
        "breakdown of data.json", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"]["key"] == 6
    result = engine.solve_task(
        "breakdown of plain.txt", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["answer"] == {"line": 2, "word": 5, "character": len(PLAIN_TXT)}


# ---------------------------------------------------------------------------
# Pillar 4 — causal verifier
# ---------------------------------------------------------------------------

def test_successful_answer_carries_full_causal_receipt(workspace, engine):
    result = engine.solve_task(
        "Count functions in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    verification = result["causal_verification"]
    assert verification["all_passed"] is True
    probes = {p["probe"]: p for p in verification["probes"]}
    assert probes["positive_intervention_probe"]["passed"] is True
    assert probes["null_probe"]["passed"] is True
    assert probes["confounder_intervention_probe"]["passed"] is True
    assert result["postconditions"]["all_passed"] is True


def test_verifier_fails_closed_when_mechanism_is_sabotaged(workspace, engine, monkeypatch):
    def fake_select(tree, concept):
        return []

    monkeypatch.setattr(eng, "_select_python", fake_select)
    result = engine.solve_task(
        "Count functions in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["pass"] is False
    assert result["status"] == "FAIL_CLOSED__CAUSAL_VERIFICATION_FAILED"
    assert result["failed_probe"] == "positive_intervention_probe"


def test_confounder_probe_rejects_lexical_cheat(workspace, engine):
    confounder = eng.PY_CONFOUNDER
    for concept in ("function", "class", "if_statement", "for_loop", "import", "return_statement", "call"):
        assert _select_concept_in_source("python_ast", concept, confounder) == [], concept


def test_verify_postconditions_compare_delta_identity():
    ok = verify_postconditions("compare", {"left_target": "a", "right_target": "b", "left": 5, "right": 2, "delta": 3})
    assert ok["all_passed"] is True
    bad = verify_postconditions("compare", {"left_target": "a", "right_target": "b", "left": 5, "right": 2, "delta": 99})
    assert bad["all_passed"] is False


def test_qualifier_fixture_self_check_catches_impossible_combo():
    with pytest.raises(eng.QualifierFailure):
        build_qualified_python_fixture("function", {"public": True, "name_prefix": "_"})


# ---------------------------------------------------------------------------
# Honesty gates
# ---------------------------------------------------------------------------

def test_no_target_fails_closed(engine, tmp_path):
    result = engine.solve_task("count functions", work_cwd=tmp_path,
                               learn_update=False, persist_policy=False, store_experience=False)
    assert result["status"] == "FAIL_CLOSED__NO_TARGET_FILE"


def test_missing_target_fails_closed(engine, tmp_path):
    result = engine.solve_task("Count functions in nope.py", work_cwd=tmp_path,
                               learn_update=False, persist_policy=False, store_experience=False)
    assert result["status"] == "FAIL_CLOSED__TARGET_NOT_FOUND"


def test_unrecognized_operation_fails_closed(workspace, engine):
    result = engine.solve_task("Frobnicate sample.py", work_cwd=workspace,
                               learn_update=False, persist_policy=False, store_experience=False)
    assert result["status"] == "FAIL_CLOSED__OPERATION_UNRECOGNIZED"


def test_unrecognized_concept_fails_closed(workspace, engine):
    result = engine.solve_task("Count frobnicators in sample.py", work_cwd=workspace,
                               learn_update=False, persist_policy=False, store_experience=False)
    assert result["status"] == "FAIL_CLOSED__CONCEPT_UNRECOGNIZED"


def test_mixed_domains_fail_closed(workspace, engine):
    result = engine.solve_task(
        "Count functions in sample.py and data.json", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["status"] == "FAIL_CLOSED__DOMAIN_UNRECOGNIZED"


def test_negation_fails_closed(workspace, engine):
    result = engine.solve_task(
        "Count functions without touching sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["status"] == "FAIL_CLOSED__UNGROUNDED_NEGATION"


def test_qualifier_on_non_named_concept_fails_closed(workspace, engine):
    result = engine.solve_task(
        "Count if statements with at least 2 arguments in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["status"] == "FAIL_CLOSED__INAPPLICABLE_QUALIFIER"


def test_qualifier_on_wrong_domain_fails_closed(workspace, engine):
    result = engine.solve_task(
        "Count functions with at least 2 parameters in data.json", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    # the domain-coherent lexicon refuses the concept before qualifiers are considered
    assert result["status"] == "FAIL_CLOSED__CONCEPT_UNRECOGNIZED"


def test_infeasible_qualifier_window_fails_closed(workspace, engine):
    result = engine.solve_task(
        "Count functions with at least 5 parameters and at most 2 parameters in sample.py",
        work_cwd=workspace, learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["status"] == "FAIL_CLOSED__INAPPLICABLE_QUALIFIER"


def test_unparseable_qualifier_marker_fails_closed(workspace, engine):
    result = engine.solve_task(
        "Count parameters with at least 2 in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["status"] == "FAIL_CLOSED__QUALIFIER_UNPARSED"


def test_breakdown_with_qualifiers_fails_closed(workspace, engine):
    result = engine.solve_task(
        "breakdown of public functions in sample.py", work_cwd=workspace,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["status"] == "FAIL_CLOSED__INAPPLICABLE_QUALIFIER"


def test_open_ended_goal_is_refused_not_guessed(engine):
    result = engine.solve_task(
        "Fix the failing tests in this repository", work_cwd=REPO_ROOT,
        learn_update=False, persist_policy=False, store_experience=False,
    )
    assert result["pass"] is False
    assert result["status"] == "FAIL_CLOSED__OPERATION_UNRECOGNIZED"
    assert result["answer"] is None


# ---------------------------------------------------------------------------
# Pillar 1 — the online parametric policy model
# ---------------------------------------------------------------------------

def test_policy_learns_from_verified_experience(tmp_path):
    model = OnlineParametricPolicyModel(state_path=tmp_path / "policy.json")
    receipt = model.update_from_experience(
        "count functions in x.py", "count", "function", "python_ast", persist=True,
    )
    assert receipt["post_loss"] < receipt["pre_loss"]
    assert receipt["delta_w_l2"] > 0.0
    assert receipt["heads_updated"] == ["op", "concept", "domain"]
    assert receipt["updates"] == 1
    reloaded = OnlineParametricPolicyModel(state_path=tmp_path / "policy.json")
    assert reloaded.updates == 1


def test_policy_prediction_distribution_sums_to_one(tmp_path):
    model = OnlineParametricPolicyModel(state_path=tmp_path / "policy.json")
    out = model.predict("count functions in x.py")
    for head in ("operation", "concept", "domain"):
        assert abs(sum(out[head].values()) - 1.0) < 1e-6


def test_policy_receipt_present_in_verified_answer(workspace, engine):
    result = engine.solve_task("Count functions in sample.py", work_cwd=workspace,
                               learn_update=True, persist_policy=False, store_experience=False)
    receipt = result["policy_receipt"]
    assert receipt["post_loss"] < receipt["pre_loss"]
    assert 0.0 <= receipt["pre_correct_prob"] <= 1.0


def test_backwards_compatible_generalize_and_solve_shape(workspace, tmp_path, monkeypatch):
    monkeypatch.chdir(workspace)
    state = tmp_path / "genstate2"
    state.mkdir()
    from canonical.swe_kernel.semantic_generalization_engine_v1 import SemanticGeneralizationEngine

    compat = SemanticGeneralizationEngine(
        experiences_path=state / "exp.json",
        embeddings_path=state / "emb.json",
        policy_path=state / "policy.json",
    )
    result = compat.generalize_and_solve("Count functions in sample.py", top_k=3)
    for key in ("novel_task", "similar_experiences_found", "top_similarities", "adapted_strategy", "timestamp", "pass", "status", "answer"):
        assert key in result


# ---------------------------------------------------------------------------
# Integration — solve_or_learn honours the Mapping request-level `learn` flag
# ---------------------------------------------------------------------------

ASSOC_MEM = REPO_ROOT / "canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json"
GEN_EXP = REPO_ROOT / "canonical/astra_runtime/generalization/GENERALIZATION_EXPERIENCES_V1.json"
GEN_POLICY = REPO_ROOT / "canonical/astra_runtime/generalization/GENERALIZATION_POLICY_V1.json"


@pytest.fixture()
def tracked_state_guard():
    snapshots = {p: (p.read_bytes() if p.is_file() else None) for p in (ASSOC_MEM, GEN_EXP, GEN_POLICY)}
    try:
        yield
    finally:
        for path, before in snapshots.items():
            if before is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(before)


def test_mapping_learn_false_is_honoured_and_structured(tracked_state_guard):
    from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn

    result = solve_or_learn({
        "goal": "How many classes does canonical/swe_kernel/verified_skill_crystallizer_v1.py contain?",
        "learn": False,
    })
    assert result.get("pass") is True
    assert isinstance(result.get("answer"), int)
    assert result["answer"] == 1


def test_mapping_learn_flag_must_be_bool(tracked_state_guard):
    from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn

    with pytest.raises(ValueError):
        solve_or_learn({"goal": "anything", "learn": "yes"})


def test_mapping_learn_true_novel_phrasing_answered_by_engine(tracked_state_guard, tmp_path):
    from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn

    goal = "Count for loops in canonical/runtime/solve_v1.py"
    result = solve_or_learn({"task_id": "engine-integration", "goal": goal, "learn": True})
    assert result.get("pass") is True
    expected = _independent_python_counts((REPO_ROOT / "canonical/runtime/solve_v1.py").read_text(encoding="utf-8"))["for_loop"]
    assert result.get("answer") == expected
