import copy
import unittest
from unittest.mock import patch

from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof
from canonical.runtime import tool_discovery_dynamic_v3_interface_instance_v1 as instance


class ToolDiscoveryDynamicV3InterfaceInstanceTests(unittest.TestCase):
    def test_exact_frozen_instance_passes_all_seven_properties(self):
        out = instance.evaluate()
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertTrue(out["instance_verified_candidate"])
        self.assertEqual(out["semantic_variant_count"], 6)
        self.assertTrue(all(out["required_properties"].values()))
        self.assertFalse(out["whole_protocol_scope_proved"])
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_missing_authoritative_source_tool_fails_completeness(self):
        original = proof.generate_case

        def broken(seed, ordinal):
            case = copy.deepcopy(original(seed, ordinal))
            case["discovery_sources"][1]["tool_ids"].remove("T5")
            return case

        with patch.object(proof, "generate_case", side_effect=broken):
            out = instance.evaluate()
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("AUTHORITATIVE_UNION_INCOMPLETE:T5" in x for x in out["errors"]))

    def test_discovery_receipt_must_identify_source(self):
        original = proof._discover

        def broken(case, source_id, query):
            rec = copy.deepcopy(original(case, source_id, query))
            rec["source_id"] = "WRONG"
            return rec

        with patch.object(proof, "_discover", side_effect=broken):
            out = instance.evaluate()
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("DISCOVERY_RECEIPT_SOURCE_MISMATCH" in x for x in out["errors"]))

    def test_discovered_metadata_must_match_authoritative_tool_record(self):
        original = proof._discover

        def broken(case, source_id, query):
            rec = copy.deepcopy(original(case, source_id, query))
            if rec["tools"]:
                rec["tools"][0]["cost"] = 999999.0
            return rec

        with patch.object(proof, "_discover", side_effect=broken):
            out = instance.evaluate()
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("DISCOVERED_METADATA_NOT_EXACT" in x for x in out["errors"]))

    def test_probe_receipt_must_be_truthful_and_epoch_bound(self):
        original = proof._probe

        def broken(case, stage, tool_id, capability):
            rec = copy.deepcopy(original(case, stage, tool_id, capability))
            rec["supported"] = not rec["supported"]
            return rec

        with patch.object(proof, "_probe", side_effect=broken):
            out = instance.evaluate()
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("PROBE_RECEIPT_NOT_TRUTHFUL_EPOCH_BOUND" in x for x in out["errors"]))

    def test_epoch_must_be_stable_within_episode(self):
        original = proof._epoch_map
        calls = {}

        def broken(case, stage):
            key = (case["case_class"], stage)
            calls[key] = calls.get(key, 0) + 1
            out = dict(original(case, stage))
            if calls[key] % 2 == 0:
                out["T0"] = out["T0"] + 1
            return out

        with patch.object(proof, "_epoch_map", side_effect=broken):
            out = instance.evaluate()
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("EPOCH_MAP_UNSTABLE_WITHIN_STAGE" in x for x in out["errors"]))

    def test_instance_proof_never_self_promotes_to_whole_protocol(self):
        out = instance.evaluate()
        self.assertFalse(out["whole_protocol_scope_proved"])
        self.assertIn("DOES_NOT_PROVE", out["whole_protocol_scope_nonclaim"])
        self.assertIn("SEPARATE_TOOL_DISCOVERY_ACCEPTANCE_SCOPE_REDUCTION", out["next_if_independently_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
