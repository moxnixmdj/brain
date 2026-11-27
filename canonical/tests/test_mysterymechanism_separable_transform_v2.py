from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_separable_transform_v2 as sep


def _law(x: float, z: float) -> float:
    return 2.0 * x + 3.0 * z


def _fit_rows():
    points = [
        (-1.5, -1.2),
        (1.5, -1.2),
        (-1.5, 1.2),
        (1.5, 1.2),
        (0.7, -0.4),
        (-0.6, 0.8),
    ]
    return [{"x": x, "z": z, "out": _law(x, z)} for x, z in points]


class MysteryMechanismProspectiveSelectionV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fit_rows = _fit_rows()
        cls.good_point = {"x": 0.4, "z": 0.5}
        cls.hostile_point = {"x": 1.1, "z": -0.8}
        cls.good = sep.discover(
            fit_rows + [{**cls.good_point, "out": _law(**cls.good_point)}],
            bounds={"x": [-2.0, 2.0], "z": [-2.0, 2.0]},
            target="out",
        )
        cls.hostile = sep.discover(
            fit_rows
            + [{**cls.hostile_point, "out": _law(**cls.hostile_point) + 1000.0}],
            bounds={"x": [-2.0, 2.0], "z": [-2.0, 2.0]},
            target="out",
        )
        cls.good_solve = sep.solve(
            fit_rows + [{**cls.good_point, "out": _law(**cls.good_point)}],
            bounds={"x": [-2.0, 2.0], "z": [-2.0, 2.0]},
            target="out",
        )
        cls.hostile_solve = sep.solve(
            fit_rows
            + [{**cls.hostile_point, "out": _law(**cls.hostile_point) + 1000.0}],
            bounds={"x": [-2.0, 2.0], "z": [-2.0, 2.0]},
            target="out",
        )

    def test_reserved_observation_is_causally_absent_from_selection(self):
        # Both the reserved coordinates and target are different.  The complete
        # prevalidation selection state must remain byte-for-byte equivalent.
        self.assertEqual(
            self.good["selected_prevalidation"]["selection_fingerprint"],
            self.hostile["selected_prevalidation"]["selection_fingerprint"],
        )
        for a, b in zip(
            self.good["selected_prevalidation"]["prevalidation_coefficients"],
            self.hostile["selected_prevalidation"]["prevalidation_coefficients"],
        ):
            self.assertAlmostEqual(a, b, places=10)
        self.assertEqual(self.good["left_library_size"], self.hostile["left_library_size"])
        self.assertEqual(self.good["right_library_size"], self.hostile["right_library_size"])
        self.assertFalse(self.good["validation_observation_used_for_library"])
        self.assertFalse(self.good["validation_observation_used_for_selection"])
        self.assertFalse(self.hostile["validation_observation_used_for_library"])
        self.assertFalse(self.hostile["validation_observation_used_for_selection"])

    def test_good_prospective_observation_passes_and_hostile_one_fails_closed(self):
        self.assertTrue(self.good["prospective_validation_pass"])
        self.assertIsNotNone(self.good["candidate"])
        self.assertTrue(self.good["status"].startswith("PROSPECTIVELY_VALIDATED_"))
        self.assertTrue(self.good["selection_exact_branch_and_bound"])

        self.assertFalse(self.hostile["prospective_validation_pass"])
        self.assertIsNone(self.hostile["candidate"])
        self.assertIsNone(self.hostile["expression"])
        self.assertEqual(
            self.hostile["status"],
            "PROSPECTIVE_VALIDATION_FAILED__EXPAND_GRAMMAR",
        )

    def test_exact_linear_surface_generalizes_after_prospective_gate(self):
        c = self.good["candidate"]
        self.assertIsNotNone(c)
        self.assertLess(c["fit_nrmse"], 1e-8)
        self.assertLess(c["inner_loo_nrmse"], 1e-7)
        self.assertLess(c["prospective_validation_nrmse"], 1e-7)
        for x, z in ((-1.7, 1.6), (0.2, -1.1), (1.8, 1.25)):
            self.assertAlmostEqual(
                sep.predict(c, {"x": x, "z": z}),
                _law(x, z),
                places=6,
            )
        self.assertEqual(self.good["acceptance_credit_delta"], 0)
        self.assertEqual(self.good["family_credit_delta"], 0)
        self.assertEqual(self.good["capability_credit_delta"], 0)
        self.assertEqual(self.good["ownership_credit_delta"], 0)
        self.assertFalse(self.good["private_score_claimed"])

    def test_solver_audits_before_reusing_final_observation_for_refinement(self):
        self.assertEqual(
            self.good_solve["status"],
            "CANDIDATE_READY__PROSPECTIVE_AUDIT_PASSED__ZERO_PRIVATE_SCORE_CREDIT",
        )
        self.assertTrue(self.good_solve["audit_passed_before_refinement"])
        self.assertTrue(self.good_solve["final_row_reused_for_refinement"])
        self.assertEqual(
            self.good_solve["route"],
            "PROSPECTIVE_AUDIT_THEN_ACTIVE_REFINEMENT",
        )
        self.assertFalse(
            self.good_solve["final_row_refinement_metric_is_independent_validation"]
        )
        self.assertIsNotNone(self.good_solve["candidate"])

        self.assertEqual(
            self.hostile_solve["status"],
            "FAIL_CLOSED__PROSPECTIVE_AUDIT_FAILED__NO_REFINEMENT",
        )
        self.assertFalse(self.hostile_solve["final_row_reused_for_refinement"])
        self.assertIsNone(self.hostile_solve["candidate"])
        self.assertIsNone(self.hostile_solve["expression"])

    def test_nonfinite_input_still_fails_before_search(self):
        rows = _fit_rows() + [{"x": 0.4, "z": 0.5, "out": _law(0.4, 0.5)}]
        rows[2]["x"] = math.inf
        with self.assertRaises(Exception):
            sep.discover(
                rows,
                bounds={"x": [-2.0, 2.0], "z": [-2.0, 2.0]},
                target="out",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
