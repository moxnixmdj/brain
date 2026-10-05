from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_separable_transform_v1 as sep
from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as sparse


class MysteryMechanismSeparableTransformTests(unittest.TestCase):
    def test_public_rows_are_compatibility_only_without_stored_public_formula(self):
        # Public development rows only. No public example final formula is
        # stored here and no benchmark/acceptance credit is inferred from them.
        rows = [
            {"x1":0.5944,"x2":1.9188,"out":12.2245},
            {"x1":0.5044,"x2":0.2068,"out":10.3732},
            {"x1":0.05,"x2":0.05,"out":4.3715},
            {"x1":0.70,"x2":0.05,"out":30.6686},
            {"x1":0.05,"x2":30.0,"out":2.3912},
            {"x1":0.70,"x2":30.0,"out":16.3743},
            {"x1":0.375,"x2":1.225,"out":5.7241},
        ]
        out = sep.discover(
            rows,
            bounds={"x1":[0.05,0.70],"x2":[0.05,30.0]},
            target="out",
        )
        self.assertEqual(out["status"], "SEPARABLE_CANDIDATE_FOUND__PUBLIC_OR_SYNTHETIC_ONLY", out)
        self.assertEqual(out["selection_rule"], "LOO_NRMSE_THEN_ALL_ROW_NRMSE_THEN_COMPLEXITY")
        self.assertTrue(out["selection_exact_branch_and_bound"])
        self.assertTrue(math.isfinite(out["candidate"]["loo_nrmse"]))
        self.assertFalse(out["private_score_claimed"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_fresh_separable_structure_exact_under_leave_one_out(self):
        def law(x, z):
            f = x / (1 - x) ** 2
            g = 1 / (1 + math.sqrt(z))
            return 1.2 + 2.5 * f + 1.7 * g + 3.1 * f * g

        pts = [
            (0.22,2.3),(0.63,0.4),(0.05,0.1),(0.8,0.1),
            (0.05,20.0),(0.8,20.0),(0.425,math.sqrt(2.0)),
            (0.31,5.0),(0.69,11.0),
        ]
        rows = [{"x":x,"z":z,"out":law(x,z)} for x,z in pts]
        out = sep.discover(
            rows,
            bounds={"x":[0.05,0.8],"z":[0.1,20.0]},
            target="out",
        )
        c = out["candidate"]
        self.assertLess(c["loo_nrmse"], 1e-7, c)
        self.assertLess(c["all_row_nrmse"], 1e-8, c)
        for x,z in ((0.1,0.2),(0.3,1.7),(0.55,7.0),(0.75,16.0)):
            self.assertAlmostEqual(sep.predict(c,{"x":x,"z":z}), law(x,z), places=5)

    def test_stored_loo_matches_direct_refit_leave_one_out(self):
        def law(x, z):
            f = math.sqrt(abs(x))
            g = abs(z) ** 0.625
            return -0.4 + 1.8 * f + 0.7 * g + 2.2 * f * g

        pts = [
            (0.25,0.2),(1.0,0.5),(4.0,0.9),(9.0,1.4),
            (16.0,2.0),(25.0,2.6),(36.0,3.2),(49.0,3.8),
        ]
        rows = [{"x":x,"z":z,"out":law(x,z)} for x,z in pts]
        out = sep.discover(
            rows,
            bounds={"x":[0.25,49.0],"z":[0.2,3.8]},
            target="out",
        )
        c = out["candidate"]
        left = [sep._transform(c["left"], row["x"]) for row in rows]
        right = [sep._transform(c["right"], row["z"]) for row in rows]
        y = [row["out"] for row in rows]
        pred = []
        for hold in range(len(rows)):
            keep = [i for i in range(len(rows)) if i != hold]
            fit = sep._fit_bilinear(
                [left[i] for i in keep],
                [right[i] for i in keep],
                [y[i] for i in keep],
            )
            self.assertIsNotNone(fit)
            coeff, _ = fit
            pred.append(
                coeff[0]
                + coeff[1] * left[hold]
                + coeff[2] * right[hold]
                + coeff[3] * left[hold] * right[hold]
            )
        direct = sparse._nrmse(y, pred)
        self.assertAlmostEqual(c["loo_nrmse"], direct, places=12)

    def test_boundary_ratio_anchors_are_outside_declared_interval(self):
        rows = [
            {"x":x,"z":z,"out":2*x+3*z}
            for x,z in (
                (1.2,2.2),(1.4,3.1),(1.0,2.0),(2.0,2.0),
                (1.0,4.0),(2.0,4.0),(1.5,3.0),(1.8,2.6),
            )
        ]
        out = sep.discover(
            rows,
            bounds={"x":[1.0,2.0],"z":[2.0,4.0]},
            target="out",
        )
        c = out["candidate"]
        for d,bound in ((c["left"],(1.0,2.0)),(c["right"],(2.0,4.0))):
            if d["kind"] == "boundary_ratio":
                self.assertTrue(float(d["anchor"]) < bound[0] or float(d["anchor"]) > bound[1])

    def test_nonfinite_rejected(self):
        rows = [
            {"x":x,"z":z,"out":x+z}
            for x,z in (
                (1,1),(2,1),(1,2),(2,2),(1.5,1.2),
                (1.2,1.7),(1.4,1.4),
            )
        ]
        rows[2]["x"] = math.inf
        with self.assertRaises(Exception):
            sep.discover(rows,bounds={"x":[1,2],"z":[1,2]},target="out")


if __name__ == "__main__":
    unittest.main(verbosity=2)
