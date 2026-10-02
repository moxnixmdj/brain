from __future__ import annotations
import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof


class Tests(unittest.TestCase):
    def test_full_192_case_cross_product_passes(self):
        cases=proof.suite_cases()
        self.assertEqual(len(cases),192)
        failures=[]
        for case in cases:
            out=candidate.solve(proof.public_task(case))
            verdict=proof.score_case(case,out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"],verdict,out))
        self.assertEqual(failures,[])

    def test_scope_is_first_class_across_all_domains_and_patterns(self):
        cases=[c for c in proof.suite_cases() if c["_oracle"]["mechanisms"]["A1"][0]=="SCOPE"]
        self.assertEqual(len(cases),24)
        self.assertEqual({c["task"]["domain"] for c in cases},set(proof.DOMAINS))
        self.assertEqual({c["_oracle"]["status"] for c in cases},{"IDENTIFIED","INTERACTION","AMBIGUOUS"})
        for case in cases:
            out=candidate.solve(proof.public_task(case))
            self.assertTrue(proof.score_case(case,out)["pass"])

    def test_drop_provenance_receipts_is_killed(self):
        case=proof.generate_case(61001,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
        public=copy.deepcopy(proof.public_task(case))
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    check["evidence"]=[]
        out=candidate.solve(public)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertFalse(proof.score_case(case,out)["pass"])

    def test_unfalsifiable_extra_diagnosis_is_killed(self):
        case=proof.generate_case(61002,pattern="DELAYED",domain="CODE",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        self.assertTrue(proof.score_case(case,out)["pass"])
        mutated=dict(out)
        mutated["diagnosis"]={"claim":"UNOBSERVABLE_FORCE","falsifiable":False}
        verdict=proof.score_case(case,mutated)
        self.assertFalse(verdict["pass"])
        self.assertEqual(verdict["reason"],"OUTPUT_SCHEMA_NOT_EXACT")

    def test_interaction_requires_all_root_repairs(self):
        case=proof.generate_case(61003,pattern="INTERACTION",domain="TOOL_API",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        repairs=out["repair_targets"]
        self.assertEqual(len(repairs),2)
        self.assertTrue(proof.evaluate_intervention(case,repairs)["rescued"])
        for r in repairs:
            self.assertFalse(proof.evaluate_intervention(case,[r])["rescued"])

    def test_symptom_only_repair_does_not_rescue(self):
        case=proof.generate_case(61004,pattern="DELAYED",domain="BROWSER",kind="AUTHORITY")
        symptoms=case["_intervention_model"]["downstream_symptom_repairs"]
        self.assertTrue(symptoms)
        self.assertFalse(proof.evaluate_intervention(case,symptoms)["rescued"])

    def test_hidden_oracle_and_intervention_state_not_public(self):
        case=proof.generate_case(61005,pattern="INTERACTION",domain="FILESYSTEM",kind="DEPENDENCY")
        public=proof.public_task(case)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("_intervention_model",public)
        self.assertNotIn("required_root_repairs",str(public))

    def test_ambiguous_case_never_forces_unique_cause(self):
        case=proof.generate_case(61006,pattern="AMBIGUOUS",domain="ARTIFACT",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"],"AMBIGUOUS")
        self.assertIsNone(out["cause_action_id"])
        self.assertTrue(proof.score_case(case,out)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
