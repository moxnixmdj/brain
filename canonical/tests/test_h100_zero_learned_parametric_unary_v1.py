from __future__ import annotations

import math
import unittest

from canonical.runtime.h100_zero_learned_parametric_unary_v1 import discover, predict


class H100ZeroLearnedParametricUnaryTests(unittest.TestCase):
    XS = [-4,-3,-2,-1,-0.5,0,0.5,1,2,3,4,5]

    def rows(self, fn):
        return [{"x":x,"y":fn(x)} for x in self.XS]

    def test_unseen_frequency_linear_trend_sinusoid(self):
        omega = 1.1137
        rows = self.rows(lambda x: -0.3 + 0.17*x + 1.4*math.sin(omega*x+0.41))
        out = discover(rows,target="y")
        self.assertEqual(out["status"],"EXACT_CANDIDATE_FOUND",out)
        c=out["best_candidate"]
        self.assertEqual(c["family"],"linear_trend_sinusoid")
        for x in (-3.55,-1.23,-0.14,0.37,1.91,4.44):
            self.assertAlmostEqual(predict(c,{"x":x}),-0.3+0.17*x+1.4*math.sin(omega*x+0.41),places=6)

    def test_unseen_exp_abs_rate(self):
        rows=self.rows(lambda x:1.7*math.exp(0.227*abs(x)))
        out=discover(rows,target="y")
        self.assertEqual(out["status"],"EXACT_CANDIDATE_FOUND",out)
        c=out["best_candidate"]
        self.assertEqual(c["family"],"exp_abs")
        for x in (-3.2,-0.2,0.8,3.6):
            self.assertAlmostEqual(predict(c,{"x":x}),1.7*math.exp(0.227*abs(x)),places=8)

    def test_observed_threshold_step(self):
        rows=self.rows(lambda x:-2.0 if x<1.0 else 3.0)
        out=discover(rows,target="y")
        self.assertEqual(out["status"],"EXACT_CANDIDATE_FOUND",out)
        c=out["best_candidate"]
        self.assertEqual(c["family"],"threshold_step")
        self.assertAlmostEqual(c["threshold"],1.0,places=12)
        for x in (-2.2,0.2,0.999,1.0,2.4):
            self.assertAlmostEqual(predict(c,{"x":x}),-2.0 if x<1.0 else 3.0,places=8)

    def test_nonmatching_cubic_fails_closed(self):
        rows=self.rows(lambda x:0.31*x**3-0.77*x+0.19)
        out=discover(rows,target="y")
        self.assertEqual(out["status"],"PARAMETRIC_FAMILIES_NOT_EXACT",out)

    def test_accounting_is_zero_learned(self):
        out=discover(self.rows(lambda x:math.exp(0.19*abs(x))),target="y")
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_frontier_model_calls"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)
        self.assertFalse(out["random_search"])
        self.assertFalse(out["dynamic_code_execution"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
