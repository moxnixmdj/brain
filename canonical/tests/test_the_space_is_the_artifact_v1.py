"""The ceiling must be measured against a space that can say the fix, and the walls must be named.

Four things are pinned here, each of which was wrong at some point while this round was built:

  * crossing the names in scope with the file's own attribute vocabulary is what makes a fix like
    `ca.converter -> ca._converter` sayable at all -- the merged proximity pool never crossed them, and
    the first construction here did not either;
  * the attribute vocabulary of a value (`", ".join(parts)`) is not in the artifact and is in the
    interpreter, so it must be computed from `dir()` at run time rather than stored;
  * a miss has a KIND, and the kind decides whether the wall is this construction's poverty (a missing
    production), the parent file's vocabulary, or genuine new content. A miss that is reported without
    its kind is a claim about the world that was never checked;
  * a commit whose fix is two edits is EXCLUDED, not scored as a miss: 10 of 19 fresh real commits are
    of that shape, and calling them failures of a single-expression space would be a lie about the world.

The end-to-end test runs a REAL patch against a REAL failing test, because a space that cannot produce a
green suite has measured nothing.
"""

import ast
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import the_space_is_the_artifact_v1 as sp  # noqa: E402

FIXTURE = '''
class CountingAttr:
    def __init__(self, converter=None):
        self._converter = converter

    def converter(self):
        return self._converter


def make(ca):
    return ca.converter
'''


def test_the_crossing_says_an_attribute_the_site_never_mentions():
    """`ca._converter` is the human's fix and nothing in the file writes `ca._converter`."""
    text = sp.attribute_vocabulary(FIXTURE)
    assert "_converter" in text
    said = [candidate for _ring, candidate in sp.atoms(FIXTURE, 11, "ca.converter")]
    assert "ca._converter" in said
    assert "ca.converter" in said


def test_the_merged_proximity_pool_could_not_say_it():
    """The delta this round's construction buys, asserted against the construction that existed."""
    said = [candidate for _ring, candidate in sp.atoms(FIXTURE, 11, "ca.converter",
                                                       attributes_cap=0)]
    assert "ca._converter" not in said


def test_a_values_method_is_computed_from_the_machine_and_not_stored():
    source = 'VALUE = "a" + str(b)\n'
    assert "join" not in sp.attribute_vocabulary(source)
    live = sp.live_vocabulary()
    assert "join" in live and "copy" in live and "items" in live
    assert all(not name.startswith("_") for name in live)


def test_each_kind_of_miss_is_named_for_what_it_is():
    source = "def f(x, ca):\n    return ca.converter\n"
    vocabulary = sp.classify_miss("ca._converter", source, 2, "ca.converter")
    grammar = sp.classify_miss("[item for item in ca]", source, 2, "ca.converter")
    content = sp.classify_miss("ca.get('brand_new_key')", source, 2, "ca.converter")
    constant = sp.classify_miss("None", source, 2, "ca.converter")
    assert any(reason.startswith("VOCABULARY__") and "_converter" in reason for reason in vocabulary)
    assert any(reason.startswith("GRAMMAR__") for reason in grammar)
    assert any(reason.startswith("SPECIFICATION__") for reason in content)
    assert any(reason.startswith("THE_FIX_IS_A_BARE_CONSTANT") for reason in constant)


def test_a_miss_is_never_reported_as_impossible():
    """The tree's own law: a failure to find is about this code, not about the world."""
    for expression in ("ca._converter", "[i for i in ca]", "ca.get('k')", "None", "ca and ca"):
        reasons = sp.classify_miss(expression, "def f(ca):\n    return ca\n", 2, "ca")
        assert reasons
        assert not any("IMPOSSIBLE" in reason for reason in reasons)


def test_the_space_is_ordered_by_ring_then_size_and_ranks_are_contiguous():
    offered = list(sp.space(FIXTURE, 11, "ca.converter", cap=400))
    assert offered
    assert [rank for rank, _text, _ring in offered] == list(range(len(offered)))
    order = [(ring, sp.expressions._size(text)) for _rank, text, ring in offered]
    assert order == sorted(order)


def test_the_site_expression_itself_is_not_offered():
    offered = {text for _rank, text, _ring in sp.space(FIXTURE, 11, "ca.converter", cap=400)}
    assert "ca.converter" not in offered


def test_a_bare_constant_is_in_the_space_because_a_real_fix_was_one():
    """attrs 937b1e2328 fixed a default by changing `False` to `None`; refusing constants hid it."""
    offered = [text for _rank, text, _ring in sp.space("def f(x=0):\n    return x\n", 2, "x", cap=80)]
    assert "None" in offered and "False" in offered


def _repo(tmp_path: pathlib.Path, first: str, second: str, path: str = "pkg/m.py") -> tuple:
    repo = tmp_path / "r"
    (repo / pathlib.Path(path).parent).mkdir(parents=True)
    target = repo / path
    target.write_text(first, encoding="utf-8")
    for args in (["git", "init", "-q"], ["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "one"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    target.write_text(second, encoding="utf-8")
    for args in (["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "two"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                         capture_output=True, text=True).stdout.strip()
    return repo, sha


def test_one_expression_replacement_is_located_with_its_span(tmp_path):
    repo, sha = _repo(tmp_path, "def f(ca):\n    return ca.converter\n",
                      "def f(ca):\n    return ca._converter\n")
    parent = subprocess.run(["git", "show", f"{sha}^:pkg/m.py"], cwd=repo, check=True,
                            capture_output=True, text=True).stdout
    site = sp.site_of(repo, sha, "pkg/m.py", parent)
    assert site is not None
    assert site["line"] == 2
    assert site["old_expression"] == "ca.converter"
    assert site["human_expression"] == "ca._converter"
    start, end = site["span"]
    assert parent.splitlines()[1][start:end] == "ca.converter"


def test_a_commit_whose_fix_is_two_edits_is_excluded_not_scored(tmp_path):
    repo, sha = _repo(tmp_path, "def f(x, y):\n    return x + y\n",
                      "def f(x, y):\n    return x - y\n\n\ndef g(z):\n    return z\n")
    parent = subprocess.run(["git", "show", f"{sha}^:pkg/m.py"], cwd=repo, check=True,
                            capture_output=True, text=True).stdout
    assert sp.site_of(repo, sha, "pkg/m.py", parent) is None


@pytest.mark.skipif(not (ROOT / "canonical" / "tools").exists(), reason="tree")
def test_a_real_patch_greens_a_real_failing_test(tmp_path):
    """The search is blind: nothing reads the human expression, and a green suite is the only verdict."""
    pytest.importorskip("pytest")
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "m.py").write_text("def twice(x):\n    return x + 1\n", encoding="utf-8")
    (repo / "tests" / "test_m.py").write_text(
        "import os, sys\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n"
        "from m import twice\n\n\ndef test_twice():\n    assert twice(2) == 4\n\n\n"
        "def test_thrice():\n    assert twice(3) == 6\n", encoding="utf-8")
    for args in (["git", "init", "-q"], ["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "one"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    (repo / "src" / "m.py").write_text("def twice(x):\n    return x + x\n", encoding="utf-8")
    for args in (["git", "add", "-A"],
                 ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "two"]):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                         capture_output=True, text=True).stdout.strip()
    entry = {"repo": "fixture", "commit": sha, "sources": ["src/m.py"], "tests": ["tests/test_m.py"],
             "test": "tests/test_m.py", "repo_path": str(repo)}
    result = sp.explore(repo, entry, budget=64, cap=20_000, seconds=120, grammar="wide")
    assert result["stage"] == "VERIFIED", result
    assert 0 < result["oracle_calls"] <= 64
    assert result["parameters_stored"] == 0
    # one change point (`1` -> `x`) means the site is that sub-expression, not the whole line
    assert result["site_expression"] == "1"
    assert result["human_expression"] == "x"
    # the patch that was found really greens the file, checked here and not taken on trust: the
    # reported expression is written into the reported line and the suite is run again, by hand.
    subprocess.run(["git", "checkout", "-q", f"{sha}^", "--", "src/m.py"], cwd=repo, check=True)
    lines = (repo / "src" / "m.py").read_text(encoding="utf-8").splitlines(keepends=True)
    index = result["site_line"] - 1
    assert result["site_expression"] in lines[index]
    lines[index] = lines[index].replace(result["site_expression"], result["found"]["expression"], 1)
    (repo / "src" / "m.py").write_text("".join(lines), encoding="utf-8")
    again = sp.identify.run_tests(repo, "tests/test_m.py", 120)
    assert again and all(verdict == "PASSED" for verdict in again.values()), again


def test_a_rewrite_that_changes_two_nodes_is_one_site_not_an_exclusion(tmp_path):
    """`x + 1 -> x * 2` differs at the operator and at the operand; the site is the whole expression.

    Requiring exactly one differing node rejected every repair of this shape, which is why the first
    sweep reported 10 of 19 fresh commits as "not a single expression replacement". That number was a
    property of this file, not of the world.
    """
    repo, sha = _repo(tmp_path, "def f(x):\n    return x + 1\n", "def f(x):\n    return x * 2\n")
    parent = subprocess.run(["git", "show", f"{sha}^:pkg/m.py"], cwd=repo, check=True,
                            capture_output=True, text=True).stdout
    site = sp.site_of(repo, sha, "pkg/m.py", parent)
    assert site is not None
    assert site["old_expression"] == "x + 1"
    assert site["human_expression"] == "x * 2"
