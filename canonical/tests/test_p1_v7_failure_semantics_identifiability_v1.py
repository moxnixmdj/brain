from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_v7_failure_semantics_identifiability_v1 as cut
from canonical.runtime.p1_v6_derived_only_counterexample_v1 import public_counterexample


class Tests(unittest.TestCase):
    def test_current_projection_is_nonidentifying(self):
        out = cut.evaluate()
        self.assertTrue(out["theorem_established"], out)
        self.assertEqual(
            out["status"],
            "PASS__CURRENT_FROZEN_TRANSPORT_PROJECTION_UNDERDETERMINES_V7_FAILURE_SEMANTICS__ZERO_CREDIT",
        )
        self.assertTrue(out["projection_equal_after_removing_failure_semantics"])
        self.assertTrue(out["required_behavior_differs"])
        self.assertEqual(out["worlds"]["derived_upstream"]["candidate_status"], "ESCALATE")
        self.assertFalse(out["worlds"]["derived_upstream"]["terminal_rescued"])
        self.assertEqual(out["worlds"]["direct_contract"]["candidate_status"], "IDENTIFIED")
        self.assertEqual(out["worlds"]["direct_contract"]["cause_action_id"], "A1")
        self.assertTrue(out["worlds"]["direct_contract"]["terminal_rescued"])
        self.assertEqual(
            out["minimum_missing_fact"],
            "FAILURE_SEMANTICS_OR_AN_INDEPENDENTLY_PROVED_EQUIVALENT_DISCRIMINATOR",
        )
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_projection_really_erases_only_semantic_discriminator(self):
        derived = public_counterexample()
        direct = cut._set_failed_semantics(derived, "DIRECT_CONTRACT")
        self.assertNotEqual(derived, direct)
        self.assertEqual(
            cut._project_without_failure_semantics(derived),
            cut._project_without_failure_semantics(direct),
        )

    def test_worlds_have_same_nonsemantic_failed_check_fields(self):
        derived = public_counterexample()
        direct = cut._set_failed_semantics(derived, "DIRECT_CONTRACT")
        for drow, xrow in zip(derived["task"]["trajectory"], direct["task"]["trajectory"]):
            for dc, xc in zip(drow["checks"], xrow["checks"]):
                d = copy.deepcopy(dc)
                x = copy.deepcopy(xc)
                d.pop("failure_semantics", None)
                x.pop("failure_semantics", None)
                self.assertEqual(d, x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
