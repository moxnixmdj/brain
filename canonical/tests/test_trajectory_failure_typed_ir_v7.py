from __future__ import annotations
import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof


class Tests(unittest.TestCase):
    def test_full_240_case_cross_product_and_forward_rescue(self):
        cases=proof.suite_cases()
        self.assertEqual(len(cases),240)
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
        self.assertEqual(rescued,192)
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

    def test_serial_direct_cofault_requires_both_direct_repairs(self):
        case=proof.generate_case(62010,pattern="SERIAL_COFAULT",domain="TOOL_API",kind="SCOPE")
        public=proof.public_task(case)
        out=candidate.solve(public)
        self.assertEqual(out["status"],"INTERACTION")
        self.assertEqual(out["cause_action_ids"],["A1","A2"])
        self.assertEqual(len(out["repair_targets"]),2)
        verdict=proof.score_case(case,out)
        self.assertTrue(verdict["pass"],verdict)
        self.assertTrue(verdict["intervention"]["terminal_rescued"])

        partial=copy.deepcopy(out)
        partial["repair_targets"]=partial["repair_targets"][:1]
        iv=proof.execute_intervention(public,partial)
        self.assertFalse(iv["terminal_rescued"])
        self.assertTrue(iv["active_direct_failures"])

    def test_failure_semantics_is_load_bearing(self):
        case=proof.generate_case(62011,pattern="SERIAL_COFAULT",domain="CODE",kind="SCOPE")
        public=proof.public_task(case)
        before=candidate.solve(copy.deepcopy(public))
        self.assertEqual(before["cause_action_ids"],["A1","A2"])

        for row in public["task"]["trajectory"]:
            if row["action_id"]=="A2":
                for check in row["checks"]:
                    if check["pass"] is False:
                        check["failure_semantics"]="DERIVED_UPSTREAM"
        after=candidate.solve(copy.deepcopy(public))
        self.assertEqual(after["status"],"IDENTIFIED")
        self.assertEqual(after["cause_action_ids"],["A1"])
        self.assertEqual(after["repair_targets"],["restore:A1:SCOPE"])
        iv=proof.execute_intervention(public,after)
        self.assertTrue(iv["terminal_rescued"],iv)

    def test_invalid_failure_semantics_fails_closed(self):
        case=proof.generate_case(62012,pattern="SINGLE",domain="FILESYSTEM",kind="SCOPE")
        public=proof.public_task(case)
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    check["failure_semantics"]="MAGIC"
                    out=candidate.solve(public)
                    self.assertEqual(out["status"],"FAIL_CLOSED")
                    return
        self.fail("expected failed check")

    def test_missing_failure_semantics_fails_closed(self):
        case=proof.generate_case(62013,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
        public=proof.public_task(case)
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    check.pop("failure_semantics",None)
                    out=candidate.solve(public)
                    self.assertEqual(out["status"],"FAIL_CLOSED")
                    return
        self.fail("expected failed check")

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
