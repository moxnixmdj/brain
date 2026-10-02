from __future__ import annotations

import json
import unittest

from canonical.runtime.opus55_family_ownership_promotion_eligibility_v1 import (
    ROOT,
    _assert_witness_doc,
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

    def test_tool_witness_scope_weakened_fails_closed(self):
        p=ROOT/"canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        d["closes_entire_protocol"]=False
        with self.assertRaises(AssertionError):
            _assert_witness_doc(d,"TOOL_DISCOVERY_SELECTION_AND_LEARNING",180)

    def test_delegation_non_ceiling_fails_closed(self):
        p=ROOT/"canonical/governance/DELEGATION_ACCEPTANCE_CEILING_WITNESS_V1.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        d["result"]["brain_lower_bound"]=0.99
        with self.assertRaises(AssertionError):
            _assert_witness_doc(d,"SUBAGENT_DELEGATION_AND_COORDINATION",132)

    def test_contamination_fails_closed(self):
        p=ROOT/"canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        d["contamination_clean"]=False
        with self.assertRaises(AssertionError):
            _assert_witness_doc(d,"TOOL_DISCOVERY_SELECTION_AND_LEARNING",180)

    def test_verifier_keeps_promotion_separate(self):
        out=verify()
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
