from __future__ import annotations

import unittest

from canonical.runtime import post_tool_discovery_zero_reality_recompile_v1 as r


class Tests(unittest.TestCase):
    def test_current_exact_recompile(self):
        out = r.evaluate()
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertEqual(out["current_acceptance"]["accepted_families"], 5)
        self.assertEqual(out["current_acceptance"]["proved_atomic"], 12)
        self.assertEqual(out["current_acceptance"]["unresolved_atomic"], 26)
        self.assertEqual(out["cut"]["available_action_count"], 17)
        self.assertEqual(out["cut"]["selected_action_count"], 15)
        self.assertEqual(out["cut"]["covered_predicate_count"], 26)
        self.assertEqual(out["cut"]["uncovered_predicates"], [])
        self.assertEqual(out["cut"]["selected_new_reality_units"], 0)
        self.assertEqual(out["cut"]["selected_actions"], r.EXPECTED_SELECTED_ACTIONS)

    def test_tool_discovery_closed_target_is_not_rescheduled(self):
        out = r.evaluate()
        self.assertTrue(out["tool_discovery_replay_removed"], out)
        self.assertNotIn(
            "BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
            out["cut"]["selected_actions"],
        )

    def test_zero_credit_and_no_execution_authority(self):
        out = r.evaluate()
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_source_drift_fails_closed(self):
        key = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
        old = r.INPUTS[key]
        try:
            r.INPUTS[key] = "0" * 40
            out = r.evaluate()
            self.assertEqual(out["status"], "FAIL_CLOSED__SOURCE_BLOB_DRIFT__ZERO_CREDIT")
            self.assertIn(key, out["source_blob_drift"])
        finally:
            r.INPUTS[key] = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
