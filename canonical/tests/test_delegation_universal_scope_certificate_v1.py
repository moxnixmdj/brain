from __future__ import annotations

import unittest

from canonical.runtime.delegation_universal_scope_certificate_v1 import (
    REQUIRED_FACTS,
    ROOT,
    derive_source_facts,
    prove_from_facts,
    verify,
)


class DelegationUniversalScopeCertificateTests(unittest.TestCase):
    def test_live_exact_sources_derive_universal_candidate(self):
        out = verify()
        self.assertTrue(out["universal_scope_proved"])
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"], "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        self.assertEqual(out["new_reality_units"], 0)
        self.assertEqual(out["terminal_cases_replayed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        baseline = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(baseline)["universal_scope_proved"])
        for name in REQUIRED_FACTS:
            facts = dict(baseline)
            facts[name] = False
            out = prove_from_facts(facts)
            self.assertFalse(out["universal_scope_proved"], name)
            self.assertIn(name, out["missing"])

    def test_sequence_reuse_mutation_kills_finiteness_premise(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = candidate.replace("if sid in used:", "if False:")
        facts = derive_source_facts(mutant, oracle)
        self.assertFalse(facts["FINITE_SIMPLE_SEQUENCE_SEARCH"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_negative_cost_firewall_mutation_kills_optimality_premise(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = candidate.replace("float(cost)<0", "False")
        facts = derive_source_facts(mutant, oracle)
        self.assertFalse(facts["NONNEGATIVE_FINITE_STEP_COSTS_ENFORCED"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_schedulability_gate_mutation_kills_scope_proof(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = candidate.replace(
            "_schedule(list(seq),deps,steps,workers,caps)",
            "None",
        )
        facts = derive_source_facts(mutant, oracle)
        self.assertFalse(facts["GOAL_REQUIRES_SCHEDULABILITY_BEFORE_RETURN"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_oracle_exhaustiveness_mutation_kills_equivalence_premise(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = oracle.replace(
            "for order in permutations(subset):",
            "for order in [subset]:",
        )
        facts = derive_source_facts(candidate, mutant)
        self.assertFalse(
            facts["EXHAUSTIVE_ORACLE_ENUMERATES_ALL_SUBSETS_AND_PERMUTATIONS"]
        )
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_empirical_sample_is_not_a_premise(self):
        out = verify()
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["uses_new_acceptance_cases"])


if __name__ == "__main__":
    unittest.main()
