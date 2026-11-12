#!/usr/bin/env python3
"""A refusal that says WHY must not be replaced by a refusal that says only WHERE it happened.

MEASURED, 2026-11-12, on the 39 realistic advanced-coding sentences of
`canonical/tools/realistic_goal_reach_probe_v1.py`, in a disposable clone:

    carrier status (`...COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`)  21 of 39
    ... of those, already refused for a DIFFERENT, specific reason          18 of 21

`_serve_by_acting` is a carrier rule: it fires whenever a sentence names an output suffix the
program synthesizer can verify.  When it fired, it returned a fresh result carrying the carrier
status and kept the door's own already-computed reason only in `served_after` -- so every reader
downstream saw "confinement", including the two documents merged the same day that then
diagnosed this wall in opposite directions (one "binding, 54 capabilities", one "no
binding-shaped status at the door").  Both were reading the label.

THE RULE THIS FILE PINS.  When the door has already decided why a request cannot be served, and
NOTHING has executed, that decision is the answer; the carrier status is recorded under
`carrier_gate` rather than deleted.  When the earlier attempt reports `executed: True` or
`side_effects_may_exist: True`, uncertainty wins and the carrier status stays -- that half is a
safety property, not the defect, and is pinned below so a later round cannot "fix" it.

Producer-run, one machine, $0, zero model dependency.  Authority NONE.
"""
from __future__ import annotations

import unittest
from unittest import mock

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller

BOUNDARY = "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"

#: A sentence the carrier rule actually fires on: it names an output suffix the program
#: synthesizer has a verifier and content evidence for.  Copied from the realistic corpus.
CARRIER_SENTENCE = ("Rank the markdown sources in this repository by their relevance to "
                    "binding repair and write the ranking to relevance_ranking.json")


class TheCarrierGateDoesNotEatTheReasonTests(unittest.TestCase):
    def test_the_carrier_rule_really_fires_on_this_sentence(self):
        """Without this the two tests below could pass by measuring nothing."""
        from canonical.runtime import cli_capability_acquisition_v1 as acq
        from canonical.runtime import program_synthesis_v1 as ps

        suffix = acq._requested_suffix(CARRIER_SENTENCE)
        self.assertTrue(suffix, "the sentence must name an output suffix")
        self.assertTrue(ps.has_verifier(suffix) and ps.carries_content_evidence(suffix),
                        "the carrier rule must fire on this sentence, or this file measures nothing")

    def test_a_specific_refusal_that_executed_nothing_keeps_its_own_reason(self):
        prior = {"pass": False, "executed": False,
                 "status": "FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED",
                 "failure_class": "STATED_SWE_EFFECT_UNSERVED"}
        with mock.patch.object(door, "_solve_request", return_value=prior):
            result = door.solve({"task_id": "T", "goal": CARRIER_SENTENCE})
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], "FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED",
                         "the reason the door computed must survive the carrier gate")
        self.assertNotEqual(result["status"], BOUNDARY)
        # The carrier decision is NOT deleted -- it moves.
        self.assertEqual(result["carrier_gate"]["status"], BOUNDARY)
        self.assertEqual(result["served_after"], prior["status"])
        self.assertTrue(result["refusal_precedes_the_carrier_gate"])
        # Still a refusal, still nothing claimed as executed.
        self.assertFalse(result.get("executed"))
        self.assertFalse(result["fallback_executed"])

    def test_an_attempt_that_may_have_executed_keeps_the_carrier_answer(self):
        """THE SAFETY HALF.  Uncertainty about effects outranks a tidier label."""
        prior = {"pass": False, "executed": True, "side_effects_may_exist": True,
                 "status": "FAIL__RAW_GOAL_COMPILATION_GAP",
                 "failure_class": "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP"}
        with mock.patch.object(door, "_solve_request", return_value=prior):
            result = door.solve({"task_id": "T", "goal": CARRIER_SENTENCE})
        self.assertEqual(result["status"], BOUNDARY)
        self.assertTrue(result.get("side_effects_may_exist"))
        self.assertNotIn("refusal_precedes_the_carrier_gate", result)

    def test_a_request_that_reached_no_decision_keeps_the_carrier_answer(self):
        """`FAIL_CLOSED` alone names no reason, so there is nothing worth keeping.

        (Note `REQUEST_INVALID` is a recognised honest refusal and never reaches this branch at
        all -- it is returned untouched, which is the stronger outcome, not this one.)
        """
        prior = {"pass": False, "executed": False, "status": "FAIL_CLOSED"}
        with mock.patch.object(door, "_solve_request", return_value=prior):
            result = door.solve({"task_id": "T", "goal": CARRIER_SENTENCE})
        self.assertEqual(result["status"], BOUNDARY)

    def test_the_predicate_agrees_with_the_three_cases(self):
        decided = door._decided_before_the_carrier_gate
        self.assertTrue(decided({"status": "FAIL_CLOSED__NO_OBSERVED_EFFECT"}))
        self.assertFalse(decided({"status": "FAIL_CLOSED__NO_OBSERVED_EFFECT", "executed": True}))
        self.assertFalse(decided({"status": "FAIL__RAW_GOAL_COMPILATION_GAP",
                                  "side_effects_may_exist": True}))
        self.assertFalse(decided({"status": ""}))
        self.assertFalse(decided({"status": "FAIL_CLOSED"}))

    def test_the_carrier_status_is_still_a_honest_refusal_class(self):
        """The boundary's own answer is still recognised; nothing here loosens the gate."""
        self.assertTrue(controller._is_honest_contract_refusal({"status": BOUNDARY}))


if __name__ == "__main__":
    unittest.main()
