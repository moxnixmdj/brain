"""A sentence that states an EFFECT is answered by a capability that DECLARES that effect.

A capability's `expect` field says what its own goal is.  The door was reading that field as the
sentence's goal, so anything the registry could do was an answer to anything the sentence asked.
Measured 2026-10-29 on a fresh tree, filesystem as the oracle::

    "Run a security audit on <pkg>"
      PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE
      python.source.audit.ast, function_count: 6      <- a symbol count, not a security review

    "Measure the test coverage of <pkg>"
      PASS   python.repository.acceptance.measure.v1  <- repository metadata, no coverage number

Both are the same seam the explanation gate already closed (`stated_answer_errors`, "Explain why
the test fails" answered by a test SELECTOR).  The table is data, not a list of ids: the surface is
the capability's own id, `provides` and `keywords`, so a real security or coverage capability is
admitted the moment one is bound -- and the registry does contain both
(`python.review.diff_security_gate.v1`, `python.review.diff_coverage_gate.v1`), which these tests
pin: the gate refuses the wrong capability and admits the right one.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_stated_effect"

SYMBOL_AUDIT = {"capability_id": "python.source.audit.ast",
                "provides": ["python.source.audit.ast"], "keywords": ["audit", "source"]}
SECURITY_GATE = {"capability_id": "python.review.diff_security_gate.v1",
                 "provides": ["python.review.diff_security_gate"],
                 "keywords": ["security", "review"]}
REPO_MEASURE = {"capability_id": "python.repository.acceptance.measure.v1",
                "provides": ["python.repository.acceptance.measure"]}
COVERAGE_GATE = {"capability_id": "python.review.diff_coverage_gate.v1",
                 "provides": ["python.review.diff_coverage_gate"],
                 "keywords": ["coverage", "review"]}


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/mod.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef unused_helper(x):\n    return x * 2\n",
        encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TheGateReadsTheDeclarationNotTheExpectField(unittest.TestCase):
    def test_a_symbol_audit_is_not_a_security_review(self):
        errors = door.stated_answer_errors("Run a security audit on pkg.",
                                           SYMBOL_AUDIT)
        self.assertEqual(errors,
                         ["STATED_SECURITY_REVIEW_NOT_PROVIDED_BY_CAPABILITY:"
                          "python.source.audit.ast"])

    def test_a_real_security_capability_is_admitted(self):
        self.assertEqual(
            door.stated_answer_errors("Run a security audit on pkg.", SECURITY_GATE), [])

    def test_repository_metadata_is_not_a_coverage_measurement(self):
        self.assertEqual(
            door.stated_answer_errors("Measure the test coverage of pkg.", REPO_MEASURE),
            ["STATED_COVERAGE_NOT_MEASURED_BY_CAPABILITY:"
             "python.repository.acceptance.measure.v1"])

    def test_a_real_coverage_capability_is_admitted(self):
        self.assertEqual(
            door.stated_answer_errors("Measure the test coverage of pkg.", COVERAGE_GATE), [])

    def test_a_request_that_states_no_effect_is_untouched(self):
        """The whole point: the gate must not fire on an ordinary request.

        ("Repair the python source pkg/calc.py" used to be listed here.  It is not an
        ordinary request -- it asks for a change to be MADE -- so it moved to
        ``TheSentenceThatAsksForTheChange`` below, where an auditing capability that
        makes no change is refused instead of admitted.)
        """
        for goal in ("Count the functions in pkg/calc.py",
                     "Find every caller of the function add in pkg/mod.py"):
            self.assertEqual(door.stated_answer_errors(goal, SYMBOL_AUDIT), [], goal)


class TheSentenceThatAsksForTheChange(unittest.TestCase):
    """A patch SEARCH is not a patch APPLIED -- the door accepted the search as the repair.

    Measured 2026-10-29 on a fresh tree, filesystem as the oracle::

        "The CI is failing because <test_calc.py> fails. Fix the build."
          PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
          python.patch.search.test_guided.ast.v1   -> PASS__VERIFIED_CANDIDATE_PATCH_FOUND
          calc.py byte-identical, the stated suite still red

    The registry already draws the line in its own ``provides`` declarations
    (``...candidate.test_verified`` vs ``...verified_repair_applied``); the gate reads those,
    so a real repair capability is admitted the moment one is bound.
    """

    SEARCH = {"capability_id": "python.patch.search.test_guided.ast.v1",
              "provides": ["python.patch.candidate.test_verified"]}
    APPLY = {"capability_id": "python.software.repair.apply.verified.v1",
             "provides": ["python.source.write.verified_repair_applied"]}
    LOOP = {"capability_id": "python.software.repair.loop.test_guided.ast.v1",
            "provides": ["python.patch.candidate.multi_edit.test_verified"]}

    def test_a_patch_search_is_not_a_repair(self):
        self.assertEqual(
            door.stated_answer_errors("Repair the python source pkg/calc.py", self.SEARCH),
            ["STATED_APPLICATION_NOT_PERFORMED_BY_CAPABILITY:"
             "python.patch.search.test_guided.ast.v1"])

    def test_a_repair_capability_is_admitted(self):
        self.assertEqual(
            door.stated_answer_errors("Repair the python source pkg/calc.py", self.APPLY), [])

    def test_a_request_that_states_where_the_report_goes_asked_for_a_report(self):
        """The repair family's own contract: untouched source + one applicable patch."""
        goal = ("Repair the python source pkg/calc.py so the unit test pkg/test_calc.py passes, "
                "and save the repair report to pkg/out.json")
        self.assertEqual(door.stated_answer_errors(goal, self.LOOP), [])

    def test_an_audit_is_not_a_repair(self):
        self.assertEqual(
            door.stated_answer_errors("Repair the python source pkg/calc.py", SYMBOL_AUDIT),
            ["STATED_APPLICATION_NOT_PERFORMED_BY_CAPABILITY:python.source.audit.ast"])

    def test_the_door_refuses_the_search_as_an_answer_to_a_broken_build(self):
        base = _fresh("ci")
        before = _digest(base / "pkg/mod.py")
        result = door.solve({"task_id": "EFF_CI", "goal":
                             "The CI is failing because %s fails. Fix the build."
                             % _rel(base / "pkg/mod.py")})
        self.assertIs(result.get("pass"), False,
                      "a candidate patch search was reported as a repair: %s"
                      % result.get("status"))
        self.assertEqual(_digest(base / "pkg/mod.py"), before)


class TheDoorStopsClaimingTheWrongEffect(unittest.TestCase):
    def test_a_security_audit_is_not_reported_as_done_by_a_symbol_count(self):
        base = _fresh("security")
        src = base / "pkg/mod.py"
        before = _digest(src)
        result = door.solve({"task_id": "EFF_SECURITY", "goal":
                             "Run a security audit on %s" % _rel(base / "pkg")})
        self.assertIs(result.get("pass"), False,
                      "a symbol count was reported as a security review: %s"
                      % result.get("status"))
        self.assertEqual(_digest(src), before)

    def test_a_coverage_request_is_not_reported_as_done_by_repository_metadata(self):
        base = _fresh("coverage")
        result = door.solve({"task_id": "EFF_COVERAGE", "goal":
                             "Measure the test coverage of %s" % _rel(base / "pkg")})
        self.assertIs(result.get("pass"), False,
                      "repository metadata was reported as a coverage measurement: %s"
                      % result.get("status"))


if __name__ == "__main__":
    unittest.main()
