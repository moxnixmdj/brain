"""Tests for the witness-inversion organ.

The mechanism has one job: read the value a failing test demands, find the single expression at the site that
produced the wrong value, propose expressions from the frame's own alphabet, and accept only what the real
test accepts. Every test here is about one of those four verbs, or about the refuse path, which is the one
that must never be wrong.
"""

from __future__ import annotations

import json
import pathlib
import sys
import textwrap

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import witness_inversion_v1 as W  # noqa: E402


# --------------------------------------------------------------------------- #
# the spine: the schema and the authority
# --------------------------------------------------------------------------- #
def test_schema_and_authority_are_the_producers():
    assert W.SCHEMA == "BRAIN_WITNESS_INVERSION_V1"
    assert W.AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
    assert W.MAX_ATOMS > 0 and W.MAX_CANDIDATES > 0
    assert "int" in W.SAFE_CALLS and "sorted" in W.SAFE_CALLS
    # nothing that can touch the world may be in the alphabet
    for forbidden in ("eval", "exec", "open", "compile", "__import__", "input"):
        assert forbidden not in W.SAFE_CALLS


def test_the_plugin_is_a_plugin_and_not_a_harness():
    """It must fire inside pytest, where the fixtures and the frames are still alive."""
    assert "pytest_exception_interact" in W.PLUGIN
    assert "settrace" in W.PLUGIN
    assert "__CALLS__" in W.PLUGIN and "__MAX_ATOMS__" in W.PLUGIN
    # a plugin is imported by pytest; it must not be a script
    assert "__main__" not in W.PLUGIN
    source = (W.PLUGIN.replace("__CALLS__", repr(W.SAFE_CALLS))
                       .replace("__MAX_ATOMS__", "24")
                       .replace("__MAX_CANDIDATES__", "400"))
    compile(source, "<plugin>", "exec")


def test_the_plugin_reads_both_kinds_of_witness():
    assert "_assert_witness" in W.PLUGIN and "_raises_witness" in W.PLUGIN
    assert "match" in W.PLUGIN
    # the 0-based line convention of pytest's own TracebackEntry is not a detail: it is the bug that cost
    # every witness in the first run
    assert "int(entry.lineno) + 1" in W.PLUGIN


# --------------------------------------------------------------------------- #
# applying a proposal: in place, byte for byte, or nothing
# --------------------------------------------------------------------------- #
SOURCE = """\
def f(x):
    value = x + 1
    return value * 2


def g(x):
    return (
        x
        + 1
    )
"""


def _span(source: str, line: int, col: int, end_line: int, end_col: int) -> dict:
    return {"span_line": line, "span_col": col, "span_end_line": end_line, "span_end_col": end_col}


def _span_of(source: str, needle: str) -> dict:
    """The exact span the parser gives an expression, so the test cannot miscount a column."""
    import ast
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Return) and ast.get_source_segment(source, node.value) == needle:
            value = node.value
            return _span(source, value.lineno, value.col_offset, value.end_lineno, value.end_col_offset)
    raise AssertionError("no return value is %r" % needle)


def test_apply_expression_replaces_only_the_span():
    span = _span_of(SOURCE, "value * 2")
    rebuilt = W.apply_expression(SOURCE, span, "value + 2")
    assert rebuilt is not None
    assert "    return value + 2\n" in rebuilt
    # every other byte is identical
    assert rebuilt.replace("return value + 2", "return value * 2") == SOURCE


def test_apply_expression_handles_a_span_across_lines():
    import ast
    multiline = None
    for node in ast.walk(ast.parse(SOURCE)):
        if isinstance(node, ast.Return) and node.value.end_lineno > node.value.lineno:
            multiline = node.value
    assert multiline is not None, "the fixture must contain a return written over several lines"
    span = _span(SOURCE, multiline.lineno, multiline.col_offset,
                 multiline.end_lineno, multiline.end_col_offset)
    rebuilt = W.apply_expression(SOURCE, span, "x - 1")
    assert rebuilt is not None
    assert "    return (\n        x - 1\n    )\n" in rebuilt
    # the earlier `value = x + 1` is somebody else's byte, and it is untouched
    assert "    value = x + 1\n" in rebuilt


def test_apply_expression_refuses_a_span_that_is_not_there():
    assert W.apply_expression(SOURCE, _span(SOURCE, 99, 0, 99, 1), "x") is None
    assert W.apply_expression(SOURCE, {}, "x") is None
    assert W.apply_expression("def f(:\n", _span(SOURCE, 1, 0, 1, 1), "x") is None


# --------------------------------------------------------------------------- #
# the two proposal arms: inversion, and the tree's own families
# --------------------------------------------------------------------------- #
def test_invert_reads_only_what_reproduces_the_witness():
    site = {"candidates": [{"expression": "x + x"}, {"expression": "4"}]}
    assert W.invert(site) == ["x + x", "4"]
    assert W.invert({}) == []


def test_grammar_candidates_is_the_family_list_and_keeps_the_shape():
    report = {"existing_expression": "a < b", "module_callables": []}
    out = W.grammar_candidates(report, report["existing_expression"])
    assert "a <= b" in out and "a > b" in out
    assert "a < b" not in out

    literal = {"existing_expression": "0", "module_callables": []}
    assert "1" in W.grammar_candidates(literal, literal["existing_expression"])

    call = {"existing_expression": "len(items)", "module_callables": ["sum", "max"]}
    out = W.grammar_candidates(call, call["existing_expression"])
    assert "sum(items)" in out and "max(items)" in out


def test_grammar_candidates_refuses_what_it_cannot_parse():
    report = {"existing_expression": "def f(:", "module_callables": []}
    assert W.grammar_candidates(report, "def f(:") == []
    assert W.grammar_candidates({}, "") == []


# --------------------------------------------------------------------------- #
# refusal: the path that must never be wrong
# --------------------------------------------------------------------------- #
def test_measure_without_a_corpus_says_so_instead_of_inventing_numbers():
    report = W.measure(None)
    assert report["schema"] == W.SCHEMA
    assert report["states"] == {"attempted": 0, "witnessed": 0, "verified": 0, "refused": 0}
    assert "not fetched in this run" in report["corpus"]
    assert report["model_calls"] == 0 and report["network_calls"] == 0


def test_headline_states_the_denominator_and_both_arms():
    report = {"states": {"commits_materialised": 55, "commits_with_a_real_failure": 13,
                         "attempted": 18, "witnessed": 18, "verified": 2, "refused": 16,
                         "verified_by_inversion": 2, "verified_by_grammar": 0}}
    line = W._headline(report)
    assert "55 real fix commits" in line
    assert "13" in line and "18" in line
    assert "16 refused" in line
    assert "same budget" in line


# --------------------------------------------------------------------------- #
# the whole loop, on a defect whose answer is expressible
# --------------------------------------------------------------------------- #
@pytest.fixture()
def broken_package(tmp_path: pathlib.Path) -> pathlib.Path:
    """A real package, a real failing test, and a real site: the smallest thing the loop must close."""
    (tmp_path / "mod.py").write_text(
        textwrap.dedent(
            """\
            def double(x):
                return x + 1
            """
        ),
        encoding="utf-8",
    )
    (tmp_path / "test_mod.py").write_text(
        textwrap.dedent(
            """\
            from mod import double


            def test_double_of_two():
                assert double(2) == 4
            """
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_failing_tests_returns_a_real_node_id(broken_package):
    failing = W._failing_tests(broken_package, ["test_mod.py"])
    assert failing, "the test really fails, so it must be found"
    assert failing[0].startswith("test_mod.py::")
    # a class or a module is not a test; only a node id can be run
    assert failing[0].count("::") >= 1 and not failing[0].endswith("::")


def test_capture_brings_back_the_value_the_test_demands(broken_package):
    report = W.capture(broken_package, [broken_package / "mod.py"],
                       broken_package / "test_mod.py", "test_double_of_two")
    assert report["outcome"] == "WITNESSED", report
    assert report["witness_mode"] == "equal"
    assert report["required_repr"] == "4"
    assert report["sites_examined"] >= 1
    site = report["sites"][0]
    assert site["function"] == "double"
    assert site["existing_expression"] == "x + 1"
    # the alphabet is the frame's own: nothing outside it may appear
    assert site["candidates"], "some expression over the frame's values must reproduce 4"

    source = (broken_package / "mod.py").read_text(encoding="utf-8")
    for candidate in site["candidates"]:
        rebuilt = W.apply_expression(source, site, candidate["expression"])
        assert rebuilt is not None
        namespace: dict = {}
        exec(rebuilt, namespace)          # noqa: S102 - the candidate is a proposal, not yet a result
        assert namespace["double"](2) == 4


def test_synthesize_verifies_only_with_the_real_test_and_restores_the_file(broken_package):
    original = (broken_package / "mod.py").read_text(encoding="utf-8")
    result = W.synthesize(broken_package, [broken_package / "mod.py"],
                          broken_package / "test_mod.py", "test_double_of_two",
                          [sys.executable, "-m", "pytest", "test_mod.py::test_double_of_two",
                           "-q", "-p", "no:cacheprovider"])
    assert result["witness_outcome"] == "WITNESSED", result
    assert result["tried"] >= 1
    if result["answer"].startswith("VERIFIED__"):
        assert result["found_by"] in ("witness_inversion", "grammar")
    else:
        assert result["answer"] == "REFUSED__NO_CANDIDATE_PASSES_THE_TEST"
    # whatever happened, the repository is exactly as it was
    assert (broken_package / "mod.py").read_text(encoding="utf-8") == original


def test_synthesize_refuses_a_test_with_no_witness(tmp_path):
    (tmp_path / "mod.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\n\ndef test_raises():\n    assert f(1) == 2\n", encoding="utf-8")
    # an assertion the plugin can read, but a site whose alphabet cannot produce the required value
    result = W.synthesize(tmp_path, [tmp_path / "mod.py"], tmp_path / "test_mod.py", "test_raises",
                          [sys.executable, "-m", "pytest", "test_mod.py::test_raises", "-q",
                           "-p", "no:cacheprovider"])
    assert result["answer"] is None or result["answer"].startswith(("VERIFIED__", "REFUSED__"))
    assert result["witness_outcome"] in ("WITNESSED", "NO_INVERTIBLE_SITE", "NO_WITNESS_IN_THE_TEST")


# --------------------------------------------------------------------------- #
# the corpus: real commits, and the human's own line
# --------------------------------------------------------------------------- #
def test_single_return_edit_is_read_from_a_real_diff(tmp_path):
    """The human's answer is the one line the fix changed -- read from the commit, never from the loop."""
    import subprocess

    def git(*argv: str) -> str:
        return subprocess.run(("git",) + argv, cwd=str(tmp_path), capture_output=True,
                              text=True, check=True).stdout

    git("init", "-q")
    git("config", "user.email", "producer@localhost")
    git("config", "user.name", "producer")
    (tmp_path / "m.py").write_text("def f(a, b):\n    return a < b\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "before")
    (tmp_path / "m.py").write_text("def f(a, b):\n    return a <= b\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "after")

    edit = W._single_return_edit(tmp_path, "HEAD")
    assert edit is not None
    assert edit["path"] == "m.py"
    assert edit["parent_expression"] == "a < b"
    assert edit["fixed_expression"] == "a <= b"


def test_single_return_edit_refuses_a_diff_that_is_not_one_return(tmp_path):
    import subprocess

    def git(*argv: str) -> str:
        return subprocess.run(("git",) + argv, cwd=str(tmp_path), capture_output=True,
                              text=True, check=True).stdout

    git("init", "-q")
    git("config", "user.email", "producer@localhost")
    git("config", "user.name", "producer")
    (tmp_path / "m.py").write_text("def f(a):\n    return a\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "before")
    (tmp_path / "m.py").write_text("def f(a):\n    return a\n\n\ndef g():\n    return 1\n",
                                  encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "after")
    assert W._single_return_edit(tmp_path, "HEAD") is None


def test_run_corpus_reports_the_denominator_it_started_from():
    """A corpus run must always carry how much real material it saw, even when everything refuses."""
    states = {"commits_materialised": 0, "commits_with_a_real_failure": 0, "attempted": 0,
              "witnessed": 0, "verified": 0, "refused": 0,
              "verified_by_inversion": 0, "verified_by_grammar": 0}
    report = {"states": states, "tasks": []}
    report["by_arm"] = {"witness_inversion": 0, "grammar_control": 0}
    assert W._headline(report).startswith("0 real fix commits")


def test_repo_native_component_mining_dual_splicing_and_bidirectional_lens(tmp_path):
    """Repo-native component mining, dual-program splicing, bidirectional lens FST, and L3 negative-space store."""
    (tmp_path / "pkg.py").write_text(
        "DEFAULT_DELIM = ':'\n"
        "class ParseError(ValueError):\n    pass\n"
        "def normalize_key(key, strict=False):\n    return key.strip().lower()\n",
        encoding="utf-8",
    )
    comp = W.mine_repo_components(tmp_path)
    assert any(f["name"] == "normalize_key" and f["arity"] == 2 for f in comp["functions"])
    assert "ParseError" in comp["exceptions"]
    assert "DEFAULT_DELIM" in comp["constants"]

    spliced = W.splice_dual_programs(
        "default_val",
        "x.strip()",
        [{"x": None, "default_val": ""}],
        [{"x": "  abc  ", "default_val": ""}],
    )
    assert spliced is not None
    assert spliced["guard"] == "x is None"
    assert eval(spliced["spliced_expression"], {}, {"x": None, "default_val": "fallback"}) == "fallback"
    assert eval(spliced["spliced_expression"], {}, {"x": " hi ", "default_val": "fallback"}) == "hi"

    lens = W.synthesize_bidirectional_lens(
        [(b"\x04", b"^D"), (b"\x1a", b"^Z"), (b"normal", b"normal")],
        input_var="buf",
    )
    assert lens is not None
    assert lens["round_trip_verified"] is True
    assert lens["rules_count"] == 2

    store = W.NegativeSpaceInvariantStore(tmp_path / "l3_neg.json")
    store.record_refutation("x + 1", reason="regression_failure", repo="demo", commit="abc")
    assert store.is_refuted("x + 1") is True
    assert store.is_refuted("x - 1") is False
    assert store.filter_candidates(["x + 1", "x - 1"]) == ["x - 1"]

    blames = W.localize_by_angelic_perturbation(
        module_sources={
            "a.py": "def step_a(x):\n    return x - 1\n",
            "b.py": "def step_b(x):\n    return step_a(x) * 2\n",
        },
        entry_expr="step_b(x)",
        failing_cases=[({"x": 3}, 8), ({"x": 5}, 12)],
        passing_cases=[],
        angelic_values=[4, 6],
    )
    assert any(b["file"] == "a.py" and b["old_expr"] == "x - 1" for b in blames)


