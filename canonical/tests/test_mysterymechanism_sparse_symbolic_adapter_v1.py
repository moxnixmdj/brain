from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as mm


class MysteryMechanismSparseSymbolicAdapterTests(unittest.TestCase):
    def test_2d_contract_uses_four_initial_plus_one_reserved(self):
        out = mm.plan_experiments({"x1": [0.1, 10000], "x2": [0.001, 0.5]})
        self.assertEqual(out["active_budget"], 5)
        self.assertEqual(out["initial_experiment_count"], 4)
        self.assertEqual(out["reserved_count"], 1)
        self.assertEqual(len(out["initial_experiments"]) + 1, 5)
        for point in out["initial_experiments"] + [out["reserved_final_experiment"]]:
            self.assertGreaterEqual(point["x1"], 0.1)
            self.assertLessEqual(point["x1"], 10000)
            self.assertGreaterEqual(point["x2"], 0.001)
            self.assertLessEqual(point["x2"], 0.5)

    def test_sparse_seven_rows_recover_two_feature_nested_saturation(self):
        def sat(x):
            return x / (1.0 + abs(x))
        rows = [{"x": x, "out": 2.0 * x + 3.0 * sat(x)}
                for x in (-4.0, -2.0, -0.5, 0.25, 1.0, 2.5, 5.0)]
        out = mm.sparse_discover(rows, target="out", max_depth=2)
        self.assertEqual(out["status"], "SPARSE_CANDIDATES_FOUND", out)
        best = out["best_candidate"]
        self.assertIsNotNone(best)
        self.assertLess(best["loo_nrmse"], 1e-7, best)
        self.assertLess(best["all_nrmse"], 1e-8, best)
        self.assertEqual(out["row_count"], 7)
        self.assertEqual(out["persistent_learned_bytes"], 0)

    def test_sparse_five_rows_runs_instead_of_old_eight_row_failure(self):
        rows = [{"x": x, "out": 4.0 * x * x + 2.0}
                for x in (1.0, 2.0, 3.0, 4.0, 5.0)]
        out = mm.sparse_discover(rows, target="out", max_depth=1)
        self.assertEqual(out["row_count"], 5)
        self.assertEqual(out["status"], "SPARSE_CANDIDATES_FOUND")
        self.assertLess(out["best_candidate"]["loo_nrmse"], 1e-8)

    def test_public_stream_power_shape_uses_continuous_power_route(self):
        # Public MysteryMechanism development example only; not a hidden scored case.
        rows = [
            {"x1":25.5646,"x2":0.1859,"out":0.0012396},
            {"x1":0.1108,"x2":0.0187,"out":-0.0000064},
            {"x1":100.0,"x2":0.05,"out":0.0008841},
            {"x1":10000.0,"x2":0.05,"out":0.0082336},
            {"x1":100.0,"x2":0.5,"out":0.0049850},
            {"x1":10000.0,"x2":0.5,"out":0.0454408},
            {"x1":1000.0,"x2":0.2,"out":0.0078693},
        ]
        out = mm.solve(
            rows,
            bounds={"x1":[0.1,10000.0],"x2":[0.001,0.5]},
            target="out",
            fit_threshold=0.05,
        )
        self.assertEqual(out["status"], "CANDIDATE_READY__UNVERIFIED_ON_PRIVATE_STRUCTURAL_PROBES", out)
        self.assertEqual(out["route"], "BASE_ZERO_LEARNED", out)
        self.assertEqual(out["candidate"]["family"], "log_power")
        self.assertAlmostEqual(out["candidate"]["exponents"][0], 0.4822, delta=0.01)
        self.assertAlmostEqual(out["candidate"]["exponents"][1], 0.7478, delta=0.01)
        self.assertIn("x1**", out["expression"])
        self.assertIn("x2**", out["expression"])
        self.assertFalse(out["private_score_claimed"])
        self.assertEqual(out["external_learned_capability_calls"], 0)

    def test_reserved_discriminator_never_leaves_declared_bounds(self):
        rows = [
            {"x":1.0,"out":1.0},
            {"x":2.0,"out":4.0},
            {"x":3.0,"out":9.0},
            {"x":4.0,"out":16.0},
            {"x":5.0,"out":25.1},
        ]
        out = mm.choose_final_experiment(rows, bounds={"x":[1.0,9.0]}, target="out")
        self.assertIn(out["status"], {"BOUND_CONSTRAINED_DISCRIMINATOR","RESERVED_CENTER"})
        self.assertGreaterEqual(out["point"]["x"], 1.0)
        self.assertLessEqual(out["point"]["x"], 9.0)

    def test_out_of_grammar_is_fail_closed_at_strict_threshold(self):
        rows = [{"x": x, "out": math.sin(x)}
                for x in (0.2, 0.9, 1.7, 2.6, 3.8, 5.1, 6.4)]
        out = mm.solve(rows, bounds={"x":[0.2,6.4]}, target="out", fit_threshold=1e-7)
        self.assertEqual(out["status"], "FAIL_CLOSED__EXPAND_MECHANISM_LANGUAGE", out)
        self.assertIsNone(out["expression"])

    def test_accounting_is_zero_credit(self):
        rows = [{"x": x, "out": 3.0*x + 1.0} for x in (1,2,3,4,5)]
        out = mm.solve(rows, bounds={"x":[1,5]}, target="out")
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["persistent_learned_bytes"], 0)
        self.assertEqual(out["external_learned_capability_calls"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
