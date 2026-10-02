from __future__ import annotations
import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof


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

    def test_derived_only_visible_failure_abstains_instead_of_fake_root(self):
        public={
            "schema":proof.SCHEMA,
            "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
            "task":{
                "domain":"CODE",
                "trajectory":[
                    {
                        "step":0,"action_id":"A0","domain":"CODE","reads":[],
                        "writes":["code:upstream"],"depends_on":[],"dependency_composition":"SEQUENTIAL",
                        "checks":[{"kind":"INVARIANT","id":"A0:INVARIANT","pass":True,
                                   "evidence":["receipt:A0"],"failure_semantics":"DIRECT_CONTRACT"}],
                    },
                    {
                        "step":1,"action_id":"A1","domain":"CODE","reads":["code:upstream"],
                        "writes":["code:symptom"],"depends_on":["A0"],"dependency_composition":"SEQUENTIAL",
                        "checks":[
                            {"kind":"INVARIANT","id":"A1:INVARIANT:baseline","pass":True,
                             "evidence":["receipt:A1"],"failure_semantics":"DIRECT_CONTRACT"},
                            {"kind":"SCOPE","id":"A1:SCOPE","pass":False,
                             "evidence":["receipt:A1","check:A1:SCOPE"],"failure_semantics":"DERIVED_UPSTREAM"},
                        ],
                    },
                    {
                        "step":2,"action_id":"A2","domain":"CODE","reads":["code:symptom"],
                        "writes":["code:terminal"],"depends_on":["A1"],"dependency_composition":"SEQUENTIAL",
                        "checks":[{"kind":"INVARIANT","id":"A2:INVARIANT","pass":True,
                                   "evidence":["receipt:A2"],"failure_semantics":"DIRECT_CONTRACT"}],
                    },
                ],
                "terminal_failed_resources":["code:terminal"],
                "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
            },
        }
        out=candidate.solve(public)
        self.assertEqual(out["status"],"ESCALATE",out)
        self.assertEqual(out["reason"],"DERIVED_FAILURE_WITHOUT_VISIBLE_DIRECT_CAUSAL_PREDECESSOR")
        self.assertEqual(out["derived_action_ids"],["A1"])
        self.assertNotIn("repair_targets",out)

    def test_missing_failure_semantics_fails_closed(self):
        case=proof.generate_case(63010,pattern="SINGLE",domain="RESEARCH",kind="SCOPE")
        public=proof.public_task(case)
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False and check["failure_semantics"]=="DIRECT_CONTRACT":
                    del check["failure_semantics"]
                    out=candidate.solve(public)
                    self.assertEqual(out["status"],"FAIL_CLOSED")
                    self.assertEqual(out["reason"],"STEP_SCHEMA_INVALID")
                    return
        self.fail("no direct failed check found")


if __name__=="__main__":
    unittest.main(verbosity=2)
