from __future__ import annotations
from copy import deepcopy
import inspect
import unittest

from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as proof

class DelegationWholeScopeV2Tests(unittest.TestCase):
    def test_information_boundary(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("delegation_whole_scope_proof_v2",src)
        self.assertNotIn("_oracle",src)
        case=proof.generate_case(81277,0)
        self.assertNotIn("_oracle",proof.public_initial(case))
        self.assertNotIn("_oracle",proof.public_after_receipt(case))

    def test_180_cross_dimension_cases(self):
        out=proof.run_batch(81277,180,candidate.solve_initial,candidate.solve_after_receipt)
        self.assertTrue(out["all_pass"],out["failures"][:5])

    def test_missing_terminal_evidence_is_rejected(self):
        case=proof.generate_case(81277,1)
        first=candidate.solve_initial(proof.public_initial(case))
        second=candidate.solve_after_receipt(proof.public_after_receipt(case),first)
        self.assertTrue(proof.score_episode(case,first,second)["pass"])
        bad=deepcopy(second);bad["terminal_evidence"]=bad["terminal_evidence"][:-1]
        self.assertFalse(proof.score_episode(case,first,bad)["pass"])

    def test_resource_conflict_in_same_wave_is_rejected(self):
        case=proof.generate_case(81277,1)  # RESOURCE_CONFLICT
        first=candidate.solve_initial(proof.public_initial(case))
        self.assertTrue(proof.score_episode(
            case,first,candidate.solve_after_receipt(proof.public_after_receipt(case),first)
        )["pass"])
        # Forge one wave containing every selected task; dependency/resource oracle must kill it.
        bad=deepcopy(first);bad["waves"]=[list(bad["task_ids"])]
        receipt=case["_oracle"]["receipt"]
        revised=candidate.solve_after_receipt(proof.public_after_receipt(case),first)
        self.assertFalse(proof.score_episode(case,bad,revised)["pass"])

    def test_wrong_worker_is_rejected(self):
        case=proof.generate_case(81277,0)
        first=candidate.solve_initial(proof.public_initial(case))
        bad=deepcopy(first)
        sid=bad["task_ids"][0]
        bad["assignment"][sid]="NOT_A_WORKER"
        revised=candidate.solve_after_receipt(proof.public_after_receipt(case),first)
        self.assertFalse(proof.score_episode(case,bad,revised)["pass"])

    def test_no_static_twenty_step_guard_in_candidate(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("TOO_MANY_STEPS",src)
        self.assertNotIn(">20",src.replace(" ",""))

if __name__=="__main__":
    unittest.main(verbosity=2)
