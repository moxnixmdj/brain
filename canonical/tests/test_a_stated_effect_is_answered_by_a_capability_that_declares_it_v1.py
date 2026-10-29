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
        """The whole point: the gate must not fire on an ordinary request."""
        for goal in ("Count the functions in pkg/calc.py",
                     "Find every caller of the function add in pkg/mod.py",
                     "Repair the python source pkg/calc.py"):
            self.assertEqual(door.stated_answer_errors(goal, SYMBOL_AUDIT), [], goal)


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
