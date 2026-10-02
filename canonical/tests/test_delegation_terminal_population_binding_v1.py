import unittest
from canonical.runtime import delegation_terminal_population_binding_v1 as t

class DelegationTerminalPopulationBindingTests(unittest.TestCase):
    def test_seed_binding(self):
        a=t.derive_seed("commit-A","beacon-A",0)
        self.assertEqual(a,t.derive_seed("commit-A","beacon-A",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-B",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-A",1))

    def test_development_population_smoke(self):
        out=t.run_population("DEV_ONLY_NOT_TERMINAL_COMMITMENT","DEV_ONLY_NOT_TERMINAL_BEACON")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["executed_count"],512)
        self.assertEqual(set(out["covered_case_classes"]),t.REQUIRED_CLASSES)
        self.assertEqual(out["failed_slots"],[])
        self.assertEqual(out["coverage_missing"],[])
        self.assertFalse(out["adaptive_case_selection"])
        self.assertFalse(out["replay_for_tuning"])
        self.assertFalse(out["case_replacement"])

    def test_index_fails_closed(self):
        with self.assertRaises(ValueError):
            t.derive_seed("x","y",512)

if __name__=="__main__":
    unittest.main(verbosity=2)
