from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from canonical.runtime import root2_proof_hypergraph_v1 as r

class Tests(unittest.TestCase):
    def test_binary_guaranteed_pass(self):
        self.assertEqual(r.binary_prefix_decision(successes=7,observed=7,total=10,threshold="0.7")["status"],"GUARANTEED_PASS")
    def test_binary_guaranteed_fail(self):
        self.assertEqual(r.binary_prefix_decision(successes=0,observed=4,total=10,threshold="0.7")["status"],"GUARANTEED_FAIL")
    def test_binary_continue(self):
        self.assertEqual(r.binary_prefix_decision(successes=4,observed=5,total=10,threshold="0.7")["status"],"CONTINUE")
    def test_metric_bounds(self):
        self.assertEqual(r.bounded_metric_decision(lower=65.7,upper=70,target=65.7)["status"],"GUARANTEED_PASS")
        self.assertEqual(r.bounded_metric_decision(lower=60,upper=65.6,target=65.7)["status"],"GUARANTEED_FAIL")
    def test_paid_and_unsafe_actions_removed(self):
        rows=r.rank_actions([
          {"id":"paid","safe":True,"incremental_spend_usd":1,"closes":["p"],"p_close_low":1,"time_high":1},
          {"id":"unsafe","safe":False,"incremental_spend_usd":0,"closes":["p"],"p_close_low":1,"time_high":1},
          {"id":"ok","safe":True,"incremental_spend_usd":0,"closes":["p"],"p_close_low":"1/2","information_gain_low":1,"time_high":1},
        ],open_predicates=["p"])
        self.assertEqual([x["id"] for x in rows],["ok"])
    def test_interval_probabilities_not_invalid_points(self):
        with self.assertRaises(r.Root2OptimizerError):
            r.rank_actions([{"id":"bad","safe":True,"closes":["p"],"p_close_low":".8","p_close_high":".2","time_high":1}],open_predicates=["p"])
    def test_correlation_penalty(self):
        rows=r.rank_actions([
          {"id":"a","safe":True,"closes":["p"],"p_close_low":1,"p_close_high":1,"time_high":1,"correlation_high":"3/4"},
          {"id":"b","safe":True,"closes":["p"],"p_close_low":1,"p_close_high":1,"time_high":1,"correlation_high":0},
        ],open_predicates=["p"])
        self.assertEqual(rows[0]["id"],"b")
    def test_exact_minimum_guaranteed_cover(self):
        out=r.minimum_guaranteed_cover([
          {"id":"a","safe":True,"guaranteed":True,"closes":["p","q"],"p_close_low":1,"p_close_high":1,"time_high":1},
          {"id":"b","safe":True,"guaranteed":True,"closes":["q"],"p_close_low":1,"p_close_high":1,"time_high":1},
          {"id":"c","safe":True,"guaranteed":True,"closes":["r"],"p_close_low":1,"p_close_high":1,"time_high":1},
        ],open_predicates=["p","q","r"])
        self.assertEqual(out["selected"],["a","c"])
    def test_no_guaranteed_cover(self):
        out=r.minimum_guaranteed_cover([
          {"id":"a","safe":True,"guaranteed":True,"closes":["p"],"p_close_low":1,"p_close_high":1,"time_high":1},
        ],open_predicates=["p","q"])
        self.assertEqual(out["status"],"NO_GUARANTEED_FULL_COVER")
        self.assertEqual(out["uncovered"],["q"])
    def test_robust_frontier_orthogonalizes_sources(self):
        out=r.robust_frontier([
          {"id":"w1","safe":True,"source_class":"web","closes":["p"],"p_close_low":"1/2","information_gain_low":1,"time_high":1},
          {"id":"w2","safe":True,"source_class":"web","closes":["q"],"p_close_low":"1/2","information_gain_low":1,"time_high":1},
          {"id":"c1","safe":True,"source_class":"code","closes":["r"],"p_close_low":"1/2","information_gain_low":1,"time_high":1},
        ],open_predicates=["p","q","r"],max_same_source_class=1)
        self.assertEqual(set(out["selected_action_ids"]),{"w1","c1"})
    def test_blob_binding(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x"; p.write_text("abc")
            sha=r.git_blob_sha(p)
            self.assertTrue(r.verify_inventory_binding(p,sha)["bound"])
            self.assertFalse(r.verify_inventory_binding(p,"0"*40)["bound"])

if __name__=="__main__":
    unittest.main(verbosity=2)
