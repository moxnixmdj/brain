from __future__ import annotations

import unittest

from canonical.runtime import learning_strategy_optimizer_v9 as opt
from canonical.runtime import meta_strategy_abstraction_v9 as msa
from canonical.runtime import universal_learning_meta_router_v9 as v9


def episodes(candidate="new", candidate_success=True, candidate_clock="5"):
    return [
        {"strategy_id":"old","task_id":"t","verified":True,"success":True,"safety_violation":False,
         "wall_clock":"10","reality_calls":1,"information_actions":3},
        {"strategy_id":candidate,"task_id":"t","verified":True,"success":candidate_success,"safety_violation":False,
         "wall_clock":candidate_clock,"reality_calls":1,"information_actions":2},
    ]


def verified_policy(env="api",strategy="new"):
    eps=episodes(candidate=strategy)
    comp=opt.meta.compare(episodes=eps,incumbent="old",candidate=strategy)
    cr={
        "receipt_id":"cmp-"+env,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
        "environment_class":env,"candidate_strategy":strategy,"comparison_sha256":comp["comparison_sha256"],
    }
    cand=opt.build_policy_candidate(
        episodes=eps,incumbent_strategy="old",candidate_strategy=strategy,
        environment_class=env,comparison_verification_receipt=cr,
    )
    pr={
        "receipt_id":"policy-"+env,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
        "environment_class":env,"strategy_id":strategy,"policy_sha256":cand["policy_sha256"],
    }
    return opt.verify_policy_candidate(candidate=cand,policy_artifact_receipt=pr)


def mapping(policy,target,relation="SOURCE_PROVEN_SUPERSET_OF_TARGET"):
    src=policy["environment_class"]; strategy=policy["preferred_learning_strategy"]
    dg=opt.class_mapping_digest(source_class=src,target_class=target,strategy_id=strategy,relation=relation)
    return {
        "source_class":src,"target_class":target,"strategy_id":strategy,"relation":relation,
        "verification_receipt":{
            "receipt_id":"map-"+src+"-"+target,"independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","strategy_behavior_preserved_on_target":True,
            "source_class":src,"target_class":target,"strategy_id":strategy,"relation":relation,
            "mapping_sha256":dg,
        },
    }


def strategy(sid,level,sig):
    dg=msa.signature_digest(sig)
    return {
        "strategy_id":sid,"meta_level":level,"canonical_strategy_signature":sig,
        "verification_receipt":{
            "receipt_id":"s-"+sid,"independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","behavior_verified":True,
            "strategy_id":sid,"meta_level":level,"canonical_signature_sha256":dg,
        },
    }


class LearningStrategyOptimizerV9Tests(unittest.TestCase):
    def test_verified_exact_policy_selected(self):
        p=verified_policy()
        out=opt.select_strategy(environment_class="api",policies=[p])
        self.assertEqual(out["preferred_learning_strategy"],"new")
        self.assertTrue(out["selection_authorized"])
        self.assertFalse(out["execution_authority"])

    def test_policy_candidate_cannot_select_before_independent_verification(self):
        eps=episodes()
        comp=opt.meta.compare(episodes=eps,incumbent="old",candidate="new")
        cr={"receipt_id":"c","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
            "environment_class":"api","candidate_strategy":"new","comparison_sha256":comp["comparison_sha256"]}
        cand=opt.build_policy_candidate(
            episodes=eps,incumbent_strategy="old",candidate_strategy="new",
            environment_class="api",comparison_verification_receipt=cr)
        with self.assertRaises(opt.LearningStrategyOptimizerError):
            opt.select_strategy(environment_class="api",policies=[cand])

    def test_regressing_strategy_cannot_create_policy_candidate(self):
        eps=episodes(candidate_success=False)
        comp=opt.meta.compare(episodes=eps,incumbent="old",candidate="new")
        self.assertFalse(comp["preference_admissible"])
        cr={"receipt_id":"c","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
            "environment_class":"api","candidate_strategy":"new","comparison_sha256":comp["comparison_sha256"]}
        with self.assertRaises(Exception):
            opt.build_policy_candidate(
                episodes=eps,incumbent_strategy="old",candidate_strategy="new",
                environment_class="api",comparison_verification_receipt=cr)

    def test_unseen_class_falls_back_without_mapping(self):
        p=verified_policy()
        out=opt.select_strategy(environment_class="unseen",policies=[p])
        self.assertFalse(out["selection_authorized"])
        self.assertIsNone(out["preferred_learning_strategy"])
        self.assertEqual(out["fallback"],"UNIVERSAL_LEARNING_EQUIVALENCE_BASIS_ROUTER_V8")

    def test_proved_class_mapping_transfers_strategy(self):
        p=verified_policy()
        out=opt.select_strategy(environment_class="schema-api",policies=[p],class_mappings=[mapping(p,"schema-api")])
        self.assertEqual(out["preferred_learning_strategy"],"new")
        self.assertTrue(out["selection_authorized"])

    def test_tampered_class_mapping_rejected(self):
        p=verified_policy()
        m=mapping(p,"schema-api")
        m["verification_receipt"]["mapping_sha256"]="sha256:bad"
        with self.assertRaises(opt.LearningStrategyOptimizerError):
            opt.select_strategy(environment_class="schema-api",policies=[p],class_mappings=[m])

    def test_conflicting_transferred_strategies_fail_closed(self):
        a=verified_policy("api-a","new")
        b=verified_policy("api-b","other")
        with self.assertRaises(opt.LearningStrategyOptimizerError):
            opt.select_strategy(
                environment_class="target",policies=[a,b],
                class_mappings=[mapping(a,"target"),mapping(b,"target")],
            )


class MetaStrategyAbstractionV9Tests(unittest.TestCase):
    def test_candidate_cannot_self_certify(self):
        cand=msa.induce_candidate([
            strategy("a",0,["probe","verify","a"]),
            strategy("b",0,["probe","verify","b"]),
        ])
        self.assertFalse(cand["verified_meta_strategy"])
        self.assertFalse(cand["recursive_reuse_authorized"])

    def test_independent_verification_enables_recursive_reuse(self):
        cand=msa.induce_candidate([
            strategy("a",0,["probe","verify","a"]),
            strategy("b",0,["probe","verify","b"]),
        ])
        receipt={
            "receipt_id":"meta","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
            "behavior_verified":True,"behavior_preserving_across_source_strategies":True,
            "candidate_sha256":cand["candidate_sha256"],"strategy_id":cand["strategy_id"],
            "meta_level":cand["meta_level"],"source_strategy_ids":cand["source_strategy_ids"],
            "canonical_signature_sha256":cand["canonical_signature_sha256"],"scope_relation":"EXACT",
        }
        verified=msa.verify_candidate(candidate=cand,verification_receipt=receipt)
        self.assertTrue(verified["recursive_reuse_authorized"])
        second=msa.induce_candidate([verified,strategy("c",0,["probe","verify","c"])])
        self.assertEqual(second["meta_level"],2)

    def test_unverified_source_rejected(self):
        bad=strategy("bad",0,["x"])
        bad["verification_receipt"]["independent_verified"]=False
        with self.assertRaises(msa.MetaStrategyAbstractionError):
            msa.induce_candidate([bad,strategy("good",0,["x"])])


class UniversalLearningV9Tests(unittest.TestCase):
    def test_router_never_overrides_v8_task_authority(self):
        original=v9.v8.route
        try:
            v9.v8.route=lambda **kwargs:{
                "route":"V8_ROUTE","next_action":{"type":"V8_ACTION"},
                "trusted_execution_authorized":False,
                "empirical_information_action_authorized":True,
            }
            out=v9.route(v8_args={},environment_class="none")
            self.assertEqual(out["route"],"V8_ROUTE")
            self.assertEqual(out["next_action"],{"type":"V8_ACTION"})
            self.assertFalse(out["trusted_execution_authorized"])
            self.assertFalse(out["execution_authority"])
        finally:
            v9.v8.route=original

    def test_invariant_bundle(self):
        out=v9.prove_v9_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["v8_base_preserved"])
        self.assertTrue(out["recursive_meta_abstraction"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertFalse(out["universal_strategy_superiority_proved"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["execution_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
