"""The demand must come from the program, the table must constrain it, and a green file must not be a lie.

Five defects were produced by this instrument on its first real runs, and every one of them is pinned
here, because each of them would have shipped a false number:

  * the helper was written above a `from __future__` import, so the module stopped parsing and the row
    was reported as `NO_ASSERTION_DEMAND` -- a false negative manufactured by the tool;
  * pytest's own `Failed` exception was read as a demand, and its args are pytest's *rendering* of the
    failure, so a line of code was replaced by the string `assert 2 == 0 ... <Result ...>` and the file
    stayed green. That is a plausible patch, not a fix, and it is the trap this tree keeps naming;
  * a candidate that calls a function calling `sys.exit` raised `SystemExit`, which is not an `Exception`
    and killed the driver for a whole row;
  * the dotted module name derived from a path under `src/` is wrong (`src.attr._make` vs `attr._make`),
    so every row claimed the site never ran;
  * the demand was compared to the site's value as a whole, so `(msg,) == exc.args` never related a
    string site to the message it must produce.

The end-to-end tests run real patches against real failing tests and a real second test that must not
break: a green suite alone is what a lie looks like.
"""

import ast
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import the_assertion_is_the_demand_v1 as demand  # noqa: E402


def test_the_helper_never_splits_a_future_import():
    source = "from __future__ import annotations\n\n\ndef f(x):\n    return x + 1\n"
    site_line, span = 5, (11, 16)
    instrumented = demand.instrument(source, site_line, span)
    assert instrumented.startswith("from __future__ import annotations")
    ast.parse(instrumented)
    assert demand.HELPER in instrumented


def test_a_rewritten_line_still_means_the_same_expression():
    source = "def f(x):\n    return x + 1\n"
    instrumented = demand.instrument(source, 2, (11, 16))
    tree = ast.parse(instrumented)
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "f")
    call = function.body[0].value
    assert isinstance(call, ast.Call) and call.func.id == demand.HELPER


class _Info:
    def __init__(self, value):
        self.value = value
        self.typename = type(value).__name__


class _Call:
    def __init__(self, value, when="call"):
        self.excinfo = _Info(value) if value is not None else None
        self.when = when


class _Item:
    def __init__(self, nodeid):
        self.nodeid = nodeid


class _PytestFailed(Exception):
    """Stands in for _pytest.outcomes.Failed, which carries the runner's own rendering in its args."""


_PytestFailed.__name__ = "Failed"


def test_the_runners_own_rendering_is_not_a_demand():
    capture = demand.Capture("")
    capture.pytest_runtest_makereport(
        _Item("t::a"), _Call(_PytestFailed("assert 2 == 0\n + where 2 = <Result SystemExit(2)>.exit_code")))
    assert capture.rows == []


def test_a_real_exception_still_carries_its_args():
    capture = demand.Capture("")
    capture.pytest_runtest_makereport(_Item("t::a"), _Call(ValueError("bad value", 3)))
    assert capture.rows and capture.rows[0]["right"] == ("bad value", 3)


def test_a_patch_made_of_the_reporters_text_is_refused_by_the_file():
    source = "def f(x):\n    return x + 1\n"
    test_source = "def test_a():\n    assert f(2) == 3\n"
    assert not demand.plausible("'assert 2 == 0 + where 2 = <Result SystemExit(2)>'", source, test_source)
    assert demand.plausible("'the exact message the test demands'", source,
                            "assert str(e) == 'the exact message the test demands'")


def test_the_demand_is_aligned_to_the_site():
    # `assert (msg,) == exc.args` against a string site is the exception-args convention, not equality
    unwrapped = demand.site_demand(("the message",), ["the message"])
    assert unwrapped == ("the message", "UNWRAPPED")
    element = demand.site_demand(("a", "b"), [("a", "b")])
    assert element is not None
    # A one-element tuple demand binds across the unwrap *only* when it is the same slot. This assertion
    # used to demand the opposite — that any one-element tuple bind to any string — and that is exactly
    # how the instrument came to accuse two human fixes whose message merely differed from the site's
    # (jinja `a150ff749a`, attrs `13105a64f2`). The demand is *meant* to differ; sharing no content means
    # it was never about this site.
    assert demand.site_demand(("the message",), ["something else"]) is None
    assert demand.site_demand(("the message, for 'x'",), ["the message"]) == (
        "the message, for 'x'", "UNWRAPPED")
    assert demand.site_demand(object(), [1, 2]) is None


def test_an_unrelated_demand_is_refused_rather_than_guessed():
    class Thing:
        def __eq__(self, other):
            return False
        __hash__ = None

    assert demand.site_demand(Thing(), [1]) is None


def test_the_induced_template_reproduces_the_demand():
    frames = [{"name": "x", "__globals__": {}}]
    made = demand.induced_string_candidates("annotation conflict for 'x'.", frames)
    assert made, "no template was induced"
    for expression in made:
        value = eval(expression, {}, {"name": "x"})  # noqa: S307
        assert value == "annotation conflict for 'x'."


def test_a_candidate_that_exits_is_refused_not_fatal():
    namespace = {"boom": lambda: (_ for _ in ()).throw(SystemExit(2)), "__globals__": {}}
    assert demand.evaluate("boom()", [namespace]) is None


def _repo(tmp_path, source, tests) -> tuple[pathlib.Path, str]:
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "m.py").write_text(source, encoding="utf-8")
    (repo / "tests" / "test_m.py").write_text(tests, encoding="utf-8")
    for args in (["git", "init", "-q"], ["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "one"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    (repo / "src" / "m.py").write_text(source.replace("x + 1", "x + x"), encoding="utf-8")
    for args in (["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "two"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                         capture_output=True, text=True).stdout.strip()
    return repo, sha


TWO_DEMANDS = (
    "import os, sys\n"
    "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n"
    "from m import twice\n\n\n"
    "def test_two():\n    assert twice(2) == 4\n\n\n"
    "def test_three():\n    assert twice(3) == 6\n"
)


@pytest.mark.skipif(not (ROOT / "canonical" / "tools").exists(), reason="tree")
def test_two_demands_and_a_passing_test_constrain_the_candidate(tmp_path):
    """The table is the instrument: one point of demand is not a specification."""
    repo, sha = _repo(tmp_path, "def twice(x):\n    return x + 1\n", TWO_DEMANDS)
    entry = {"repo": "fixture", "commit": sha, "sources": ["src/m.py"], "test": "tests/test_m.py",
             "repo_path": str(repo)}
    result = demand.explore(repo, entry, cap=20_000, survivors_cap=12, verifications=8, seconds=120)
    # `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` is now the honest answer for this fixture: the only
    # "demand" it ever produced was pytest's rendering, which the reader refuses as prose.
    assert result["stage"] in ("DEMAND_MET", "NO_VALUE_MATCHES",
                               "NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE"), result
    if result["stage"] == "DEMAND_MET":
        assert result["found"]["tests_green"] >= 2
        assert result["parameters_stored"] == 0
        # The site here is the literal `1` inside `return x + 1`, so the replacement is `x` -- the
        # enclosing `x + x` is the human's fix, produced by substituting at the site, not by rewriting it.
        found = result["found"]["expression"]
        assert found != "1", found
        # substituting at the site: `x + 1` becomes `x + (<found>)`
        assert eval(f"x + ({found})", {}, {"x": 2}) == 4, found  # noqa: S307
        assert eval(f"x + ({found})", {}, {"x": 3}) == 6, found  # noqa: S307


def test_a_constant_that_greens_one_test_and_breaks_another_is_refused(tmp_path):
    """`9` satisfies the failing assertion and destroys the passing one; the table must say no."""
    tests = (
        "import os, sys\n"
        "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n"
        "from m import f\n\n\n"
        "def test_a():\n    assert f(2) == 3\n\n\n"
        "def test_b():\n    assert f(2) == 9\n"
    )
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "m.py").write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
    (repo / "tests" / "test_m.py").write_text(tests, encoding="utf-8")
    for args in (["git", "init", "-q"], ["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "one"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    (repo / "src" / "m.py").write_text("def f(x):\n    return x * 9\n", encoding="utf-8")
    for args in (["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "two"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                         capture_output=True, text=True).stdout.strip()
    entry = {"repo": "fixture", "commit": sha, "sources": ["src/m.py"], "test": "tests/test_m.py",
             "repo_path": str(repo)}
    result = demand.explore(repo, entry, cap=20_000, survivors_cap=12, verifications=8, seconds=120)
    assert result["stage"] != "DEMAND_MET", result


def test_the_witness_is_not_the_demand():
    """`assert not x` demands falsiness; x is the witness that the demand was violated.

    Reading x as the demand made a measured row (click 18d29196c5) demand an `AssertionError` object
    that no expression in any grammar could produce -- a false negative manufactured by the reader.
    """
    assert demand.assert_form("assert not excinfo\n", 1) == ("falsy", None)
    assert demand.assert_form("assert value is None\n", 1) == ("is_none", None)
    assert demand.assert_form("assert value is not None\n", 1) == ("is_not_none", None)
    assert demand.assert_form("assert f(2) == 3\n", 1) == ("compare", None)
    assert demand.assert_form("assert flag\n", 1) == ("truthy", None)
    assert demand.assert_form("x = 1\n", 1) == ("unknown", None)


def test_the_live_set_is_counted_at_every_contrast_depth():
    """|S_k| counts the candidates that satisfy the first k contrasts; |S_0| is one trace's live set.

    The real rows measured 6,924 and 21,051 candidates admitting the single demanded value, and 154,157
    offered. The arithmetic of the count is what must not be wrong, so it is pinned here directly.
    """
    masks = {0b000: 5, 0b001: 3, 0b011: 2, 0b111: 1}
    assert demand.survivors_at(masks, 0) == 11
    assert demand.survivors_at(masks, 1) == 6
    assert demand.survivors_at(masks, 2) == 3
    assert demand.survivors_at(masks, 3) == 1
    assert demand.survivors_at(masks, 4) == 0  # no candidate survives a contrast it never met


def test_the_identify_curve_never_increases():
    """More observation can only remove candidates; a curve that rises is a counting defect."""
    depths = {0: 900, 1: 60, 2: 7, 5: 1}
    curve = demand.contraction(depths, 5)
    assert curve[0] == 968
    assert curve[1] == 68
    assert curve[2] == 8
    assert curve[3] == 1
    assert curve[5] == 1
    assert [curve[k] for k in range(6)] == sorted((curve[k] for k in range(6)), reverse=True)


def test_explore_reports_the_ambiguity_of_the_gate(tmp_path):
    """The receipt must carry how many DISTINCT rules the suite accepts, or the ambiguity is invisible."""
    repo, sha = _repo(tmp_path, "def twice(x):\n    return x + 1\n", TWO_DEMANDS)
    entry = {"repo": "fixture", "commit": sha, "sources": ["src/m.py"], "test": "tests/test_m.py",
             "repo_path": str(repo)}
    result = demand.explore(repo, entry, cap=20_000, survivors_cap=8, verifications=6, seconds=120,
                            count_contrasts=True, identify_curve=True, audit=True)
    assert isinstance(result.get("greens"), list)
    assert result.get("green_count") == len(result["greens"])
    contrast = result.get("contrast") or {}
    assert sum((contrast.get("masks") or {}).values()) == contrast.get("admissible", 0)
    curve = result.get("identify_curve") or {}
    if curve:
        values = [curve["curve"][str(k)] for k in range(curve["observations"] + 1)]
        assert values == sorted(values, reverse=True)


def test_a_rendered_assertion_is_not_a_demand():
    """pytest's rendering of a failure is not a value the site owes, and reading it as one accuses the truth.

    On the audit this was measured: three of fourteen rows carried a demand that began with `assert `, and
    the instrument then reported that the human's own fix "produced the wrong value".
    """
    assert demand.is_prose_demand("assert 'line one\nline two\n\n' == 'line one\n\n + where x = 1")
    assert demand.is_prose_demand("assert not AssertionError('assert a is not b')")
    assert demand.is_prose_demand("Failed: DID NOT RAISE <class 'ValueError'>")
    assert not demand.is_prose_demand("Type annotation and type argument cannot both be present for 'x'.")
    assert not demand.is_prose_demand(0)
    assert not demand.is_prose_demand(("the message",))
    assert not demand.is_prose_demand("")


def test_a_demand_is_bound_by_the_slot_not_by_equality():
    """`0 == False` in Python, so equality alone binds a demand to a comparison the site never fed.

    That is exactly how the instrument accused the human's own fix of producing "the wrong value" for an
    assertion it had nothing to do with (`demanded=[0] produced=[True]`).
    """
    assert demand.site_demand(0, [False]) is None
    assert demand.site_demand(1, [True]) is None
    assert demand.site_demand(False, [False]) == (False, "DIRECT")
    assert demand.site_demand("a message", ["a message"]) == ("a message", "DIRECT")


def test_the_demanded_text_may_differ_but_must_be_the_same_slot():
    """A repair IS a difference in content; what must not differ is the kind of thing the slot holds."""
    old = "Type annotation and type argument cannot both be present"
    new = "Type annotation and type argument cannot both be present for 'x'."
    assert demand.site_demand((new,), [old]) == (new, "UNWRAPPED")
    # an exception message bound to a bool site is not that site's slot
    assert demand.site_demand(("'MyConv' object has no attribute '_fmt'",), [True]) is None
    # nor is an unrelated string bound to a string site
    assert demand.site_demand(("'coroutine' object is not subscriptable",), ["jinja2.compiler"]) is None
    assert demand.same_slot(new, old) is True
    assert demand.same_slot("unrelated", "jinja2.compiler") is False
    assert demand.same_slot(True, 1) is False


def test_a_paired_demand_may_differ_from_what_the_site_produced():
    """The one thing a demand may never do is equal the site's value *because* it is the repair.

    A test that demands 2 where the site produces 3 is the ordinary shape of a numeric bug, and a message
    repair demands text that differs from the message the site emits. Both are bound by the pairing -- the
    assertion's other operand already holds what the site produced -- and not by equality, which refuses
    exactly the rows worth verifying.
    """
    assert demand.site_demand(2, [3], paired=True) == (2, "DIRECT")
    assert demand.site_demand("the message, corrected", ["the message"], paired=True) == (
        "the message, corrected", "DIRECT")
    assert demand.site_demand(("the message, corrected",), ["the message"], paired=True) == (
        "the message, corrected", "UNWRAPPED")
    # without that evidence the same demand is not bound to that site at all
    assert demand.site_demand(2, [3]) is None
    assert demand.site_demand("the message, corrected", ["the message"]) is None


def test_the_specification_is_the_failing_test_and_not_the_whole_file():
    """A test states what it expects; the other tests in the file state something else.

    Reading the file's literals would put another test's expected value into this site's demand -- and the
    site would then be asked to produce a value its own failing test never mentions.
    """
    import textwrap
    source = textwrap.dedent('''
        def test_one():
            assert render("x") == "for x."

        def test_two():
            assert render("y") == "a completely different message"
            assert 7 == 7
    ''')
    one = demand.test_literals(source, "tests/test_m.py::test_one")
    two = demand.test_literals(source, "tests/test_m.py::test_two")
    assert sorted(one) == sorted(["x", "for x."])
    assert "a completely different message" in two and "for x." not in two
    # a boolean is a predicate, never a demanded value
    assert True not in one and True not in two
    assert demand.test_literals(source, "tests/test_m.py::test_missing") == []


def test_a_specification_demand_never_wears_the_bound_demand_s_verdict():
    """A demand read from the test's own text is weaker evidence than a demand bound at runtime.

    Reporting the weaker one as `NO_VALUE_MATCHES` would claim the instrument proved no expression can
    produce the demand, when all it proved is that the closure was searched against a literal.
    """
    tool = (pathlib.Path(__file__).resolve().parents[1] / "tools" /
            "the_assertion_is_the_demand_v1.py").read_text(encoding="utf-8")
    assert '"SPEC_DEMAND_FOUND_NOTHING"' in tool
    assert 'demand_provenance' in tool
    # the fallback fires only when nothing bound at runtime
    assert 'if not targets:' in tool and 'SPEC_LITERALS' in tool


def test_test_literals_cross_the_process_boundary_as_source_text():
    """The config is JSON: a bytes literal in it killed two whole rows before this was fixed."""
    import textwrap
    source = textwrap.dedent('''
        def test_bytes():
            assert b"#compdef cli" in out
    ''')
    values = demand.test_literals(source, "tests/test_t.py::test_bytes")
    assert any(isinstance(value, bytes) for value in values)
    encoded = json.dumps([demand.live_repr(value) for value in values])
    assert json.loads(encoded)


# The candidate-side gate for specification demands is measured on REAL material rather than reproduced
# in a fixture: click 91de59c6c8, where the ungated instrument accepted `flag_value` (533 tests green,
# 0 of 12 recorded passing values preserved, human fix 12 of 12). A fixture that reproduces it would
# prove only that the fixture fails the same way.
