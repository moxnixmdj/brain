from __future__ import annotations
import json
import pathlib
import unittest

from canonical.runtime import delegation_terminal_population_binding_v2 as t

ROOT=pathlib.Path(__file__).resolve().parents[2]

class DelegationTerminalPopulationBindingV2Tests(unittest.TestCase):
    def test_seed_binding_and_case_identity(self):
        a=t.derive_seed("commit-A","beacon-A",0)
        self.assertEqual(a,t.derive_seed("commit-A","beacon-A",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-B",0))
        self.assertNotEqual(a,t.derive_seed("commit-A","beacon-A",1))
        self.assertIn("DELEGATION_TERMINAL_POPULATION_V2",t.case_id(0))

    def test_development_population_smoke(self):
        out=t.run_population("DEV_ONLY_NOT_TERMINAL_COMMITMENT","DEV_ONLY_NOT_TERMINAL_BEACON")
        self.assertTrue(out["pass"],out["results"][:10])
        self.assertEqual(out["executed_count"],512)
        self.assertEqual(out["dynamic_count"],256)
        self.assertEqual(out["structural_count"],256)
        self.assertEqual(set(out["covered_class_tags"]),t.REQUIRED_CLASS_TAGS)
        self.assertEqual(out["failed_slots"],[])
        self.assertEqual(out["coverage_missing"],[])
        self.assertFalse(out["adaptive_case_selection"])
        self.assertFalse(out["replay_for_tuning"])
        self.assertFalse(out["case_replacement"])
        self.assertEqual(out["allowed_failed_cases"],0)

    def test_registry_acceptance_mode_is_authorized(self):
        reg=json.loads((ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json").read_text())
        self.assertIn(
            "THEORETICAL_CEILING_OR_MACHINE_CHECKED_FORMAL_PROOF",
            reg["terminal_acceptance_proof_modes"],
        )

    def test_index_fails_closed(self):
        with self.assertRaises(ValueError):
            t.derive_seed("x","y",512)

if __name__=="__main__":
    unittest.main(verbosity=2)
