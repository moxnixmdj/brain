from __future__ import annotations
import unittest
from canonical.runtime.terminal_distribution_outcome_order_v1 import (
    OutcomeOrderError,equivalent,verify_finite_countermodels,verify_order_laws,weakly_dominates
)

class DistributionOutcomeOrderTests(unittest.TestCase):
    def setUp(self):
        self.u={
          "success":{"excellent":1.0,"ok":1.0,"fail":0.0},
          "quality":{"excellent":1.0,"ok":0.5,"fail":0.0},
        }
        self.h={"critical_violation":{"excellent":0.0,"ok":0.0,"fail":1.0}}
        self.a={"excellent":0.7,"ok":0.2,"fail":0.1}
        self.b={"excellent":0.6,"ok":0.25,"fail":0.15}
        self.c={"excellent":0.5,"ok":0.3,"fail":0.2}

    def test_countermodels_reject_shortcuts(self):
        out=verify_finite_countermodels()
        self.assertTrue(all(out.values()))

    def test_reflexive_transitive_and_quotient_equivalence(self):
        out=verify_order_laws([self.a,self.b,self.c],self.u,self.h)
        self.assertTrue(all(out.values()))
        self.assertTrue(weakly_dominates(self.a,self.b,self.u,self.h).weakly_dominates)
        self.assertTrue(weakly_dominates(self.b,self.c,self.u,self.h).weakly_dominates)
        self.assertTrue(weakly_dominates(self.a,self.c,self.u,self.h).weakly_dominates)

    def test_equivalent_distribution_is_equivalent(self):
        self.assertTrue(equivalent(self.a,dict(self.a),self.u,self.h))

    def test_outcome_space_mismatch_fails(self):
        with self.assertRaises(OutcomeOrderError):
            weakly_dominates({"x":1.0},{"y":1.0},{"u":{"x":1.0}},{})

    def test_empty_utility_family_fails(self):
        with self.assertRaises(OutcomeOrderError):
            weakly_dominates(self.a,self.b,{},self.h)

    def test_probability_mass_must_be_valid(self):
        bad={"excellent":0.8,"ok":0.8,"fail":0.0}
        with self.assertRaises(OutcomeOrderError):
            weakly_dominates(bad,self.b,self.u,self.h)

if __name__=="__main__":
    unittest.main(verbosity=2)
