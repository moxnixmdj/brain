from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_universal_scope_certificate_v2 import (
    REQUIRED_FACTS,
    derive_source_facts,
    prove_from_facts,
    verify,
    _text,
)


class ToolDiscoveryUniversalScopeCertificateV2Tests(unittest.TestCase):
    def setUp(self):
        self.interface = _text("canonical/runtime/tool_discovery_common_authority_interface_v1.py")
        self.v4 = _text("canonical/runtime/tool_discovery_dynamic_candidate_v4.py")

    def test_live_sources_derive_candidate_universal_scope_proof(self):
        out = verify()
        self.assertTrue(out["universal_scope_proved"], out)
        self.assertTrue(out["scope_atom_satisfied_candidate"])
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"], "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"], 0)
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

    def test_interface_coverage_mutation_kills_scope_proof(self):
        mutant = self.interface.replace(
            "for i, row in enumerate(authority):",
            "for i, row in enumerate(authority[:-1]):",
        )
        facts = derive_source_facts(mutant, self.v4)
        self.assertFalse(facts["COMMON_AUTHORITY_PARTITION_COVERS_EVERY_IDENTITY"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_interface_union_check_mutation_kills_scope_proof(self):
        mutant = self.interface.replace(
            "if union_ids != authority_ids:",
            "if False:",
        )
        facts = derive_source_facts(mutant, self.v4)
        self.assertFalse(facts["COMMON_AUTHORITY_VALIDATOR_REQUIRES_EXACT_UNION"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_outside_action_authority_mutation_kills_scope_proof(self):
        mutant = self.interface.replace(
            "return str(tool_id) in ids",
            "return True",
        )
        facts = derive_source_facts(mutant, self.v4)
        self.assertFalse(facts["OUTSIDE_COMMON_AUTHORITY_NOT_INVOCABLE"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_capability_leak_guard_mutation_kills_scope_proof(self):
        mutant = self.interface.replace(
            'FORBIDDEN_DISCOVERY_FIELDS = ("capabilities", "supports", "required_capabilities", "oracle")',
            "FORBIDDEN_DISCOVERY_FIELDS = ()",
        )
        facts = derive_source_facts(mutant, self.v4)
        self.assertFalse(facts["COMMON_AUTHORITY_VALIDATOR_REJECTS_CAPABILITY_TRUTH_LEAK"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_v4_discovery_before_commitment_mutation_kills_scope_proof(self):
        marker = '''    queried=_queried_sources(public)
    sources=[s for s in public.get("discovery_sources",[])
'''
        replacement = '''    constraint=public.get("constraint"); evidence=_evidence(public)
    queried=_queried_sources(public)
    sources=[s for s in public.get("discovery_sources",[])
'''
        mutant = self.v4.replace(marker, replacement)
        facts = derive_source_facts(self.interface, mutant)
        self.assertFalse(facts["V4_DISCOVERY_PRECEDES_EVIDENCE_ROUTE_COMMITMENT"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
