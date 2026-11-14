"""The ledger must be able to say NO, and must refuse to say anything when the runner said nothing.

Every case here is a defect this tool actually shipped with during development, found by pointing it
at real repositories:

1. **A runner that ran nothing passed everything.** `torproject/stem`'s first invocation reported
   "Ran 1 test ... OK" for the whole of `test/unit/util`, all 12 reverted fixes came back
   `REVERT_NOT_NOTICED`, and not one of them was evidence. Same shape as this repository's own
   "our verifier was running zero tests and reporting PASS". Now `CHECK_RAN_NOTHING`.
2. **A version bump counted as an unprotected fix.** Two of the first 20 commits on
   `more-itertools` were a version bump and a docstring edit. Nobody writes a test for those.
3. **A type hint counted as an unprotected fix.** `stem`'s "Fix timeout argument type hint" is not
   something any test can notice at runtime.
4. **`import packaging` resolved to site-packages.** src-layout again: 10 commits all came back
   `BASELINE_RED` because the tests were importing the installed copy.

The end-to-end test builds a real git repository and proves the instrument separates a fix that
shipped with a test from a fix that did not. The fixtures are here because what is under test is the
INSTRUMENT; the prevalence claim is measured on real public repositories by the tool itself.
"""
from __future__ import annotations

import json
import subprocess
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import revert_test_ledger_v1 as R  # noqa: E402


# ------------------------------------------------------------------------ what the runner said

@pytest.mark.parametrize("text,expected", [
    ("Ran 28 tests in 0.1s\n\nOK", 28),
    ("771 passed, 21203 subtests passed in 16.47s", 771),
    ("63795 passed, 3 skipped in 51.0s", 63795),
    ("Ran 1 test in 0.000s\n\nOK", 1),
    ("12 failed, 3 passed", 3),
    ("OK", 0),                     # said nothing -> ran nothing we can see
    ("", 0),
    ("no tests ran in 0.75s", 0),
])
def test_the_quantifier_is_read_from_what_the_runner_printed(text, expected):
    assert R.tests_ran(text) == expected


def test_a_runner_that_ran_nothing_is_not_a_green_suite():
    """The stem bug, pinned. Exit 0 with no tests named must never be read as a pass."""
    assert R.tests_ran("Ran 0 tests in 0.000s\n\nOK") == 0


# --------------------------------------------------------------------- what kind of change it was

def test_a_docstring_edit_is_not_a_code_change():
    assert R.classify_change(b'def f():\n    """old"""\n    return 1\n',
                             b'def f():\n    """new"""\n    return 1\n') == "DOCSTRING_OR_COMMENT"


def test_a_version_bump_is_not_a_code_change():
    assert R.classify_change(b'__version__ = "11.2.0"\nx = 1\n',
                             b'__version__ = "11.2.1"\nx = 1\n') == "VERSION_ONLY"


def test_a_type_hint_is_not_a_code_change():
    assert R.classify_change(b"def f(x: int) -> None:\n    return None\n",
                             b"def f(x):\n    return None\n") == "ANNOTATION_ONLY"


def test_a_changed_constant_is_a_code_change():
    assert R.classify_change(b"def f():\n    return 1\n",
                             b"def f():\n    return 2\n") == "CODE_CHANGE"


def test_a_new_file_is_a_code_change():
    assert R.classify_change(None, b"x = 1\n") == "CODE_CHANGE"


def test_an_unparseable_side_is_named_not_guessed():
    assert R.classify_change(b"def f(:\n", b"x = 1\n") == "UNPARSEABLE"


def test_a_default_value_change_is_not_hidden_by_the_annotation_rule():
    """Stripping annotations must not strip defaults; that would hide real behavioural changes."""
    assert R.classify_change(b"def f(x=None):\n    return 1\n",
                             b"def f(x: int = 5):\n    return 1\n") == "CODE_CHANGE"


def test_test_paths_are_recognised():
    for path in ("tests/test_a.py", "a_test.py", "conftest.py", "src/test/x.py", "testing/helpers.py"):
        assert R.is_test_path(path) is True
    for path in ("more_itertools/more.py", "src/packaging/utils.py"):
        assert R.is_test_path(path) is False


# --------------------------------------------------------------- a real repository, end to end

def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def _commit(repo: pathlib.Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture()
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "calc.py").write_text("def double(n):\n    return n + n\n")
    (root / "test_calc.py").write_text(
        "import unittest\nimport calc\n\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_double(self):\n        self.assertEqual(calc.double(3), 6)\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n')
    _commit(root, "initial")

    # A BUG FIX THAT SHIPPED WITH A TEST: `limit` is off by one, and the fix comes with an assertion.
    (root / "calc.py").write_text("def double(n):\n    return n + n\n\n\n"
                                  "def limit(n):\n    return n < 10\n")
    _commit(root, "add limit")

    (root / "calc.py").write_text("def double(n):\n    return n + n\n\n\n"
                                  "def limit(n):\n    return n <= 10\n")
    (root / "test_calc.py").write_text(
        "import unittest\nimport calc\n\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_double(self):\n        self.assertEqual(calc.double(3), 6)\n\n"
        "    def test_limit_boundary(self):\n        self.assertTrue(calc.limit(10))\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n')
    _commit(root, "fix limit boundary, with a test")

    # A BUG FIX THAT SHIPPED WITHOUT ONE: `floor` is wrong, and nothing asserts it.
    (root / "calc.py").write_text("def double(n):\n    return n + n\n\n\n"
                                  "def limit(n):\n    return n <= 10\n\n\n"
                                  "def floor(n):\n    return n\n")
    _commit(root, "fix floor, no test")
    return root


CHECK = [sys.executable, "-m", "unittest", "-q", "test_calc"]


def test_a_fix_that_shipped_with_a_test_is_noticed_when_reverted(repo):
    commits = R.candidate_commits(repo, 10, None, "HEAD")
    target = next(c for c in commits if c["subject"].startswith("fix limit"))
    row = R.measure_commit(repo, target, CHECK, repo.parent / "work", 120)
    assert row["verdict"] == "REVERT_NOTICED", row
    assert row["change_class"] == "CODE_CHANGE"
    assert row["baseline"]["passed"] is True
    assert row["after_revert"]["passed"] is False


def test_a_fix_that_shipped_without_a_test_is_measurably_unprotected(repo):
    commits = R.candidate_commits(repo, 10, None, "HEAD")
    target = next(c for c in commits if c["subject"].startswith("fix floor"))
    row = R.measure_commit(repo, target, CHECK, repo.parent / "work", 120)
    assert row["verdict"] == "REVERT_NOT_NOTICED", row
    assert row["baseline"]["passed"] is True
    assert row["after_revert"]["passed"] is True


def test_a_commit_that_touches_only_tests_is_not_a_candidate(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "a.py").write_text("x = 1\n")
    _commit(root, "code")
    (root / "tests").mkdir()
    (root / "tests" / "test_a.py").write_text("def test_x():\n    assert True\n")
    _commit(root, "tests only")
    subjects = [c["subject"] for c in R.candidate_commits(root, 10, None, "HEAD")]
    assert "tests only" not in subjects
    assert "code" in subjects


def test_a_suite_that_runs_nothing_refuses_instead_of_reporting(repo, tmp_path):
    """Exit 0, no tests named: the stem failure. Must be CHECK_RAN_NOTHING, not a pass."""
    commits = R.candidate_commits(repo, 10, None, "HEAD")
    target = next(c for c in commits if c["subject"].startswith("fix floor"))
    row = R.measure_commit(repo, target, [sys.executable, "-c", "print('Ran 0 tests'); raise SystemExit(0)"],
                           tmp_path / "work2", 120)
    assert row["verdict"] == "CHECK_RAN_NOTHING"


def test_a_red_baseline_is_not_counted_against_the_commit(repo, tmp_path):
    commits = R.candidate_commits(repo, 10, None, "HEAD")
    target = next(c for c in commits if c["subject"].startswith("fix floor"))
    row = R.measure_commit(repo, target, [sys.executable, "-c", "print('1 failed, 0 passed'); raise SystemExit(1)"],
                           tmp_path / "work3", 120)
    assert row["verdict"] == "BASELINE_RED"


def test_the_two_denominators_are_both_reported(repo, tmp_path):
    """The headline is over CODE_CHANGE only; the unfiltered count must sit beside it."""
    out = tmp_path / "ledger.json"
    assert R.main(["--repo", str(repo), "--limit", "10", "--out", str(out),
                   "--check", *CHECK]) == 0
    payload = json.loads(out.read_text())
    assert payload["judged"] == payload["noticed"] + payload["not_noticed"]
    code = payload["code_change_only"]
    assert code["judged"] <= payload["judged"]
    assert code["noticed"] + code["not_noticed"] == code["judged"]
    assert payload["authority"] == "NONE" and payload["spend_usd"] == 0
    assert sum(payload["by_change_class"][k]["noticed"] + payload["by_change_class"][k]["not_noticed"]
               for k in payload["by_change_class"]) == payload["judged"]
