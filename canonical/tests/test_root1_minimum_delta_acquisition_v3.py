from fractions import Fraction
import unittest

from canonical.runtime import root1_minimum_delta_acquisition_v3 as r

class Root1MinimumDeltaTests(unittest.TestCase):
    def test_minimum_delta_subtracts_all_verified_coverage_classes(self):
        out = r.minimum_capability_delta(
            {"a", "b", "c", "d"},
            owned={"a"},
            transferable={"b"},
            composable={"c"},
            known_internalizable_routes=set(),
        )
        self.assertEqual(out["residual_primitives"], ["d"])

    def test_unknown_is_not_missing_by_default(self):
        out = r.minimum_capability_delta({"a"}, owned=set())
        self.assertEqual(out["residual_primitives"], ["a"])
        self.assertNotIn("missing", out)

    def test_beta_posterior_jeffreys_prior(self):
        self.assertEqual(r.beta_posterior_mean(0, 0), Fraction(1, 2))
        self.assertEqual(r.beta_posterior_mean(1, 1), Fraction(3, 4))

    def test_rank_discards_paid_or_unsafe_actions(self):
        actions = [
            {
                "action_id": "good",
                "source_class": r.REQUIRED_SOURCE_CLASSES[0],
                "successes": 1, "trials": 1,
                "expected_closure_mass": 5, "information_gain": 1,
                "transfer_gain": 1, "proof_gain": 1,
                "time_cost": 1, "risk": 0, "correlation_penalty": 0,
                "incremental_spend_usd": 0, "safe": True, "covers": ["x"],
            },
            {
                "action_id": "paid",
                "source_class": r.REQUIRED_SOURCE_CLASSES[1],
                "successes": 100, "trials": 100,
                "expected_closure_mass": 100,
                "time_cost": 1, "risk": 0, "correlation_penalty": 0,
                "incremental_spend_usd": 1, "safe": True, "covers": ["x"],
            },
        ]
        ranked = r.rank_discovery_actions(actions)
        self.assertEqual([x["action_id"] for x in ranked], ["good"])

    def test_exact_minimum_route_cover_prefers_lower_total_cost(self):
        routes = [
            {
                "route_id":"ab","covers":["a","b"],"verified":True,"safe":True,
                "durable":True,"internalizable":True,"ownership_compatible":True,
                "incremental_spend_usd":0,"expected_time":4,"risk":0,"integration_cost":0,
            },
            {
                "route_id":"a","covers":["a"],"verified":True,"safe":True,
                "durable":True,"internalizable":True,"ownership_compatible":True,
                "incremental_spend_usd":0,"expected_time":1,"risk":0,"integration_cost":0,
            },
            {
                "route_id":"b","covers":["b"],"verified":True,"safe":True,
                "durable":True,"internalizable":True,"ownership_compatible":True,
                "incremental_spend_usd":0,"expected_time":1,"risk":0,"integration_cost":0,
            },
        ]
        out = r.exact_minimum_route_cover({"a","b"}, routes)
        self.assertEqual(out["selected_routes"], ["a","b"])
        self.assertEqual(out["total_cost"], 2)

    def test_inadmissible_route_cannot_close_cover(self):
        routes = [{
            "route_id":"paid","covers":["a"],"verified":True,"safe":True,
            "durable":True,"internalizable":True,"ownership_compatible":True,
            "incremental_spend_usd":"0.01","expected_time":1,"risk":0,"integration_cost":0,
        }]
        out = r.exact_minimum_route_cover({"a"}, routes)
        self.assertTrue(out["status"].startswith("OPEN__"))

    def test_envelope_seal_requires_lossless_independent_complete_coverage(self):
        route = {
            "verified":True,"safe":True,"durable":True,"internalizable":True,
            "ownership_compatible":True,"incremental_spend_usd":0,
        }
        receipts = {"a":{"verified_owned":True}, "b":{"route":route}}
        sealed = r.envelope_seal_verdict(
            {"a","b"}, receipts,
            decomposition_complete=True,
            decomposition_lossless=True,
            independent_verification=True,
        )
        self.assertTrue(sealed["frozen_envelope_sealed"])

        open_verdict = r.envelope_seal_verdict(
            {"a","b"}, receipts,
            decomposition_complete=True,
            decomposition_lossless=False,
            independent_verification=True,
        )
        self.assertFalse(open_verdict["frozen_envelope_sealed"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
