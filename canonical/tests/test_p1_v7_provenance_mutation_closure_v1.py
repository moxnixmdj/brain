import copy,unittest
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof
from canonical.runtime.p1_v7_provenance_mutation_closure_v1 import evaluate

class Tests(unittest.TestCase):
    def test_live_v7_kills_drop_provenance(self):
        out=evaluate()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["candidate_status"],"FAIL_CLOSED")
        self.assertFalse(out["scorer_pass_after_mutation"])
    def test_original_unmutated_case_still_passes(self):
        case=proof.generate_case(71001,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
        public=proof.public_task(case)
        out=candidate.solve(copy.deepcopy(public))
        verdict=proof.score_case(case,out)
        self.assertTrue(verdict["pass"],(out,verdict))

if __name__=="__main__": unittest.main(verbosity=2)
