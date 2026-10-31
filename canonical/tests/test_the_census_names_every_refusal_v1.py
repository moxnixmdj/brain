"""The census must name the cause, and the git fixture must have a history.

Two defects measured 2026-10-31, both in the instrument rather than the machine:

1. **The cause was unread, not absent.** The door returns ``reason`` for a failed chain
   (``RuntimeError:INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS``,
   ``BINDING_REFUSED:message:value_not_parseable``) and the census kept only ``failure_class``,
   so ten different failures were reported as one string and the inventory called them opaque.

2. **The git class was asked of a directory with no history.** Five git sentences and two
   history questions were measured against plain directories, so the whole class measured the
   absence of a fixture. The capability matrix had already built the tree
   (``_seed_git_repository``); it has one owner now and the census uses it.

Independent oracles: the git binary itself (a repository exists, has one commit, and has a
non-empty diff), and the door's own vocabulary for the causes.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_GUARD = ROOT / "execution_guard"
if str(_GUARD) not in sys.path:
    sys.path.insert(0, str(_GUARD))

WORK = ROOT / "canonical/astra_runtime/tmp/test_census_causes"


def _probe():
    spec = importlib.util.spec_from_file_location(
        "swe_advanced_probe_under_test", _GUARD / "swe_advanced_probe_v1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheCauseIsReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = _probe()

    def test_the_exception_prefix_is_not_the_cause(self):
        row = {"status": "FAIL__LIVE_CONTROLLER_EXECUTION",
               "reason": "RuntimeError:INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS"}
        self.assertEqual(self.probe._cause(row), "INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS")

    def test_a_binding_refusal_keeps_the_slot_it_names(self):
        row = {"status": "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED",
               "reason": "BINDING_REFUSED:message:value_not_parseable"}
        self.assertEqual(self.probe._cause(row), "BINDING_REFUSED:message")

    def test_a_traceback_fragment_does_not_swallow_the_cause(self):
        row = {"status": "FAIL__LIVE_CONTROLLER_EXECUTION",
               "reason": "RuntimeError:CHOREOGRAPHY_REPAIR_UNRESOLVED:x\n  File \"<x>\", line 1"}
        self.assertEqual(self.probe._cause(row), "CHOREOGRAPHY_REPAIR_UNRESOLVED:x")

    def test_no_reason_falls_back_to_the_status(self):
        row = {"status": "FAIL__RAW_GOAL_COMPILATION_GAP", "reason": ""}
        self.assertEqual(self.probe._cause(row), "FAIL__RAW_GOAL_COMPILATION_GAP")

    def test_a_route_rule_is_the_cause_when_the_sentence_is_what_failed(self):
        """A sentence that names no function must not be reported as a controller crash."""
        self.assertTrue(self.probe._asks_about_history("Show me the diff of pkg/calc.py against HEAD~1."))
        self.assertTrue(self.probe._asks_about_history("Commit the changes in pkg with a clear message."))
        self.assertTrue(self.probe._asks_about_history("Create a branch named feature/x."))
        self.assertTrue(self.probe._asks_about_history("Find the commit that broke the test."))
        self.assertFalse(self.probe._asks_about_history("Fix the off-by-one bug in src/main.cpp."))


class TheFixtureHasHistoryTests(unittest.TestCase):
    def test_the_seeded_tree_has_a_commit_and_a_non_empty_diff(self):
        from swe_git_fixture_v1 import seed_repository

        base = WORK / "history"
        if base.exists():
            shutil.rmtree(base)
        (base / "pkg").mkdir(parents=True)
        (base / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

        self.assertTrue(seed_repository(base))

        def git(*argv: str) -> str:
            return subprocess.run(("git", "-C", str(base)) + argv, capture_output=True,
                                  text=True, timeout=60).stdout.strip()

        self.assertTrue((base / ".git").is_dir())
        self.assertEqual(git("rev-list", "--count", "HEAD"), "1")
        # The oracle is the diff itself: "no hunk" and "no diff produced" are different claims.
        self.assertTrue(git("diff", "--stat"))
        self.assertTrue(git("status", "--porcelain").strip())

    def test_a_missing_directory_is_a_refusal_not_a_crash(self):
        from swe_git_fixture_v1 import seed_repository

        self.assertFalse(seed_repository(WORK / "does_not_exist"))


if __name__ == "__main__":
    unittest.main()
