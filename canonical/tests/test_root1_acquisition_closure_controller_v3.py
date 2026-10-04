from __future__ import annotations

import unittest
from fractions import Fraction

from canonical.runtime import root1_acquisition_closure_controller_v3 as r3

def manifest():
    return {
        "expected_family_count": 3,
        "actual_family_count": 3,
        "families": [
            {"id":"A","target_behavior":"alpha","ownership_status":"VERIFIED_OWNED_EQUAL_OR_BETTER","opus55_acceptance_state":"PASS"},
            {"id":"B","target_behavior":"beta","ownership_status":"PROVISIONAL","opus55_acceptance_state":"OPEN"},
            {"id":"C","target_behavior":"gamma","ownership_status":"PROVISIONAL","opus55_acceptance_state":"OPEN"},
        ],
    }

def matrix():
    return {
        "rows": [
            {"family":"A","best_existing_routes":["owned"]},
            {"family":"B","internalized_configuration":"x","best_existing_routes":["x"]},
            {"family":"C","candidate_internalization_routes":[{"repo":"r"}],"best_existing_routes":["r"]},
        ]
    }

class Tests(unittest.TestCase):
    def test_declared_terminal_envelope_is_lossless_only_at_declared_boundary(self):
        out=r3.extract_terminal_family_envelope(manifest())
        self.assertEqual(out["family_ids"],["A","B","C"])
        self.assertTrue(out["lossless_at_declared_family_boundary"])
        self.assertEqual(out["claim_scope"],"DECLARED_TERMINAL_FAMILY_BOUNDARY_ONLY")
        self.assertFalse(out["universal_semantic_learning_success_claimed"])

    def test_envelope_rejects_count_drift_and_duplicate_ids(self):
        bad=manifest();bad["actual_family_count"]=2
        with self.assertRaises(r3.Root1V3Error):
            r3.extract_terminal_family_envelope(bad)
        dup=manifest();dup["families"][2]["id"]="B"
        with self.assertRaises(r3.Root1V3Error):
            r3.extract_terminal_family_envelope(dup)

    def test_route_audit_never_reclassifies_unproved_as_missing(self):
        out=r3.audit_current_family_routes(manifest=manifest(),ownership_matrix=matrix())
        self.assertEqual(out["verified_owned_count"],1)
        self.assertEqual(out["route_coverage_unproved_count"],2)
        self.assertEqual(out["root1_positive_gap_count_delta"],0)
        self.assertFalse(out["root1_seal_authorized"])
        self.assertIn("ROUTE_COVERAGE_UNPROVED_NOT_MISSING",{x["classification"] for x in out["details"]})

    def test_jeffreys_prior_is_neutral_and_data_updates_it(self):
        self.assertEqual(r3.beta_posterior_mean(0,0),Fraction(1,2))
        self.assertGreater(r3.beta_posterior_mean(8,10),r3.beta_posterior_mean(2,10))
        with self.assertRaises(r3.Root1V3Error):
            r3.beta_posterior_mean(2,1)

    def test_probabilistic_ranking_rejects_paid_and_penalizes_correlation(self):
        actions=[
          {"id":"cheap","safe":True,"source_class":"code","dependency_cluster":"a","historical_successes":2,"historical_attempts":4,"closure_mass":10,"time":1,"risk":0,"correlation_penalty":0,"incremental_spend_usd":0},
          {"id":"correlated","safe":True,"source_class":"paper","dependency_cluster":"b","historical_successes":2,"historical_attempts":4,"closure_mass":10,"time":1,"risk":0,"correlation_penalty":10,"incremental_spend_usd":0},
          {"id":"paid","safe":True,"source_class":"social","dependency_cluster":"c","historical_successes":99,"historical_attempts":100,"closure_mass":999,"time":1,"risk":0,"correlation_penalty":0,"incremental_spend_usd":1},
        ]
        out=r3.rank_probabilistic_actions(actions)
        self.assertEqual(out[0]["id"],"cheap")
        self.assertNotIn("paid",[x["id"] for x in out])

    def test_orthogonal_portfolio_uses_distinct_source_and_dependency_clusters(self):
        actions=[
          {"id":"a","safe":True,"source_class":"code","dependency_cluster":"same","historical_successes":1,"historical_attempts":1,"closure_mass":10,"time":1,"risk":0,"incremental_spend_usd":0},
          {"id":"b","safe":True,"source_class":"paper","dependency_cluster":"same","historical_successes":1,"historical_attempts":1,"closure_mass":9,"time":1,"risk":0,"incremental_spend_usd":0},
          {"id":"c","safe":True,"source_class":"official","dependency_cluster":"other","historical_successes":1,"historical_attempts":1,"closure_mass":8,"time":1,"risk":0,"incremental_spend_usd":0},
        ]
        out=r3.select_probabilistic_orthogonal_portfolio(actions,max_actions=3)
        self.assertEqual(len({x["source_class"] for x in out}),len(out))
        self.assertEqual(len({x["dependency_cluster"] for x in out}),len(out))

    def test_exact_minimum_route_cover_beats_single_broad_expensive_route(self):
        out=r3.minimum_weight_route_cover(
          missing_primitives={"a","b","c"},
          routes=[
            {"id":"ab","safe":True,"covers":["a","b"],"time":1,"risk":0,"complexity":0,"incremental_spend_usd":0},
            {"id":"c","safe":True,"covers":["c"],"time":1,"risk":0,"complexity":0,"incremental_spend_usd":0},
            {"id":"abc","safe":True,"covers":["a","b","c"],"time":3,"risk":0,"complexity":0,"incremental_spend_usd":0},
          ],
        )
        self.assertEqual(out["status"],"EXACT_MINIMUM_ADMISSIBLE_ROUTE_COVER")
        self.assertEqual(out["selected_route_ids"],["ab","c"])
        self.assertEqual(out["total_weight"],"2")

    def test_paid_route_cannot_cover(self):
        out=r3.minimum_weight_route_cover(
          missing_primitives={"x"},
          routes=[{"id":"paid","safe":True,"covers":["x"],"time":1,"risk":0,"complexity":0,"incremental_spend_usd":1}],
        )
        self.assertEqual(out["status"],"NO_ADMISSIBLE_ROUTE_COVER")

    def test_root1_inactive_means_zero_acquisition_even_with_tempting_routes(self):
        out=r3.root1_atomic_transaction(
          gap_evidence=None,
          required_primitives={"x"},
          verified_primitives=set(),
          search_actions=[{"id":"tempt","safe":True,"source_class":"code","historical_successes":100,"historical_attempts":100,"closure_mass":999,"time":1,"risk":0,"incremental_spend_usd":0}],
          acquisition_routes=[{"id":"route","safe":True,"covers":["x"],"time":1,"risk":0,"complexity":0,"incremental_spend_usd":0}],
        )
        self.assertEqual(out["status"],"ROOT1_INACTIVE_ZERO_ACQUISITION_ACTIONS")
        self.assertEqual(out["search_portfolio"],[])
        self.assertIsNone(out["route_cover"])

if __name__=="__main__":
    unittest.main(verbosity=2)
