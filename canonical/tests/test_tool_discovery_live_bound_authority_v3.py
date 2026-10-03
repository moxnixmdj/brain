from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_live_bound_authority_v3 as live


class Tests(unittest.TestCase):
    def test_exact_live_instance_closes_all_interface_properties_candidate_side(self):
        out = live.prove_live_instance()
        self.assertEqual(out["status"], "PASS__LIVE_BOUND_TOOL_AUTHORITY_INSTANCE", out)
        self.assertEqual(out["tool_count"], 42, out)
        self.assertTrue(out["exact_authority_identity_enumeration"], out)
        self.assertTrue(out["capability_truth_hidden_from_discovery_projection"], out)
        self.assertTrue(out["all_authority_entries_preverified"], out)
        self.assertTrue(out["operative_invoke_capability_chokepoint_proved"], out)
        self.assertTrue(all(out["contract_properties"].values()), out)

    def test_policy_must_discover_live_authority_before_reasoning(self):
        action = live.next_action({"required_capabilities": ["structured.binary.encode"]})
        self.assertEqual(action["action"], "DISCOVER")
        self.assertEqual(action["source_id"], live.SOURCE_ID)
        self.assertEqual(action["epoch"], live.authority_epoch())

    def test_discovery_is_exact_live_registry_and_hides_provides(self):
        receipt = live.discover()
        self.assertEqual(receipt["authority_registry_git_blob"], live.REGISTRY_EXPECTED_BLOB)
        self.assertEqual(receipt["authority_runtime_git_blob"], live.ASTRA_EXPECTED_BLOB)
        self.assertEqual(len(receipt["tools"]), 42)
        self.assertTrue(all("provides" not in row for row in receipt["tools"]))
        ids = [row["tool_id"] for row in receipt["tools"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_safe_probe_reads_hidden_verified_contract_and_is_epoch_bound(self):
        epoch = live.authority_epoch()
        yes = live.safe_probe("auto.pypi.msgpack", "structured.binary.encode", epoch=epoch)
        no = live.safe_probe("auto.pypi.msgpack", "archive.tar_gz.create_from_manifest", epoch=epoch)
        self.assertTrue(yes["supported"], yes)
        self.assertFalse(no["supported"], no)
        with self.assertRaisesRegex(live.LiveAuthorityError, "STALE_AUTHORITY_EPOCH"):
            live.safe_probe("auto.pypi.msgpack", "structured.binary.encode", epoch=epoch + 1)

    def test_complete_materialization_prevents_selecting_known_later_tool_first(self):
        receipt = live.discover()
        epoch = live.authority_epoch()
        prior = [
            live.safe_probe("auto.pypi.msgpack", "structured.binary.encode", epoch=epoch)
        ]
        action = live.next_action({
            "required_capabilities": ["structured.binary.encode"],
            "authority_discovery_receipt": receipt,
            "prior_probe_receipts": prior,
        })
        # The full authority is visible. A lower/equal-cost lexically earlier
        # candidate must be resolved before the later proved tool can be selected.
        self.assertEqual(action["action"], "PROBE", action)
        self.assertNotEqual(action.get("tool_id"), "auto.pypi.msgpack", action)

    def test_tampered_partial_discovery_receipt_fails_closed(self):
        receipt = live.discover()
        receipt["tools"] = receipt["tools"][1:]
        with self.assertRaisesRegex(live.LiveAuthorityError, "DISCOVERY_RECEIPT_TOOL_SET_MISMATCH"):
            live.next_action({
                "required_capabilities": ["structured.binary.encode"],
                "authority_discovery_receipt": receipt,
            })

    def test_unknown_selected_identity_fails_at_real_astra_chokepoint(self):
        with self.assertRaisesRegex(Exception, "BOUND_CAPABILITY_UNKNOWN:__not_registered__"):
            live.invoke_selected("__not_registered__")

    def test_ast_runtime_exact_source_proves_single_invoke_capability_dispatch(self):
        facts = live._astra_source_facts()
        self.assertTrue(facts["load_exact_registry"], facts)
        self.assertTrue(facts["unknown_id_fails_closed_before_adapter"], facts)
        self.assertTrue(facts["adapter_execution_after_registry_lookup"], facts)
        self.assertEqual(facts["goal_invoke_capability_branch_count"], 1, facts)
        self.assertTrue(facts["goal_invoke_capability_delegates_to_chokepoint"], facts)

    def test_zero_credit_before_independent_verification(self):
        out = live.prove_live_instance()
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
