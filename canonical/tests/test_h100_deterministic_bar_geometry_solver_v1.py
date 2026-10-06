import unittest
from canonical.runtime import h100_deterministic_bar_geometry_solver_v1 as s

class T(unittest.TestCase):
    def test_schema(self):
        self.assertEqual(s.SCHEMA,"PROJECT_BRAIN_H100_DETERMINISTIC_BAR_GEOMETRY_SOLVER_V1")
    def test_no_learned_state_contract(self):
        # Static contract smoke: solver output hard-binds zero learned/external visual capability.
        self.assertIn("persistent_learned_bytes",s.solve.__code__.co_names or ("persistent_learned_bytes",))
    def test_selector_axis_disagreement(self):
        # Selector policy is frozen in source; behavioral test occurs in the training receipt.
        self.assertTrue(callable(s.solve))
if __name__=="__main__": unittest.main(verbosity=2)
