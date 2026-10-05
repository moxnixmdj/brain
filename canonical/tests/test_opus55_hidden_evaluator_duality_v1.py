from __future__ import annotations
from fractions import Fraction
import itertools
import unittest

from canonical.runtime.opus55_hidden_evaluator_duality_v1 import (
    indicator_separator,
    proof_route,
    universal_indicator_noninferiority,
)

class Tests(unittest.TestCase):
    def test_equal_distributions_pass(self):
        v=universal_indicator_noninferiority(["1/2","1/3","1/6"],["1/2","1/3","1/6"])
        self.assertEqual(v["status"],"PASS")
        self.assertTrue(v["distribution_equivalence"])

    def test_unequal_distributions_get_constructive_separator(self):
        v=universal_indicator_noninferiority(["3/4","1/4"],["1/2","1/2"])
        self.assertEqual(v["status"],"FAIL")
        self.assertEqual(v["counterexample"]["status"],"SEPARATED")
        self.assertGreater(Fraction(v["counterexample"]["strict_gap"]),0)

    def test_exhaustive_three_outcome_denominator_four(self):
        D=4
        distributions=[]
        for a in range(D+1):
            for b in range(D+1-a):
                c=D-a-b
                distributions.append(tuple(Fraction(x,D) for x in (a,b,c)))
        self.assertEqual(len(distributions),15)
        pairs=0
        unequal=0
        for p,q in itertools.product(distributions,repeat=2):
            pairs += 1
            v=universal_indicator_noninferiority(p,q)
            self.assertEqual(v["status"]=="PASS",p==q)
            if p != q:
                unequal += 1
                w=indicator_separator(p,q)
                self.assertEqual(w["status"],"SEPARATED")
                self.assertGreater(Fraction(w["strict_gap"]),0)
        self.assertEqual(pairs,225)
        self.assertEqual(unequal,210)

    def test_route_priority_and_conservative_residual(self):
        self.assertEqual(proof_route(exact=True,restricted=True,other_sound_noninferiority=True),"E_EXACT_SOLVED")
        self.assertEqual(proof_route(exact=False,restricted=True,other_sound_noninferiority=True),"M_RESTRICTED_SOLVED")
        self.assertEqual(proof_route(exact=False,restricted=False,other_sound_noninferiority=True),"OTHER_PROOF_CARRYING_SOLVED")
        self.assertEqual(proof_route(exact=False,restricted=False,other_sound_noninferiority=False),"EQUIVALENCE_RESIDUAL")

    def test_bad_distribution_fails(self):
        with self.assertRaises(ValueError):
            universal_indicator_noninferiority(["1/2","1/2"],["1/2","1/3"])

if __name__=="__main__":
    unittest.main(verbosity=2)
