from __future__ import annotations
from copy import deepcopy
import inspect
import unittest

from canonical.runtime import saccr_credit_information_safe_candidate as candidate
from canonical.runtime import saccr_credit_information_safe_proof as proof

class SaccrCreditInformationSafeTests(unittest.TestCase):
    def test_information_boundary(self):
        source=inspect.getsource(candidate)
        self.assertNotIn("saccr_credit_information_safe_proof",source)
        self.assertNotIn("_oracle",source)
        case=proof.generate_case(7)
        public=proof.public_task(case)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("credit_addon",public["task"])
        self.assertNotIn("trade_traces",public["task"])

    def test_2000_fresh_deterministic_cases(self):
        for seed in range(2000):
            case=proof.generate_case(seed)
            out=candidate.solve(proof.public_task(case))
            verdict=proof.score_case(case,out)
            self.assertTrue(verdict["pass"],(seed,verdict,out))

    def test_intermediate_lineage_is_load_bearing(self):
        case=proof.generate_case(991)
        out=candidate.solve(proof.public_task(case))
        self.assertTrue(proof.score_case(case,out)["pass"])
        bad=deepcopy(out)
        bad["trade_traces"][0]["maturity_factor"] *= 1.01
        self.assertFalse(proof.score_case(case,bad)["pass"])

    def test_final_aggregation_is_load_bearing(self):
        case=proof.generate_case(7919)
        out=candidate.solve(proof.public_task(case))
        bad=deepcopy(out)
        bad["credit_addon"] += max(1.0,abs(float(bad["credit_addon"]))*0.01)
        self.assertFalse(proof.score_case(case,bad)["pass"])

    def test_missing_trace_fails(self):
        case=proof.generate_case(1234)
        out=candidate.solve(proof.public_task(case))
        bad=deepcopy(out)
        bad["trade_traces"].pop()
        self.assertFalse(proof.score_case(case,bad)["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
