"""Two requests that PASSED by answering a different question with the same words.

Measured 2026-10-29 on a fresh tree, the filesystem as the oracle::

    "Set up CI to run the tests in <pkg>."          PASS
      python.repository.acceptance.measure.v1 measured the tree it was standing in
      (test_count 0, test_returncode 1, tests_pass false) and wrote that to a spool file.
      No workflow, no config, no runner: nothing was set up.

    "Bisect the regression that broke the test in <T>."   PASS
      code.impact.tree_sitter.testselect.v1 treated <T> as the changed file and selected <T>
      as the candidate test.  No commit, no history traversed, no bisect.

Both are the S-1 seam again, with two new shapes: a MEASUREMENT of the current state accepted as
a DELIVERABLE the repository does not have, and a TEST SELECTION accepted as a HISTORY ANSWER.
The answer gate already decides this class from the sentence and the capability's own declaration,
so the fix is two rows -- and 0 of 125 routable rows declare either surface, which is why the
honest outcome today is a refusal.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_deliverable"
REL = WORK.relative_to(ROOT).as_posix()


def _fresh() -> pathlib.Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "pkg").mkdir(parents=True)
    (WORK / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (WORK / "pkg/test_calc.py").write_text(
        "import unittest\nfrom pkg.calc import add\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n", encoding="utf-8")
    return WORK


class ADeliverableIsNotAMeasurement(unittest.TestCase):
    def setUp(self):
        _fresh()

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def _refused_with(self, goal: str, code: str) -> None:
        result = door.solve({"task_id": "TEST_DELIVERABLE", "goal": goal})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertEqual(result.get("status"), "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED")
        self.assertTrue(any(code in e for e in (result.get("stated_answer_errors") or [])),
                        result.get("stated_answer_errors"))

    def test_setting_up_ci_is_not_measuring_the_repository(self):
        # 1. Measurement capability is still refused by stated_answer_errors for CI setup.
        registry = door.load_verified_registry()
        suite = registry.get("python.repository.acceptance.measure.v1") or {}
        errs = door.stated_answer_errors("Set up CI to run the tests in %s/pkg." % REL, suite)
        self.assertTrue(any("STATED_CI_SETUP_NOT_PROVIDED_BY_CAPABILITY" in e for e in errs), errs)
        # 2. Live solve() must NEVER pass via python.repository.acceptance.measure.v1; if it
        #    passes via a real CI workflow writer, an actual workflow YAML must exist on disk.
        result = door.solve({"task_id": "TEST_DELIVERABLE", "goal": "Set up CI to run the tests in %s/pkg." % REL})
        self.assertNotEqual(result.get("compiled_capability_id"), "python.repository.acceptance.measure.v1")
        if result.get("pass") is True:
            self.assertTrue(list(WORK.rglob("*.yml")) or list(WORK.rglob("*.yaml")),
                            "PASS without creating a real CI workflow file")

    def test_a_bisect_is_not_a_test_selection(self):
        # 1. Test-selection capability is still refused by stated_answer_errors for bisect.
        registry = door.load_verified_registry()
        impact = registry.get("code.impact.tree_sitter.testselect.v1") or {}
        errs = door.stated_answer_errors(
            "Bisect the regression that broke the test in %s/pkg/test_calc.py." % REL, impact)
        self.assertTrue(any("STATED_BISECT_NOT_PROVIDED_BY_CAPABILITY" in e for e in errs), errs)
        # 2. On this history-less tree, live solve() must fail closed (never pass via testselect).
        result = door.solve({"task_id": "TEST_DELIVERABLE",
                             "goal": "Bisect the regression that broke the test in %s/pkg/test_calc.py." % REL})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertNotEqual(result.get("compiled_capability_id"), "code.impact.tree_sitter.testselect.v1")

    def test_the_ordinary_neighbours_are_untouched(self):
        """The gate must not fire on the sentences next door to the ones it refuses.

        ``"Which tests are affected if I change <f>?"`` used to be pinned HERE as a neighbour that
        ``python.repository.acceptance.measure.v1`` was allowed to answer -- and that was the defect
        in miniature: the repository measurement runs the tree's suite and reports whether it is
        green, which is an answer to "do the tests pass here", not to "which tests does this change
        touch".  Measured 2026-10-30 it returned PASS with ``selected_tests: []``.  The neighbour
        assertion now uses the row that DECLARES impact analysis, and the measurement is pinned on
        the other side, where it belongs.
        """
        registry = door.load_verified_registry()
        suite = registry.get("python.repository.acceptance.measure.v1") or {}
        impact = registry.get("python.source.change_impact.testselect.v1") or {}
        self.assertEqual(door.stated_answer_errors("Run the test suite in %s/pkg." % REL, suite), [])
        self.assertEqual(door.stated_answer_errors(
            "Which tests are affected if I change %s/pkg/calc.py?" % REL, impact), [])
        self.assertEqual(door.stated_answer_errors(
            "Which tests are affected if I change %s/pkg/calc.py?" % REL, suite),
            ["STATED_CHANGE_IMPACT_NOT_ANSWERED_BY_CAPABILITY:UNNAMED"])

    def test_a_real_ci_capability_would_be_admitted_by_its_declaration(self):
        real = {"capability_id": "python.ci.workflow.write.v1",
                "provides": ["python.ci.workflow.written"],
                "keywords": ["ci", "workflow", "actions"]}
        self.assertEqual(door.stated_answer_errors("Set up CI to run the tests in pkg.", real), [])
        bisect = {"capability_id": "git.bisect.run.v1", "provides": ["git.history.bisect"],
                  "keywords": ["bisect", "regression"]}
        self.assertEqual(door.stated_answer_errors(
            "Bisect the regression that broke the test in t.py.", bisect), [])


if __name__ == "__main__":
    unittest.main()
