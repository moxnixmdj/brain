from __future__ import annotations
import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof


class Tests(unittest.TestCase):
    def test_full_192_case_cross_product_and_forward_rescue(self):
        cases=proof.suite_cases()
        self.assertEqual(len(cases),192)
        rescued=0
        ambiguous=0
        failures=[]
        for case in cases:
            public=proof.public_task(case)
            self.assertNotIn("_oracle",public)
            out=candidate.solve(public)
            verdict=proof.score_case(case,out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"],verdict,out))
                continue
            if case["_oracle"]["status"]=="AMBIGUOUS":
                ambiguous+=1
                self.assertFalse(verdict["intervention_rescue_verified"])
            else:
                rescued+=1
                self.assertTrue(verdict["intervention_rescue_verified"])
                self.assertTrue(verdict["intervention"]["terminal_rescued"])
        self.assertEqual(failures,[])
        self.assertEqual(rescued,144)
        self.assertEqual(ambiguous,48)

    def test_scope_is_first_class_not_authority_alias(self):
        for domain in proof.DOMAINS:
            case=proof.generate_case(62001,pattern="DELAYED",domain=domain,kind="SCOPE")
            out=candidate.solve(proof.public_task(case))
            self.assertEqual(out["mechanism_classes"],["SCOPE"])
            self.assertEqual(out["repair_targets"],["restore:A1:SCOPE"])
            verdict=proof.score_case(case,out)
            self.assertTrue(verdict["pass"],verdict)
            self.assertTrue(verdict["intervention"]["terminal_rescued"])

    def test_drop_provenance_receipts_fails_closed(self):
        case=proof.generate_case(62002,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
        public=proof.public_task(case)
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    check["evidence"]=[]
        out=candidate.solve(public)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertFalse(proof.score_case(case,out)["pass"])

    def test_unbound_output_field_is_rejected(self):
        case=proof.generate_case(62003,pattern="DELAYED",domain="CODE",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        self.assertTrue(proof.score_case(case,out)["pass"])
        attacked=dict(out)
        attacked["diagnosis"]={"claim":"UNOBSERVABLE_FORCE"}
        verdict=proof.score_case(case,attacked)
        self.assertFalse(verdict["pass"])
        self.assertEqual(verdict["reason"],"OUTPUT_SCHEMA_NOT_EXACT")

    def test_interaction_partial_repair_cannot_rescue(self):
        case=proof.generate_case(62004,pattern="INTERACTION",domain="TOOL_API",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        self.assertTrue(proof.score_case(case,out)["pass"])
        self.assertEqual(len(out["repair_targets"]),2)
        partial=copy.deepcopy(out)
        partial["repair_targets"]=partial["repair_targets"][:1]
        iv=proof.execute_intervention(proof.public_task(case),partial)
        self.assertFalse(iv["terminal_rescued"])
        self.assertFalse(proof.score_case(case,partial)["pass"])

    def test_symptom_only_repair_cannot_rescue(self):
        case=proof.generate_case(62005,pattern="DELAYED",domain="BROWSER",kind="AUTHORITY")
        out=candidate.solve(proof.public_task(case))
        symptom=copy.deepcopy(out)
        symptom["repair_targets"]=["restore:A4:INVARIANT"]
        iv=proof.execute_intervention(proof.public_task(case),symptom)
        self.assertFalse(iv["terminal_rescued"])

    def test_repair_string_without_causal_effect_cannot_fake_rescue(self):
        case=proof.generate_case(62006,pattern="DELAYED",domain="FILESYSTEM",kind="PROVENANCE")
        out=candidate.solve(proof.public_task(case))
        fake=copy.deepcopy(out)
        fake["repair_targets"]=["restore:A999:PROVENANCE"]
        iv=proof.execute_intervention(proof.public_task(case),fake)
        self.assertFalse(iv["terminal_rescued"])
        self.assertFalse(proof.score_case(case,fake)["pass"])

    def test_derived_failure_recomputed_after_actual_root_repair(self):
        case=proof.generate_case(62007,pattern="DELAYED",domain="CODE",kind="SCOPE")
        public=proof.public_task(case)
        out=candidate.solve(public)
        iv=proof.execute_intervention(public,out)
        self.assertTrue(iv["terminal_rescued"])
        self.assertEqual(iv["active_direct_failures"],[])
        self.assertEqual(iv["active_derived_failures"],[])

    def test_hidden_oracle_mutation_does_not_change_public_payload(self):
        case=proof.generate_case(62008,pattern="SINGLE",domain="ARTIFACT",kind="SCOPE")
        before=proof.public_task(case)
        case["_oracle"]["critical"]="A999"
        after=proof.public_task(case)
        self.assertEqual(before,after)

    def test_ambiguous_case_abstains_and_never_claims_rescue(self):
        case=proof.generate_case(62009,pattern="AMBIGUOUS",domain="ARTIFACT",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"],"AMBIGUOUS")
        self.assertIsNone(out["cause_action_id"])
        verdict=proof.score_case(case,out)
        self.assertTrue(verdict["pass"])
        self.assertFalse(verdict["intervention_rescue_verified"])


if __name__=="__main__":
    unittest.main(verbosity=2)
