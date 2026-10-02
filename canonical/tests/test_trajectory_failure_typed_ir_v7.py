from __future__ import annotations

import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof


def derived_only_case():
    return {
        "schema": proof.SCHEMA,
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task": {
            "domain": "CODE",
            "trajectory": [
                {
                    "step": 0,
                    "action_id": "A0",
                    "domain": "CODE",
                    "reads": [],
                    "writes": ["code:upstream"],
                    "depends_on": [],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "INVARIANT",
                        "id": "A0:INVARIANT",
                        "pass": True,
                        "evidence": ["receipt:A0"],
                        "failure_semantics": "DIRECT_CONTRACT",
                    }],
                },
                {
                    "step": 1,
                    "action_id": "A1",
                    "domain": "CODE",
                    "reads": ["code:upstream"],
                    "writes": ["code:symptom"],
                    "depends_on": ["A0"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "SCOPE",
                        "id": "A1:SCOPE",
                        "pass": False,
                        "evidence": ["receipt:A1"],
                        "failure_semantics": "DERIVED_UPSTREAM",
                    }],
                },
                {
                    "step": 2,
                    "action_id": "A2",
                    "domain": "CODE",
                    "reads": ["code:symptom"],
                    "writes": ["code:terminal"],
                    "depends_on": ["A1"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "INVARIANT",
                        "id": "A2:INVARIANT",
                        "pass": True,
                        "evidence": ["receipt:A2"],
                        "failure_semantics": "DIRECT_CONTRACT",
                    }],
                },
            ],
            "terminal_failed_resources": ["code:terminal"],
            "goal": "LOCALIZE_CAUSAL_ROOT",
        },
    }


class Tests(unittest.TestCase):
    def test_full_192_case_cross_product_passes_with_forward_state_replay(self):
        cases = proof.suite_cases()
        self.assertEqual(len(cases), 192)
        rescued = 0
        ambiguous = 0
        for case in cases:
            public = proof.public_task(case)
            self.assertNotIn("_oracle", public)
            out = candidate.solve(public)
            verdict = proof.score_case(case, out)
            self.assertTrue(verdict.get("pass"), (case["seed"], out, verdict))
            if case["_oracle"]["status"] == "AMBIGUOUS":
                ambiguous += 1
                self.assertFalse(verdict["intervention_rescue_verified"])
                self.assertGreaterEqual(len(verdict["alternative_rescuers"]), 2)
            else:
                rescued += 1
                self.assertTrue(verdict["intervention_rescue_verified"])
                self.assertTrue(verdict["intervention"]["terminal_rescued"])
                self.assertFalse(
                    all(verdict["intervention"]["baseline_terminal_resource_validity"].values())
                )
                self.assertTrue(
                    all(verdict["intervention"]["terminal_resource_validity"].values())
                )
        self.assertEqual(rescued, 144)
        self.assertEqual(ambiguous, 48)

    def test_v6_derived_only_counterexample_now_escalates_without_repair(self):
        public = derived_only_case()
        out = candidate.solve(public)
        self.assertEqual(out["status"], "ESCALATE", out)
        self.assertEqual(out["reason"], "DERIVED_FAILURE_WITHOUT_VISIBLE_DIRECT_CAUSE")
        self.assertNotIn("repair_targets", out)

    def test_missing_failure_semantics_fails_closed(self):
        case = proof.generate_case(73001, pattern="SINGLE", domain="CODE", kind="SCOPE")
        public = proof.public_task(case)
        del public["task"]["trajectory"][1]["checks"][1]["failure_semantics"]
        out = candidate.solve(public)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_partial_conjunctive_repair_does_not_rescue(self):
        case = proof.generate_case(73002, pattern="INTERACTION", domain="TOOL_API", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"], "INTERACTION")
        partial = {"repair_targets": out["repair_targets"][:1]}
        iv = proof.execute_intervention(proof.public_task(case), partial)
        self.assertFalse(iv["terminal_rescued"], iv)
        self.assertFalse(all(iv["terminal_resource_validity"].values()))

    def test_symptom_only_repair_does_not_rescue(self):
        case = proof.generate_case(73003, pattern="DELAYED", domain="BROWSER", kind="AUTHORITY")
        public = proof.public_task(case)
        iv = proof.execute_intervention(public, {"repair_targets": ["restore:A4:INVARIANT"]})
        self.assertFalse(iv["terminal_rescued"], iv)
        self.assertEqual(iv["matched_relevant_direct_repairs"], [])

    def test_orphan_terminal_resource_cannot_rescue(self):
        case = proof.generate_case(73004, pattern="SINGLE", domain="FILESYSTEM", kind="PROVENANCE")
        public = proof.public_task(case)
        out = candidate.solve(public)
        public["task"]["terminal_failed_resources"] = ["filesystem:orphan"]
        iv = proof.execute_intervention(public, out)
        self.assertFalse(iv["terminal_rescued"], iv)
        self.assertEqual(iv["reason"], "TERMINAL_RESOURCE_HAS_NO_WRITER")

    def test_removed_terminal_writer_cannot_rescue(self):
        case = proof.generate_case(73005, pattern="DELAYED", domain="CODE", kind="SCOPE")
        public = proof.public_task(case)
        out = candidate.solve(public)
        terminal = public["task"]["terminal_failed_resources"][0]
        public["task"]["trajectory"] = [
            row for row in public["task"]["trajectory"]
            if terminal not in row["writes"]
        ]
        iv = proof.execute_intervention(public, out)
        self.assertFalse(iv["terminal_rescued"], iv)
        self.assertEqual(iv["reason"], "TERMINAL_RESOURCE_HAS_NO_WRITER")

    def test_irrelevant_repair_token_cannot_create_rescue(self):
        case = proof.generate_case(73006, pattern="SINGLE", domain="ARTIFACT", kind="SCHEMA")
        public = proof.public_task(case)
        iv = proof.execute_intervention(
            public, {"repair_targets": ["restore:A999:SCHEMA"]}
        )
        self.assertFalse(iv["terminal_rescued"], iv)
        self.assertEqual(iv["matched_relevant_direct_repairs"], [])

    def test_alternative_single_branch_repairs_are_independent_rescuers(self):
        case = proof.generate_case(73007, pattern="AMBIGUOUS", domain="RESEARCH", kind="SCOPE")
        public = proof.public_task(case)
        out = candidate.solve(public)
        self.assertEqual(out["status"], "AMBIGUOUS", out)
        self.assertEqual(len(out["candidates"]), 2)
        baseline = proof.execute_intervention(public, {"repair_targets": []})
        self.assertFalse(baseline["terminal_rescued"], baseline)
        for item in out["candidates"]:
            iv = proof.execute_intervention(
                public, {"repair_targets": item["repair_targets"]}
            )
            self.assertTrue(iv["terminal_rescued"], (item, iv))

    def test_severed_original_causal_path_prevents_credit_for_old_root_repair(self):
        case = proof.generate_case(73008, pattern="SINGLE", domain="CODE", kind="SCOPE")
        public = proof.public_task(case)
        out = candidate.solve(public)
        terminal = public["task"]["terminal_failed_resources"][0]
        writer = next(row for row in public["task"]["trajectory"] if terminal in row["writes"])
        writer["reads"] = []
        writer["depends_on"] = []
        iv = proof.execute_intervention(public, out)
        self.assertFalse(iv["terminal_rescued"], iv)
        self.assertFalse(iv["terminal_was_failed_before_intervention"], iv)

    def test_hidden_oracle_mutation_cannot_change_candidate_payload(self):
        case = proof.generate_case(73009, pattern="SINGLE", domain="ARTIFACT", kind="SCOPE")
        before = proof.public_task(case)
        case["_oracle"]["critical"] = "A999"
        case["_oracle"]["roots"] = ["A999"]
        after = proof.public_task(case)
        self.assertEqual(before, after)

    def test_direct_failure_requires_visible_receipts(self):
        case = proof.generate_case(73010, pattern="SINGLE", domain="RESEARCH", kind="PROVENANCE")
        public = proof.public_task(case)
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False and check["failure_semantics"] == "DIRECT_CONTRACT":
                    check["evidence"] = []
        out = candidate.solve(public)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
