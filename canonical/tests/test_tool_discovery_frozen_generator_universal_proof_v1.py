from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_frozen_generator_universal_proof_v1 as p

class Tests(unittest.TestCase):
 def test_universal_proof_passes_without_terminal_replay(self):
  out=p.evaluate()
  self.assertTrue(out["universal_formal_scope_proved"],out)
  self.assertEqual(out["proof_basis"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
  self.assertTrue(out["result"]["all_admissible_inputs_proved"])
  self.assertTrue(out["result"]["formal_completeness"])
  self.assertEqual(out["terminal_cases_replayed"],0)
  self.assertEqual(out["new_reality_units_consumed"],0)
 def test_six_classes_are_exact_and_all_pass(self):
  out=p.evaluate();q=out["generator_quotient"]
  self.assertEqual(q["class_count"],6)
  self.assertEqual(tuple(q["classes"]),p.CLASSES)
  self.assertEqual({r["class"] for r in q["representatives"]},set(p.CLASSES))
  self.assertTrue(all(r["pass"] for r in q["representatives"]))
 def test_expected_route_costs(self):
  out=p.evaluate()
  got={r["class"]:(r["stage1_cost"],r["stage2_cost"]) for r in out["generator_quotient"]["representatives"]}
  self.assertEqual(got,p.EXPECTED_SELECTION_COSTS)
 def test_seed_semantics_are_alpha_renaming_only(self):
  out=p.evaluate()
  self.assertTrue(out["source_lemmas"]["V1_RANDOMNESS_ONLY_CHANGES_STRING_LABELS"])
  self.assertTrue(out["source_lemmas"]["ALL_SEED_VARIATION_IS_ALPHA_RENAMING_AFTER_CLASS_FIX"])
  self.assertTrue(out["name_equivariance"]["proved"])
 def test_budget_is_universal_bound_not_sample_statistic(self):
  out=p.evaluate()
  self.assertEqual(out["action_bound"]["bound"],9)
  self.assertLessEqual(out["action_bound"]["bound"],out["action_bound"]["minimum_evaluator_budget"])
  self.assertIn("NO_RELIANCE_ON_180_OF_180_FOR_UNIVERSALITY",out["hard_nonclaims"])

if __name__=="__main__":unittest.main(verbosity=2)
