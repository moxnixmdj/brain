from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_common_authority_scope_certificate_v1 as cert


class CommonAuthorityScopeCertificateTests(unittest.TestCase):
    def test_exact_live_sources_pass_candidate_scope_certificate(self):
        out = cert.verify()
        self.assertEqual(out["source_blob_drift"], [], out)
        self.assertTrue(out["universal_scope_relation_proved_candidate"], out)
        self.assertTrue(out["scope_atom_satisfied_candidate"], out)
        self.assertTrue(out["forbidden_shortcut_respected"], out)
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_fact_is_load_bearing(self):
        good = {name: True for name in cert.REQUIRED_FACTS}
        self.assertTrue(
            cert.prove_from_facts(good)["universal_scope_relation_proved_candidate"]
        )
        for name in cert.REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = cert.prove_from_facts(mutant)
            self.assertFalse(out["universal_scope_relation_proved_candidate"], name)
            self.assertIn(name, out["missing"])

    def test_brain_only_substitution_cannot_satisfy_fact_set(self):
        facts = {name: True for name in cert.REQUIRED_FACTS}
        facts["BRAIN_OPUS_DISCOVERY_VIEWS_IDENTICAL"] = False
        out = cert.prove_from_facts(facts)
        self.assertFalse(out["scope_atom_satisfied_candidate"])
        self.assertIn("BRAIN_OPUS_DISCOVERY_VIEWS_IDENTICAL", out["missing"])

    def test_missing_common_scope_binding_cannot_satisfy_fact_set(self):
        facts = {name: True for name in cert.REQUIRED_FACTS}
        facts["FROZEN_PROTOCOL_REQUIRES_COMMON_TOOL_AUTHORITY"] = False
        out = cert.prove_from_facts(facts)
        self.assertFalse(out["scope_atom_satisfied_candidate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
