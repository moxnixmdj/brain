from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_common_authority_interface_certificate_v1 as cert


class CommonAuthorityInterfaceCertificateV1Tests(unittest.TestCase):
    def test_live_exact_sources_derive_candidate_complete_interface(self):
        out=cert.verify()
        self.assertEqual(out["source_blob_drift"],[],out)
        self.assertTrue(out["interface_instance_verified_candidate"],out)
        self.assertTrue(out["interface_contract_satisfied_candidate"],out)
        self.assertTrue(out["universal_scope_atom_satisfied_candidate"],out)
        self.assertEqual(out["scope_relation"],"PROVEN_STRONGER")
        self.assertEqual(
            out["basis"],
            "PARAMETRIC_COMPLETE_INTERFACE_OVER_ANY_FINITE_COMMON_FROZEN_AUTHORITY",
        )
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["uses_brain_only_registry"])
        self.assertFalse(out["preenumerates_tool_identities"])
        self.assertEqual(out["terminal_cases_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        good={name:True for name in cert.REQUIRED_FACTS}
        self.assertTrue(cert.prove_from_facts(good)["interface_instance_verified_candidate"])
        for name in cert.REQUIRED_FACTS:
            mutant=dict(good)
            mutant[name]=False
            out=cert.prove_from_facts(mutant)
            self.assertFalse(out["interface_instance_verified_candidate"],name)
            self.assertIn(name,out["missing"])

    def test_exact_authority_return_mutation_kills_completeness_fact(self):
        src=cert._text(cert.INTERFACE)
        mutant=src.replace(
            '"tools":deepcopy(frozen["public_tools"])',
            '"tools":[]',
            1,
        )
        facts=cert.derive_interface_facts(mutant)
        self.assertFalse(facts["DISCOVERY_RETURNS_EXACT_PUBLIC_AUTHORITY_MANIFEST"])

    def test_hidden_truth_probe_mutation_kills_truthfulness_fact(self):
        src=cert._text(cert.INTERFACE)
        mutant=src.replace(
            '"supported":cap in truth',
            '"supported":True',
            1,
        )
        facts=cert.derive_interface_facts(mutant)
        self.assertFalse(facts["SAFE_PROBE_SUPPORT_DERIVED_FROM_HIDDEN_TRUTH"])

    def test_stale_episode_guard_mutation_kills_temporal_fact(self):
        src=cert._text(cert.INTERFACE)
        mutant=src.replace(
            '"STALE_EPISODE_RESTART_REQUIRED"',
            '"STALE_EPISODE_ALLOWED"',
        )
        facts=cert.derive_interface_facts(mutant)
        self.assertFalse(facts["STALE_EPISODE_REQUIRES_RESTART"])

    def test_hardcoded_tool_identity_kills_parametricity_fact(self):
        src=cert._text(cert.INTERFACE)+'\nSPECIAL_CASE="T0"\n'
        facts=cert.derive_interface_facts(src)
        self.assertFalse(facts["IDENTITIES_ARE_OPAQUE_AND_NOT_PREENUMERATED"])

    def test_route_specific_import_would_kill_neutrality_fact(self):
        src=cert._text(cert.INTERFACE)+'\n# tool_discovery_dynamic_candidate private coupling\n'
        facts=cert.derive_interface_facts(src)
        self.assertFalse(facts["INTERFACE_IS_ROUTE_NEUTRAL_AND_COMMON_AUTHORITY_PARAMETRIC"])


if __name__=="__main__":
    unittest.main(verbosity=2)
