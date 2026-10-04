import math
import unittest

from canonical.runtime.h100_expression_tree_symbolic_regression_v1 import (
    ExpressionTreeError,
    discover,
    predict,
)


class H100ExpressionTreeTests(unittest.TestCase):
    def rows(self, fn):
        xs = [-4, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 4, 5]
        return [{"x": x, "y": fn(x)} for x in xs]

    def test_nested_saturation_exact_recovery(self):
        sat = lambda z: z / (1 + abs(z))
        out = discover(self.rows(lambda x: sat(sat(x))), target="y")
        self.assertEqual(out["status"], "EXACT_CANDIDATE_FOUND", out)
        self.assertEqual(out["persistent_learned_bytes"], 0)
        self.assertEqual(out["external_learned_capability_calls"], 0)
        for x in (-2.5, -0.25, 0.25, 2.5):
            self.assertAlmostEqual(
                predict(out["best_candidate"], {"x": x}),
                sat(sat(x)),
                places=8,
            )

    def test_linear_plus_saturation_correction_exact_recovery(self):
        sat = lambda z: z / (1 + abs(z))
        out = discover(self.rows(lambda x: 2 * x + 3 * sat(x)), target="y")
        self.assertEqual(out["status"], "EXACT_CANDIDATE_FOUND", out)
        for x in (-2.5, -0.25, 0.25, 2.5):
            expected = 2 * x + 3 * sat(x)
            self.assertAlmostEqual(
                predict(out["best_candidate"], {"x": x}),
                expected,
                places=8,
            )

    def test_multivariable_stable_ratio_exact_recovery(self):
        rows = []
        pairs = [
            (-3, -2), (-2, 1), (-1, 3), (0, -1), (1, 0), (2, 2),
            (3, -3), (4, 1), (5, -2), (6, 3), (7, -1), (8, 2),
        ]
        for x, z in pairs:
            y = 1.5 + 2.0 * (x / (1 + abs(z)))
            rows.append({"a": x, "b": z, "y": y})
        out = discover(rows, target="y")
        self.assertEqual(out["status"], "EXACT_CANDIDATE_FOUND", out)
        self.assertLessEqual(out["best_candidate"]["nrmse"], 1e-8)

    def test_surface_renaming_preserves_exact_behavior(self):
        sat = lambda z: z / (1 + abs(z))
        rows_a = self.rows(lambda x: 1 + 4 * sat(x))
        rows_b = [{"q": row["x"], "out": row["y"]} for row in rows_a]
        a = discover(rows_a, target="y")
        b = discover(rows_b, target="out")
        self.assertEqual(a["status"], "EXACT_CANDIDATE_FOUND")
        self.assertEqual(b["status"], "EXACT_CANDIDATE_FOUND")
        self.assertEqual(
            a["best_candidate"]["feature_signatures"],
            b["best_candidate"]["feature_signatures"],
        )

    def test_out_of_grammar_sine_fails_closed(self):
        xs = [-3.4, -2.7, -2.1, -1.4, -0.8, -0.2, 0.35, 0.9, 1.6, 2.2, 2.9, 3.7]
        rows = [{"x": x, "y": math.sin(x)} for x in xs]
        out = discover(rows, target="y", max_depth=2)
        self.assertEqual(
            out["status"],
            "GRAMMAR_NOT_EXACT__EXPAND_OR_EXPERIMENT",
            out,
        )

    def test_deterministic_replay(self):
        sat = lambda z: z / (1 + abs(z))
        rows = self.rows(lambda x: 2 * x + 3 * sat(x))
        self.assertEqual(discover(rows, target="y"), discover(rows, target="y"))

    def test_nonfinite_input_rejected(self):
        rows = self.rows(lambda x: x)
        rows[3]["x"] = float("nan")
        with self.assertRaises(ExpressionTreeError):
            discover(rows, target="y")

    def test_input_count_is_bounded(self):
        rows = []
        for i in range(8):
            row = {f"x{j}": i + j + 1 for j in range(5)}
            row["y"] = i
            rows.append(row)
        with self.assertRaises(ExpressionTreeError):
            discover(rows, target="y")


if __name__ == "__main__":
    unittest.main(verbosity=2)
