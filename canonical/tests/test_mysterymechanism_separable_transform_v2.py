from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_separable_transform_v2 as sep


def _law(x: float, z: float) -> float:
    return 2.0 * x + 3.0 * z


def _six_fit_rows():
    points = [
        (1.0, 1.0),
        (2.0, 1.0),
        (1.0, 2.0),
        (2.0, 2.0),
        (1.5, 1.2),
        (1.2, 1.7),
    ]
    return [{"x": x, "z": z, "out": _law(x, z)} for x, z in points]


class MysteryMechanismProspectiveSelectionV2Tests(unittest.TestCase):
    def test_reserved_observation_cannot_change_structure_selection(self):
        fit_rows = _six_fit_rows()
        point = {"x": 1.4, "z": 1.4}

        good = sep.discover(
            fit_rows + [{**point, "out": _law(**point)}],
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )
        hostile = sep.discover(
            fit_rows + [{**point, "out": _law(**point) + 1000.0}],
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )

        self.assertEqual(
            good["selected_prevalidation"]["selection_fingerprint"],
            hostile["selected_prevalidation"]["selection_fingerprint"],
        )
        for a, b in zip(
            good["selected_prevalidation"]["prevalidation_coefficients"],
            hostile["selected_prevalidation"]["prevalidation_coefficients"],
        ):
            self.assertAlmostEqual(a, b, places=10)
        self.assertFalse(good["validation_observation_used_for_library"])
        self.assertFalse(good["validation_observation_used_for_selection"])
        self.assertFalse(hostile["validation_observation_used_for_library"])
        self.assertFalse(hostile["validation_observation_used_for_selection"])

        self.assertTrue(good["prospective_validation_pass"])
        self.assertIsNotNone(good["candidate"])
        self.assertTrue(good["status"].startswith("PROSPECTIVELY_VALIDATED_"))

        self.assertFalse(hostile["prospective_validation_pass"])
        self.assertIsNone(hostile["candidate"])
        self.assertIsNone(hostile["expression"])
        self.assertEqual(
            hostile["status"],
            "PROSPECTIVE_VALIDATION_FAILED__EXPAND_GRAMMAR",
        )

    def test_validation_input_is_absent_from_candidate_library_and_selection(self):
        fit_rows = _six_fit_rows()
        a = sep.discover(
            fit_rows + [{"x": 1.1, "z": 1.8, "out": _law(1.1, 1.8)}],
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )
        b = sep.discover(
            fit_rows + [{"x": 1.9, "z": 1.1, "out": _law(1.9, 1.1)}],
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )
        self.assertEqual(
            a["selected_prevalidation"]["selection_fingerprint"],
            b["selected_prevalidation"]["selection_fingerprint"],
        )
        self.assertEqual(a["left_library_size"], b["left_library_size"])
        self.assertEqual(a["right_library_size"], b["right_library_size"])

    def test_exact_linear_surface_survives_inner_loo_and_prospective_gate(self):
        rows = _six_fit_rows() + [{"x": 1.4, "z": 1.4, "out": _law(1.4, 1.4)}]
        out = sep.discover(
            rows,
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )
        c = out["candidate"]
        self.assertIsNotNone(c)
        self.assertLess(c["fit_nrmse"], 1e-8)
        self.assertLess(c["inner_loo_nrmse"], 1e-7)
        self.assertLess(c["prospective_validation_nrmse"], 1e-7)
        for x, z in ((1.05, 1.95), (1.33, 1.66), (1.8, 1.25)):
            self.assertAlmostEqual(
                sep.predict(c, {"x": x, "z": z}),
                _law(x, z),
                places=6,
            )
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)
        self.assertFalse(out["private_score_claimed"])

    def test_nonfinite_input_still_fails_closed(self):
        rows = _six_fit_rows() + [{"x": 1.4, "z": 1.4, "out": _law(1.4, 1.4)}]
        rows[2]["x"] = math.inf
        with self.assertRaises(Exception):
            sep.discover(
                rows,
                bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
                target="out",
            )

    def test_fail_closed_solver_exposes_only_prospectively_validated_route(self):
        fit_rows = _six_fit_rows()
        point = {"x": 1.4, "z": 1.4}
        good_rows = fit_rows + [{**point, "out": _law(**point)}]
        bad_rows = fit_rows + [{**point, "out": _law(**point) + 1000.0}]

        good = sep.solve(
            good_rows,
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )
        bad = sep.solve(
            bad_rows,
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )

        self.assertEqual(
            good["status"],
            "CANDIDATE_READY__PROSPECTIVE_SELECTION_SAFE__UNVERIFIED_PRIVATE_SCORE",
        )
        self.assertEqual(good["route"], "SEPARABLE_BILINEAR_PROSPECTIVE_HOLDOUT")
        self.assertIsNotNone(good["candidate"])
        self.assertTrue(good["expression"])

        self.assertTrue(bad["status"].startswith("FAIL_CLOSED__"))
        self.assertIsNone(bad["candidate"])
        self.assertIsNone(bad["expression"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
