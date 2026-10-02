from __future__ import annotations
import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as v6_candidate
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof


class Tests(unittest.TestCase):
    def test_preserves_full_verified_v6_192_case_envelope(self):
        failures = []
        rescued = 0
        ambiguous = 0
        for case in proof.suite_cases():
            out = candidate.solve(proof.public_task(case))
            verdict = proof.score_case(case, out)
            if verdict.get("pass") is not True:
                failures.append((case.get("seed"), verdict, out))
            elif case["_oracle"]["status"] == "AMBIGUOUS":
                ambiguous += 1
            else:
                rescued += 1
        self.assertEqual(failures, [])
        self.assertEqual(rescued, 144)
        self.assertEqual(ambiguous, 48)

    def test_derived_only_failure_abstains_in_all_domains(self):
        for domain in proof.DOMAINS:
            public = proof.derived_only_case(domain)
            old = v6_candidate.solve(public)
            self.assertEqual(old["status"], "IDENTIFIED")
            out = candidate.solve(public)
            verdict = proof.score_derived_only(out)
            self.assertTrue(verdict["pass"], (domain, out, verdict))
            self.assertEqual(out["status"], "ESCALATE")

    def test_serial_direct_cofault_preserves_both_repairs_in_all_domains(self):
        for domain in proof.DOMAINS:
            public = proof.serial_direct_cofault_case(domain)
            old = v6_candidate.solve(public)
            old_iv = proof.execute_intervention(public, old)
            self.assertFalse(old_iv["terminal_rescued"], (domain, old, old_iv))
            out = candidate.solve(public)
            verdict = proof.score_serial_direct_cofault(out, domain=domain)
            self.assertTrue(verdict["pass"], (domain, out, verdict))
            self.assertEqual(out["repair_targets"], ["restore:A1:AUTHORITY", "restore:A2:SCOPE"])

    def test_missing_failure_semantics_fails_closed(self):
        public = proof.serial_direct_cofault_case()
        attacked = copy.deepcopy(public)
        for row in attacked["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    check.pop("failure_semantics", None)
                    out = candidate.solve(attacked)
                    self.assertEqual(out["status"], "FAIL_CLOSED")
                    return
        self.fail("no failed check found")

    def test_derived_symptom_is_not_in_repair_cutset(self):
        public = proof.serial_direct_cofault_case()
        out = candidate.solve(public)
        self.assertNotIn("restore:A3:INVARIANT", out["repair_targets"])
        self.assertEqual(out["cause_action_ids"], ["A1", "A2"])

    def test_v6_scope_counterexamples_are_both_killed(self):
        d = candidate.solve(proof.derived_only_case())
        s = candidate.solve(proof.serial_direct_cofault_case())
        self.assertEqual(d["status"], "ESCALATE")
        self.assertTrue(proof.score_derived_only(d)["pass"])
        self.assertEqual(s["status"], "INTERACTION")
        self.assertTrue(proof.score_serial_direct_cofault(s)["pass"])

    def test_no_terminal_or_family_credit_is_embedded_in_candidate(self):
        # Candidate output is diagnostic only. It contains no acceptance authority fields.
        out = candidate.solve(proof.serial_direct_cofault_case())
        forbidden = {"capability_credit_delta", "family_credit_delta", "execution_authority", "promotion_authority"}
        self.assertFalse(forbidden & set(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
