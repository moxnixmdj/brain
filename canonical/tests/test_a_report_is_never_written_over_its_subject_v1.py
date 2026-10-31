"""A report about a file is not a change to that file.

Measured 2026-10-30, on one fresh tree, verbatim:

    goal   "Repair the python source <pkg>/broken.py so that its tests pass."
    bound  output_path = <pkg>/broken.py          (the only .py the sentence names)
    world  broken.py replaced by the adapter's own JSON report
    answer pass=True, status=PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED...

Two defects had to meet for that to happen, and each one hid the other:

  * the report destination was the file being repaired, and nothing on the primary
    execution path stopped it -- the typed retry path has relocated a report off a
    stated source since 2026-10-27 (``_fresh_output_path``), so the same sentence was
    destructive or not depending on which path answered it;
  * the source-change gate (added the round before) then saw a CHANGED byte and was
    satisfied -- by the report.  The gate was right that the file had changed; the
    change was the destruction.

This module pins the invariant, not the incident: **an artifact may never be written
onto a file the request named as its source**, and a pass may not rest on such a
write.  The second test is the control that keeps the first one honest -- the repair
that CAN run still runs, and it is judged by the bytes and by the real test runner,
not by the machine's own report.
"""

import hashlib
import pathlib
import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import live_brain_route_admission_v1 as ra
from canonical.runtime import swe_typed_plan_v1 as plan

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/report_never_over_a_source"

BROKEN = "def oops(:\n    return 1\n"
RED = "def add(a, b):\n    return a - b\n"
GREEN = "def add(a, b):\n    return a + b\n"
TEST = ("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n")


def _fresh(name, calc=GREEN, extra=None):
    base = "%s/%s" % (SCRATCH, name)
    shutil.rmtree(ROOT / base, ignore_errors=True)
    (ROOT / base / "pkg").mkdir(parents=True)
    (ROOT / base / "pkg" / "calc.py").write_text(calc, encoding="utf-8")
    (ROOT / base / "pkg" / "test_calc.py").write_text(TEST, encoding="utf-8")
    for fname, text in (extra or {}).items():
        (ROOT / base / "pkg" / fname).write_text(text, encoding="utf-8")
    return base


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _solve(goal):
    return ra.solve({"task_id": "RP%d" % perf_counter_ns(), "goal": goal})


class TestAnArtifactIsNeverWrittenOverItsSubject(unittest.TestCase):

    def test_an_unparseable_source_is_not_replaced_by_the_report_about_it(self):
        base = _fresh("unparseable", extra={"broken.py": BROKEN})
        source = ROOT / base / "pkg" / "broken.py"
        before = _digest(source)
        result = _solve("Repair the python source %s/pkg/broken.py so that its tests pass." % base)
        self.assertEqual(_digest(source), before,
                         "the stated source was overwritten: %r"
                         % source.read_text(encoding="utf-8")[:120])
        self.assertFalse(result.get("pass"),
                         "a pass was reported for a source that is not valid Python: %s"
                         % result.get("status"))

    def test_the_report_lands_beside_the_source_and_the_source_still_repairs(self):
        """The control: relocating the report must not stop the repair working."""
        base = _fresh("red", calc=RED)
        source = ROOT / base / "pkg" / "calc.py"
        result = _solve("fix %s/pkg/calc.py" % base)
        self.assertTrue(result.get("pass"), "a repairable red source was not repaired: %s / %s"
                        % (result.get("status"), result.get("compiled_capability_id")))
        self.assertEqual(source.read_text(encoding="utf-8"), GREEN,
                         "the source was not the thing that changed")

    def test_a_relocated_output_is_only_for_a_source_the_sentence_names(self):
        """The rule is about code files the request named, not about every output."""
        base = _fresh("rule")
        code = "%s/pkg/calc.py" % base
        report = "%s/out.json" % base
        relocated = plan._fresh_output_path(
            "fix %s and save the report to %s" % (code, report), ROOT,
            {"output_path": report, "source_root": "%s/pkg" % base})
        self.assertIsNone(relocated, "an ordinary stated report destination was moved")
        relocated = plan._fresh_output_path("fix %s" % code, ROOT,
                                            {"output_path": code, "source_root": "%s/pkg" % base})
        self.assertIsNotNone(relocated, "a report bound onto the stated source was left there")
        self.assertNotEqual(relocated, code)
        self.assertFalse(str(relocated).endswith(".py"),
                         "the relocated report would itself be Python source")


if __name__ == "__main__":
    unittest.main()
