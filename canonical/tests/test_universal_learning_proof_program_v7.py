from __future__ import annotations

import unittest

from canonical.runtime import deductive_closure_v7 as dc
from canonical.runtime import executable_skill_program_v7 as sp
from canonical.runtime import universal_learning_proof_program_router_v7 as v7


def fact(scope,fact,rid=None):
    return {
        "fact":fact,
        "verification_receipt":{
            "receipt_id":rid or "fact-"+fact,
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "scope_id":scope,
            "fact":fact,
            "fact_sha256":dc.fact_digest(scope_id=scope,fact=fact),
        },
    }


def rule(scope,rid,premises,conclusion):
    return {
        "id":rid,
        "premises":premises,
        "conclusion":conclusion,
        "verification_receipt":{
            "receipt_id":"receipt-"+rid,
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "sound_on_claimed_scope":True,
            "scope_id":scope,
            "rule_id":rid,
            "rule_sha256":dc.rule_digest(
                scope_id=scope,rule_id=rid,premises=premises,conclusion=conclusion
            ),
        },
    }


STEPS=[
    {"op":"inspect","inputs":["target"],"outputs":["model"]},
    {"op":"test","inputs":["model"],"outputs":["evidence"]},
    {"op":"verify","inputs":["evidence"],"outputs":["proof"]},
]


def episode(eid,scope,*,steps=STEPS,verified=True,pre=None,post=None,invalid=None):
    pre=pre or ["target-present","safe-access"]
    post=post or ["proof"]
    invalid=invalid or ["target-changed"]
    digest=sp.program_digest(
        steps=steps,preconditions=pre,postconditions=post,invalidators=invalid
    )
    return {
        "episode_id":eid,
        "scope_id":scope,
        "steps":steps,
        "preconditions":pre,
        "postconditions":post,
        "invalidators":invalid,
        "verification_receipt":{
            "receipt_id":"episode-"+eid,
            "independent_verified":verified,
            "exact_byte_bound":True,
            "conclusion":"success",
            "behavior_verified":True,
            "episode_id":eid,
            "scope_id":scope,
            "program_sha256":digest,
        },
    }


class DeductiveClosureV7Tests(unittest.TestCase):
    def test_transitive_verified_closure_shrinks_empirical_frontier(self):
        out=dc.derive(
            scope_id="s",
            verified_facts=[fact("s","a")],
            verified_rules=[
                rule("s","r1",["a"],"b"),
                rule("s","r2",["b"],"c"),
            ],
            required_facts=["c","d"],
        )
        self.assertEqual(out["closure"],["a","b","c"])
        self.assertEqual(out["empirical_frontier"],["d"])
        self.assertTrue(out["empirical_action_required"])

    def test_fully_derivable_requirement_forbids_empirical_frontier(self):
        out=dc.derive(
            scope_id="s",
            verified_facts=[fact("s","a")],
            verified_rules=[rule("s","r1",["a"],"b")],
            required_facts=["b"],
        )
        self.assertEqual(out["status"],"PROOF_SUFFICIENT_NO_EMPIRICAL_FRONTIER")
        self.assertFalse(out["empirical_action_required"])

    def test_tampered_fact_digest_rejected(self):
        x=fact("s","a")
        x["verification_receipt"]["fact_sha256"]="sha256:"+"0"*64
        with self.assertRaises(dc.DeductiveClosureError):
            dc.derive(scope_id="s",verified_facts=[x],verified_rules=[],required_facts=["a"])

    def test_unverified_rule_rejected(self):
        r=rule("s","r1",["a"],"b")
        r["verification_receipt"]["independent_verified"]=False
        with self.assertRaises(dc.DeductiveClosureError):
            dc.derive(scope_id="s",verified_facts=[fact("s","a")],verified_rules=[r],required_facts=["b"])

    def test_scope_mismatch_rejected(self):
        with self.assertRaises(dc.DeductiveClosureError):
            dc.derive(scope_id="other",verified_facts=[fact("s","a")],verified_rules=[],required_facts=["a"])


class ExecutableSkillProgramV7Tests(unittest.TestCase):
    def test_repeated_verified_program_induces_candidate_only(self):
        out=sp.induce_candidate([episode("e1","a"),episode("e2","b")])
        self.assertEqual(out["status"],"EXECUTABLE_SKILL_CANDIDATE_ONLY")
        self.assertFalse(out["verified_skill"])
        self.assertFalse(out["reuse_authorized"])
        self.assertEqual([x["op"] for x in out["steps"]],["inspect","test","verify"])

    def test_program_uses_common_guarantees_and_union_invalidators(self):
        e1=episode("e1","a",pre=["x","shared"],post=["proof","shared-post"],invalid=["i1"])
        e2=episode("e2","b",pre=["y","shared"],post=["done","shared-post"],invalid=["i2"])
        out=sp.induce_candidate([e1,e2])
        self.assertEqual(out["preconditions"],["shared"])
        self.assertEqual(out["postconditions"],["shared-post"])
        self.assertEqual(out["invalidators"],["i1","i2"])

    def test_different_program_skeleton_rejected(self):
        other=[
            {"op":"inspect","inputs":["target"],"outputs":["model"]},
            {"op":"guess","inputs":["model"],"outputs":["proof"]},
        ]
        with self.assertRaises(sp.ExecutableSkillProgramError):
            sp.induce_candidate([episode("e1","a"),episode("e2","b",steps=other)])

    def test_unverified_episode_rejected(self):
        with self.assertRaises(sp.ExecutableSkillProgramError):
            sp.induce_candidate([episode("e1","a"),episode("e2","b",verified=False)])

    def test_candidate_requires_external_behavior_proof(self):
        cand=sp.induce_candidate([episode("e1","a"),episode("e2","b")])
        receipt={
            "receipt_id":"program-proof",
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "candidate_sha256":cand["candidate_sha256"],
            "source_episode_ids":cand["source_episode_ids"],
            "behavior_preserving_on_claimed_scope":True,
            "scope_relation":"PROVEN_SUPERSET",
        }
        out=sp.verify_candidate(candidate=cand,verification_receipt=receipt)
        self.assertTrue(out["verified_skill"])
        self.assertTrue(out["reuse_authorized"])
        self.assertFalse(out["promotion_authority"])

    def test_self_certifying_candidate_receipt_rejected(self):
        cand=sp.induce_candidate([episode("e1","a"),episode("e2","b")])
        receipt={
            "receipt_id":"self",
            "independent_verified":False,
            "exact_byte_bound":True,
            "conclusion":"success",
            "candidate_sha256":cand["candidate_sha256"],
            "source_episode_ids":cand["source_episode_ids"],
            "behavior_preserving_on_claimed_scope":True,
            "scope_relation":"EXACT",
        }
        with self.assertRaises(sp.ExecutableSkillProgramError):
            sp.verify_candidate(candidate=cand,verification_receipt=receipt)


class UniversalLearningV7RouterTests(unittest.TestCase):
    def test_proof_sufficiency_blocks_empirical_learning(self):
        out=v7.route(
            goal="solve",
            environment_id="env",
            scope_id="scope",
            required_facts=["b"],
            verified_fact_evidence=[fact("scope","a")],
            verified_rules=[rule("scope","r",["a"],"b")],
            learning_episodes=[episode("e1","x"),episode("e2","y")],
            verified_coverage=False,
            goal_facts=["b"],
            fallback_required_facts=["b"],
            dependencies={},
            dependency_receipt=None,
            transfer_mappings=[],
            mechanism_candidates=[
                {"id":"m","best_action":"A","predictions":{"p":"x"},"invariants":[],"provenance":["src"]}
            ],
            observations=[],
            hypothesis_coverage_receipt=None,
            residual_action_receipt=None,
            probes=[],
            verified_skills=[],
        )
        self.assertEqual(out["route"],"PROOF_SUFFICIENT_NO_EMPIRICAL_LEARNING")
        self.assertFalse(out["empirical_information_action_authorized"])
        self.assertIsNone(out["v6_result"])
        self.assertEqual(out["executable_skill_candidate_status"],"EXECUTABLE_SKILL_CANDIDATE_ONLY")

    def test_unresolved_fact_is_the_only_empirical_frontier(self):
        out=v7.route(
            goal="solve",
            environment_id="env",
            scope_id="scope",
            required_facts=["a","unknown"],
            verified_fact_evidence=[fact("scope","a")],
            verified_rules=[],
            learning_episodes=[],
            verified_coverage=False,
            goal_facts=["unknown"],
            fallback_required_facts=["unknown"],
            dependencies={},
            dependency_receipt=None,
            transfer_mappings=[],
            mechanism_candidates=[
                {"id":"m","best_action":"A","predictions":{"p":"x"},"invariants":[],"provenance":["src"]}
            ],
            observations=[],
            hypothesis_coverage_receipt=None,
            residual_action_receipt=None,
            probes=[],
            verified_skills=[],
        )
        self.assertEqual(out["deductive_closure"]["empirical_frontier"],["unknown"])
        self.assertTrue(out["empirical_information_action_authorized"])
        self.assertIsNotNone(out["v6_result"])

    def test_v7_invariant_bundle(self):
        out=v7.prove_v7_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["deduction_before_observation_preserved"])
        self.assertTrue(out["executable_program_candidate_no_self_verification_preserved"])
        self.assertTrue(out["v6_base_preserved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
