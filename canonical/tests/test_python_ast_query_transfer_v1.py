"""Read-only Python AST queries must follow the current request, not a similar memory.

The seed corpus behind `solve_or_learn` contains "count functions", "find classes" and
"identify methods".  Before this module existed, the controller answered three different
questions with the same function count:

* "Count methods" counted every `FunctionDef`, including free and nested functions.
* "Count functions and classes" counted only functions.
* "Do not count functions" counted functions.

These tests pin the corrected contract: a small, explicit, read-only AST adapter binds the
operation and target from the *current* sentence, reads the *current* file under the caller's
workspace root, and refuses shapes it does not understand.  It is not a claim of general
semantic understanding, and it does not update model weights.

Authority: NONE.  Producer-run sandbox tests; temp directories only.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn  # noqa: E402

PASS_STATUS = "PASS__TIER0A_TYPED_PYTHON_AST_QUERY"

SOURCE = '''\
class Outer:
    def method(self):
        def helper():
            pass
        if True:
            pass

    async def amethod(self):
        pass

    class Nested:
        def nmethod(self):
            pass


def free():
    if False:
        pass
    elif True:
        pass


async def afree():
    pass
'''

# Hand-counted from SOURCE, not produced by the adapter under test.
FUNCTIONS = 6   # method, helper, amethod, nmethod, free, afree
METHODS = 3     # method, amethod, nmethod (helper is nested in a method, not a class)
CLASSES = 2     # Outer, Nested
IFS = 3         # one in method, if + elif in free


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "sample.py").write_text(SOURCE, encoding="utf-8")
    # A second file with identical structure but a name absent from the seed corpus.
    other = root / "pkg" / "unseen_module.py"
    other.parent.mkdir()
    other.write_text(SOURCE, encoding="utf-8")
    monkeypatch.setenv("BRAIN_COGNITIVE_STATE_DIR", str(tmp_path / "cognitive"))
    return root


def _solve(root: pathlib.Path, goal: str, **kwargs):
    return solve_or_learn(
        goal,
        learn=kwargs.pop("learn", True),
        cwd=root,
        db_path=root / "skills.sqlite",
        r3_state_path=root / "r3.json",
        allow_tier1_composition=False,
        allow_tier2_learning=False,
        allow_jit_network=False,
        record_open_gap=False,
        confinement_admitted=True,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("goal", "expected"),
    [
        ("Count if statements in sample.py", IFS),
        ("Count the number of methods in sample.py", METHODS),
        ("Count functions in sample.py", FUNCTIONS),
        ("Count classes in sample.py", CLASSES),
        ("How many async functions are in sample.py", None),  # unsupported refinement -> refuse
    ],
)
def test_count_binds_the_requested_node_kind(workspace, goal, expected):
    result = _solve(workspace, goal)
    if expected is None:
        assert result["pass"] is False, result
        assert result["status"].startswith("FAIL_CLOSED__PYTHON_AST"), result
    else:
        assert result["pass"] is True, result
        assert result["status"] == PASS_STATUS, result
        assert result["answer"] == expected, result
        assert result["from_memory"] is False, result


def test_multiple_targets_are_not_collapsed_into_the_first_keyword(workspace):
    result = _solve(workspace, "Count functions and classes in sample.py")
    assert result["pass"] is True, result
    assert result["answer"] == {"functions": FUNCTIONS, "classes": CLASSES}, result


def test_enumerate_returns_locations_not_a_count(workspace):
    result = _solve(workspace, "Enumerate subroutines in sample.py")
    assert result["pass"] is True, result
    names = {row["name"] for row in result["answer"]}
    assert names == {"method", "helper", "amethod", "nmethod", "free", "afree"}, result
    assert all(isinstance(row["line"], int) and row["line"] > 0 for row in result["answer"])


def test_negation_is_a_refusal_not_a_silent_affirmative(workspace):
    result = _solve(workspace, "Do not count functions in sample.py")
    assert result["pass"] is False, result
    assert result["status"].startswith("FAIL_CLOSED__PYTHON_AST"), result


def test_transfer_to_an_unseen_file_uses_the_same_typed_contract(workspace):
    result = _solve(workspace, "Count if statements in pkg/unseen_module.py")
    assert result["pass"] is True, result
    assert result["answer"] == IFS, result
    assert result["source_path"] == "pkg/unseen_module.py", result


def test_read_then_count_wording_is_supported(workspace):
    result = _solve(workspace, "Read sample.py and count methods")
    assert result["pass"] is True, result
    assert result["answer"] == METHODS, result


def test_missing_source_is_an_explicit_refusal(workspace):
    result = _solve(workspace, "Count functions in absent.py")
    assert result["pass"] is False, result
    assert result["status"] == "FAIL_CLOSED__PYTHON_AST_SOURCE_MISSING", result


def test_syntax_error_is_an_explicit_refusal(workspace):
    (workspace / "broken.py").write_text("def f(:\n", encoding="utf-8")
    result = _solve(workspace, "Count functions in broken.py")
    assert result["pass"] is False, result
    assert result["status"] == "FAIL_CLOSED__PYTHON_AST_PARSE_FAILED", result


def test_path_outside_workspace_is_refused(workspace, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text(SOURCE, encoding="utf-8")
    result = _solve(workspace, f"Count functions in {outside}")
    assert result["pass"] is False, result
    assert result["status"] == "FAIL_CLOSED__PYTHON_AST_PATH_OUTSIDE_ROOT", result


def test_symlink_escape_is_refused(workspace, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text(SOURCE, encoding="utf-8")
    (workspace / "link.py").symlink_to(outside)
    result = _solve(workspace, "Count functions in link.py")
    assert result["pass"] is False, result
    assert result["status"] == "FAIL_CLOSED__PYTHON_AST_PATH_OUTSIDE_ROOT", result


def test_write_request_is_not_intercepted_by_the_read_only_adapter(workspace):
    result = _solve(workspace, "Count functions in sample.py and write the report to out.json")
    assert result.get("tier_used") != "tier0a_typed_python_ast_query", result


def test_memory_off_still_uses_the_read_only_adapter(workspace):
    result = _solve(workspace, "Count methods in sample.py", learn=False)
    assert result["pass"] is True, result
    assert result["status"] == PASS_STATUS, result
    assert result["answer"] == METHODS, result


def test_answer_follows_current_bytes_not_a_previous_call(workspace):
    first = _solve(workspace, "Count functions in sample.py")
    assert first["answer"] == FUNCTIONS, first
    (workspace / "sample.py").write_text(SOURCE + "\ndef added():\n    pass\n", encoding="utf-8")
    second = _solve(workspace, "Count functions in sample.py")
    assert second["answer"] == FUNCTIONS + 1, second
    assert second["source_sha256"] != first["source_sha256"], second


def test_source_file_is_not_modified(workspace):
    before = (workspace / "sample.py").read_bytes()
    _solve(workspace, "Count functions in sample.py")
    assert (workspace / "sample.py").read_bytes() == before


def test_acceptance_is_labelled_structural_not_independent(workspace):
    result = _solve(workspace, "Count classes in sample.py")
    assert result["acceptance"] == {
        "checked": True,
        "basis": "python_ast",
        "independent_oracle": False,
        "rows_checked": CLASSES,
    }, result
    assert result["semantic_acceptance_complete"] is False, result


def test_parser_refuses_ambiguous_and_unsupported_shapes():
    from canonical.runtime import python_ast_query_v1 as adapter

    assert adapter.parse_query("Count functions in a.py and write out.json") is None
    assert adapter.parse_query("Explain the architecture of sample.py") is None
    with pytest.raises(adapter.PythonAstQueryError) as multi:
        adapter.parse_query("Count functions in a.py and b.py")
    assert multi.value.code == "AMBIGUOUS_SOURCE"
    with pytest.raises(adapter.PythonAstQueryError) as target:
        adapter.parse_query("Count imports in sample.py")
    assert target.value.code == "UNSUPPORTED_TARGET"
    with pytest.raises(adapter.PythonAstQueryError) as negated:
        adapter.parse_query("Count functions except methods in sample.py")
    assert negated.value.code == "NEGATED_OR_FILTERED_QUERY"


def test_method_scope_is_lexical_not_any_enclosing_class():
    from canonical.runtime import python_ast_query_v1 as adapter

    source = '''\
def factory():
    class Local:
        def method(self):
            def helper():
                pass
'''
    tree = __import__("ast").parse(source)
    rows = adapter._collect(tree)
    methods = [row["qualname"] for row in rows if row["kind"] == "methods"]
    functions = [row["qualname"] for row in rows if row["kind"] == "functions"]
    assert methods == ["factory.Local.method"], methods
    assert functions == ["factory", "factory.Local.method", "factory.Local.method.helper"], functions
