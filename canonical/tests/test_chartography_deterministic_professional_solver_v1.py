from __future__ import annotations

import unittest

from canonical.runtime.chartography_deterministic_professional_solver_v1 import (
    _fit_axis,
    _parse_line_question,
    _parse_precipitation_question,
    _repair_legend_target,
)


class ChartographyDeterministicProfessionalSolverV1Tests(unittest.TestCase):
    def test_axis_fit_rejects_one_numeric_ocr_outlier(self):
        axis = _fit_axis(
            [(10, 0), (30, 20), (50, 40), (70, 60), (90, 80), (110, 10)],
            "positive",
        )
        self.assertAlmostEqual(axis.value(90), 80, delta=1.0)
        self.assertGreaterEqual(axis.inlier_count, 5)

    def test_line_question_parser(self):
        out = _parse_line_question(
            "How long would it take an environment of 1100 degC / 0.03 K/m "
            "to deform 4 metres vertically."
        )
        self.assertEqual(out, {"temperature": 1100.0, "gradient": 0.03, "target_y": 4.0})

    def test_precipitation_parser(self):
        out = _parse_precipitation_question(
            "Using Mg-9 wt % Al alloy, at what temperature does Mg17Al12 precipitate?"
        )
        self.assertEqual(out, {"composition": 9.0})

    def test_legend_middle_row_repairs_single_ocr_digit_error_from_neighbors(self):
        rows = [
            {"cy": 10, "temperature": 1100.0, "gradient": 0.02},
            {"cy": 20, "temperature": 4100.0, "gradient": 0.03},
            {"cy": 30, "temperature": 1100.0, "gradient": 0.04},
        ]
        out = _repair_legend_target(rows, 1100.0, 0.03)
        self.assertEqual(out["temperature"], 1100.0)
        self.assertTrue(out["temperature_repaired_by_neighbors"])


if __name__ == "__main__":
    unittest.main()
