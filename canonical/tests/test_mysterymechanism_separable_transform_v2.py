from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_separable_transform_v1 as v1
from canonical.runtime import mysterymechanism_separable_transform_v2 as v2
from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as sparse


class MysteryMechanismSeparableTransformV2Tests(unittest.TestCase):
    def test_affine_equivalence_quotients_sat_and_inv1p(self):
        values = [0.05, 0.2, 0.7, 1.5, 5.0, 12.0, 30.0]
        inv = [1.0 / (1.0 + abs(x) ** 0.5) for x in values]
        sat = [(abs(x) ** 0.5) / (1.0 + abs(x) ** 0.5) for x in values]
        self.assertEqual(
            v2._affine_behavior_key(inv),
            v2._affine_behavior_key(sat),
        )

        lib = v2._library("x", values, (0.05, 30.0))
        keys = [v2._affine_behavior_key(rec["values"]) for rec in lib]
        self.assertEqual(len(keys), len(set(keys)))

    def test_public_example_one_structural_holdouts_pass_published_public_threshold(self):
        # These seven rows are the public development transcript on Vals.
        # The twelve fixed holdouts below were derived solely from the public
        # example law before this V2 test was frozen. The final public formula
        # is intentionally not stored in the repository.
        rows = [
            {"x1":0.5944,"x2":1.9188,"out":12.2245},
            {"x1":0.5044,"x2":0.2068,"out":10.3732},
            {"x1":0.05,"x2":0.05,"out":4.3715},
            {"x1":0.70,"x2":0.05,"out":30.6686},
            {"x1":0.05,"x2":30.0,"out":2.3912},
            {"x1":0.70,"x2":30.0,"out":16.3743},
            {"x1":0.375,"x2":1.225,"out":5.7241},
        ]
        heldout = [
            (0.08,0.08,4.386962237930895),
            (0.12,0.3,4.1632071065154514),
            (0.18,1.0,4.001738076078943),
            (0.25,5.0,3.727127614073479),
            (0.32,20.0,3.7093056504098008),
            (0.4,0.1,7.846432637185288),
            (0.48,0.7,8.492005215420377),
            (0.55,3.0,9.394232048330792),
            (0.6,12.0,10.077530751367854),
            (0.64,25.0,11.555092068877146),
            (0.68,0.2,24.53576846465379),
            (0.69,10.0,17.082349918382906),
        ]
        out = v2.discover(
            rows,
            bounds={"x1":[0.05,0.70],"x2":[0.05,30.0]},
            target="out",
        )
        self.assertEqual(
            out["status"],
            "SEPARABLE_V2_CANDIDATE_FOUND__PUBLIC_OR_SYNTHETIC_ONLY",
            out,
        )
        self.assertTrue(out["affine_equivalence_quotient"])
        self.assertTrue(out["selection_exact_branch_and_bound"])
        self.assertLess(out["candidate"]["delete_two_nrmse"], 0.05, out)

        gold = [y for _, _, y in heldout]
        pred = [
            v2.predict(out["candidate"], {"x1":x1, "x2":x2})
            for x1, x2, _ in heldout
        ]
        mean = sum(gold) / len(gold)
        variance = sum((y - mean) ** 2 for y in gold) / len(gold)
        nmse = sum((a - b) ** 2 for a, b in zip(gold, pred)) / len(gold) / variance
        self.assertLess(nmse, 0.000697, (nmse, out["candidate"]))
        self.assertFalse(out["private_score_claimed"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_fresh_exact_separable_law_and_direct_delete_two_agree(self):
        def law(x, z):
            f = x / (1 - x) ** 2
            g = 1 / (1 + math.sqrt(z))
            return 1.2 + 2.5 * f + 1.7 * g + 3.1 * f * g

        points = [
            (0.22,2.3),(0.63,0.4),(0.05,0.1),(0.8,0.1),
            (0.05,20.0),(0.8,20.0),(0.425,math.sqrt(2.0)),
            (0.31,5.0),(0.69,11.0),
        ]
        rows = [{"x":x,"z":z,"out":law(x,z)} for x,z in points]
        out = v2.discover(
            rows,
            bounds={"x":[0.05,0.8],"z":[0.1,20.0]},
            target="out",
        )
        candidate = out["candidate"]
        self.assertIsNotNone(candidate)
        self.assertLess(candidate["delete_two_nrmse"], 1e-7, candidate)
        self.assertLess(candidate["loo_nrmse"], 1e-7, candidate)
        self.assertLess(candidate["all_row_nrmse"], 1e-8, candidate)

        a = [v1._transform(candidate["left"], row["x"]) for row in rows]
        b = [v1._transform(candidate["right"], row["z"]) for row in rows]
        y = [row["out"] for row in rows]
        predicted = []
        actual = []
        n = len(rows)
        for first in range(n):
            for second in range(first + 1, n):
                keep = [i for i in range(n) if i not in (first, second)]
                fit = v1._fit_bilinear(
                    [a[i] for i in keep],
                    [b[i] for i in keep],
                    [y[i] for i in keep],
                )
                self.assertIsNotNone(fit)
                coeff, _ = fit
                for hold in (first, second):
                    predicted.append(
                        coeff[0]
                        + coeff[1] * a[hold]
                        + coeff[2] * b[hold]
                        + coeff[3] * a[hold] * b[hold]
                    )
                    actual.append(y[hold])
        direct = sparse._nrmse(actual, predicted)
        self.assertAlmostEqual(candidate["delete_two_nrmse"], direct, places=12)

        for x, z in ((0.1,0.2),(0.3,1.7),(0.55,7.0),(0.75,16.0)):
            self.assertAlmostEqual(
                v2.predict(candidate, {"x":x,"z":z}),
                law(x,z),
                places=5,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
