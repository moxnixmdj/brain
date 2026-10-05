import unittest
from canonical.runtime import h100_sign_quotient_depth8_v1 as q

class H100SignQuotientDepth8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=q.run()

    def test_congruence_is_verified_for_every_operator(self):
        self.assertTrue(self.out["congruence_audit"]["all_pass"])
        self.assertEqual(set(self.out["congruence_audit"]["operators"]),{"neg","abs","square","sqrt_abs","log1p_abs","sat"})

    def test_quotient_reduces_raw_space(self):
        b=self.out["basis"]
        self.assertLess(b["global_unique_class_count"],b["raw_cumulative_sequence_count"])
        self.assertGreater(b["reduction_factor_raw_over_unique"],1.0)

    def test_all_five_fresh_tasks_are_solved_and_transfer(self):
        self.assertEqual(self.out["task_count"],5)
        for row in self.out["tasks"]:
            self.assertIsNotNone(row["solve"]["selected"],row["task_id"])
            self.assertLessEqual(row["solve"]["selected"]["holdout_nrmse"],1e-8,row["task_id"])
            self.assertEqual(row["transfer"]["status"],"TRANSFER_OK",row["task_id"])
            self.assertLessEqual(row["transfer"]["holdout_nrmse"],1e-8,row["task_id"])

    def test_at_least_three_require_depth7_or_8(self):
        self.assertGreaterEqual(self.out["first_exact_depth_ge_7_count"],3)

    def test_no_persistent_fit_state_or_learned_macros(self):
        self.assertEqual(self.out["persistent_m_fit_bytes"],0)
        self.assertEqual(self.out["persistent_learned_macros"],0)
        self.assertEqual(self.out["persistent_quotient_basis"],0)
        self.assertFalse(self.out["writes_selected_structure"])

if __name__=="__main__":
    unittest.main(verbosity=2)
