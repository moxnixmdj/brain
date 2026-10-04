from __future__ import annotations

import json
import unittest

from canonical.runtime import h100_zero_learned_transfer_v1 as t


class H100ZeroLearnedTransferTests(unittest.TestCase):
    def test_preexposure_freezes_both_a_and_b_before_outcomes(self):
        pre=json.loads(t.PRE.read_text())
        self.assertEqual(pre["status"],"FROZEN_BEFORE_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT")
        self.assertEqual(len(pre["families"]),3)
        for family in pre["families"]:
            self.assertIn("compile_seed",family)
            self.assertIn("transfer_task",family)

    def test_truth_is_not_exposed_to_solver_routes(self):
        pre=json.loads(t.PRE.read_text())
        rows=t._rows("SIN_A",[float(x) for x in pre["training_x"]])
        self.assertTrue(all(set(row)=={"x","y"} for row in rows))

    def test_exact_catalog_probability_is_success_fraction(self):
        pre=json.loads(t.PRE.read_text())
        row=t._evaluate_catalog("EXP_B","exp_abs",True,pre)
        self.assertEqual(row["p_exact"],row["successful_proposals"]/row["proposal_catalog_size"])

    def test_zero_mass_has_unbounded_t95(self):
        self.assertIsNone(t._t95(0.0))

    def test_compiled_mass_has_finite_t95(self):
        self.assertIsNotNone(t._t95(0.25))
        self.assertEqual(t._t95(0.25),11)

    def test_full_transfer_gate(self):
        out=t.run()
        self.assertTrue(out["all_families_transfer_pass"],out)
        self.assertEqual(out["status"],"FINITE_ZERO_LEARNED_TRANSFER_PASS")
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)
        for family in out["families"]:
            self.assertEqual(family["reuse_effect"],"UNBOUNDED_TO_FINITE_T95")
            self.assertEqual(family["transfer_task"]["baseline"]["p_exact"],0.0)
            self.assertGreater(family["transfer_task"]["post_compile"]["p_exact"],0.0)


if __name__=="__main__":
    unittest.main(verbosity=2)
