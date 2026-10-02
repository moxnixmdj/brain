from __future__ import annotations
import copy
import inspect
import random
import unittest

from canonical.runtime import structured_method_normalized_graph_candidate_v3 as candidate
from canonical.runtime import structured_method_normalized_graph_proof_v3 as proof

class StructuredMethodNormalizedGraphV3Tests(unittest.TestCase):
    def test_information_boundary(self):
        case=proof.generate_case(101,8)
        public=proof.public_task(case)
        self.assertNotIn("_oracle",public)
        src=inspect.getsource(candidate)
        self.assertNotIn("structured_method_normalized_graph_proof_v3",src)
        self.assertNotIn("_oracle",src)

    def test_generated_population(self):
        for seed in range(200,456):
            case=proof.generate_case(seed)
            out=candidate.solve(proof.public_task(case))
            verdict=proof.score(case,out)
            self.assertTrue(verdict["pass"],(seed,out,verdict))

    def test_arbitrary_operator_vocabulary_has_no_whitelist_cutoff(self):
        case=proof.generate_case(777,12)
        ops=[r["operator"] for r in case["public"]["task"]["normalized_rules"]]
        self.assertEqual(len(ops),len(set(ops)))
        self.assertTrue(all(op.startswith("NORMALIZED_OP_") for op in ops))
        self.assertTrue(proof.score(case,candidate.solve(proof.public_task(case)))["pass"])

    def test_rule_order_independent(self):
        case=proof.generate_case(888,24)
        public=proof.public_task(case)
        baseline=candidate.solve(copy.deepcopy(public))
        rng=random.Random(9)
        rng.shuffle(public["task"]["normalized_rules"])
        shuffled=candidate.solve(public)
        self.assertEqual(baseline,shuffled)
        self.assertTrue(proof.score(case,shuffled)["pass"])

    def test_load_bearing_mutations_fail_closed(self):
        case=proof.generate_case(999,10)
        for name,public in proof.mutation_cases(case):
            out=candidate.solve(public)
            self.assertEqual(out["status"],"FAIL_CLOSED",(name,out))

    def test_unknown_source_kind_fails_closed(self):
        case=proof.generate_case(444,6)
        public=proof.public_task(case)
        public["task"]["requirements"][0]["source_kind"]="__UNKNOWN__"
        self.assertEqual(candidate.solve(public)["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)
