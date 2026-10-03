from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_scope_truth_repair_v1 as r

class Tests(unittest.TestCase):
 def test_scope_overclaim_is_falsified(self):
  out=r.evaluate()
  self.assertTrue(out["status"].startswith("PASS__"),out)
  self.assertTrue(out["target_requires_identity_discovery"])
  self.assertTrue(out["bound_terminal_route_preenumerates_all_case_tool_ids"])
  self.assertFalse(out["complete_target_case_set_supported"])
  self.assertFalse(out["acceptance_reduction_using_exact_complete_target_case_universe_is_admissible"])

 def test_no_credit_or_replay(self):
  out=r.evaluate()
  self.assertEqual(out["terminal_results_replayed"],0)
  self.assertEqual(out["new_reality_units_consumed"],0)
  self.assertEqual(out["family_credit_delta"],0)
  self.assertEqual(out["capability_credit_delta"],0)
  self.assertFalse(out["execution_authority"])
  self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
 unittest.main(verbosity=2)
