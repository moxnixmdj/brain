"""A bisect costs what the NAMED tree costs, and answers about the NAMED tree.

Measured 2026-10-31 on this repository: ``git.history.bisect_regression.v1`` ran
``git clone --shared`` of the whole repository for every request -- 35.5 s against its own 30 s
timeout on 241 MB of tracked files -- and then ran the REPOSITORY's suite, not the sentence's
test.  So the row that answers "which commit broke the test" timed out on every other run and,
when the clone won the race, answered "the first commit broke it" about a history that had
nothing to do with the test the sentence named (which was not in git at all).

Both halves of that are now the same rule: the named tree is what gets materialised and what
gets tested.  One worktree shares the object database (8 ms to create, 2.3 s for the first full
checkout, 0.2 s per later revision because git only rewrites changed files), and a named path
that git does not track is refused in milliseconds instead of being answered with somebody
else's history.

The measurement that matters here is the one a reader can falsify: bring back a whole-repository
clone and the elapsed time below exceeds the 20 s this test allows.
"""

import pathlib
import shutil
import subprocess
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import git_bisect_regression as row  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/bisect_named_tree"


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def _commit(repo: pathlib.Path, message: str, calc: str) -> str:
    (repo / "pkg/calc.py").write_text(calc, encoding="utf-8")
    (repo / "pkg/test_calc.py").write_text(
        "import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _history() -> tuple[pathlib.Path, str, str]:
    base = WORK / "repo"
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    _git(base, "init", "-q", "-b", "main")
    good = _commit(base, "good", "def add(a, b):\n    return a + b\n")
    bad = _commit(base, "break", "def add(a, b):\n    return a - b\n")
    _commit(base, "later", "def add(a, b):\n    return a - b\n\n\ndef noise():\n    return 1\n")
    return base, good, bad


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


class TheNamedTreeIsWhatGetsBisected(unittest.TestCase):
    def test_the_breaking_commit_is_the_commit_that_broke_the_named_test(self):
        repo, good, bad = _history()
        outcome = row.run({"source_root": _rel(repo / "pkg"),
                           "output_path": _rel(WORK / "answer.json")}, ROOT)
        self.assertEqual(outcome.get("mode"), "commit_bisect")
        import json
        doc = json.loads((ROOT / outcome["output_path"]).read_text(encoding="utf-8"))
        self.assertEqual(doc.get("breaking_commit"), bad)
        self.assertEqual(doc.get("last_good_commit"), good)

    def test_it_costs_seconds_not_a_whole_repository_clone(self):
        repo, _good, _bad = _history()
        started = time.perf_counter()
        row.run({"source_root": _rel(repo / "pkg"), "output_path": _rel(WORK / "timed.json")}, ROOT)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 20.0, "a whole-repository clone is back: %.1f s" % elapsed)


class ATreeGitDoesNotTrackIsRefused(unittest.TestCase):
    def test_an_untracked_test_is_not_bisected(self):
        _history()
        scratch = WORK / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "test_x.py").write_text("print(1)\n", encoding="utf-8")
        started = time.perf_counter()
        with self.assertRaises(RuntimeError) as caught:
            row.run({"source_root": _rel(scratch), "output_path": _rel(WORK / "refused.json")}, ROOT)
        self.assertIn("NAMED_TEST_NOT_IN_GIT_HISTORY", str(caught.exception))
        self.assertLess(time.perf_counter() - started, 5.0,
                        "the refusal must happen before anything is materialised")


if __name__ == "__main__":
    unittest.main()
