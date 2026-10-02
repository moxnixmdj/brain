from __future__ import annotations

import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof


class Tests(unittest.TestCase):
    def test_full_192_case_cross_product_passes(self):
        cases = proof.suite_cases()
        self.assertEqual(len(cases), 192)
        failures = []
        for case in cases:
            out = candidate.solve(proof.public_task(case))
            verdict = proof.score_case(case, out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"], case["_oracle"], verdict, out))
        self.assertEqual(failures, [])

    def test_scope_is_first_class_across_all_domains_and_patterns(self):
        cases = [
            c for c in proof.suite_cases()
            if c["_causal_model"]["local_faults"].get("A1") == "SCOPE"
        ]
        self.assertEqual(len(cases), 24)
        self.assertEqual({c["task"]["domain"] for c in cases}, set(proof.DOMAINS))
        self.assertEqual(
            {c["_oracle"]["status"] for c in cases},
            {"IDENTIFIED", "INTERACTION", "AMBIGUOUS"},
        )
        for case in cases:
            out = candidate.solve(proof.public_task(case))
            self.assertTrue(proof.score_case(case, out)["pass"])

    def test_replay_recomputes_terminal_and_is_not_oracle_lookup(self):
        case = proof.generate_case(81001, pattern="DELAYED", domain="CODE", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        repairs = list(out["repair_targets"])
        before = proof.replay_terminal(case, [])
        rescued = proof.replay_terminal(case, repairs)
        self.assertTrue(before["terminal_failed"])
        self.assertFalse(rescued["terminal_failed"])

        mutated = copy.deepcopy(case)
        mutated["_oracle"] = {
            "status": "AMBIGUOUS",
            "roots": ["A999"],
            "critical": None,
            "mechanisms": {"A999": ["AUTHORITY"]},
            "minimal_rescuing_repair_sets": [["restore:A999:AUTHORITY"]],
            "baseline_terminal_failed": True,
        }
        self.assertEqual(
            proof.replay_terminal(mutated, repairs)["terminal_failed"],
            rescued["terminal_failed"],
        )

    def test_scope_to_authority_repair_does_not_clear_scope_fault(self):
        case = proof.generate_case(81002, pattern="SINGLE", domain="BROWSER", kind="SCOPE")
        self.assertTrue(proof.replay_terminal(case, [])["terminal_failed"])
        self.assertTrue(
            proof.replay_terminal(case, ["restore:A1:AUTHORITY"])["terminal_failed"]
        )
        self.assertFalse(
            proof.replay_terminal(case, ["restore:A1:SCOPE"])["terminal_failed"]
        )

    def test_delayed_symptom_only_repair_does_not_rescue(self):
        case = proof.generate_case(
            81003, pattern="DELAYED", domain="FILESYSTEM", kind="PROVENANCE"
        )
        symptoms = proof._symptom_repairs(case)
        self.assertTrue(symptoms)
        self.assertTrue(proof.replay_terminal(case, symptoms)["terminal_failed"])

    def test_interaction_requires_complete_root_repair_set(self):
        case = proof.generate_case(
            81004, pattern="INTERACTION", domain="TOOL_API", kind="SCOPE"
        )
        rescuers = case["_oracle"]["minimal_rescuing_repair_sets"]
        self.assertEqual(len(rescuers), 1)
        repairs = rescuers[0]
        self.assertEqual(len(repairs), 2)
        self.assertFalse(proof.replay_terminal(case, repairs)["terminal_failed"])
        for repair in repairs:
            self.assertTrue(proof.replay_terminal(case, [repair])["terminal_failed"])

    def test_ambiguous_case_has_multiple_single_repair_rescuers(self):
        case = proof.generate_case(
            81005, pattern="AMBIGUOUS", domain="ARTIFACT", kind="SCOPE"
        )
        rescuers = case["_oracle"]["minimal_rescuing_repair_sets"]
        self.assertGreaterEqual(len(rescuers), 2)
        self.assertTrue(all(len(x) == 1 for x in rescuers))
        for repair_set in rescuers:
            self.assertFalse(
                proof.replay_terminal(case, repair_set)["terminal_failed"]
            )
        out = candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"], "AMBIGUOUS")
        self.assertTrue(proof.score_case(case, out)["pass"])

    def test_hidden_model_and_oracle_never_enter_public_payload(self):
        case = proof.generate_case(
            81006, pattern="INTERACTION", domain="RESEARCH", kind="DEPENDENCY"
        )
        public = proof.public_task(case)
        self.assertNotIn("_causal_model", public)
        self.assertNotIn("_oracle", public)
        blob = repr(public)
        self.assertNotIn("minimal_rescuing_repair_sets", blob)
        self.assertNotIn("local_faults", blob)

    def test_drop_failed_check_receipts_fails_closed(self):
        case = proof.generate_case(
            81007, pattern="SINGLE", domain="RESEARCH", kind="SCOPE"
        )
        public = copy.deepcopy(proof.public_task(case))
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    check["evidence"] = []
        out = candidate.solve(public)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(proof.score_case(case, out)["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
