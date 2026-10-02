from __future__ import annotations
import unittest
from pathlib import Path
from canonical.runtime.cad_t0_post_refreeze_binding_v4_validator import validate

class CadT0PostRefreezeBindingV4ValidatorTests(unittest.TestCase):
    def test_live_v4_binding_is_structurally_valid_before_promotion(self):
        out=validate(Path("."))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["slot_count"],128)
        self.assertEqual(out["candidate_blob"],"aa32750b220a023617938b7be9476f6b3aac6704")
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"],0)

if __name__=="__main__": unittest.main(verbosity=2)
