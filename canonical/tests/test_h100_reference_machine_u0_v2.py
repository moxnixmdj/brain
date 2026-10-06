import unittest
from canonical.runtime import h100_reference_machine_u0_v2 as u
class T(unittest.TestCase):
 def test_helper_function_module_semantics(self):
  src="def inc(x):\n return x+1\ndef solve(x):\n return inc(x)*2\n"
  self.assertEqual(u.execute(src,4),10)
 def test_import_rejected(self):
  with self.assertRaises(u.ReferenceMachineError): u.execute("import math\ndef solve(x): return 1\n",None)
 def test_attribute_rejected(self):
  with self.assertRaises(u.ReferenceMachineError): u.execute("def solve(x): return x.bit_length()\n",2)
 def test_canonical_whitespace_invariant(self):
  a="def solve(x):\n return x+1\n"; b="def solve(x):\n    return x + 1\n"
  self.assertEqual(u.canonical_program_bytes(a),u.canonical_program_bytes(b))
 def test_shared_namespace_contract(self):
  self.assertTrue(u.machine_contract()["shared_module_namespace"])
if __name__=="__main__": unittest.main(verbosity=2)
