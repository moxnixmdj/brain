from __future__ import annotations
import inspect
import unittest
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate

BEACONS=[
 "QUAL-V2-A-0123456789abcdef",
 "QUAL-V2-B-fedcba9876543210",
 "QUAL-V2-C-3141592653589793",
]

class UnknownDomainDirectCandidateV2Tests(unittest.TestCase):
    def _run(self,beacon):
        packet=generator.generate_qualification_fixture_population(beacon=beacon)
        self.assertFalse(packet["production"])
        results=[]; executions=[]
        for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
            out=harness.execute_case(candidate_step=candidate.step,case_visible=visible,hidden_record=hidden)
            executions.append(out); results.append(out["scorer_result"])
        return scorer.aggregate(results),executions

    def test_all_three_v2_generator_populations_pass(self):
        for beacon in BEACONS:
            with self.subTest(beacon=beacon):
                agg,executions=self._run(beacon)
                self.assertTrue(agg["all_27_cases_pass"],agg)
                self.assertTrue(agg["transfer_leaf_pass"],agg)
                self.assertTrue(agg["abstention_leaf_pass"],agg)
                transfer=[x for x in executions if x["leaf_id"]==scorer.TRANSFER]
                self.assertEqual(len(transfer),12)
                self.assertTrue(all(x["probe_count"]<=2 for x in transfer))

    def test_zero_learned_no_hidden_import_surface(self):
        src=inspect.getsource(candidate)
        for token in ["unknown_domain_direct_hidden_generator","unknown_domain_direct_hidden_scorer","unknown_domain_direct_execution_harness","torch","transformers","openai","anthropic"]:
            self.assertNotIn(token,src)

    def test_v2_is_additive_over_frozen_v1(self):
        src=inspect.getsource(candidate)
        self.assertIn("unknown_domain_direct_candidate_v1",src)
        self.assertIn("STRUCTURAL_SCALE_TIE",src)

if __name__=="__main__":
    unittest.main(verbosity=2)
