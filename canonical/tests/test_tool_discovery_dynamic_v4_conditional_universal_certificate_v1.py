from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_dynamic_v4_conditional_universal_certificate_v1 as cert


class ToolDiscoveryDynamicV4CertificateTests(unittest.TestCase):
    def test_live_exact_sources_compile_conditional_universal_program_proof(self):
        out = cert.evaluate()
        self.assertTrue(out["conditional_program_side_universal_proof"], out)
        self.assertTrue(out["target_preserved"])
        self.assertFalse(out["universal_target_proved"])
        self.assertEqual(out["errors"], [])
        self.assertEqual(
            out["minimum_missing_fact"],
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
            "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1",
        )

    def test_discovery_order_is_load_bearing(self):
        source = (cert.ROOT / cert.CANDIDATE).read_text(encoding="utf-8")
        mutant = source.replace("if sources:", "if False and sources:", 1)
        out = cert.evaluate(candidate_source_override=mutant)
        self.assertFalse(out["conditional_program_side_universal_proof"])
        self.assertIn("V3_GLOBAL_OPTIMALITY_COUNTEREXAMPLE_NOT_REPAIRED", out["errors"])

    def test_discovery_receipt_catalog_merge_is_load_bearing(self):
        source = (cert.ROOT / cert.CANDIDATE).read_text(encoding="utf-8")
        mutant = source.replace(
            'for tool in rec.get("tools", []) or []:',
            'for tool in []:',
            1,
        )
        out = cert.evaluate(candidate_source_override=mutant)
        self.assertFalse(out["conditional_program_side_universal_proof"])
        self.assertIn("DISCOVERY_RECEIPTS_NOT_MERGED_INTO_CATALOG", out["errors"])

    def test_complete_interface_union_property_is_load_bearing(self):
        contract = copy.deepcopy(cert._load(cert.CONTRACT))
        contract["required_properties"] = [
            x
            for x in contract["required_properties"]
            if x != "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE"
        ]
        out = cert.evaluate(contract_override=contract)
        self.assertFalse(out["conditional_program_side_universal_proof"])
        self.assertIn("COMPLETE_INTERFACE_CONTRACT_DRIFT", out["errors"])

    def test_external_instance_is_not_self_certified(self):
        contract = copy.deepcopy(cert._load(cert.CONTRACT))
        contract["instance_verified"] = True
        out = cert.evaluate(contract_override=contract)
        self.assertFalse(out["conditional_program_side_universal_proof"])
        self.assertIn("CONTRACT_SELF_ASSERTS_EXTERNAL_INSTANCE", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
