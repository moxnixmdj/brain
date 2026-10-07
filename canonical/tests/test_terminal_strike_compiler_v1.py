import unittest
from pathlib import Path
from canonical.runtime.terminal_strike_compiler_v1 import compile_strike

class StrikeTests(unittest.TestCase):
    def test_live_repo_compiles_only_terminal_scale_actions(self):
        root=Path(__file__).resolve().parents[2]
        out=compile_strike(root)
        self.assertTrue(out["pass"])
        self.assertEqual(out["single_live_primitive"],"ESCAPE_POLICY_ADEQUACY")
        self.assertEqual(out["open_independent_obligation_count"],13)
        ids={x["route_id"] for x in out["dispatch"]}
        self.assertIn("GENERATOR_CLOSURE_SCOPE_COMPLETE",ids)
        self.assertIn("SELECTED_COVER_COMPLEMENT_UNSAT",ids)
        self.assertTrue(all(x["potential_discharge"]==13 for x in out["dispatch"]))
        self.assertFalse(out["terminal_credit"])

if __name__=="__main__":
    unittest.main()
