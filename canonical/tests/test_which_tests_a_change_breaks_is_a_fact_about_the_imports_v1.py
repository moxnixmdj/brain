"""Which tests a change breaks must be answered, not rolled back.

Measured on main at c4128ca, for the sentence "Show which tests are affected by a
change to D/p/calc.py and write the report to D/r.json":

  capability_id  python.source.change_impact.testselect.v1
  selected_test_count  0          candidate_test_count  2
  unknown_symbol_module_count  1
  side_effects_rolled_back_because  composed_chain_not_verified
  unverified_reason  NO_INDEPENDENT_REINSPECTION_FOR:python.source.change_impact.testselect.v1

Three separate faults, each of which alone was enough to make the answer
unreachable, and the third of which made the lane permanently unreachable no
matter how correct the answer was:

1. THE CHANGE WAS KEYED DIFFERENTLY FROM THE INDEX.  ``run`` stored
   ``str(raw)`` verbatim after validating containment, while the index keys its
   modules by repo-relative posix path.  The composer binds ABSOLUTE paths, so
   no changed module was ever found, every one came back MODULE_NOT_INDEXED, and
   the report said ``selected_tests: []`` against two candidates.  An empty
   selection a caller reads as "nothing to run" is worse than a refusal.

2. AN UNLOCATABLE CHANGE WAS REPORTED AS AN UNAFFECTED ONE.  The adapter already
   counted the modules it could not find and then said nothing about them.

3. NO INDEPENDENT RE-INSPECTOR EXISTED.  The acceptance layer refuses any
   capability it cannot re-measure, rolls the artifact back, and reports the
   artifact missing.  That is correct and is the reason a producer's own
   ``output_verified`` is not acceptance -- but it also meant the correct answer
   could never survive.

Every test here fails on baseline.
"""
from __future__ import annotations

import ast
import json
import shutil
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
from canonical.runtime.bound_capabilities import python_change_impact_testselect as impact

CALC = "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n"
OTHER = "def unused():\n    return 1\n"
TEST_REACHING = (
    "import unittest\nimport calc\n\n\n"
    "class TestCalc(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(calc.add(1, 2), 3)\n"
)
TEST_LONELY = (
    "import unittest\n\n\n"
    "class TestLonely(unittest.TestCase):\n"
    "    def test_solo(self):\n"
    "        self.assertTrue(True)\n"
)


class _Tree(unittest.TestCase):
    """A fixture under the repository, removed when the test ends."""

    _NEXT = 0

    def setUp(self):
        type(self)._NEXT += 1
        self.base = (REPO_ROOT / "canonical/astra_runtime/tmp"
                     / ("test_change_impact_%d_%d" % (os_pid(), type(self)._NEXT)))
        shutil.rmtree(self.base, ignore_errors=True)
        (self.base / "p" / "tests").mkdir(parents=True)
        (self.base / "p" / "calc.py").write_text(CALC)
        (self.base / "p" / "other.py").write_text(OTHER)
        (self.base / "p" / "tests" / "test_calc.py").write_text(TEST_REACHING)
        (self.base / "p" / "tests" / "test_lonely.py").write_text(TEST_LONELY)
        self.addCleanup(shutil.rmtree, self.base, True)

    @property
    def src(self) -> Path:
        return self.base / "p"

    def run_impact(self, changed, name="r.json"):
        return impact.run(
            {"changed_paths": [changed], "source_root": str(self.src),
             "output_path": str(self.base / name)}, REPO_ROOT)

    def rel(self, path: Path) -> str:
        return str(path.relative_to(REPO_ROOT))


def os_pid() -> int:
    import os
    return os.getpid()


class TheChangeIsKeyedTheWayTheIndexIsKeyedTests(_Tree):
    """Defect 1: an absolute path never matched a repo-relative index."""

    def test_an_absolute_changed_path_selects_the_test_that_reaches_it(self):
        out = self.run_impact(str(self.src / "calc.py"), "abs.json")
        self.assertEqual(out.get("unknown_symbol_module_count"), 0)
        report = json.loads((self.base / "abs.json").read_text())
        self.assertEqual(report["selected_tests"], [self.rel(self.src / "tests" / "test_calc.py")])

    def test_a_relative_changed_path_gives_the_same_answer(self):
        # Both spellings must agree.  If they do not, the answer depends on how
        # the caller happened to write the path, which is not a fact about the
        # tree.
        a = self.run_impact(str(self.src / "calc.py"), "a.json")
        b = self.run_impact(self.rel(self.src / "calc.py"), "b.json")
        ra = json.loads((self.base / "a.json").read_text())
        rb = json.loads((self.base / "b.json").read_text())
        self.assertEqual(ra["selected_tests"], rb["selected_tests"])
        self.assertEqual(a.get("selected_test_count"), b.get("selected_test_count"), 1)

    def test_the_test_that_does_not_reach_the_change_is_omitted(self):
        self.run_impact(str(self.src / "calc.py"), "c.json")
        report = json.loads((self.base / "c.json").read_text())
        omitted = [r["path"] for r in report["tests"] if not r.get("selected")]
        self.assertEqual(omitted, [self.rel(self.src / "tests" / "test_lonely.py")])

    def test_a_change_to_an_unimported_module_selects_nothing_and_says_why(self):
        out = self.run_impact(str(self.src / "other.py"), "d.json")
        report = json.loads((self.base / "d.json").read_text())
        self.assertEqual(report["selected_tests"], [])
        self.assertEqual(out.get("unknown_symbol_module_count"), 0,
                         "an empty selection here is a real answer, not a "
                         "failure to locate the change")


class AnUnlocatableChangeIsNotAnUnaffectingOneTests(_Tree):
    """Defect 2: silence where the run could not reason."""

    def test_a_changed_module_outside_the_indexed_root_is_refused(self):
        outside = REPO_ROOT / "canonical/runtime/goal_compiler.py"
        with self.assertRaises(Exception) as ctx:
            impact.run({"changed_paths": [str(outside)],
                        "source_root": str(self.src),
                        "output_path": str(self.base / "e.json")}, REPO_ROOT)
        self.assertIn("CHANGED_PYTHON_MODULE_NOT_INDEXED", str(ctx.exception))


class TheAnswerSurvivesItsOwnVerifierTests(_Tree):
    """Defect 3: no re-inspector, so the artifact was always rolled back."""

    def test_the_capability_now_has_an_independent_re_inspector(self):
        table = acceptance.INSPECTORS
        self.assertIn("python.source.change_impact.testselect.v1", table,
                      "no re-inspector is registered, so the acceptance layer "
                      "will roll the artifact back on every run")

    def test_end_to_end_the_report_is_kept_and_the_selection_is_right(self):
        goal = ("Show which tests are affected by a change to %s and write the "
                "report to %s" % (self.src / "calc.py", self.base / "f.json"))
        result = admission.solve({"task_id": "t", "goal": goal}) or {}
        self.assertIsNone(result.get("failure_class"),
                          str(result.get("failure_class")) + " " +
                          str(result.get("unverified_reason")))
        report_path = self.base / "f.json"
        self.assertTrue(report_path.is_file(),
                        "the artifact was rolled back: " +
                        str(result.get("side_effects_rolled_back_because")))
        report = json.loads(report_path.read_text())
        self.assertEqual(report["selected_tests"],
                         [self.rel(self.src / "tests" / "test_calc.py")])


class TheInspectorCanActuallyFailTests(_Tree):
    """A verifier that cannot fail is not a verifier."""

    def _inspect(self, report_name, changed):
        report = self.base / report_name
        args = {"changed_paths": [changed], "source_root": str(self.src),
                "output_path": str(report)}
        result = {"output_path": str(report)}
        data = json.loads(report.read_text())
        result["selected_test_count"] = len(data.get("selected_tests") or [])
        result["candidate_test_count"] = len(data.get("tests") or [])
        return acceptance._inspect_change_impact_testselect(args, result, REPO_ROOT)

    def test_a_real_report_is_accepted(self):
        self.run_impact(str(self.src / "calc.py"), "g.json")
        ok, reason, _ = self._inspect("g.json", str(self.src / "calc.py"))
        self.assertTrue(ok, reason)

    def test_a_report_that_omits_a_test_reaching_the_change_is_refused(self):
        self.run_impact(str(self.src / "calc.py"), "h.json")
        path = self.base / "h.json"
        data = json.loads(path.read_text())
        for row in data["tests"]:
            row["selected"] = False
            row["reason"] = "UNAFFECTED"
        data["selected_tests"] = []
        data["totals"]["selected_tests"] = 0
        path.write_text(json.dumps(data))
        args = {"changed_paths": [str(self.src / "calc.py")],
                "source_root": str(self.src), "output_path": str(path)}
        ok, reason, _ = acceptance._inspect_change_impact_testselect(
            args, {"output_path": str(path), "selected_test_count": 0,
                   "candidate_test_count": len(data["tests"])}, REPO_ROOT)
        self.assertFalse(ok)
        self.assertIn("OMITTED", reason)

    def test_a_report_that_pads_its_selection_is_refused(self):
        self.run_impact(str(self.src / "calc.py"), "i.json")
        path = self.base / "i.json"
        data = json.loads(path.read_text())
        # test_lonely.py imports nothing the change touches; claiming it does is
        # padding, and a padded selection hides the real answer in noise.
        for row in data["tests"]:
            row["selected"] = True
        data["selected_tests"] = [r["path"] for r in data["tests"]]
        data["totals"]["selected_tests"] = len(data["selected_tests"])
        path.write_text(json.dumps(data))
        args = {"changed_paths": [str(self.src / "calc.py")],
                "source_root": str(self.src), "output_path": str(path)}
        ok, reason, _ = acceptance._inspect_change_impact_testselect(
            args, {"output_path": str(path),
                   "selected_test_count": len(data["selected_tests"]),
                   "candidate_test_count": len(data["tests"])}, REPO_ROOT)
        self.assertFalse(ok)
        self.assertIn("REACHES_NOTHING", reason)

    def test_a_report_whose_counts_do_not_reconcile_is_refused(self):
        self.run_impact(str(self.src / "calc.py"), "j.json")
        ok, reason, _ = self._inspect("j.json", str(self.src / "calc.py"))
        self.assertTrue(ok, reason)
        args = {"changed_paths": [str(self.src / "calc.py")],
                "source_root": str(self.src),
                "output_path": str(self.base / "j.json")}
        ok2, reason2, _ = acceptance._inspect_change_impact_testselect(
            args, {"output_path": str(self.base / "j.json"),
                   "selected_test_count": 99, "candidate_test_count": 2}, REPO_ROOT)
        self.assertFalse(ok2)
        self.assertIn("MISMATCH", reason2)

    def test_a_missing_report_is_refused(self):
        ok, reason, _ = acceptance._inspect_change_impact_testselect(
            {"output_path": str(self.base / "never.json")},
            {"output_path": str(self.base / "never.json")}, REPO_ROOT)
        self.assertFalse(ok)
        self.assertEqual(reason, "IMPACT_REPORT_ABSENT_FROM_DISK")


if __name__ == "__main__":
    unittest.main()
