import unittest

from canonical.runtime.contract_native_proof_suites import (
    CONTRACTS, generate_case, oracle_candidate, public_task, score_case,
)


class ContractNativeProofSuitesTests(unittest.TestCase):
    def test_oracle_candidate_passes_many_seeds(self):
        for contract in sorted(CONTRACTS):
            for seed in range(40):
                case=generate_case(contract, seed, difficulty=1+(seed%5))
                self.assertNotIn("_oracle", public_task(case))
                out=score_case(case, oracle_candidate(case))
                self.assertTrue(out["pass"], (contract,seed,out))

    def test_structured_method_omission_is_killed(self):
        case=generate_case("STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001", 101, 4)
        candidate=oracle_candidate(case)
        candidate["graph"]=candidate["graph"][:-1]
        out=score_case(case,candidate)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("MISSING_FACTOR:") for x in out["reasons"]))

    def test_structured_method_wrong_semantics_is_killed(self):
        case=generate_case("STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001", 102, 5)
        candidate=oracle_candidate(case)
        candidate["graph"][0]["coefficient"] += 1
        self.assertFalse(score_case(case,candidate)["pass"])

    def test_trajectory_downstream_symptom_repair_fails(self):
        case=generate_case("TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", 202, 4)
        gold=case["_oracle"]["cause_step"]
        candidate={"cause_step":gold+1,"repair_id":f"repair_{gold+1}","evidence_steps":[gold+1]}
        out=score_case(case,candidate)
        self.assertFalse(out["pass"])
        self.assertFalse(out["rescue_pass"])

    def test_synthesis_unsupported_claim_fails(self):
        seed=0
        while True:
            case=generate_case("EVIDENCE_TO_AUDIENCE_SYNTHESIS_001", seed, 5)
            if case["_oracle"]["forbidden"]:
                break
            seed+=1
        candidate=oracle_candidate(case)
        candidate["selected_claims"].append(case["_oracle"]["forbidden"][0])
        self.assertFalse(score_case(case,candidate)["pass"])

    def test_synthesis_required_omission_fails(self):
        case=generate_case("EVIDENCE_TO_AUDIENCE_SYNTHESIS_001", 303, 5)
        candidate=oracle_candidate(case)
        victim=case["_oracle"]["required"][0]
        candidate["selected_claims"]=[x for x in candidate["selected_claims"] if x!=victim]
        candidate["uncertainty_claims"]=[x for x in candidate["uncertainty_claims"] if x!=victim]
        self.assertFalse(score_case(case,candidate)["pass"])

    def test_professional_suboptimal_plan_fails(self):
        case=generate_case("PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001", 404, 5)
        gold=oracle_candidate(case)
        bad={"selected_edits":[] if gold["selected_edits"] else [case["task"]["edit_candidates"][0]["id"]]}
        self.assertFalse(score_case(case,bad)["pass"])

    def test_deterministic_generation(self):
        for contract in CONTRACTS:
            self.assertEqual(generate_case(contract,777,3),generate_case(contract,777,3))


if __name__=="__main__":
    unittest.main()
