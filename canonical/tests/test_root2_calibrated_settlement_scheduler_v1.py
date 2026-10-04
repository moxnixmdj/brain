from __future__ import annotations
import unittest

from canonical.runtime.root2_calibrated_settlement_scheduler_v1 import (
    INPUT_SCHEMA,
    compile_settlement_schedule,
)

SHA = "a" * 40


def receipt():
    return {"path": "canonical/verification/history.json", "git_blob_sha": SHA}


def action(aid, sec, settles, *, settled=None, trials=None, deletes=None, deterministic=False, zr=True):
    row = {
        "action_id": aid,
        "critical_path_seconds": sec,
        "zero_reality": zr,
        "settles_predicates": settles,
        "deletes_actions_if_settled": deletes or [],
    }
    if deterministic:
        row["deterministic_settlement"] = True
    if trials is not None:
        row["calibration_history"] = {
            "trials": trials,
            "settled": settled,
            "receipt": receipt(),
        }
    return row


class Root2CalibratedSettlementSchedulerTests(unittest.TestCase):
    def test_higher_expected_terminal_delta_rate_wins(self):
        d = {
            "schema": INPUT_SCHEMA,
            "allow_fresh_reality": False,
            "actions": [
                action("slow-certain", 10, ["P1"], deterministic=True),
                action("fast-history", 2, ["P2"], settled=7, trials=8),
            ],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["status"], "PASS__CALIBRATED_SCHEDULING_ONLY__ZERO_CREDIT")
        self.assertEqual(o["ranked_actions"][0]["action_id"], "fast-history")

    def test_downstream_deletion_counts_as_structural_delta(self):
        d = {
            "schema": INPUT_SCHEMA,
            "actions": [
                action("fanout", 2, ["P"], settled=1, trials=1, deletes=["b", "c", "d"]),
                action("plain", 1, ["Q"], deterministic=True),
            ],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["ranked_actions"][0]["action_id"], "fanout")

    def test_uncalibrated_gets_no_probability_advantage(self):
        d = {
            "schema": INPUT_SCHEMA,
            "actions": [
                action("unknown-fast", 1, ["P"]),
                action("known-slower", 3, ["Q"], deterministic=True),
            ],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["ranked_actions"][0]["action_id"], "known-slower")
        self.assertEqual(o["ranked_actions"][1]["calibration_method"], "UNCALIBRATED")

    def test_jeffreys_mean_exact(self):
        d = {
            "schema": INPUT_SCHEMA,
            "actions": [action("a", 1, ["P"], settled=0, trials=1)],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["ranked_actions"][0]["settlement_probability"], "0.25")

    def test_history_requires_content_addressed_receipt(self):
        d = {
            "schema": INPUT_SCHEMA,
            "actions": [{
                "action_id": "a",
                "critical_path_seconds": 1,
                "zero_reality": True,
                "settles_predicates": ["P"],
                "deletes_actions_if_settled": [],
                "calibration_history": {"trials": 2, "settled": 1, "receipt": {"path": "x", "git_blob_sha": "bad"}},
            }],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["status"], "FAIL_CLOSED")

    def test_fresh_reality_blocked(self):
        d = {
            "schema": INPUT_SCHEMA,
            "allow_fresh_reality": False,
            "actions": [action("fresh", 1, ["P"], deterministic=True, zr=False)],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["ranked_actions"], [])
        self.assertEqual(o["blocked_fresh_reality_actions"], ["fresh"])

    def test_invalid_counts_fail_closed(self):
        d = {
            "schema": INPUT_SCHEMA,
            "actions": [action("bad", 1, ["P"], settled=3, trials=2)],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["status"], "FAIL_CLOSED")

    def test_no_credit_or_authority(self):
        d = {
            "schema": INPUT_SCHEMA,
            "actions": [action("a", 1, ["P"], deterministic=True)],
        }
        o = compile_settlement_schedule(d)
        self.assertEqual(o["acceptance_credit_delta"], 0)
        self.assertFalse(o["fresh_reality_authority"])
        self.assertFalse(o["execution_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
