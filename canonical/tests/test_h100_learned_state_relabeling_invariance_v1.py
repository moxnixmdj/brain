import unittest
from canonical.runtime import h100_learned_state_relabeling_invariance_v1 as r

class T(unittest.TestCase):
 def test_roundtrip(self):
  x=bytes(range(256))
  o=r.behavior_preserving_relabel(x)
  self.assertTrue(o["behavioral_state_bytes_identical"])
  self.assertEqual(o["original_learned_bytes"],256)
  self.assertEqual(o["relabelled_accounted_learned_bytes"],0)
 def test_hash_preserved(self):
  o=r.behavior_preserving_relabel(b"capability-state")
  self.assertEqual(o["payload_sha256"],o["recovered_sha256"])
 def test_invariant_accounting_unchanged_by_category_swap(self):
  self.assertEqual(r.invariant_accounting_bits(learned_bytes=100,deterministic_capability_bytes=0),r.invariant_accounting_bits(learned_bytes=0,deterministic_capability_bytes=100))
 def test_invalid(self):
  with self.assertRaises(r.RelabelingInvariantError): r.embed_bytes_as_deterministic_literal(b"")
if __name__=="__main__": unittest.main(verbosity=2)
