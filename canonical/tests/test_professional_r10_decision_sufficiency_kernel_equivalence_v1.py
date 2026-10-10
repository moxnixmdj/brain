from __future__ import annotations
import unittest
from canonical.runtime import professional_r10_decision_sufficiency_kernel_v1 as k
from canonical.runtime import one_shot_reality_closure_v2 as v2

class R10KernelEquivalenceTests(unittest.TestCase):
    def cases(self):
        base={
            "gap_class":"PENDING_ACQUISITION_OR_EXPERIMENT",
            "required_action":"SEARCH_SIMULATE_EXPERIMENT_OR_ACQUIRE_MINIMUM_NEEDED_EVIDENCE",
            "basis_digest":"a"*64,
            "pending_semantic_work_digest":"b"*64,
            "constructive_capability_contracts":[],
        }
        yield {**base,"basis":{"constructive_internal_blockers":["ROOT1_GAP"],"evidence_blockers":["MISSING_FACT"],"r2_acquisition_requests":[]}}
        req={
            "cell_id":"FINANCE_SEMANTIC_ADEQUACY_TAIL",
            "request_sha256":"8"*64,
            "source_r2_authority_sha256":"9"*64,
            "required_action":"ACQUIRE_ONLY_MINIMUM_AUTHENTICATED_DISCRIMINATOR",
            "remaining_boundary":"UNBOUND",
            "wake_conditions":["A","B"],
        }
        yield {**base,"basis":{"constructive_internal_blockers":[],"evidence_blockers":["R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL"],"r2_acquisition_requests":[req]}}
        yield {**base,"basis":{"constructive_internal_blockers":[],"evidence_blockers":["B","A","B"],"r2_acquisition_requests":[]}}

    def test_decision_and_minimum_information_outputs_match_v2(self):
        for g in self.cases():
            with self.subTest(g=g):
                kd=k.compile_decision_sufficient_contract(g)
                vd=v2.compile_decision_sufficient_contract(g)
                self.assertEqual(kd,vd)
                km=k.compile_minimum_information_contract(g,kd)
                vm=v2.compile_minimum_information_contract(g,vd)
                self.assertEqual(km,vm)

if __name__=="__main__":
    unittest.main()
