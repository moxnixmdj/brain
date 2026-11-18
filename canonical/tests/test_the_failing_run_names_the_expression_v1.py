"""The blame has to be causal, and an empty suite has to stop the run instead of passing it.

Two defects were found by running this on real code before any of it was believed:

  * the first blame picked the *accumulated* message string, which contains the failure text and is the
    longest match, so it had no arguments to blame at all -- the tool fell back to matching any value
    that appeared in the text and blamed `'bar'`, an envvar from an unrelated branch;
  * `requests` and `httpx` conftests import `urllib3`; when it was missing, pytest produced no verdict
    lines, the pool saw an empty verdict map, and the run reported `NO_ORACLE` -- "the project's tests
    pass on the parent" -- for 19 commits that had never run a single test.

These tests pin the blame chain (message -> formatter -> argument), the ordering of the derived
candidates, and the refusal to call an empty suite a pass.
"""

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import the_failing_run_names_the_expression_v1 as blame  # noqa: E402

FAILURE = ('assert "Error: Missing option \'--foo\'." in "Error: Missing option \'--foo\' '
           '(env var: \'None\')."')


def records():
    """One trace of the click bug, cut down to the four records the blame has to separate."""
    return [
        {"line": 2680, "expr": "self.show_envvar", "value": "True", "type": "bool"},
        {"line": 2680, "expr": "f\" (env var: '{self.envvar}')\"", "value": '" (env var: \'bar\')"',
         "type": "str"},
        {"line": 2680, "expr": "f\" (env var: '{self.envvar}')\"", "value": '" (env var: \'None\')"',
         "type": "str"},
        {"line": 2680, "expr": "self.envvar", "value": "'bar'", "type": "str"},
        {"line": 2680, "expr": "self.envvar", "value": "None", "type": "NoneType"},
        {"line": 2690, "expr": "result", "value": '"Error: Missing option \'--foo\' (env var: \'None\')"',
         "type": "str"},
    ]


def test_the_blame_is_the_argument_of_the_message_not_the_accumulator():
    blamed = blame.blame_from_messages(records(), FAILURE)
    assert blamed, "the message that carries the failure has an argument to blame"
    assert blamed[0]["expr"] == "self.envvar", blamed


def test_the_blame_picks_the_occurrence_that_made_that_message():
    """`self.envvar` held `'bar'` earlier in the same test. The message carries `None`."""
    blamed = blame.blame_from_messages(records(), FAILURE)
    assert [b["value"] for b in blamed] == ["None"], blamed


def test_an_accumulated_string_cannot_be_a_message():
    """It has no `FormattedValue`, so it has no arguments, so it is not the thing that formatted."""
    assert blame._formatted_arguments("result") == []
    assert blame._formatted_arguments("f\" (env var: '{self.envvar}')\"") == ["self.envvar"]


def test_the_fallback_blame_ignores_a_bare_hole():
    """`{x}` is an f-string hole, not a value; recording it blamed the text of the hole."""
    found = blame.blame(records() + [{"line": 1, "expr": "{self.envvar}", "value": "None", "type": "str"}],
                        'the answer was None')
    assert all("{" not in record["expr"] for record in found)


def test_a_none_blame_offers_the_none_test_first():
    candidates = blame.derived_candidates("self.show_envvar", "self.envvar", "None")
    assert candidates[0] == "(self.show_envvar) and (self.envvar) is not None", candidates


def test_another_value_offers_its_own_exclusion_first():
    candidates = blame.derived_candidates("x > 0", "limit", "7")
    assert candidates[0] == "(x > 0) and (limit) != 7", candidates


def test_the_guard_is_the_innermost_one_above_the_blamed_value():
    source = ("def f(self):\n"
              "    if self.a:\n"
              "        if self.b:\n"
              "            out = f\"{self.c}\"\n"
              "    return out\n")
    guard_line, text, start, end = blame.guard_span(source, 4)
    assert (guard_line, text) == (3, "self.b")
    assert source.splitlines()[2][start:end] == "self.b"


def test_an_empty_verdict_map_is_not_a_passing_suite(tmp_path):
    """A conftest that cannot import is not a green suite. This is the 19-commit defect."""
    (tmp_path / "conftest.py").write_text("import a_module_that_does_not_exist\n")
    (tmp_path / "test_x.py").write_text("def test_ok():\n    assert True\n")
    outcomes, output = identify.run_tests_full(tmp_path, "test_x.py", seconds=60)
    assert outcomes == {}, outcomes
    assert "ModuleNotFoundError" in output or "ImportError" in output, output[-300:]
