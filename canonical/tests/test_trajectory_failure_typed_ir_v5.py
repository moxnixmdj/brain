from __future__ import annotations

import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof


class TrajectoryFailureTypedIRV5Tests(unittest.TestCase):
    def test_full_192_case_scope_rescue_matrix_passes(self):
        cases = proof.suite_cases()
        self.assertEqual(len(cases), 192)
        failed = []
        for case in cases:
            out = candidate.solve(proof.public_task(case))
            scored = proof.score_case(case, out)
            if scored.get("pass") is not True:
                failed.append((case["seed"], case["_oracle"]["status"], scored))
        self.assertEqual(failed, [])

    def test_public_payload_hides_intervention_worlds(self):
        case = proof.generate_case(7001, pattern="DELAYED", domain="CODE", kind="SCOPE")
        public = proof.public_task(case)
        self.assertNotIn("_oracle", public)
        self.assertNotIn("intervention_worlds", repr(public))
        self.assertIn("intervention_worlds", case["_oracle"])

    def test_scope_is_first_class_and_never_inferred_from_authority(self):
        case = proof.generate_case(7002, pattern="SINGLE", domain="BROWSER", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"], "IDENTIFIED")
        self.assertEqual(out["mechanism_classes"], ["SCOPE"])
        self.assertEqual(out["repair_targets"], ["restore:A1:SCOPE"])
        self.assertTrue(proof.score_case(case, out)["pass"])

        authority_case = copy.deepcopy(case)
        for row in authority_case["task"]["trajectory"]:
            for check in row["checks"]:
                if check["kind"] == "SCOPE":
                    check["kind"] = "AUTHORITY"
                    check["id"] = check["id"].replace(":SCOPE", ":AUTHORITY")
        authority_case["_oracle"]["mechanisms"]["A1"] = ["AUTHORITY"]
        authority_case["_oracle"]["intervention_worlds"] = [["restore:A1:AUTHORITY"]]
        authority_out = candidate.solve(proof.public_task(authority_case))
        self.assertEqual(authority_out["mechanism_classes"], ["AUTHORITY"])
        self.assertNotIn("SCOPE", authority_out["mechanism_classes"])

    def test_delayed_scope_repair_rescues_hidden_terminal_world(self):
        case = proof.generate_case(7003, pattern="DELAYED", domain="TOOL_API", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        self.assertEqual(out["cause_action_id"], "A1")
        self.assertTrue(
            proof._intervention_outcome(case, out["repair_targets"])["all_worlds_rescued"]
        )
        self.assertFalse(
            proof._intervention_outcome(case, ["restore:A4:INVARIANT"])["all_worlds_rescued"]
        )
        self.assertTrue(proof.score_case(case, out)["pass"])

    def test_interaction_requires_full_conjunctive_repair(self):
        case = proof.generate_case(7004, pattern="INTERACTION", domain="ARTIFACT", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"], "INTERACTION")
        repairs = out["repair_targets"]
        self.assertGreaterEqual(len(repairs), 2)
        self.assertTrue(proof._intervention_outcome(case, repairs)["all_worlds_rescued"])
        for token in repairs:
            self.assertFalse(
                proof._intervention_outcome(case, [token])["all_worlds_rescued"]
            )
        self.assertTrue(proof.score_case(case, out)["pass"])

    def test_ambiguous_repairs_rescue_some_but_not_all_hidden_worlds(self):
        case = proof.generate_case(7005, pattern="AMBIGUOUS", domain="RESEARCH", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"], "AMBIGUOUS")
        self.assertIsNone(out["cause_action_id"])
        union = []
        for row in out["candidates"]:
            repairs = row["repair_targets"]
            result = proof._intervention_outcome(case, repairs)
            self.assertTrue(result["any_world_rescued"])
            self.assertFalse(result["all_worlds_rescued"])
            union.extend(repairs)
        self.assertTrue(proof._intervention_outcome(case, union)["all_worlds_rescued"])
        self.assertTrue(proof.score_case(case, out)["pass"])

    def test_scope_cross_product_has_24_cases_and_all_pass(self):
        scope_cases = [
            case for case in proof.suite_cases()
            if "SCOPE" in {
                kind
                for kinds in case["_oracle"]["mechanisms"].values()
                for kind in kinds
            }
        ]
        self.assertGreaterEqual(len(scope_cases), 24)
        primary_scope = []
        for domain in proof.DOMAINS:
            for pattern in ("SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS"):
                case = proof.generate_case(8000 + len(primary_scope), pattern=pattern, domain=domain, kind="SCOPE")
                primary_scope.append(case)
                out = candidate.solve(proof.public_task(case))
                self.assertTrue(proof.score_case(case, out)["pass"])
        self.assertEqual(len(primary_scope), 24)


if __name__ == "__main__":
    unittest.main(verbosity=2)
