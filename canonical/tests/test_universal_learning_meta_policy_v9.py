from __future__ import annotations
import unittest
from canonical.runtime import meta_learning_policy_v9 as mp
from canonical.runtime import meta_strategy_abstraction_v9 as ma
from canonical.runtime import universal_learning_meta_policy_router_v9 as r9

class MetaPolicyTests(unittest.TestCase):
    def episode(self, *, ctx, eid, sid, success=True, b0=10, b1=5, t=1, risk=0, spend=0):
        csha=mp.context_digest(features=ctx)
        dig=mp.episode_digest(
            episode_id=eid,context_sha256=csha,strategy_id=sid,success=success,
            burden_before=b0,burden_after=b1,wall_clock=t,risk=risk,incremental_spend_usd=spend
        )
        return {
            "episode_id":eid,"context_sha256":csha,"strategy_id":sid,"success":success,
            "burden_before":b0,"burden_after":b1,"wall_clock":t,"risk":risk,"incremental_spend_usd":spend,
            "verification_receipt":{
                "receipt_id":"r-"+eid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","episode_id":eid,"episode_sha256":dig,
            },
        }

    def test_matched_context_prefers_strongest_verified_burden_reduction(self):
        ctx=["interactive","source-rich"]
        out=mp.recommend(context_features=ctx,episodes=[
            self.episode(ctx=ctx,eid="a",sid="inspect-first",b1=1,t=3),
            self.episode(ctx=ctx,eid="b",sid="probe-first",b1=4,t=1),
        ])
        self.assertEqual(out["recommended_strategy_id"],"inspect-first")
        self.assertTrue(out["planning_only"])
        self.assertFalse(out["execution_authority"])

    def test_context_leakage_rejected(self):
        with self.assertRaises(mp.MetaLearningError):
            mp.recommend(
                context_features=["A"],
                episodes=[self.episode(ctx=["B"],eid="x",sid="s")]
            )

    def test_failed_strategy_not_admissible(self):
        ctx=["x"]
        out=mp.recommend(context_features=ctx,episodes=[
            self.episode(ctx=ctx,eid="good",sid="safe",success=True,b1=5),
            self.episode(ctx=ctx,eid="bad",sid="fast",success=False,b1=1),
        ])
        self.assertEqual(out["recommended_strategy_id"],"safe")

    def test_regressive_strategy_not_admissible(self):
        ctx=["x"]
        out=mp.recommend(context_features=ctx,episodes=[
            self.episode(ctx=ctx,eid="r",sid="regress",b0=5,b1=6),
        ])
        self.assertIsNone(out["recommended_strategy_id"])
        self.assertEqual(out["status"],"NO_NO_REGRESSION_STRATEGY")

    def test_positive_spend_rejected(self):
        ctx=["x"]
        with self.assertRaises(mp.MetaLearningError):
            mp.recommend(context_features=ctx,episodes=[
                self.episode(ctx=ctx,eid="p",sid="paid",spend="0.01")
            ])

class MetaAbstractionTests(unittest.TestCase):
    def strategy(self,sid,steps,verified=True):
        return {
            "strategy_id":sid,"steps":steps,
            "verification_receipt":{
                "receipt_id":"r-"+sid,"independent_verified":verified,"exact_byte_bound":True,
                "conclusion":"success","strategy_id":sid,"skeleton_sha256":ma.skeleton_digest(steps),
            },
        }

    def test_common_verified_structure_is_candidate_only(self):
        out=ma.induce_candidate([
            self.strategy("a",["decompose","verify","compile"]),
            self.strategy("b",["decompose","experiment","verify","compile"]),
        ])
        self.assertEqual(out["common_steps"],["compile","decompose","verify"])
        self.assertFalse(out["verified_abstraction"])
        self.assertFalse(out["reuse_authorized"])

    def test_unverified_strategy_rejected(self):
        with self.assertRaises(ma.MetaStrategyError):
            ma.induce_candidate([
                self.strategy("a",["verify"]),
                self.strategy("b",["verify"],verified=False),
            ])

    def test_no_common_structure_rejected(self):
        with self.assertRaises(ma.MetaStrategyError):
            ma.induce_candidate([
                self.strategy("a",["inspect"]),
                self.strategy("b",["experiment"]),
            ])

class RouterInvariantTests(unittest.TestCase):
    def test_v9_invariant_bundle(self):
        out=r9.prove_v9_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["v8_base_preserved"])
        self.assertTrue(out["meta_policy_planning_only"])
        self.assertTrue(out["meta_abstraction_candidate_only"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["acceptance_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
