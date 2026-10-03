from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.delegation_universal_scope_certificate_v2 import (
    REQUIRED_FACTS,
    ROOT,
    derive_source_facts,
    prove_from_facts,
    verify,
)


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class DelegationUniversalScopeCertificateV2Tests(unittest.TestCase):
    def setUp(self):
        self.v4 = text("canonical/runtime/delegation_receipt_history_candidate_v4.py")
        self.v2 = text("canonical/runtime/delegation_whole_scope_candidate_v2.py")
        self.oracle = text("canonical/runtime/delegation_whole_scope_proof_v2.py")

    def test_live_exact_sources_derive_candidate_universal_scope_proof(self):
        out = verify()
        self.assertTrue(out["universal_scope_proved"])
        self.assertTrue(out["scope_atom_satisfied_candidate"])
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"], "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        good = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(good)["universal_scope_proved"])
        for name in REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = prove_from_facts(mutant)
            self.assertFalse(out["universal_scope_proved"], name)
            self.assertIn(name, out["missing"])

    def test_history_append_mutation_kills_induction_premise(self):
        mutant = self.v4.replace("history.append(current)", "history = [current]")
        facts = derive_source_facts(mutant, self.v2, self.oracle)
        self.assertFalse(facts["V4_FULL_HISTORY_REPLAY_FROM_BASE"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_worker_union_mutation_kills_persistence_premise(self):
        mutant = self.v4.replace(
            "unavailable_workers.add(entity)",
            "unavailable_workers = {entity}",
        )
        facts = derive_source_facts(mutant, self.v2, self.oracle)
        self.assertFalse(facts["V4_DISABLE_EFFECTS_ARE_IDEMPOTENT_SET_UNIONS"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_resource_update_mutation_kills_ordered_state_premise(self):
        mutant = self.v4.replace(
            'resource_caps[entity] = receipt["capacity"]',
            'resource_caps.setdefault(entity, receipt["capacity"])',
        )
        facts = derive_source_facts(mutant, self.v2, self.oracle)
        self.assertFalse(facts["V4_RESOURCE_STATE_IS_ORDERED_LAST_WRITE"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_exact_v2_schedulability_gate_is_load_bearing(self):
        mutant = self.v2.replace(
            "_schedule(list(seq),deps,steps,workers,caps)",
            "None",
        )
        facts = derive_source_facts(self.v4, mutant, self.oracle)
        self.assertFalse(facts["V2_GOAL_REQUIRES_SCHEDULABILITY"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_oracle_exhaustiveness_is_load_bearing(self):
        mutant = self.oracle.replace(
            "for order in permutations(subset):",
            "for order in [subset]:",
        )
        facts = derive_source_facts(self.v4, self.v2, mutant)
        self.assertFalse(facts["ORACLE_ENUMERATES_ALL_SUBSETS_AND_PERMUTATIONS"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
