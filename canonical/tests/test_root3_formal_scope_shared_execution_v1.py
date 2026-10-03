from __future__ import annotations
import copy
import unittest
from unittest import mock
from canonical.runtime import root3_formal_scope_shared_execution_v1 as r

class TestRoot3FormalScopeSharedExecutionV1(unittest.TestCase):
    def test_current_bound_execution_localizes_all_seven(self):
        out=r.execute()
        self.assertTrue(out["pass"])
        self.assertEqual(out["formal_target_count"],7)
        self.assertEqual(out["formal_targets_closed"],0)
        self.assertEqual(out["formal_targets_open"],7)
        self.assertTrue(out["current_bound_formal_search_exhausted"])
        self.assertFalse(out["global_nonexistence_claimed"])
        self.assertFalse(out["fresh_reality_authority"])

    def test_new_full_protocol_witness_invalidates_fixed_result(self):
        real=r.load
        def fake(key):
            x=copy.deepcopy(real(key))
            if key=="saturation":
                x["other_live_root3_target_result"]["current_full_protocol_transmutation_witness_count"]=1
            return x
        with mock.patch.object(r,"load",side_effect=fake):
            out=r.execute()
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_FULL_PROTOCOL_WITNESS_APPEARED",out["errors"])

    def test_composition_delta_wakes_formal_state(self):
        real=r.load
        def fake(key):
            x=copy.deepcopy(real(key))
            if key=="composition":
                x["truth"]["current_admissible_scoped_proved"]=5
                x["truth"]["current_open"]=7
            return x
        with mock.patch.object(r,"load",side_effect=fake):
            out=r.execute()
        self.assertFalse(out["pass"])
        self.assertIn("COMPOSITION_COMPONENT_STATE_DRIFT",out["errors"])

    def test_generated_matched_portfolio_invalidates_current_blocker(self):
        real=r.load
        def fake(key):
            x=copy.deepcopy(real(key))
            if key=="superportfolio":
                for row in x["root3_reality_fallback"]["batch_classes"]:
                    if row["id"]=="ROOT3_MATCHED_SUPERPORTFOLIO_WAVE":
                        row["current_state"]="READY"
            return x
        with mock.patch.object(r,"load",side_effect=fake):
            out=r.execute()
        self.assertFalse(out["pass"])
        self.assertIn("MATCHED_PORTFOLIO_GENERATION_STATE_DRIFT",out["errors"])

if __name__=="__main__":
    unittest.main()
