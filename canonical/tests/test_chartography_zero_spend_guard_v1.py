from __future__ import annotations
import unittest
from canonical.runtime import chartography_zero_spend_guard_v1 as g

def snap(**kw):
    x={
      "receipt_verified":True,
      "model_id":"google/gemini-3.5-flash",
      "model_access":True,
      "free_tier_active":True,
      "paid_fallback_enabled":False,
      "overage_enabled":False,
      "incremental_spend_usd":0,
      "project_hash":"0123456789abcdef0123456789abcdef",
      "verified_free_call_capacity":1100,
    }
    x.update(kw)
    return x

class Tests(unittest.TestCase):
    def test_exact_minimum_plan_passes(self):
        out=g.authorize_plan(snap(),required_calls=1000,retry_reserve=100)
        self.assertEqual(out["status"],"PASS__HARD_ZERO_SPEND_PLAN_AUTHORIZED")
    def test_unverified_snapshot_fails(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_plan(snap(receipt_verified=False))
    def test_model_drift_fails(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_plan(snap(model_id="google/gemini-other"))
    def test_paid_fallback_fails(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_plan(snap(paid_fallback_enabled=True))
    def test_overage_fails(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_plan(snap(overage_enabled=True))
    def test_nonzero_spend_fails(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_plan(snap(incremental_spend_usd="0.01"))
    def test_insufficient_capacity_fails(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_plan(snap(verified_free_call_capacity=999))
    def test_retry_reserve_is_load_bearing(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_plan(snap(verified_free_call_capacity=1000),retry_reserve=1)
    def test_next_call_passes_only_with_remaining_capacity(self):
        out=g.authorize_next_call(snap(),successful_calls=500,attempted_calls=520,retry_reserve_remaining=50)
        self.assertTrue(out["authorize_call"])
    def test_next_call_fails_if_capacity_erodes(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.authorize_next_call(snap(verified_free_call_capacity=1000),successful_calls=500,attempted_calls=520,retry_reserve_remaining=1)
    def test_completion_stops(self):
        out=g.authorize_next_call(snap(),successful_calls=1000,attempted_calls=1010)
        self.assertFalse(out["authorize_call"])
        self.assertTrue(out["status"].startswith("STOP__"))

if __name__=="__main__":
    unittest.main(verbosity=2)
