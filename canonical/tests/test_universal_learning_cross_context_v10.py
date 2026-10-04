from __future__ import annotations
import unittest
from canonical.runtime import meta_learning_policy_v9 as mp
from canonical.runtime import context_morphism_v10 as cm
from canonical.runtime import cross_context_meta_policy_v10 as cc
from canonical.runtime import universal_learning_cross_context_router_v10 as r10

class V10Tests(unittest.TestCase):
    def setUp(self):
        self.src=["source-code-rich","interactive"]
        self.dst=["new-sdk","interactive"]
        self.ssha=mp.context_digest(features=self.src)
        self.dsha=mp.context_digest(features=self.dst)
        self.semantics={
            "ordered_steps":["inspect","model","verify"],
            "preconditions":["source-inspectable"],
            "invalidators":["source-unavailable"],
        }

    def ep(self,eid,*,sid="inspect-first",success=True,b0=10,b1=3,t=2,risk=0,spend=0,ctx=None):
        csha=ctx or self.ssha
        dig=mp.episode_digest(
            episode_id=eid,context_sha256=csha,strategy_id=sid,success=success,
            burden_before=b0,burden_after=b1,wall_clock=t,risk=risk,incremental_spend_usd=spend)
        return {
            "episode_id":eid,"context_sha256":csha,"strategy_id":sid,"success":success,
            "burden_before":b0,"burden_after":b1,"wall_clock":t,"risk":risk,"incremental_spend_usd":spend,
            "verification_receipt":{
                "receipt_id":"r-"+eid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","episode_id":eid,"episode_sha256":dig}}

    def morphism(self,*,sid="inspect-first",episodes=None,valid=True,src=None,dst=None,semantics=None):
        src=src or self.ssha; dst=dst or self.dsha
        semantics=semantics or self.semantics
        episodes=episodes or [self.ep("e1",sid=sid),self.ep("e2",sid=sid,b1=4)]
        strategy_sha=cm.strategy_semantics_digest(strategy_id=sid,strategy_semantics=semantics)
        episode_set_sha=cm.source_episode_set_digest(
            strategy_sha256=strategy_sha,episode_ids=[x["episode_id"] for x in episodes])
        pre=["source-inspectable"]; metrics=["BURDEN_REDUCTION","WALL_CLOCK","RISK"]; inv=["source-unavailable"]
        md=cm.morphism_digest(
            source_context_sha256=src,target_context_sha256=dst,strategy_id=sid,
            strategy_sha256=strategy_sha,source_episode_set_sha256=episode_set_sha,
            preserved_preconditions=pre,preserved_metric_semantics=metrics,invalidators_checked=inv)
        return {
            "source_context_sha256":src,"target_context_sha256":dst,"strategy_id":sid,
            "strategy_sha256":strategy_sha,"source_episode_set_sha256":episode_set_sha,
            "preserved_preconditions":pre,"preserved_metric_semantics":metrics,"invalidators_checked":inv,
            "verification_receipt":{
                "receipt_id":"m1","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
                "strategy_applicability_preserved":True,
                "performance_metric_semantics_preserved":True,
                "no_new_strategy_invalidators":valid,
                "conservative_performance_transport_valid":True,
                "source_episodes_executed_bound_strategy":True,
                "source_context_sha256":src,"target_context_sha256":dst,"strategy_id":sid,
                "strategy_sha256":strategy_sha,"source_episode_set_sha256":episode_set_sha,
                "morphism_sha256":md}}

    def candidate(self,**kw):
        sid=kw.get("sid","inspect-first")
        episodes=kw.get("episodes",[self.ep("e1",sid=sid),self.ep("e2",sid=sid,b1=4)])
        semantics=kw.get("semantics",self.semantics)
        return {
            "source_context_features":self.src,"strategy_id":sid,
            "strategy_semantics":semantics,"source_episodes":episodes,
            "context_morphism":kw.get("morphism",self.morphism(sid=sid,episodes=episodes,semantics=semantics))}

    def test_verified_cold_start_transfer(self):
        out=cc.recommend(target_context_features=self.dst,transfer_candidates=[self.candidate()])
        self.assertEqual(out["recommended_strategy_id"],"inspect-first")
        self.assertEqual(out["evidence_mode"],"PROOF_GATED_ONE_WAY_CONTEXT_MORPHISM")
        self.assertFalse(out["execution_authority"])

    def test_strategy_semantics_tamper_blocked(self):
        c=self.candidate()
        c["strategy_semantics"]={**self.semantics,"ordered_steps":["inspect","execute"]}
        out=cc.recommend(target_context_features=self.dst,transfer_candidates=[c])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_source_episode_set_tamper_blocked(self):
        c=self.candidate()
        c["source_episodes"]=[self.ep("e1"),self.ep("e3")]
        out=cc.recommend(target_context_features=self.dst,transfer_candidates=[c])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_unverified_morphism_blocked(self):
        episodes=[self.ep("e1"),self.ep("e2")]
        out=cc.recommend(target_context_features=self.dst,
            transfer_candidates=[self.candidate(
                episodes=episodes,morphism=self.morphism(episodes=episodes,valid=False))])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_context_binding_mismatch_blocked(self):
        episodes=[self.ep("e1"),self.ep("e2")]
        bad=self.morphism(episodes=episodes,dst=mp.context_digest(features=["other"]))
        out=cc.recommend(target_context_features=self.dst,
            transfer_candidates=[self.candidate(episodes=episodes,morphism=bad)])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_insufficient_source_evidence_blocked(self):
        episodes=[self.ep("one")]
        out=cc.recommend(target_context_features=self.dst,
            transfer_candidates=[self.candidate(episodes=episodes,
                morphism=self.morphism(episodes=episodes))])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_failed_source_episode_blocked(self):
        episodes=[self.ep("a"),self.ep("b",success=False)]
        out=cc.recommend(target_context_features=self.dst,
            transfer_candidates=[self.candidate(episodes=episodes,
                morphism=self.morphism(episodes=episodes))])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_positive_spend_source_blocked(self):
        episodes=[self.ep("a"),self.ep("b",spend="0.01")]
        out=cc.recommend(target_context_features=self.dst,
            transfer_candidates=[self.candidate(episodes=episodes,
                morphism=self.morphism(episodes=episodes))])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_exact_target_policy_has_priority(self):
        target_eps=[
            self.ep("t1",sid="target-native",ctx=self.dsha,b1=1),
            self.ep("t2",sid="target-native",ctx=self.dsha,b1=2),
        ]
        out=cc.recommend(target_context_features=self.dst,exact_target_episodes=target_eps,
                         transfer_candidates=[self.candidate()])
        self.assertEqual(out["recommended_strategy_id"],"target-native")
        self.assertEqual(out["evidence_mode"],"EXACT_TARGET_CONTEXT")

    def test_exact_target_failure_blocks_transfer(self):
        target_eps=[
            self.ep("t1",sid="bad",ctx=self.dsha,b0=5,b1=6),
            self.ep("t2",sid="bad",ctx=self.dsha,b0=5,b1=7),
        ]
        out=cc.recommend(target_context_features=self.dst,exact_target_episodes=target_eps,
                         transfer_candidates=[self.candidate()])
        self.assertIsNone(out["recommended_strategy_id"])
        self.assertEqual(out["status"],"EXACT_TARGET_EVIDENCE_BLOCKS_CROSS_CONTEXT_FALLBACK")

    def test_v10_invariants(self):
        out=r10.prove_v10_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["v9_base_preserved"])
        self.assertTrue(out["exact_strategy_semantics_binding_preserved"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
