from __future__ import annotations
import unittest
from pathlib import Path
from canonical.runtime.cad_t0_post_refreeze_guard_v2 import evaluate

ROOT=Path(__file__).resolve().parents[2]

class CadT0PostRefreezeGuardV2Tests(unittest.TestCase):
    def test_live_repo_passes_exact_refreeze_guard(self):
        out=evaluate(ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertFalse(out["execution_authority"])
if __name__=="__main__": unittest.main()
