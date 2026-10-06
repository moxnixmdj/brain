import unittest
from canonical.runtime import h100_shared_substrate_portfolio_bound_v1 as p

class T(unittest.TestCase):
    def test_portfolio(self):
        self.assertEqual(p.portfolio_bits(100,[10,20,30]),160)
    def test_beneficial(self):
        r=p.primitive_delta(added_shared_bits=50,before_patch_bits=[40,40,40],after_patch_bits=[10,10,10])
        self.assertTrue(r["beneficial"])
        self.assertEqual(r["net_portfolio_delta_bits"],-40)
    def test_not_beneficial(self):
        r=p.primitive_delta(added_shared_bits=100,before_patch_bits=[40,40],after_patch_bits=[10,10])
        self.assertFalse(r["break_even_or_better"])
    def test_break_even(self):
        self.assertEqual(p.uniform_break_even_reuse_count(100,30),4)
        self.assertIsNone(p.uniform_break_even_reuse_count(100,0))
    def test_compare(self):
        self.assertTrue(p.compare(0,[100,100,100],80,[10,10,10])["improved"])

if __name__=="__main__":
    unittest.main(verbosity=2)
