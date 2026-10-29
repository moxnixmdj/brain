"""Failing to REACH a capability is not a verdict about the world, so a decisive plan may answer.

Measured 2026-10-29 on a fresh tree, filesystem as the oracle::

    "Rename the parameter old_price to price in the python module <util.py> and save the report
     to <out.json>"
      FAIL__LIVE_CONTROLLER_EXECUTION
      capability document.convert.markdown_pdf.pandoc_weasyprint
      reason     Blocker:BOUND_APT_METADATA_NOT_FOUND:pandoc

The door had routed a Python refactor to a Markdown->PDF converter and failed to find apt
metadata for pandoc.  A decisive typed plan existed the whole time
(``python.refactor.rename_parameter.v1``, which really renames the parameter and rewrites the
body), and the retry that would have used it was blocked by ``executed is True``.  That flag was
protecting a real rule -- an honest verdict must never be overwritten by a second guess -- but
"the capability I picked could not run" is not an honest verdict.

The retry therefore stays refused for every failure a truth/observation/promise gate produced
(those fields are evidence the world was judged) and for a named set of judged failure classes.
These tests pin both sides: the supersede happens where it is safe, and the refusal survives
everywhere it is not.
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

WORK = ROOT / "canonical/astra_runtime/tmp/test_failed_attempt"


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/util.py").write_text("def total(old_price, qty):\n    return old_price * qty\n",
                                      encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


class OnlyAnAttemptThatJudgedNothingMayBeSuperseded(unittest.TestCase):
    def test_a_pass_is_never_superseded(self):
        self.assertFalse(door._may_supersede_a_failed_attempt({"pass": True}))

    def test_a_judged_failure_class_is_never_superseded(self):
        for cls in ("TOOL_REPORTED_NON_SUCCESS", "PROMISED_ARTIFACT_MISSING",
                    "NO_OBSERVED_EFFECT", "STATED_ANSWER_NOT_PROVIDED",
                    "NAMED_INPUT_REMOVED"):
            self.assertFalse(
                door._may_supersede_a_failed_attempt({"pass": False, "failure_class": cls}), cls)

    def test_an_observation_gate_that_spoke_is_never_superseded(self):
        for field in ("tool_truth_errors", "observed_effect_errors",
                      "promised_source_change_errors", "promised_artifact_errors",
                      "stated_answer_errors"):
            self.assertFalse(
                door._may_supersede_a_failed_attempt({"pass": False, field: ["x"]}), field)

    def test_an_attempt_that_never_reached_a_capability_may_be_superseded(self):
        self.assertTrue(door._may_supersede_a_failed_attempt(
            {"pass": False, "executed": True, "failure_class": "ROUTE_ADMISSION_REJECTED:R3_WEAK_EVIDENCE",
             "reason": "Blocker:BOUND_APT_METADATA_NOT_FOUND:pandoc"}))


class TheDoorReachesThePlanItAlreadyHad(unittest.TestCase):
    def test_a_parameter_rename_is_executed_not_mis_routed(self):
        base = _fresh("rename")
        util = base / "pkg/util.py"
        result = door.solve({"task_id": "SUP_RENAME", "goal":
                             "Rename the parameter old_price to price in the python module %s and "
                             "save the report to %s." % (_rel(util), _rel(base / "out.json"))})
        body = util.read_text(encoding="utf-8")
        self.assertNotIn("old_price", body, "the rename never touched the file: %s"
                         % result.get("status"))
        self.assertIn("def total(price, qty)", body)
        self.assertIs(result.get("pass"), True, result.get("status"))
        retry = result.get("typed_swe_retry") or {}
        self.assertEqual(retry.get("selected_capability"), "python.refactor.rename_parameter.v1")
        self.assertEqual(retry.get("model_dependency_count"), 0)

    def test_an_honest_refusal_is_not_overwritten_by_a_retry(self):
        base = _fresh("audit")
        result = door.solve({"task_id": "SUP_AUDIT", "goal":
                             "Run a security audit on %s" % _rel(base / "pkg")})
        self.assertIs(result.get("pass"), False,
                      "a stated security review was reported as done: %s" % result.get("status"))
        self.assertIsNone(result.get("typed_swe_retry"))


if __name__ == "__main__":
    unittest.main()
