"""The classification of a real edit must survive three things: AST depth, scope, and the temptation to
report 100%.

The bug this file exists for: `single_change` first took the SHALLOWEST differing node, which is always
the module (every ancestor of an edit differs, because its dump contains the edit). That made every
real edit "not a single expression" -- 100% over 242 real commits -- which reads exactly like a law of
nature and was the instrument.
"""

import ast
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import what_a_real_fix_needs_from_the_site_v1 as needs  # noqa: E402

REPOS = pathlib.Path("/tmp/repos")
needs_repos = pytest.mark.skipif(not any((p / ".git").exists() for p in REPOS.iterdir())
                                 if REPOS.exists() else True, reason="no real repositories cloned")


def change(old: str, new: str):
    return needs.single_change(ast.parse(old), ast.parse(new))


def test_the_change_point_is_the_deepest_differing_node():
    found = change("fndoc = path.join(src_dir, 'README.rst')",
                   "fndoc = path.join(path.dirname(src_dir), 'README.rst')")
    assert found is not None
    old_expr, new_expr = found
    assert ast.unparse(old_expr) == "src_dir"
    assert ast.unparse(new_expr) == "path.dirname(src_dir)"


def test_a_missing_negation_is_one_change():
    found = change("x = sys._is_gil_enabled()", "x = not sys._is_gil_enabled()")
    assert found is not None
    assert ast.unparse(found[1]) == "not sys._is_gil_enabled()"


def test_two_independent_differences_are_not_one_edit():
    assert change("x = a.b + c", "x = a.d + e") is None


def test_a_structural_change_is_not_an_expression_change():
    assert change("rv = self.split(value)", "return self.split(value)") is None


def test_scope_contains_parameters_locals_imports_and_builtins():
    source = ("import os\n"
              "LIMIT = 3\n"
              "\n"
              "def f(raw):\n"
              "    cleaned = raw.strip()\n"
              "    return cleaned\n")
    scope = needs.names_in_scope(source, 6)
    assert {"os", "LIMIT", "raw", "cleaned", "len"} <= scope


def test_a_missing_name_is_reported_as_missing():
    source = "def f(n):\n    return n\n"
    scope = needs.names_in_scope(source, 2)
    assert "length_hint" not in scope


@needs_repos
def test_real_history_is_not_all_one_verdict():
    """The regression that matters: if a future change makes every real edit classify the same way
    again, this fails."""
    receipt = needs.sweep(REPOS, limit=400)
    examined = receipt["single_line_edits_examined"]
    assert examined > 20, receipt
    assert len(receipt["totals"]) >= 2, receipt["totals"]
    assert receipt["rates"].get(needs.IN_VOCABULARY, 0) > 0.2, receipt["rates"]
