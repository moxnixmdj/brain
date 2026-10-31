"""A stated defect is a request to change the file -- and it is answered by repairing it.

Measured 2026-10-29 on `4340001`, fresh tree, filesystem and the real runner as oracles::

    "Bug: <T>/pkg/calc.py add() returns the wrong value. Failing test: <T>/pkg/test_calc.py."

had no imperative verb, so no route saw a request for a change.  The primary compiler
planned `docx.document.create_from_json_record` for it (matched on the single token
"value") and the decisive typed selection picked the repair LOOP, whose declared contract
is a candidate patch with the source restored -- a PASS over a file that was still broken,
and a refusal once the source-change gate learned to read the promise.

The selector's own effect vocabulary (`capability_selection_retrieval_v1._EFFECT_WORDS`)
has always listed bug/broken/failing as repair words.  What was missing is the same
three-part family the caller-finding route already uses: enumerate candidates from the
registry's OWN keyword data, let `selection.admit` be the oracle, take the single admitted
capability whose name carries the effect token.  Nothing here is a new subsystem and no
capability id is hardcoded: of the four rows whose declared surface mentions landing a
fix, exactly one admits every input the sentence states, and it is the one that lands the
patch.

Every case below checks the WORLD -- file bytes for "did anything change", a real
subprocess exit code for "is the stated suite green" -- and never the machine's report.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import swe_typed_plan_v1 as typed_plan  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_stated_defect"
BROKEN = "def add(a, b):\n    return a - b\n"
# No `__main__` guard on purpose: a script run of such a file executes zero tests and
# exits 0, which is the trap the suite runner exists to avoid.
TEST_SOURCE = ("import calc, unittest\n\n\n"
               "class T(unittest.TestCase):\n"
               "    def test_add(self):\n"
               "        self.assertEqual(calc.add(2, 3), 5)\n")
REPAIR_APPLY = "python.software.repair.apply.verified.v1"


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text(BROKEN, encoding="utf-8")
    (base / "pkg/test_calc.py").write_text(TEST_SOURCE, encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bug_report(base: pathlib.Path) -> str:
    return ("Bug: %s add() returns the wrong value. Failing test: %s."
            % (_rel(base / "pkg/calc.py"), _rel(base / "pkg/test_calc.py")))


def _suite_green(pkg: pathlib.Path) -> bool:
    """The stated test, run by the real runner.  Exit code is the oracle."""
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "test_calc"],
        cwd=str(pkg), capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": str(pkg), "PATH": "/usr/bin:/bin:/usr/local/bin"})
    return proc.returncode == 0


class ADefectIsReadAsARepairRequest(unittest.TestCase):
    def test_the_repair_family_is_recognised_without_an_imperative(self):
        base = _fresh("family")
        terms = typed_plan._family_terms(_bug_report(base))
        self.assertIsNotNone(terms, "a stated defect is a SWE repair request")
        self.assertEqual(terms[1], "repair",
                         "the effect token is the one that lands the change")

    def test_a_question_about_the_defect_is_not_a_request_to_change_it(self):
        """`Explain the bug in X` must not be ROUTED as a request to change X.

        The route is what this change owns.  Whether the lexically-scored path that
        does answer it is allowed to write a report over the file it was asked
        about is a separate, pre-existing defect: measured here on both sides of
        this change, `DETERMINISTIC_VERIFIED_CAPABILITY_MATCH` binds the named
        source as the tool's output and the source is replaced by the tool's JSON
        (inventory §2.5).  This test pins the half this change is responsible for.
        """
        base = _fresh("question")
        self.assertIsNone(
            typed_plan._family_terms("Explain the bug in %s" % _rel(base / "pkg/calc.py")))

    def test_the_decisive_plan_is_the_capability_that_lands_the_patch(self):
        base = _fresh("plan")
        plan = typed_plan.build_plan(_bug_report(base), ROOT)
        self.assertIsNotNone(plan, "the registry data must make this decisive")
        self.assertEqual(plan[2].get("selected_capability"), REPAIR_APPLY)


class TheDoorActuallyRepairsIt(unittest.TestCase):
    def test_the_measured_bug_report_repairs_the_source_and_greens_the_test(self):
        base = _fresh("end_to_end")
        pkg = base / "pkg"
        before = _digest(pkg / "calc.py")
        result = door.solve({"task_id": "STATED_DEFECT", "goal": _bug_report(base)})
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertNotEqual(_digest(pkg / "calc.py"), before,
                            "a PASS that reports a repair must have changed the file")
        self.assertTrue(_suite_green(pkg), "the named test must actually pass")


if __name__ == "__main__":
    unittest.main()
