from __future__ import annotations
import unittest
from canonical.runtime.finance_index_direct_threshold_v1 import compile_verified_lower_bounds, FinanceThresholdError

NAMES=[
 "BUSINESS_KNOWLEDGE","AGENTIC_KNOWLEDGE_WORK","REASONING",
 "AGENTIC_TOOL_USE","LONG_CONTEXT","NON_HALLUCINATION"
]
def rows(vals):
    return {n:{"verified":True,"lower_bound":v,"receipt":"sha256:"+n} for n,v in zip(NAMES,vals)}

class TestFinanceDirectThreshold(unittest.TestCase):
    def test_exact_61_passes(self):
        out=compile_verified_lower_bounds(rows([61,61,61,61,61,61]))
        self.assertTrue(out["mathematically_sufficient"])
        self.assertEqual(out["weighted_lower_bound"],"61")
    def test_compensation_is_allowed(self):
        out=compile_verified_lower_bounds(rows([100,100,5,0,0,0]))
        self.assertTrue(out["mathematically_sufficient"])
        self.assertEqual(out["weighted_lower_bound"],"61")
    def test_componentwise_opus_dominance_not_required(self):
        out=compile_verified_lower_bounds(rows([100,100,5,0,0,0]))
        self.assertFalse(out["componentwise_opus_noninferiority_required"])
    def test_below_threshold_fails_closed(self):
        out=compile_verified_lower_bounds(rows([60,60,60,60,60,60]))
        self.assertFalse(out["mathematically_sufficient"])
    def test_unverified_bound_rejected(self):
        x=rows([61]*6); x["LONG_CONTEXT"]["verified"]=False
        with self.assertRaises(FinanceThresholdError):
            compile_verified_lower_bounds(x)
    def test_missing_component_rejected(self):
        x=rows([61]*6); x.pop("LONG_CONTEXT")
        with self.assertRaises(FinanceThresholdError):
            compile_verified_lower_bounds(x)

if __name__=="__main__":
    unittest.main(verbosity=2)
