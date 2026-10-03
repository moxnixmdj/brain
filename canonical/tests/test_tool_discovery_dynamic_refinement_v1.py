from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime import tool_discovery_dynamic_refinement_v1 as ref

ROOT = Path(__file__).resolve().parents[2]


class Tests(unittest.TestCase):
    def test_current_exact_sources_compile_conditional_refinement(self):
        out = ref.evaluate()
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["source_blob_drift"], [])
        self.assertEqual(
            out["dynamic_candidate"]["actions"],
            ["DISCOVER", "ESCALATE", "PROBE", "SELECT"],
        )
        self.assertTrue(out["conditional_refinement_obligations_pass"])
        self.assertFalse(out["universal_target_proved"])

    def test_exact_frozen_target_literals_are_bound(self):
        out = ref.evaluate()
        self.assertTrue(out["target_literals"]["unknown_tool_discovery"])
        self.assertTrue(out["target_literals"]["discover_candidate_tools_if_needed"])
        self.assertEqual(
            out["target_literals"]["scope"],
            "Unknown/changing tool ecosystem to verified usable route",
        )

    def test_removing_discover_fails_closed(self):
        source = (ROOT / ref.DYNAMIC).read_text(encoding="utf-8")
        source = source.replace('"action":"DISCOVER"', '"action":"LOOKUP"', 1)
        out = ref.evaluate(dynamic_source_override=source)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DYNAMIC_ACTION_MISSING:DISCOVER", out["errors"])

    def test_contract_cannot_self_assert_verified_instance(self):
        contract = json.loads((ROOT / ref.CONTRACT).read_text(encoding="utf-8"))
        contract["instance_verified"] = True
        out = ref.evaluate(interface_contract_override=contract)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn(
            "CANDIDATE_CONTRACT_MUST_NOT_SELF_ASSERT_VERIFIED_INSTANCE",
            out["errors"],
        )

    def test_contract_property_set_is_exact(self):
        contract = json.loads((ROOT / ref.CONTRACT).read_text(encoding="utf-8"))
        contract = copy.deepcopy(contract)
        contract["required_properties"] = contract["required_properties"][:-1]
        out = ref.evaluate(interface_contract_override=contract)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("INTERFACE_CONTRACT_PROPERTIES_NOT_EXACT", out["errors"])

    def test_residual_is_reduced_but_acceptance_stays_open(self):
        out = ref.evaluate()
        self.assertEqual(
            out["minimum_missing_fact"],
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
            "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1",
        )
        self.assertFalse(out["universal_target_proved"])
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["terminal_results_replayed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
