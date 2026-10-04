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

    def target_state(self,episodes=(),count_override=None):
        rows=[{"episode_id":x["episode_id"],"episode_sha256":x["verification_receipt"]["episode_sha256"]} for x in episodes]
        epoch="epoch-1"
        digest=cc.target_evidence_state_digest(
            target_context_sha256=self.dsha,episode_bindings=rows,evidence_epoch=epoch)
        return {
            "receipt_id":"ts1","independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","exact_target_evidence_complete":True,
            "target_context_sha256":self.dsha,"evidence_epoch":epoch,
            "exact_target_episode_count":len(rows) if count_override is None else count_override,
            "zero_exact_target_evidence_verified":len(rows)==0,
            "evidence_state_sha256":digest}

    def morphism(self,episodes,*,valid=True,semantics=None):
        semantics=semantics or self.semantics
        strategy_sha=cm.strategy_semantics_digest(strategy_id="inspect-first",strategy_semantics=semantics)
        bindings=[{"episode_id":x["episode_id"],"episode_sha256":x["verification_receipt"]["episode_sha256"]} for x in episodes]
        episode_set_sha=cm.source_episode_set_digest(strategy_sha256=strategy_sha,episode_bindings=bindings)
        pre=["source-inspectable"]; metrics=["BURDEN_REDUCTION","WALL_CLOCK","RISK"]; inv=["source-unavailable"]
        md=cm.morphism_digest(
            source_context_sha256=self.ssha,target_context_sha256=self.dsha,strategy_id="inspect-first",
            strategy_sha256=strategy_sha,source_episode_set_sha256=episode_set_sha,
            preserved_preconditions=pre,preserved_metric_semantics=metrics,invalidators_checked=inv)
        return {
            "source_context_sha256":self.ssha,"target_context_sha256":self.dsha,
            "strategy_id":"inspect-first","strategy_sha256":strategy_sha,
            "source_episode_set_sha256":episode_set_sha,
            "preserved_preconditions":pre,"preserved_metric_semantics":metrics,"invalidators_checked":inv,
            "verification_receipt":{
                "receipt_id":"m1","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
                "strategy_applicability_preserved":True,"performance_metric_semantics_preserved":True,
                "no_new_strategy_invalidators":valid,"conservative_performance_transport_valid":True,
                "source_episodes_executed_bound_strategy":True,
                "canonical_strategy_semantics_complete_for_transport":True,
                "source_policy_evidence_complete_for_bound_strategy":True,
                "source_episodes_distinct_evidence_instances":True,
                "source_context_strategy_relevant_scope_complete":True,
                "target_context_strategy_relevant_scope_complete":True,
                "source_context_sha256":self.ssha,"target_context_sha256":self.dsha,
                "strategy_id":"inspect-first","strategy_sha256":strategy_sha,
                "source_episode_set_sha256":episode_set_sha,"morphism_sha256":md}}

    def candidate(self,episodes=None,semantics=None,morphism=None):
        episodes=episodes or [self.ep("e1"),self.ep("e2",b1=4)]
        semantics=semantics or self.semantics
        return {
            "source_context_features":self.src,"strategy_id":"inspect-first",
            "strategy_semantics":semantics,"source_episodes":episodes,
            "context_morphism":morphism or self.morphism(episodes,semantics=semantics)}

    def call(self,**kw):
        return cc.recommend(
            target_context_features=self.dst,
            target_evidence_state_receipt=kw.pop("target_evidence_state_receipt",self.target_state()),
            **kw)

    def test_verified_cold_start_transfer(self):
        out=self.call(transfer_candidates=[self.candidate()])
        self.assertEqual(out["recommended_strategy_id"],"inspect-first")

    def test_missing_target_state_blocks_transfer(self):
        out=cc.recommend(target_context_features=self.dst,transfer_candidates=[self.candidate()])
        self.assertEqual(out["status"],"TARGET_EVIDENCE_STATE_UNVERIFIED")
        self.assertIsNone(out["recommended_strategy_id"])

    def test_tampered_target_state_blocks_transfer(self):
        out=self.call(
            target_evidence_state_receipt=self.target_state(count_override=1),
            transfer_candidates=[self.candidate()])
        self.assertIsNone(out["recommended_strategy_id"])

    def test_strategy_semantics_tamper_blocked(self):
        c=self.candidate()
        c["strategy_semantics"]={**self.semantics,"ordered_steps":["inspect","execute"]}
        self.assertIsNone(self.call(transfer_candidates=[c])["recommended_strategy_id"])

    def test_exact_episode_evidence_tamper_blocked(self):
        c=self.candidate()
        c["source_episodes"]=[self.ep("e1",b1=1),c["source_episodes"][1]]
        self.assertIsNone(self.call(transfer_candidates=[c])["recommended_strategy_id"])

    def test_duplicate_source_evidence_blocked(self):
        e=self.ep("dup")
        c={"source_context_features":self.src,"strategy_id":"inspect-first",
           "strategy_semantics":self.semantics,"source_episodes":[e,e],"context_morphism":{}}
        self.assertIsNone(self.call(transfer_candidates=[c])["recommended_strategy_id"])

    def test_incomplete_source_history_blocked(self):
        episodes=[self.ep("a"),self.ep("b")]
        m=self.morphism(episodes)
        m["verification_receipt"]["source_policy_evidence_complete_for_bound_strategy"]=False
        self.assertIsNone(self.call(
            transfer_candidates=[self.candidate(episodes=episodes,morphism=m)])["recommended_strategy_id"])

    def test_exact_target_policy_has_priority(self):
        target=[self.ep("t1",sid="native",ctx=self.dsha,b1=1),self.ep("t2",sid="native",ctx=self.dsha,b1=2)]
        out=cc.recommend(
            target_context_features=self.dst,exact_target_episodes=target,
            target_evidence_state_receipt=self.target_state(target),
            transfer_candidates=[self.candidate()])
        self.assertEqual(out["recommended_strategy_id"],"native")

    def test_exact_target_failure_blocks_transfer(self):
        target=[self.ep("t1",sid="bad",ctx=self.dsha,b0=5,b1=6),self.ep("t2",sid="bad",ctx=self.dsha,b0=5,b1=7)]
        out=cc.recommend(
            target_context_features=self.dst,exact_target_episodes=target,
            target_evidence_state_receipt=self.target_state(target),
            transfer_candidates=[self.candidate()])
        self.assertIsNone(out["recommended_strategy_id"])
        self.assertEqual(out["status"],"EXACT_TARGET_EVIDENCE_BLOCKS_CROSS_CONTEXT_FALLBACK")

    def test_v10_invariants(self):
        out=r10.prove_v10_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["target_evidence_state_completeness_preserved"])
        self.assertTrue(out["source_policy_history_completeness_preserved"])

if __name__=="__main__":
    unittest.main(verbosity=2)
