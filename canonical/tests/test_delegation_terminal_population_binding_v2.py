import unittest
from canonical.runtime import delegation_terminal_population_binding_v2 as t

class DelegationTerminalPopulationBindingV2Tests(unittest.TestCase):
    def test_seed_binding_and_namespace(self):
        a=t.derive_seed("commit-A","beacon-A","interaction",0)
        self.assertEqual(a,t.derive_seed("commit-A","beacon-A","interaction",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-B","interaction",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-A","interaction",1))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-A","structural",0))

    def test_development_population_smoke(self):
        out=t.run_population("DEV_ONLY_NOT_TERMINAL_COMMITMENT","DEV_ONLY_NOT_TERMINAL_BEACON")
        self.assertTrue(out["pass"],out["failed_slots"][:10])
        self.assertEqual(out["executed_count"],512)
        self.assertEqual(out["interaction_count"],256)
        self.assertEqual(out["structural_count"],256)
        self.assertEqual(set(out["covered_interaction_classes"]),t.INTERACTION_CLASSES)
        self.assertEqual(set(out["covered_structural_classes"]),t.STRUCTURAL_CLASSES)
        self.assertEqual(out["failed_slots"],[])
        self.assertEqual(out["interaction_coverage_missing"],[])
        self.assertEqual(out["structural_coverage_missing"],[])
        self.assertFalse(out["adaptive_case_selection"])
        self.assertFalse(out["replay_for_tuning"])
        self.assertFalse(out["case_replacement"])

    def test_indices_and_population_fail_closed(self):
        with self.assertRaises(ValueError):
            t.derive_seed("x","y","interaction",256)
        with self.assertRaises(ValueError):
            t.derive_seed("x","y","structural",256)
        with self.assertRaises(ValueError):
            t.derive_seed("x","y","unknown",0)

if __name__=="__main__":
    unittest.main(verbosity=2)
