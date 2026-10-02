import unittest

from canonical.runtime.portfolio_multiplex_terminal_instrumentation_v1 import (
    BINDINGS,
    bound_behavior_ids,
    validate_parent_observation,
    reduce_behavior_receipts,
)


class Tests(unittest.TestCase):
    def _good(self, bid):
        portfolio = BINDINGS[bid]["portfolios"][0]
        return {
            "behavior_id": bid,
            "portfolio": portfolio,
            "case_id": portfolio + "::case::0",
            "candidate_package_commitment": "abc123",
            "post_freeze_beacon": "beacon123",
            "binding_blob": BINDINGS[bid]["binding_blob"],
            "load_bearing": True,
            "direct_instrumentation_pass": True,
            "parent_terminal_acceptance_pass": True,
            "case_replaced": False,
            "tuning_replay": False,
            "result_to_runtime_feedback": False,
            "candidate_visible_keys": ["task", "visible_evidence"],
            "claims_behavior_credit": False,
        }

    def test_all_seven_bound(self):
        self.assertEqual(len(bound_behavior_ids()), 7)

    def test_good_receipt_passes_component(self):
        for bid in bound_behavior_ids():
            with self.subTest(bid=bid):
                out = validate_parent_observation(bid, self._good(bid))
                self.assertTrue(out["valid"], out)
                self.assertTrue(out["behavior_evidence_pass"], out)
                self.assertFalse(out["standalone_terminal_population"])
                self.assertFalse(out["execution_authority"])

    def test_wrong_binding_blob_fails_closed(self):
        bid = bound_behavior_ids()[0]
        row = self._good(bid)
        row["binding_blob"] = "drift"
        out = validate_parent_observation(bid, row)
        self.assertFalse(out["valid"])
        self.assertIn("BINDING_BLOB_MISMATCH", out["errors"])

    def test_hidden_information_leak_fails_closed(self):
        bid = bound_behavior_ids()[0]
        row = self._good(bid)
        row["candidate_visible_keys"] = ["task", "hidden_oracle"]
        out = validate_parent_observation(bid, row)
        self.assertFalse(out["valid"])

    def test_non_load_bearing_does_not_earn_evidence(self):
        bid = bound_behavior_ids()[0]
        row = self._good(bid)
        row["load_bearing"] = False
        out = validate_parent_observation(bid, row)
        self.assertTrue(out["valid"])
        self.assertFalse(out["behavior_evidence_pass"])

    def test_reducer_requires_all_load_bearing_receipts_pass(self):
        bid = bound_behavior_ids()[0]
        good = self._good(bid)
        bad = self._good(bid)
        bad["case_id"] = "other"
        bad["direct_instrumentation_pass"] = False
        out = reduce_behavior_receipts(bid, [good, bad])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["failed_load_bearing_receipt_count"], 1)


if __name__ == "__main__":
    unittest.main()
