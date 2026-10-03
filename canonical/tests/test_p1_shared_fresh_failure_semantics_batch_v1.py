from __future__ import annotations
import copy
import unittest

from canonical.runtime import p1_shared_fresh_failure_semantics_batch_v1 as batch
from canonical.runtime.trajectory_failure_typed_ir_candidate_v7 import solve
from canonical.runtime.trajectory_failure_typed_ir_proof_v6 import score_case


class Tests(unittest.TestCase):
    BEACON="0123456789abcdef"*4

    def test_prefreeze_source_and_policy_obligations(self):
        out=batch.prefreeze_check()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["case_count_after_beacon"],96)
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["new_reality_units_consumed"],0)

    def test_complete_3x8x4_matrix(self):
        ids=set()
        for s in batch.SURFACES:
            for k in batch.KINDS:
                for p in batch.PATTERNS:
                    case=batch.generate_case(self.BEACON,s,k,p)
                    ids.add(case["cell_id"])
        self.assertEqual(len(ids),96)

    def test_same_beacon_is_deterministic_and_new_beacon_changes_structure(self):
        a=batch.generate_case(self.BEACON,batch.SURFACES[0],"AUTHORITY","DELAYED")
        b=batch.generate_case(self.BEACON,batch.SURFACES[0],"AUTHORITY","DELAYED")
        c=batch.generate_case("fedcba9876543210"*4,batch.SURFACES[0],"AUTHORITY","DELAYED")
        self.assertEqual(a,b)
        self.assertNotEqual(a["seed"],c["seed"])
        self.assertNotEqual(
            [x["writes"] for x in a["task"]["trajectory"]],
            [x["writes"] for x in c["task"]["trajectory"]],
        )

    def test_instrumentation_origin_is_not_candidate_visible(self):
        case=batch.generate_case(self.BEACON,batch.SURFACES[0],"SCHEMA","SINGLE")
        public=batch.public_case(case)
        self.assertNotIn("_oracle",public)
        raw=repr(public)
        self.assertNotIn("_instrumentation_failure_origin",raw)
        self.assertIn("failure_semantics",raw)

    def test_semantics_are_both_present_and_failed_checks_have_evidence(self):
        case=batch.generate_case(self.BEACON,batch.SURFACES[0],"PROVENANCE","DELAYED")
        semantics=set()
        for row in case["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    semantics.add(check["failure_semantics"])
                    self.assertTrue(check["evidence"])
        self.assertEqual(semantics,{"DIRECT_CONTRACT","DERIVED_UPSTREAM"})

    def test_exact_v7_candidate_and_unchanged_v6_scorer_pass_every_cell(self):
        for s in batch.SURFACES:
            for k in batch.KINDS:
                for p in batch.PATTERNS:
                    with self.subTest(surface=s,kind=k,pattern=p):
                        case=batch.generate_case(self.BEACON,s,k,p)
                        candidate=solve(batch.public_case(case))
                        verdict=score_case(case,candidate)
                        self.assertTrue(verdict["pass"],(case,candidate,verdict))

    def test_semantics_mapping_is_load_bearing(self):
        case=batch.generate_case(self.BEACON,batch.SURFACES[0],"AUTHORITY","SINGLE")
        mutant=copy.deepcopy(case)
        changed=False
        for row in mutant["task"]["trajectory"]:
            for check in row["checks"]:
                if check.get("pass") is False and check.get("failure_semantics")=="DIRECT_CONTRACT":
                    check["failure_semantics"]="DERIVED_UPSTREAM"
                    changed=True
                    break
            if changed:
                break
        self.assertTrue(changed)
        candidate=solve(batch.public_case(mutant))
        verdict=score_case(mutant,candidate)
        self.assertFalse(verdict["pass"],(candidate,verdict))

    def test_batch_execution_function_never_self_authorizes_terminal_credit(self):
        out=batch.run_batch(self.BEACON)
        self.assertEqual(out["case_count"],96)
        self.assertTrue(out["matrix_complete"])
        self.assertTrue(out["all_cases_pass"],out)
        self.assertFalse(out["terminal_credit_authorized"])
        self.assertEqual(out["new_reality_units_claimed"],0)
        self.assertFalse(out["execution_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
