import unittest
from canonical.runtime.terminal_semantic_quotient_v1 import compile_minimal_quotient,verify_binding

ROWS=[
 {"raw_id":"x0","signature_complete":True,"terminal_signature":{"decision":"ALLOW","constraint":"PASS"}},
 {"raw_id":"x1","signature_complete":True,"terminal_signature":{"decision":"ALLOW","constraint":"PASS"}},
 {"raw_id":"x2","signature_complete":True,"terminal_signature":{"decision":"DENY","constraint":"PASS"}},
 {"raw_id":"x3","signature_complete":True,"terminal_signature":{"decision":"ABSTAIN","constraint":"PASS"}},
]

class Tests(unittest.TestCase):
 def test_minimum_quotient_merges_only_terminal_equivalents(self):
  out=compile_minimal_quotient(ROWS)
  self.assertTrue(out["pass"])
  self.assertEqual(out["class_count"],3)
  self.assertEqual(out["raw_to_class"]["x0"],out["raw_to_class"]["x1"])
  self.assertNotEqual(out["raw_to_class"]["x0"],out["raw_to_class"]["x2"])

 def test_false_merge_fails_closed(self):
  out=verify_binding(ROWS,{"x0":"A","x1":"A","x2":"A","x3":"B"})
  self.assertFalse(out["pass"])
  self.assertIn("DISTINGUISHABLE",out["status"])

 def test_redundant_split_is_safe_but_nonminimal(self):
  out=verify_binding(ROWS,{"x0":"A","x1":"B","x2":"C","x3":"D"})
  self.assertTrue(out["pass"])
  self.assertFalse(out["minimal"])

 def test_exact_minimum_binding_passes(self):
  comp=compile_minimal_quotient(ROWS)
  out=verify_binding(ROWS,comp["raw_to_class"])
  self.assertTrue(out["pass"])
  self.assertTrue(out["minimal"])

 def test_incomplete_signature_fails_closed(self):
  bad=[dict(ROWS[0]),dict(ROWS[1])]
  bad[1]["signature_complete"]=False
  out=compile_minimal_quotient(bad)
  self.assertFalse(out["pass"])
  self.assertIn("COMPLETENESS_UNPROVED",out["reason"])

if __name__=="__main__":
 unittest.main(verbosity=2)
