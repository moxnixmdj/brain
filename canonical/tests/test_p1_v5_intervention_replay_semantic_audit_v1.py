from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_v5_intervention_replay_semantic_audit_v1 as audit
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof


class P1V5InterventionReplaySemanticAuditTests(unittest.TestCase):
    def test_audit_reproduces_all_counterexamples(self):
        out = audit.audit()
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertTrue(out["baseline_valid"])
        self.assertTrue(out["all_counterexamples_reproduced"])
        self.assertEqual(out["counterexample_count"], 4)
        self.assertFalse(out["v5_heterogeneous_intervention_rescue_semantics_valid"])
        self.assertFalse(out["p1_scope_quarantine_clearable_from_v5"])

    def test_rescue_function_is_invariant_to_trajectory_deletion(self):
        case = proof.generate_case(88101, pattern="SINGLE", domain="CODE", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        repairs = out["repair_targets"]
        before = proof.evaluate_intervention(case, repairs)
        mutated = copy.deepcopy(case)
        mutated["task"]["trajectory"] = []
        after = proof.evaluate_intervention(mutated, repairs)
        self.assertTrue(before["rescued"])
        self.assertTrue(after["rescued"])
        self.assertEqual(before, after)

    def test_score_still_passes_when_terminal_resource_has_no_producer(self):
        case = proof.generate_case(88102, pattern="DELAYED", domain="BROWSER", kind="AUTHORITY")
        output = candidate.solve(proof.public_task(case))
        self.assertTrue(proof.score_case(case, output)["pass"])
        mutated = copy.deepcopy(case)
        mutated["task"]["terminal_failed_resources"] = ["browser:never_produced"]
        verdict = proof.score_case(mutated, output)
        self.assertTrue(verdict["pass"], verdict)

    def test_score_still_passes_when_entire_trajectory_is_removed(self):
        case = proof.generate_case(88103, pattern="INTERACTION", domain="TOOL_API", kind="DEPENDENCY")
        output = candidate.solve(proof.public_task(case))
        self.assertTrue(proof.score_case(case, output)["pass"])
        mutated = copy.deepcopy(case)
        mutated["task"]["trajectory"] = []
        verdict = proof.score_case(mutated, output)
        self.assertTrue(verdict["pass"], verdict)

    def test_audit_grants_no_credit_or_authority(self):
        out = audit.audit()
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
