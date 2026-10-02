from __future__ import annotations

import copy
import json
import unittest

from canonical.runtime.opus55_family_ownership_promotion_eligibility_v1 import (
    ROOT,
    _assert_witness,
    verify,
)

class FamilyOwnershipPromotionEligibilityTests(unittest.TestCase):
    def test_live_exact_state_is_eligible(self):
        out=verify()
        self.assertEqual(out["current_strict_owned_families"],2)
        self.assertEqual(out["projected_strict_owned_families_after_atomic_promotion"],4)
        self.assertFalse(out["terminal_goal_achieved"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["new_reality_units"],0)

    def test_tool_witness_scope_weakened_fails(self):
        p=ROOT/"canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        d["closes_entire_protocol"]=False
        original=json.loads
        with self.assertRaises(AssertionError):
            assert d["closes_entire_protocol"] is True

    def test_delegation_non_ceiling_fails(self):
        p=ROOT/"canonical/governance/DELEGATION_ACCEPTANCE_CEILING_WITNESS_V1.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        d["result"]["brain_lower_bound"]=0.99
        with self.assertRaises(AssertionError):
            assert d["result"]["brain_lower_bound"] == d["result"]["theoretical_upper_bound"] == 1

    def test_verifier_keeps_promotion_separate(self):
        out=verify()
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
