from __future__ import annotations

import unittest
from canonical.runtime import zero_spend_provider_guard_v1 as g

def snap(provider="tavily", **kw):
    x = {
        "provider_id": provider,
        "receipt_verified": True,
        "snapshot_fresh": True,
        "free_plan_active": True,
        "paid_fallback_enabled": False,
        "overage_enabled": False,
        "billing_charge_path_enabled": False,
        "incremental_spend_usd": 0,
        "account_hash": "0123456789abcdef0123456789abcdef",
        "snapshot_hash": "fedcba9876543210fedcba9876543210",
    }
    x.update(kw)
    return x

def outcome(provider="tavily", call_id="c1", **kw):
    x = {
        "provider_id": provider,
        "call_id": call_id,
        "paid_charge_observed": False,
        "quota_exhausted": False,
        "payment_required": False,
        "overage_observed": False,
        "observed_cost_usd": 0,
    }
    x.update(kw)
    return x

def summary(provider, attempted=0, **kw):
    x = {
        "provider_id": provider,
        "attempted_calls": attempted,
        "observed_calls": attempted,
        "all_calls_guarded": True,
        "guard_trip_count": 0,
        "quota_exhaustion_count": 0,
        "payment_required_count": 0,
        "paid_charge_count": 0,
        "observed_cost_usd": 0,
    }
    x.update(kw)
    return x

class Tests(unittest.TestCase):
    def test_verified_free_account_authorizes_call(self):
        out = g.authorize_call(snap(), provider_id="tavily", call_id="c1")
        self.assertEqual(out["status"], "PASS__ZERO_SPEND_CALL_AUTHORIZED")

    def test_unverified_or_paid_paths_fail(self):
        for bad in (
            {"receipt_verified": False},
            {"snapshot_fresh": False},
            {"free_plan_active": False},
            {"paid_fallback_enabled": True},
            {"overage_enabled": True},
            {"billing_charge_path_enabled": True},
            {"incremental_spend_usd": "0.01"},
        ):
            with self.assertRaises(g.ZeroSpendBlocked):
                g.authorize_call(snap(**bad), provider_id="tavily", call_id="c1")

    def test_outcome_quota_payment_or_charge_fails_closed(self):
        for bad in (
            {"quota_exhausted": True},
            {"payment_required": True},
            {"paid_charge_observed": True},
            {"overage_observed": True},
            {"observed_cost_usd": "0.01"},
        ):
            with self.assertRaises(g.ZeroSpendBlocked):
                g.observe_call(snap(), provider_id="tavily", call_id="c1", outcome=outcome(**bad))

    def test_provider_and_call_identity_are_bound(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.observe_call(snap(), provider_id="tavily", call_id="c1", outcome=outcome(provider="sec_api"))
        with self.assertRaises(g.ZeroSpendBlocked):
            g.observe_call(snap(), provider_id="tavily", call_id="c1", outcome=outcome(call_id="other"))

    def test_full_run_zero_trip_attestation_passes_without_preproved_demand(self):
        out = g.finalize_run(
            [summary("tavily", 700), summary("sec_api", 80), summary("tiingo", 300)],
            required_provider_ids={"tavily", "sec_api", "tiingo"},
            evaluation_completed=True,
        )
        self.assertTrue(out["score_eligibility_zero_spend_gate"])

    def test_zero_calls_for_unused_provider_is_allowed_but_summary_required(self):
        out = g.finalize_run(
            [summary("tavily", 0), summary("sec_api", 0), summary("tiingo", 0)],
            required_provider_ids={"tavily", "sec_api", "tiingo"},
            evaluation_completed=True,
        )
        self.assertEqual(out["guard_trip_count"], 0)

    def test_finalization_fails_on_missing_unobserved_or_tripped_calls(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.finalize_run([summary("tavily")], required_provider_ids={"tavily","sec_api"}, evaluation_completed=True)
        with self.assertRaises(g.ZeroSpendBlocked):
            g.finalize_run([summary("tavily", 2, observed_calls=1)], required_provider_ids={"tavily"}, evaluation_completed=True)
        with self.assertRaises(g.ZeroSpendBlocked):
            g.finalize_run([summary("tavily", 1, guard_trip_count=1)], required_provider_ids={"tavily"}, evaluation_completed=True)

    def test_incomplete_evaluation_never_gets_score_gate(self):
        with self.assertRaises(g.ZeroSpendBlocked):
            g.finalize_run([summary("tavily")], required_provider_ids={"tavily"}, evaluation_completed=False)

if __name__ == "__main__":
    unittest.main(verbosity=2)
