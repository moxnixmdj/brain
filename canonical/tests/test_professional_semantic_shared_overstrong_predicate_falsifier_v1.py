from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import professional_semantic_shared_overstrong_predicate_falsifier_v1 as s

class Tests(unittest.TestCase):
 def test_current_batch_all_twelve_falsified_as_universal_success_gates(self):
  out=s.evaluate()
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["semantic_leaf_count"],12)
  self.assertEqual(out["overstrong_predicate_falsified_count"],12)
  self.assertTrue(out["all_12_existing_universal_success_predicates_falsified"])
  self.assertEqual(out["repaired_semantic_property_truth_proved_count"],0)
  self.assertFalse(out["terminal_authority"])
 def test_acceptance_drift_fails_closed(self):
  with patch.object(s,"EXPECTED_ACCEPTANCE","DRIFT"):
   out=s.evaluate()
  self.assertFalse(out["pass"])
  self.assertIn("ACCEPTANCE",out["reason"])
 def test_quantifier_drift_fails_closed(self):
  with patch.object(s,"EXPECTED_QUANTIFIER","DRIFT"):
   out=s.evaluate()
  self.assertFalse(out["pass"])
  self.assertIn("UNIVERSAL",out["reason"])

if __name__=="__main__":unittest.main(verbosity=2)
