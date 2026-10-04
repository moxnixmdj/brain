import unittest

from canonical.runtime.livebench_if_minimum_checker_surface_cut_v1 import (
    SurfaceCutError,
    solve,
)


class MinimumCheckerSurfaceCutTests(unittest.TestCase):
    def test_single_rows_exact_threshold(self):
        rows = [
            {"instruction_id_list": ["a"]},
            {"instruction_id_list": ["b"]},
            {"instruction_id_list": ["c"]},
        ]
        out = solve(rows, "66.6")
        self.assertEqual(out["minimum_checker_type_count"], 2)
        self.assertAlmostEqual(out["best_score_percent"], 200 / 3)

    def test_pair_partial_credit_is_exact_quarter(self):
        rows = [{"instruction_id_list": ["a", "b"]}]
        out = solve(rows, "25")
        self.assertEqual(out["minimum_checker_type_count"], 1)
        self.assertEqual(out["best_score4"], 1)
        self.assertEqual(out["best_score_percent"], 25.0)
        self.assertEqual(out["score_components"]["pair_one"], 1)

    def test_both_pair_types_score_full_credit(self):
        rows = [{"instruction_id_list": ["a", "b"]}]
        out = solve(rows, "25.1")
        self.assertEqual(out["minimum_checker_type_count"], 2)
        self.assertEqual(out["best_score4"], 4)
        self.assertEqual(out["best_score_percent"], 100.0)

    def test_component_dp_prefers_dense_pair_surface(self):
        rows = [
            {"instruction_id_list": ["a"]},
            {"instruction_id_list": ["b"]},
            {"instruction_id_list": ["c"]},
            {"instruction_id_list": ["a", "b"]},
            {"instruction_id_list": ["a", "b"]},
        ]
        out = solve(rows, "79")
        self.assertEqual(out["minimum_checker_type_count"], 2)
        self.assertEqual(out["checker_types"], ["a", "b"])
        self.assertEqual(out["best_score_percent"], 80.0)

    def test_three_instruction_rows_fail_closed(self):
        with self.assertRaisesRegex(SurfaceCutError, "UNSUPPORTED_INSTRUCTION_ARITY"):
            solve([{"instruction_id_list": ["a", "b", "c"]}])

    def test_duplicate_type_in_row_fails_closed(self):
        with self.assertRaisesRegex(SurfaceCutError, "DUPLICATE_INSTRUCTION_ID"):
            solve([{"instruction_id_list": ["a", "a"]}])


if __name__ == "__main__":
    unittest.main()
