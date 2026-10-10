from __future__ import annotations
import unittest
from canonical.runtime import professional_r10_decision_sufficiency_kernel_v1 as k

def gap(*, evidence=(), internal=(), r2=()):
    return {
        "gap_class":"PENDING_ACQUISITION_OR_EXPERIMENT",
        "required_action":"SEARCH_SIMULATE_EXPERIMENT_OR_ACQUIRE_MINIMUM_NEEDED_EVIDENCE",
        "basis_digest":"a"*64,
        "pending_semantic_work_digest":"b"*64,
        "basis":{
            "constructive_internal_blockers":list(internal),
            "evidence_blockers":list(evidence),
            "r2_acquisition_requests":list(r2),
        },
        "constructive_capability_contracts":[],
    }

class R10KernelTests(unittest.TestCase):
    def test_lossless_baseline(self):
        g=gap(evidence=("MISSING_FACT",),internal=("ROOT1_GAP",))
        out=k.compile_decision_sufficient_contract(g)
        self.assertTrue(out["pass"])
        self.assertEqual(out["reduction_mode"],"LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION")
        self.assertEqual(out["omitted_evidence"],[])
        kinds={x["kind"] for x in out["representation"]["policy_changing_requirements"]}
        self.assertEqual(kinds,{"INTERNAL_BLOCKER","EVIDENCE_BLOCKER"})

    def test_minimum_info_deduplicates(self):
        g=gap(evidence=("MISSING_FACT","MISSING_FACT","OTHER_FACT"))
        d=k.compile_decision_sufficient_contract(g)
        out=k.compile_minimum_information_contract(g,d)
        self.assertEqual(out["request_count"],2)
        self.assertEqual(out["proof_precedence"][-1],"FULL_EMPIRICAL_EVALUATION_LAST")
        self.assertTrue(all(x["broad_acquisition_forbidden_without_minimality_proof"] for x in out["requests"]))

    def test_structured_r2_survives(self):
        req={
            "cell_id":"FINANCE_SEMANTIC_ADEQUACY_TAIL",
            "request_sha256":"8"*64,
            "source_r2_authority_sha256":"9"*64,
            "required_action":"ACQUIRE_ONLY_MINIMUM_AUTHENTICATED_DISCRIMINATOR",
            "remaining_boundary":"UNBOUND",
            "wake_conditions":["A","B"],
        }
        g=gap(evidence=("R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL",),r2=(req,))
        d=k.compile_decision_sufficient_contract(g)
        out=k.compile_minimum_information_contract(g,d)
        self.assertEqual(out["request_count"],1)
        self.assertEqual(out["structured_r2_request_count"],1)
        self.assertEqual(out["requests"][0]["r2_cell_id"],"FINANCE_SEMANTIC_ADEQUACY_TAIL")
        self.assertFalse(out["requests"][0]["full_benchmark_default"])

    def test_provider_authority_mutation_rejected(self):
        with self.assertRaisesRegex(k.R10KernelError,"VERIFICATION_AUTHORITY_MUTATION_FORBIDDEN"):
            k.validate_provider_authority({"verification_authority_mutated":True})

    def test_provider_authority_preserved(self):
        out=k.validate_provider_authority({"verification_authority_mutated":False})
        self.assertTrue(out["pass"])

    def test_false_progress_rejected(self):
        out=k.verify_observed_frontier_progress(
            before_frontier_digest="same",after_frontier_digest="same",
            provider_claimed_frontier_changed=True,
        )
        self.assertFalse(out["pass"])
        self.assertIn("WITHOUT_OBSERVED_FRONTIER_CHANGE",out["status"])

    def test_observed_progress_passes(self):
        out=k.verify_observed_frontier_progress(
            before_frontier_digest="a",after_frontier_digest="b",
            provider_claimed_frontier_changed=True,
        )
        self.assertTrue(out["pass"])
        self.assertTrue(out["observed_frontier_changed"])

if __name__=="__main__":
    unittest.main()
