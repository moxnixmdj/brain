"""A capability that printed "no" is not a pass, whichever lane ran it.

The generic command adapter (`canonical/runtime/bound_capabilities/cli_command.py`)
reports what it ran, not what it found:

    {"adapter": "bound_capability_cli", "argv": [...], "returncode": 0,
     "stdout": "<the capability's JSON>", "stderr": ""}

The capability's judgement is the JSON on `stdout`.  `tool_truth_errors()` read
`pass` and `status` off the envelope, where neither key exists, found no evidence
of failure, and returned `[]`.  So for every capability in that lane the truth
check could not see a failure, and the door marked the goal PASS.

Measured on c79a8f5 over the 616 CLI-shaped registry rows, running each one
through `capability_receipt_lane_v1.run_cli_adapter` (the same runner that issues
their receipts): 183 ran and printed JSON, 120 print `pass`, 148 print `status`,
and **21 print a non-success verdict with exit code 0**.  All 21 were credited as
successes.  Five of them, driven through the real door on c79a8f5:

    run ...professional_quality_leaf_binder_v1.py.auto.v1
      printed {"pass": false, "status": "OPEN__DOMAIN_LEAVES_OR_EVIDENCE_FRESHNESS_REMAIN"}
      door said PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
    run ...verify_terminal_scheduling_v11_candidate_v1.py.auto.v1
      printed {"pass": false, "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT"}
      door said PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
    run ...target_role_escape_frontier_v1.py.auto.v1                     -> FAIL_CLOSED
    run ...v13_db_existing_evidence_saturation_verifier_v1.py.auto.v1     -> FAIL_CLOSED
    run ...shared_channel_dominator_v1.py.auto.v1                        -> FAIL_CLOSED
    (all five: pass=True, semantic_acceptance_complete=True, tool_truth_errors=None)

That is the defect of HARDCORE_SWE_PROBLEMS_20261029_V1.md §1.1 at the level of
one step: the answer is in hand, and the check reads the wrapper instead of the
answer.  §1.1 was a verifier whose stdout said ``"pass": true`` about set theory
being read as the verdict on a request about git; this is the same thing made
systematic by a single missing read.

The rule enforced here is two-sided on purpose.  A step that printed ``pass:
false`` or a ``FAIL*``/``OPEN*``/``UNRESOLVED*``/``ERROR*``/``BLOCKED*``/
``REJECTED*``/``INCOMPLETE*`` status fails, and a step that printed ``pass:
true`` with a ``PASS*`` status still passes.  A check that only ever says "no"
would be a different bug.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "canonical" / "runtime") not in sys.path:
    sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

from canonical.runtime.live_brain_route_admission_v1 import (  # noqa: E402
    _printed_verdict,
    failure_reason,
    solve,
    tool_truth_errors,
)

CID = "canonical/runtime/example_v1.py.auto.v1"


def _envelope(stdout: str, returncode: int = 0, capability_id: str = CID) -> dict:
    """One step result in the shape the command lane really produces."""
    return {
        "execution": [{
            "capability_id": capability_id,
            "result": {
                "adapter": "bound_capability_cli",
                "argv": ["python3", "canonical/runtime/example_v1.py"],
                "returncode": returncode,
                "stdout": stdout,
                "stderr": "",
            },
        }]
    }


class ThePrintedVerdictIsReadThroughTheEnvelope(unittest.TestCase):
    """`_printed_verdict` finds the document, and does not invent one."""

    def test_a_printed_json_object_is_the_verdict(self) -> None:
        found = _printed_verdict(_envelope('{"pass": false, "reason": "X"}')["execution"][0]["result"])
        self.assertEqual(found, {"pass": False, "reason": "X"})

    def test_a_progress_line_before_the_verdict_does_not_hide_it(self) -> None:
        # Adapters print progress, and the envelope keeps only the tail of stdout,
        # so the document is frequently not at offset 0.
        found = _printed_verdict(
            _envelope('loading sources\nscan 1/3\nscan 2/3\n{"pass": false, "status": "FAIL_CLOSED__DRIFT"}')["execution"][0]["result"]
        )
        self.assertEqual(found.get("status"), "FAIL_CLOSED__DRIFT")

    def test_prose_is_not_a_verdict(self) -> None:
        # A program that printed plain text made no claim; it must not be
        # overruled by a check that cannot read its sentence.
        self.assertIsNone(_printed_verdict(_envelope("3 rows\nall good\n")["execution"][0]["result"]))

    def test_empty_output_is_not_a_verdict(self) -> None:
        self.assertIsNone(_printed_verdict(_envelope("   ")["execution"][0]["result"]))

    def test_a_plain_result_mapping_is_not_an_envelope(self) -> None:
        # The local-adapter lane returns the verdict directly. Nothing to unwrap,
        # and in particular an unrelated `stdout` field must not be parsed.
        self.assertIsNone(_printed_verdict({"status": "PASS__OK", "stdout": '{"pass": false}'}))

    def test_a_nested_test_record_is_not_an_envelope(self) -> None:
        # Three adapters carry `returncode` beside `stdout` inside a per-test
        # record.  Unwrapping one of those would read a test runner's output as
        # the capability's verdict, which is the §1.1 mistake in reverse: an
        # answer to another question taken as the answer to this one.
        self.assertIsNone(_printed_verdict({"returncode": 0, "stdout": '{"pass": false}'}))


class APassFalseIsNeverAPass(unittest.TestCase):
    def test_pass_false_fails_even_with_exit_zero(self) -> None:
        errors = tool_truth_errors(_envelope('{"pass": false, "reason": "NO_BINDING"}'))
        self.assertEqual(errors, ["TOOL_REPORTED_PASS_FALSE:" + CID])

    def test_a_non_success_status_fails_and_is_quoted(self) -> None:
        errors = tool_truth_errors(_envelope('{"status": "OPEN__DOMAIN_LEAVES_REMAIN"}'))
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("TOOL_REPORTED_NON_SUCCESS_STATUS:" + CID))
        self.assertIn("OPEN__DOMAIN_LEAVES_REMAIN", errors[0])

    def test_every_non_success_prefix_is_recognised(self) -> None:
        for word in ("FAIL", "OPEN", "UNRESOLVED", "ERROR", "BLOCKED", "REJECTED", "INCOMPLETE"):
            with self.subTest(word=word):
                errors = tool_truth_errors(_envelope('{"status": "%s_X"}' % word))
                self.assertEqual(len(errors), 1, word)

    def test_both_causes_are_reported_once_each(self) -> None:
        errors = tool_truth_errors(_envelope('{"pass": false, "status": "FAIL_CLOSED__DRIFT"}'))
        self.assertEqual(len(errors), 2)
        self.assertEqual(len(set(errors)), 2)


class APassTrueIsStillAPass(unittest.TestCase):
    """The other half of the rule: the check must not refuse work that succeeded."""

    def test_pass_true_with_a_pass_status_is_clean(self) -> None:
        self.assertEqual(tool_truth_errors(_envelope('{"pass": true, "status": "PASS__ROWS_READ", "rows": [1, 2]}')), [])

    def test_a_verdict_with_no_pass_key_and_no_status_is_clean(self) -> None:
        self.assertEqual(tool_truth_errors(_envelope('{"rows": [1, 2, 3]}')), [])

    def test_a_nonzero_exit_is_not_an_error_by_itself(self) -> None:
        # `diff` exits 1 to say "these differ"; the adapter documents that a code
        # the caller declared is an answer, not a failure.  Exit code is not the
        # verdict, which is exactly why the printed verdict has to be read.
        self.assertEqual(tool_truth_errors(_envelope('{"pass": true}', returncode=1)), [])


class APayloadThatAnswersAnotherQuestionIsRefused(unittest.TestCase):
    """§1.1's rule, enforced where it is mechanical."""

    def test_a_payload_naming_another_capability_is_refused(self) -> None:
        errors = tool_truth_errors(_envelope('{"pass": true, "capability_id": "other.capability.v1"}'))
        self.assertEqual(errors, ["TOOL_ANSWERED_A_DIFFERENT_QUESTION:" + CID + ":PRINTED:other.capability.v1"])

    def test_a_payload_naming_the_capability_that_ran_is_clean(self) -> None:
        self.assertEqual(tool_truth_errors(_envelope('{"pass": true, "capability_id": "%s"}' % CID)), [])


class TheReasonSurvivesTheEnvelope(unittest.TestCase):
    def test_the_printed_reason_reaches_the_failure_reason(self) -> None:
        result = _envelope('{"pass": false, "reason": "V3_INPUT_REQUIRED"}')
        result["pass"] = False
        result["tool_truth_errors"] = tool_truth_errors(result)
        self.assertIn("V3_INPUT_REQUIRED", failure_reason(result))


class ThroughTheRealDoor(unittest.TestCase):
    """Five capabilities that printed "no" with exit 0, driven end to end.

    Chosen by measurement on c79a8f5 -- each one runs through the command lane,
    exits 0, and prints `pass: false` / a FAIL* status.  Each was PASS with
    `semantic_acceptance_complete: True` on c79a8f5.
    """

    REFUSED = (
        "canonical/runtime/professional_quality_leaf_binder_v1.py.auto.v1",
        "canonical/runtime/verify_terminal_scheduling_v11_candidate_v1.py.auto.v1",
        "canonical/runtime/target_role_escape_frontier_v1.py.auto.v1",
        "canonical/runtime/v13_db_existing_evidence_saturation_verifier_v1.py.auto.v1",
        "canonical/runtime/shared_channel_dominator_v1.py.auto.v1",
    )

    def test_a_capability_that_printed_no_does_not_pass(self) -> None:
        for cid in self.REFUSED:
            with self.subTest(capability_id=cid):
                verdict = solve({"task_id": "printed-verdict", "goal": "run " + cid})
                self.assertFalse(verdict.get("pass"), verdict.get("status"))
                self.assertNotIn("PASS", str(verdict.get("status")))
                self.assertTrue(verdict.get("tool_truth_errors"), verdict)

    def test_a_capability_that_printed_yes_still_passes(self) -> None:
        # The same lane, the same envelope, the same code path -- only the
        # printed verdict differs.
        verdict = solve({"task_id": "printed-verdict-ok",
                         "goal": "run canonical/runtime/accepted_pure_route_static_reachability_v1.py.auto.v1"})
        self.assertTrue(verdict.get("pass"), verdict.get("status"))
        self.assertFalse(verdict.get("tool_truth_errors"))


if __name__ == "__main__":
    unittest.main()
