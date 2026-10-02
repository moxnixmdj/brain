import unittest
from canonical.runtime import saccr_terminal_population_binding_v1 as t

class Tests(unittest.TestCase):
    def test_seed_binding(self):
        a=t.derive_seed("commit-A","beacon-A",0)
        self.assertEqual(a,t.derive_seed("commit-A","beacon-A",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-B",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-A",1))

    def test_development_population_smoke(self):
        out=t.run_population("DEV_ONLY_NOT_TERMINAL_COMMITMENT","DEV_ONLY_NOT_TERMINAL_BEACON")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["sample_count"],512)
        self.assertEqual(out["executed_count"],512)
        self.assertEqual(out["failed_slots"],[])
        self.assertEqual(out["coverage_missing"],[])
        self.assertFalse(out["case_replacement"])

    def test_index_fail_closed(self):
        with self.assertRaises(ValueError):
            t.derive_seed("x","y",512)

if __name__=="__main__":
    unittest.main(verbosity=2)
