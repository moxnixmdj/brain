from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_complete_interface_scope_certificate_v1 import (
    REQUIRED_FACTS,
    ROOT,
    derive_interface_facts,
    prove_from_facts,
    verify,
)


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class ToolDiscoveryCompleteInterfaceScopeCertificateV1Tests(unittest.TestCase):
    def setUp(self):
        self.interface = text(
            "canonical/runtime/tool_discovery_complete_interface_instance_v1.py"
        )

    def test_live_exact_sources_derive_scope_atom_candidate(self):
        out = verify()
        self.assertTrue(out["complete_interface_instance_proved"], out)
        self.assertTrue(out["minimum_missing_fact_satisfied_candidate"], out)
        self.assertTrue(out["scope_atom_satisfied_candidate"], out)
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(
            out["target_predicate"], "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
        )
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        good = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(good)["scope_atom_satisfied_candidate"])
        for name in REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = prove_from_facts(mutant)
            self.assertFalse(out["scope_atom_satisfied_candidate"], name)
            self.assertIn(name, out["missing"])

    def test_source_union_mutation_kills_completeness_premise(self):
        mutant = self.interface.replace(
            'if set(owner) != universe:',
            'if False:',
        )
        facts = derive_interface_facts(mutant)
        self.assertFalse(facts["SOURCE_PARTITION_EXACTLY_EQUALS_TOOL_UNIVERSE"])
        facts["PR1100_CONDITIONAL_REFINEMENT_IS_INDEPENDENTLY_VERIFIED"] = True
        facts["FROZEN_TOOL_DISCOVERY_SCOPE_LITERALS_ARE_BOUND"] = True
        self.assertFalse(prove_from_facts(facts)["scope_atom_satisfied_candidate"])

    def test_monotone_union_mutation_kills_discovery_premise(self):
        mutant = self.interface.replace(
            'out["visible_tool_ids"] = sorted(prior | additions)',
            'out["visible_tool_ids"] = sorted(additions)',
        )
        facts = derive_interface_facts(mutant)
        self.assertFalse(facts["DISCOVERY_SESSION_VISIBLE_SET_IS_MONOTONE"])

    def test_out_of_universe_escape_hatch_mutation_kills_closed_world_premise(self):
        mutant = self.interface.replace(
            '"reason": "TOOL_ID_OUTSIDE_CONTENT_ADDRESSED_EPOCH_UNIVERSE"',
            '"reason": "TRY_EXTERNAL_FALLBACK"',
        )
        facts = derive_interface_facts(mutant)
        self.assertFalse(facts["OUT_OF_UNIVERSE_EXECUTION_FAILS_CLOSED"])

    def test_probe_truth_mutation_kills_evidence_premise(self):
        mutant = self.interface.replace(
            '"supported": bool(truth[tid][cap])',
            '"supported": True',
        )
        facts = derive_interface_facts(mutant)
        self.assertFalse(facts["PROBE_RETURNS_EXACT_HIDDEN_TRUTH_AND_BINDS_EPOCH"])

    def test_epoch_fingerprint_mutation_kills_stability_premise(self):
        mutant = self.interface.replace(
            'if supplied != actual:',
            'if False:',
            1,
        )
        facts = derive_interface_facts(mutant)
        self.assertFalse(facts["ACTIVE_EPOCH_MUTATION_FAILS_FINGERPRINT"])

    def test_old_session_reuse_mutation_kills_restart_premise(self):
        mutant = self.interface.replace(
            'if session.get("epoch_fingerprint_sha256") != epoch.get("fingerprint_sha256"):',
            'if False:',
        )
        facts = derive_interface_facts(mutant)
        self.assertFalse(
            facts["VERSION_CHANGE_REQUIRES_NEW_EPOCH_OR_SESSION_RESTART"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
