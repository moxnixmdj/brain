from __future__ import annotations
import unittest

from canonical.runtime import contract_native_brain_candidate as candidate
from canonical.runtime import contract_native_proof_suites as suite


class ContractNativeBrainCandidateTests(unittest.TestCase):
    def test_candidate_does_not_import_evaluator(self):
        import inspect
        source=inspect.getsource(candidate)
        self.assertNotIn("contract_native_proof_suites",source)
        self.assertNotIn("_oracle",source)

    def test_all_four_contracts_across_fresh_seed_grid(self):
        for contract in sorted(suite.CONTRACTS):
            for difficulty in range(1,6):
                for seed in (17,101,991,7919):
                    case=suite.generate_case(contract,seed,difficulty)
                    public=suite.public_task(case)
                    got=candidate.solve(public)
                    verdict=suite.score_case(case,got)
                    self.assertTrue(verdict["pass"],(contract,difficulty,seed,verdict,got))

    def test_synthesis_emits_exact_public_provenance_for_selected_claims(self):
        case=suite.generate_case("EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",4321,5)
        public=suite.public_task(case)
        got=candidate.solve(public)
        by_id={row["claim_id"]:row["provenance"] for row in public["task"]["evidence"]}
        self.assertEqual(
            got["provenance_by_claim"],
            {claim_id:by_id[claim_id] for claim_id in got["selected_claims"]},
        )
        self.assertTrue(suite.score_case(case,got)["pass"])

    def test_hidden_oracle_not_required(self):
        case=suite.generate_case("TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",1234,4)
        public=suite.public_task(case)
        self.assertNotIn("_oracle",public)
        self.assertTrue(suite.score_case(case,candidate.solve(public))["pass"])


if __name__=="__main__":
    unittest.main()
