from __future__ import annotations

import unittest

from canonical.runtime import delegation_terminal_population_binding_v1 as t


class DelegationTerminalPopulationBindingTests(unittest.TestCase):
    def test_seed_binding(self):
        a=t.derive_seed("commit-A","beacon-A",0)
        self.assertEqual(a,t.derive_seed("commit-A","beacon-A",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-B",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-A",1))

    def test_index_fail_closed(self):
        for bad in (-1,t.SAMPLE_COUNT,True):
            with self.assertRaises(ValueError):
                t.derive_seed("x","y",bad)

    def test_development_population_smoke(self):
        out=t.run_population("DEV_ONLY_NOT_TERMINAL_COMMITMENT","DEV_ONLY_NOT_TERMINAL_BEACON")
        self.assertTrue(out["pass"],out["results"][:8])
        self.assertEqual(out["sample_count"],192)
        self.assertEqual(out["executed_count"],192)
        self.assertEqual(out["failed_slots"],[])
        self.assertEqual(out["coverage_missing"],[])
        self.assertFalse(out["case_replacement"])
        self.assertFalse(out["replay_for_tuning"])
        self.assertEqual(set(out["class_counts"]),set(t.proof.CLASSES))
        self.assertTrue(all(v==32 for v in out["class_counts"].values()))

if __name__=="__main__":
    unittest.main(verbosity=2)
