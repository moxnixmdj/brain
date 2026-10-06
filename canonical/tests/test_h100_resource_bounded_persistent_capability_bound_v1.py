import unittest
from canonical.runtime import h100_resource_bounded_persistent_capability_bound_v1 as b

class T(unittest.TestCase):
    def test_class_bits(self):
        self.assertEqual(b.class_bits(1),0)
        self.assertEqual(b.class_bits(2),1)
        self.assertEqual(b.class_bits(3),2)
        self.assertEqual(b.class_bits(1024),10)
    def test_code_learned_trade(self):
        self.assertEqual(b.learned_bits_lower_bound(256,4),4)
        self.assertEqual(b.learned_bits_lower_bound(256,8),0)
    def test_boolean_class(self):
        self.assertEqual(b.boolean_function_total_bits_lower_bound(3),8)
        self.assertEqual(b.boolean_function_total_bits_lower_bound(4),16)
    def test_invalid(self):
        with self.assertRaises(b.PersistentCapabilityBoundError): b.class_bits(0)
        with self.assertRaises(b.PersistentCapabilityBoundError): b.learned_bits_lower_bound(2,-1)
if __name__=="__main__": unittest.main(verbosity=2)
