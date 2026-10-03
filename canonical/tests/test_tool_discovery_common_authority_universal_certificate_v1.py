from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_common_authority_universal_certificate_v1 as cert


class ToolDiscoveryCommonAuthorityUniversalCertificateTests(unittest.TestCase):
    def test_live_candidate_derives_universal_scope_without_empirical_generalization(self):
        out=cert.verify()
        self.assertTrue(out["status"].startswith("PASS__"),out)
        self.assertTrue(out["universal_scope_proved"])
        self.assertTrue(out["whole_protocol_common_authority_scope_proved"])
        self.assertTrue(out["all_admissible_target_inputs_proved"])
        self.assertTrue(out["formal_completeness"])
        self.assertTrue(out["target_preserved"])
        self.assertTrue(out["same_tool_authority_for_brain_and_comparator"])
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["basis_kind"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["source_blob_drift"],[])
        self.assertTrue(out["constructive_witness"]["pass"],out["constructive_witness"])
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_every_source_and_target_premise_is_load_bearing(self):
        good_source=cert._source_facts()
        good_target=cert._target_facts()
        self.assertTrue(all(good_source.values()),good_source)
        self.assertTrue(all(good_target.values()),good_target)
        for key in good_source:
            mutated=dict(good_source); mutated[key]=False
            out=cert.prove_from_premises(mutated,good_target,True)
            self.assertFalse(out["universal_scope_proved"],key)
            self.assertIn(key,out["missing"])
        for key in good_target:
            mutated=dict(good_target); mutated[key]=False
            out=cert.prove_from_premises(good_source,mutated,True)
            self.assertFalse(out["universal_scope_proved"],key)
            self.assertIn(key,out["missing"])

    def test_constructive_witness_is_required(self):
        out=cert.prove_from_premises(cert._source_facts(),cert._target_facts(),False)
        self.assertFalse(out["universal_scope_proved"])
        self.assertIn("CONSTRUCTIVE_WITNESS_FAILED",out["missing"])

    def test_proof_domain_is_common_matched_not_brain_only(self):
        out=cert.verify()
        self.assertIn("COMMON_MATCHED_TOOL_AUTHORITY",out["proof_domain"])
        self.assertIn("ARBITRARY_FINITE_AUTHORITATIVE_SOURCE_PARTITIONS",out["proof_domain"])
        self.assertTrue(out["same_tool_authority_for_brain_and_comparator"])
        self.assertIn("NO_BRAIN_ONLY_REGISTRY_OR_ASYMMETRIC_TOOL_AUTHORITY",out["hard_nonclaims"])

    def test_terminal_180_sample_is_not_used_as_universal_premise(self):
        out=cert.verify()
        self.assertFalse(out["uses_empirical_generalization"])
        proof_text=str(out["proof"])
        self.assertNotIn("180/180",proof_text)
        self.assertIn("NO_EMPIRICAL_EXTRAPOLATION_FROM_180_TERMINAL_CASES",out["hard_nonclaims"])

    def test_no_credit_or_authority_is_self_granted(self):
        out=cert.verify()
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
