from __future__ import annotations
import copy, inspect, json, unittest

from canonical.runtime import p3_information_safe_proof_suite_v3 as proof
from canonical.runtime import p3_information_safe_candidate_v3 as candidate

class P3RawEvidenceInformationSafeV3Tests(unittest.TestCase):
    def test_information_boundary(self):
        case=proof.generate_case(17,3)
        public=proof.public_task(case)
        raw=json.dumps(public,sort_keys=True).lower()
        self.assertNotIn("_oracle",public)
        self.assertNotIn("hidden_support",raw)
        self.assertNotIn("hidden_decision",raw)
        self.assertNotIn('"stance"',raw)
        src=inspect.getsource(candidate)
        self.assertNotIn("p3_information_safe_proof_suite_v3",src)
        self.assertNotIn("_oracle",src)

    def test_large_preflight_population(self):
        for difficulty in range(1,6):
            for seed in range(250):
                case=proof.generate_case(seed + difficulty*10000,difficulty)
                out=candidate.solve(proof.public_task(case))
                verdict=proof.score_case(case,out)
                self.assertTrue(verdict["pass"],(difficulty,seed,verdict,out,case["task"]))

    def test_support_is_derived_from_raw_values(self):
        case=proof.generate_case(4242,4)
        public=proof.public_task(case)
        out=candidate.solve(public)
        self.assertTrue(proof.score_case(case,out)["pass"])
        # At least one claim has evidence. Move every value for that claim across
        # its visible threshold and verify the candidate output responds.
        changed=False
        for claim in public["task"]["claims"]:
            cid=claim["claim_id"]; metric=claim["metric"]; threshold=float(claim["threshold"])
            mutated=copy.deepcopy(public)
            before=candidate.solve(mutated)
            for row in mutated["task"]["evidence"]:
                if row["metric"]==metric:
                    if claim["relation"]=="at_least":
                        row["value"]=threshold-1000.0
                    else:
                        row["value"]=threshold+1000.0
            after=candidate.solve(mutated)
            if before!=after:
                changed=True
                break
        self.assertTrue(changed,"raw evidence mutation never changed synthesis")

    def test_budget_is_load_bearing(self):
        case=proof.generate_case(9191,5)
        public=proof.public_task(case)
        out=candidate.solve(public)
        self.assertLessEqual(len(out["selected_claims"]),public["task"]["max_claims"])
        bad=copy.deepcopy(out)
        bad["selected_claims"]=bad["selected_claims"]+["EXTRA"]*(public["task"]["max_claims"]+1)
        self.assertFalse(proof.score_case(case,bad)["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
