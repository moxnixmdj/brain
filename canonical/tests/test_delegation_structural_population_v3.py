from copy import deepcopy
import inspect, unittest
from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_structural_population_v3 as proof

class DelegationStructuralPopulationV3Tests(unittest.TestCase):
    def test_information_boundary_and_structural_grid(self):
        self.assertNotIn("delegation_structural_population_v3", inspect.getsource(candidate))
        out=proof.run_batch(20261002,128,candidate.solve_initial)
        self.assertTrue(out["all_pass"],out["failures"][:3])
        self.assertGreaterEqual(out["topology_fingerprint_count"],2)
        self.assertTrue(out["fanin_present"])
        self.assertTrue(out["alternative_plan_present"])
    def test_lost_fanin_evidence_fails(self):
        case=proof.generate_case(17,3)
        out=candidate.solve_initial(proof.public_task(case))
        self.assertTrue(proof.score_case(case,out)["pass"])
        bad=deepcopy(out); bad["terminal_evidence"]=bad["terminal_evidence"][:-1]
        self.assertFalse(proof.score_case(case,bad)["pass"])
    def test_redundant_task_fails(self):
        case=proof.generate_case(19,4)
        out=candidate.solve_initial(proof.public_task(case))
        bad=deepcopy(out)
        extra=next(x["id"] for x in case["task"]["steps"] if x["id"] not in bad["task_ids"])
        bad["task_ids"].append(extra)
        self.assertFalse(proof.score_case(case,bad)["pass"])
if __name__=="__main__": unittest.main(verbosity=2)
