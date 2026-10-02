from __future__ import annotations
import copy
import unittest

from canonical.runtime.p1_composite_proof_role_verifier_v1 import CANDIDATE, evaluate, load


class P1CompositeProofRoleVerifierTests(unittest.TestCase):
    def candidate(self):
        return load(CANDIDATE)

    def test_live_candidate_is_lift_eligible_but_not_lifted(self):
        out = evaluate(self.candidate())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["quarantine_lift_eligible"])
        self.assertFalse(out["quarantine_resolved"])
        self.assertEqual(out["required_check_count"], 8)
        self.assertEqual(out["required_mutation_count"], 9)

    def test_missing_check_fails_closed(self):
        c = copy.deepcopy(self.candidate())
        c["proof_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"].pop()
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertIn("CHECK_PARTITION_NOT_EXACT_FROZEN_SET", out["errors"])

    def test_cross_role_overlap_fails_closed(self):
        c = copy.deepcopy(self.candidate())
        x = c["proof_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"][0]
        c["proof_roles"]["T0_T2_TERMINAL_INTERVENTION_RESCUE"].append(x)
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertTrue(any(e.startswith("CHECK_CROSS_ROLE_OVERLAP:") for e in out["errors"]))

    def test_unfalsifiable_diagnosis_must_stay_on_v4_side(self):
        c = copy.deepcopy(self.candidate())
        c["mutation_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"].remove("UNFALSIFIABLE_DIAGNOSIS")
        c["mutation_roles"]["T0_T2_TERMINAL_INTERVENTION_RESCUE"].append("UNFALSIFIABLE_DIAGNOSIS")
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertIn("UNFALSIFIABLE_DIAGNOSIS_NOT_ASSIGNED_TO_V4_HIDDEN_ORACLE_PROOF", out["errors"])
        self.assertIn("UNFALSIFIABLE_DIAGNOSIS_STILL_ASSIGNED_TO_NARROW_TERMINAL_SCORER", out["errors"])

    def test_authority_blob_mutation_fails_closed(self):
        c = copy.deepcopy(self.candidate())
        c["authority"]["v4_proof"]["git_blob_sha"] = "0" * 40
        out = evaluate(c)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_BLOB_MISMATCH:v4_proof", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
