from __future__ import annotations

import unittest
from fractions import Fraction

from canonical.runtime import finite_probe_nonidentifiability_certificate_v1 as n


class FiniteProbeNonidentifiabilityTests(unittest.TestCase):
    def test_arbitrary_finite_2d_transcript_has_distinct_polynomial_extension(self):
        probes=[(Fraction(i,7),Fraction(i*i+3,11)) for i in range(17)]
        out=n.prove(probes)
        self.assertEqual(out["status"],"PASS__FINITE_PROBES_CANNOT_UNIVERSALLY_IDENTIFY_UNRESTRICTED_FUNCTION_CLASS")
        self.assertEqual(out["probe_count"],17)
        self.assertNotEqual(out["f1_at_witness"],"0")

    def test_repeated_probes_do_not_change_construction(self):
        out=n.prove([(0,),(0,),(1,),(2,)])
        self.assertEqual(out["f1_on_all_probes"],["0","0","0","0"])

    def test_any_dimension(self):
        for d in (1,2,3,5):
            probes=[tuple(i+j for j in range(d)) for i in range(9)]
            out=n.prove(probes)
            self.assertEqual(out["dimension"],d)
            self.assertGreater(Fraction(out["f1_at_witness"]),0)

    def test_dimension_mismatch_fails(self):
        with self.assertRaises(ValueError):
            n.prove([(1,2),(3,)])


if __name__=="__main__":
    unittest.main(verbosity=2)
