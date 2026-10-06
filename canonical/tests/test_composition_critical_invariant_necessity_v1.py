import unittest
from canonical.runtime.composition_critical_invariant_necessity_v1 import countermodel, verify

class TestCompositionCriticalInvariantNecessity(unittest.TestCase):
    def test_countermodel(self):
        x=countermodel()
        self.assertTrue(x["terminal_equal"])
        self.assertFalse(x["zero_internal_failures"])
        self.assertTrue(x["necessity_countermodel"])

    def test_verifier(self):
        self.assertTrue(verify().startswith("PASS__"))

if __name__=="__main__":
    unittest.main(verbosity=2)
