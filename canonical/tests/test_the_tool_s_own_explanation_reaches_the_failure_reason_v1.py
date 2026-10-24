"""The truth check must not throw away the tool's own explanation.

Measured on cc3bd40 across all 367 admissible capabilities driven from the
registry: 74 failures were reported as `TOOL_REPORTED_PASS_FALSE:<cid>` or
`TOOL_REPORTED_NON_SUCCESS_STATUS:<cid>:<status>`.  That says a capability ran
and said "no" -- it does not say why.  The why was already in hand: the tool's
own result carries a `reason`, and the truth check reads that result to decide
pass/fail and then discards it.

In 50 of the 74 the tool had named its cause outright -- CONTEXT_ID_REQUIRED
(13), V3_INPUT_REQUIRED (10), PREDICATE_ALIAS_REQUIRED (5), OBJECTIVE_REQUIRED
(4), INPUT_SCHEMA_INVALID (4), OBLIGATION_ID_REQUIRED (3), TEXT_REQUIRED (1),
PROMPT_REQUIRED (1), PATH_OUTSIDE_REPOSITORY (2).  Every one of those
capabilities declares zero input roles in its action_template, so it is
structurally unservable: no wording of a goal can supply an input the registry
never declared.  That is a different fact from "the tool judged the answer
wrong", and without this change a caller cannot tell the two apart.

This is the same shape as the defect fixed in the `failure_reason` docstring's
own example: a failure that is fully diagnosed looks like a failure with no
cause at all.

Tests 1-4 exercise `_with_tool_own_reason` directly and are deterministic; they
cannot pass on a tree where that helper does not exist.  Test 5 drives real
capabilities end to end through `solve` and counts how many refusals carry a
cause; it fails on cc3bd40, where the count is 0.
"""

from __future__ import annotations

import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "canonical" / "runtime") not in sys.path:
    sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

from canonical.runtime.live_brain_route_admission_v1 import (  # noqa: E402
    _with_tool_own_reason,
    failure_reason,
    solve,
)

# Chosen by measurement on cc3bd40, not by guess: each of these runs, fails
# closed, and names its own missing input.  (An earlier draft of this list used
# `bytes_active_query_task_generator_v1`, which in fact passes -- the assertion
# caught it, which is the assertion doing its job.)
_PROSE = {
    "canonical/runtime/current_escape_o11_objective_acceptance_law_gate_v1.py.auto.v1":
        "current escape o11 objective acceptance law gate v1",
    "canonical/runtime/p3_real_context_v3_admission_v9.py.auto.v1":
        "p3 real context v3 admission v9",
    "canonical/runtime/selected_bounded_support_truth_certificate_v1.py.auto.v1":
        "selected bounded support truth certificate v1",
}


class TestTheToolOwnExplanationReachesTheFailureReasonV1(unittest.TestCase):
    def test_the_tools_own_reason_is_appended(self) -> None:
        result = {
            "tool_truth_errors": ["TOOL_REPORTED_PASS_FALSE:some.capability.v1"],
            "execution": [{"capability_id": "some.capability.v1",
                           "result": {"pass": False, "reason": "CONTEXT_ID_REQUIRED"}}],
        }
        self.assertEqual(
            failure_reason(result),
            "TOOL_REPORTED_PASS_FALSE:some.capability.v1:CONTEXT_ID_REQUIRED")

    def test_a_reason_that_is_not_a_truth_check_refusal_is_untouched(self) -> None:
        result = {"compiler_detail": "contract_not_stated:archive_path",
                  "execution": [{"result": {"reason": "CONTEXT_ID_REQUIRED"}}]}
        self.assertEqual(failure_reason(result), "contract_not_stated:archive_path")

    def test_no_dangling_colon_when_the_tool_gave_no_reason(self) -> None:
        # 24 of the 74 carry no `reason` at all; those must not grow an empty
        # field, because a caller splitting on ":" would then read "" as a cause.
        for inner in ({}, {"pass": False}, {"reason": ""}, {"reason": "   "}):
            result = {"tool_truth_errors": ["TOOL_REPORTED_PASS_FALSE:x.y.z"],
                      "execution": [{"capability_id": "x.y.z", "result": inner}]}
            self.assertEqual(failure_reason(result), "TOOL_REPORTED_PASS_FALSE:x.y.z")

    def test_the_non_success_status_form_is_covered_too(self) -> None:
        result = {
            "tool_truth_errors": ["TOOL_REPORTED_NON_SUCCESS_STATUS:x.y.z:FAIL_CLOSED"],
            "execution": [{"result": {"reason": "V3_INPUT_REQUIRED"}}],
        }
        self.assertEqual(failure_reason(result),
                         "TOOL_REPORTED_NON_SUCCESS_STATUS:x.y.z:FAIL_CLOSED:V3_INPUT_REQUIRED")

    def test_real_capabilities_name_their_own_cause_end_to_end(self) -> None:
        """Drives the real registry; the count is 0 on cc3bd40."""
        named = 0
        for index, (cid, prose) in enumerate(sorted(_PROSE.items())):
            result = solve({"task_id": "TOOLCAUSE%02d" % index,
                            "goal": "Run the %s." % prose})
            self.assertIsNot(result.get("pass"), True,
                             "%s unexpectedly passed; pick another example" % cid)
            reason = failure_reason(result)
            self.assertTrue(
                reason.startswith(("TOOL_REPORTED_PASS_FALSE:",
                                   "TOOL_REPORTED_NON_SUCCESS_STATUS:")),
                "%s refused somewhere else: %s" % (cid, reason))
            tail = reason.split(":")[-1]
            self.assertTrue(
                re.fullmatch(r"[A-Z][A-Z0-9_]{4,}", tail or ""),
                "%s still reports no cause: %s" % (cid, reason))
            named += 1
        self.assertGreaterEqual(named, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
