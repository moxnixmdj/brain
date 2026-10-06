import unittest
from canonical.runtime import h100_representation_invariance_v1 as r

class T(unittest.TestCase):
    XS=[-3,-1,0,0.5,2,7]
    def test_learned_blob_can_be_compiled_into_code_constants(self):
        out=r.learned_to_code_equivalent({"a":1.75,"b":-0.4},self.XS)
        self.assertTrue(out["equivalent"])
        self.assertEqual(out["parameter_behavior_sha256"],out["compiled_behavior_sha256"])
    def test_code_constants_can_be_externalized_as_frozen_blob(self):
        out=r.code_to_blob_equivalent(1.75,-0.4,self.XS)
        self.assertTrue(out["equivalent"])
        self.assertEqual(out["code_behavior_sha256"],out["blob_behavior_sha256"])
    def test_accounting_conclusion(self):
        c=r.accounting_conclusion()
        self.assertFalse(c["learned_bytes_representation_invariant"])
        self.assertTrue(c["total_persistent_capability_bearing_information_should_be_reported"])
    def test_payload_size_nonzero(self):
        out=r.learned_to_code_equivalent({"a":1.0,"b":2.0},[0,1])
        self.assertGreater(out["parameter_blob_bytes"],0)
        self.assertGreater(out["code_constant_payload_bytes"],0)

if __name__=="__main__": unittest.main(verbosity=2)
