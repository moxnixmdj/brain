import unittest
from canonical.runtime import h100_reference_machine_u0_v1 as u

class T(unittest.TestCase):
 def test_pure_program_executes(self):
  src="def solve(x):\n return x[0]+x[1]\n"
  self.assertEqual(u.execute(src,[2,5]),7)
 def test_import_rejected(self):
  with self.assertRaises(u.ReferenceMachineError): u.execute("import math\ndef solve(x): return 1\n",None)
 def test_attribute_rejected(self):
  with self.assertRaises(u.ReferenceMachineError): u.execute("def solve(x): return x.bit_length()\n",2)
 def test_open_rejected(self):
  with self.assertRaises(u.ReferenceMachineError): u.execute("def solve(x): return open(x)\n","a")
 def test_canonical_measure_ignores_whitespace(self):
  a="def solve(x):\n return x+1\n"
  b="def solve(x):\n    return x + 1\n"
  self.assertEqual(u.canonical_program_bytes(a),u.canonical_program_bytes(b))
 def test_contract_has_no_imports(self):
  self.assertFalse(u.machine_contract()["imports_allowed"])
if __name__=="__main__": unittest.main(verbosity=2)
