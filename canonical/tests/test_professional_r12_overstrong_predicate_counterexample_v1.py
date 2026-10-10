from __future__ import annotations
from copy import deepcopy
import unittest
from canonical.runtime import professional_r12_overstrong_predicate_counterexample_v1 as c

class Tests(unittest.TestCase):
 def test_constructive_counterexample_falsifies_universal_success_predicate(self):
  out=c.verify()
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["counterexample_admissible"])
  self.assertTrue(out["stronger_universal_predicate_falsified"])
  self.assertFalse(out["common_positive_semantic_resolution_policy_exists"])
  self.assertTrue(out["safe_fail_closed_policy_exists"])
  self.assertTrue(out["mission_correct_abstention"])
  self.assertFalse(out["stronger_r12_property_truth_authority"])
 def test_visible_world_distinction_breaks_counterexample(self):
  x=c.build_counterexample()
  x["worlds"][1]["visible_input"]=deepcopy(x["worlds"][1]["visible_input"])
  x["worlds"][1]["visible_input"]["source_evidence"]=deepcopy(x["worlds"][1]["visible_input"]["source_evidence"])
  x["worlds"][1]["visible_input"]["source_evidence"]["visible_statement"]="H=1"
  out=c.evaluate(x)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"WORLDS_NOT_VISIBLY_INDISTINGUISHABLE")
 def test_source_disclosure_breaks_information_boundary(self):
  x=c.build_counterexample()
  x["visible_input"]["source_evidence"]["value_disclosed"]=True
  for w in x["worlds"]:w["visible_input"]=x["visible_input"]
  out=c.evaluate(x)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"SOURCE_VALUE_NOT_PROVED_WITHHELD")
 def test_incomplete_world_set_fails_closed(self):
  x=c.build_counterexample();x["world_hypothesis_set_complete"]=False
  out=c.evaluate(x)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"HYPOTHESIS_SET_COMPLETENESS_UNPROVED")
 def test_abstention_must_have_zero_positive_credit(self):
  x=c.build_counterexample();x["safe_common_policy"]["positive_property_credit"]=True
  out=c.evaluate(x)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"SAFE_ABSTENTION_POLICY_INVALID")

if __name__=="__main__":unittest.main(verbosity=2)
