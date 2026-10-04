from __future__ import annotations

import math
import unittest

from canonical.runtime.synthesis_matched_quality_metric_v1 import (
    QUALITY_COMPONENTS,
    aggregate,
)

def vals(x=1.0):
    return {k: x for k in QUALITY_COMPONENTS}

class Tests(unittest.TestCase):
    def test_ceiling(self):
        out=aggregate(vals(1.0))
        self.assertEqual(out["matched_quality"],1.0)
        self.assertFalse(out["required_claim_coverage_included"])

    def test_noncompensatory_minimum(self):
        x=vals(1.0)
        x["audience_adaptation"]=0.25
        out=aggregate(x)
        self.assertEqual(out["matched_quality"],0.25)

    def test_unsupported_claim_hard_zero(self):
        out=aggregate(vals(1.0),unsupported_material_claims=1)
        self.assertEqual(out["matched_quality"],0.0)
        self.assertEqual(out["reason"],"UNSUPPORTED_MATERIAL_CLAIM_HARD_ZERO")

    def test_missing_component_fails_closed(self):
        x=vals()
        del x["format_and_style_constraints"]
        with self.assertRaises(ValueError):
            aggregate(x)

    def test_extra_component_fails_closed(self):
        x=vals()
        x["required_claim_coverage"]=1.0
        with self.assertRaises(ValueError):
            aggregate(x)

    def test_out_of_range_fails_closed(self):
        for bad in (-0.01,1.01):
            x=vals()
            x["claim_to_source_fidelity"]=bad
            with self.assertRaises(ValueError):
                aggregate(x)

    def test_nonfinite_fails_closed(self):
        for bad in (math.inf,-math.inf,math.nan):
            x=vals()
            x["claim_to_source_fidelity"]=bad
            with self.assertRaises(ValueError):
                aggregate(x)

    def test_bool_is_not_numeric_component(self):
        x=vals()
        x["claim_to_source_fidelity"]=True
        with self.assertRaises(ValueError):
            aggregate(x)

    def test_invalid_unsupported_count_fails_closed(self):
        with self.assertRaises(ValueError):
            aggregate(vals(),unsupported_material_claims=-1)
        with self.assertRaises(ValueError):
            aggregate(vals(),unsupported_material_claims=True)

    def test_monotone_nonincreasing_when_any_component_drops(self):
        base=aggregate(vals(0.8))["matched_quality"]
        for key in QUALITY_COMPONENTS:
            x=vals(0.8)
            x[key]=0.7
            self.assertLessEqual(aggregate(x)["matched_quality"],base)

if __name__=="__main__":
    unittest.main(verbosity=2)
