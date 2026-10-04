from __future__ import annotations
import unittest
from canonical.runtime.threshold_proof_dag_v1 import INPUT_SCHEMA, compile_threshold_proof_dag

SHA="a"*40

def receipt(path="target.json"):
    return {"path":path,"git_blob_sha":SHA}

def base(kind, **target):
    return {
        "schema": INPUT_SCHEMA,
        "target":{"id":"P","metric_kind":kind,"receipt":receipt(),**target},
        "allow_fresh_reality":False,
        "actions":[],
    }

def action(aid, sec, *, gain=0, loss=0, margin=0, cov=None, deps=None, zr=True, route=None):
    out={
        "action_id":aid,
        "critical_path_seconds":sec,
        "zero_reality":zr,
        "coverage_ids":cov or [aid],
        "depends_on":deps or [],
        "lower_gain_if_pass":gain,
        "upper_loss_if_fail":loss,
        "margin_gain_if_pass":margin,
    }
    if route:
        out["route_class"]=route
    return out

class ThresholdProofDagTests(unittest.TestCase):
    def test_additive_existing_lower_bound_closes_without_actions(self):
        d=base("ADDITIVE_THRESHOLD",total_mass=100,threshold_mass=66.4,current_lower_mass=67,current_upper_mass=90)
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["verdict"],"PASS")
        self.assertEqual(o["compiled"]["minimum_pass_cut"],[])

    def test_additive_exact_minimum_critical_path_cut(self):
        d=base("ADDITIVE_THRESHOLD",total_mass=100,threshold_mass=66,current_lower_mass=60,current_upper_mass=100)
        d["actions"]=[
            action("slow-one",10,gain=6,cov=["x"]),
            action("fast-a",2,gain=3,cov=["a"]),
            action("fast-b",2,gain=3,cov=["b"]),
        ]
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["minimum_pass_cut"]["actions"],["fast-a","fast-b"])
        self.assertEqual(o["compiled"]["minimum_pass_cut"]["critical_path_seconds"],"2")

    def test_dependencies_count_in_critical_path(self):
        d=base("ADDITIVE_THRESHOLD",total_mass=10,threshold_mass=8,current_lower_mass=5,current_upper_mass=10)
        d["actions"]=[
            action("prep",2,gain=0,cov=["prep"]),
            action("measure",3,gain=3,cov=["m"],deps=["prep"]),
        ]
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["minimum_pass_cut"]["critical_path_seconds"],"5")
        self.assertEqual(o["compiled"]["minimum_pass_cut"]["actions"],["measure","prep"])

    def test_overlap_cannot_double_count(self):
        d=base("ADDITIVE_THRESHOLD",total_mass=10,threshold_mass=9,current_lower_mass=5,current_upper_mass=10)
        d["actions"]=[
            action("a",1,gain=2,cov=["same"]),
            action("b",1,gain=2,cov=["same"]),
        ]
        o=compile_threshold_proof_dag(d)
        self.assertIsNone(o["compiled"]["minimum_pass_cut"])

    def test_failure_cut_is_strict(self):
        d=base("ADDITIVE_THRESHOLD",total_mass=10,threshold_mass=7,current_lower_mass=1,current_upper_mass=9)
        d["actions"]=[
            action("lose2",1,loss=2,cov=["x"]),
            action("lose3",1,loss=3,cov=["y"]),
        ]
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["minimum_fail_cut"]["actions"],["lose3"])

    def test_fresh_reality_is_blocked(self):
        d=base("ADDITIVE_THRESHOLD",total_mass=10,threshold_mass=6,current_lower_mass=5,current_upper_mass=10)
        d["actions"]=[action("fresh",1,gain=5,zr=False)]
        o=compile_threshold_proof_dag(d)
        self.assertIn("fresh",o["blocked_fresh_reality_actions"])
        self.assertIsNone(o["compiled"]["minimum_pass_cut"])

    def test_relative_rating_requires_relative_bridge_or_owner_score(self):
        d=base("RELATIVE_RATING_THRESHOLD",threshold_rating=1846)
        d["actions"]=[action("absolute-proof",1,route="ABSOLUTE_PROOF")]
        o=compile_threshold_proof_dag(d)
        self.assertIsNone(o["compiled"]["minimum_pass_cut"])
        d["actions"]=[action("owner-score",3,route="OWNER_SCORE_RECEIPT")]
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["minimum_pass_cut"]["actions"],["owner-score"])

    def test_relative_verified_lower_bound_pass_requires_receipt(self):
        d=base("RELATIVE_RATING_THRESHOLD",threshold_rating=1846,verified_rating_lower=1900)
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        d["target"]["verified_relative_bridge_receipt"]=receipt("bridge.json")
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["verdict"],"PASS")

    def test_matched_noninferiority_uses_margin_only(self):
        d=base("MATCHED_NONINFERIORITY",brain_lower=0.70,comparator_upper=0.75)
        d["actions"]=[
            action("brain-bound",2,margin=0.03,cov=["a"]),
            action("opus-bound",2,margin=0.02,cov=["b"]),
        ]
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["minimum_pass_cut"]["critical_path_seconds"],"2")
        self.assertEqual(o["compiled"]["minimum_pass_cut"]["actions"],["brain-bound","opus-bound"])

    def test_gated_weighted_dealbreaker_zeroes_component(self):
        d=base(
            "GATED_WEIGHTED_THRESHOLD",
            threshold_mass=0.5,
            components=[
                {"id":"q1","weight":0.6,"score_lower":0.9,"score_upper":1.0,"gate":"FAIL"},
                {"id":"q2","weight":0.4,"score_lower":1.0,"score_upper":1.0,"gate":"PASS"},
            ],
        )
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["compiled"]["verdict"],"FAIL")
        self.assertEqual(o["compiled"]["upper"],"0.40")

    def test_cycle_fails_closed(self):
        d=base("ADDITIVE_THRESHOLD",total_mass=10,threshold_mass=6,current_lower_mass=0,current_upper_mass=10)
        d["actions"]=[
            action("a",1,gain=3,deps=["b"]),
            action("b",1,gain=3,deps=["a"]),
        ]
        o=compile_threshold_proof_dag(d)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertTrue(any("CYCLE" in e for e in o["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
