#!/usr/bin/env python3
import hashlib
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=CANONICAL_ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("astra_runtime_semantic_goal_quorum_test",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)


class SemanticGoalQuorumTests(unittest.TestCase):
    GOAL="Materialize the supported fact."
    TARGET="knowledge.fact.materialized"

    def registry(self):
        return {
            "test.materialize":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":[],
                "provides":[self.TARGET],
                "cost":1,
                "result_fields":["output_path"],
                "platforms":["linux","windows","darwin"],
                "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
            },
            "test.other":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":[],
                "provides":["other.effect"],
                "cost":1,
                "result_fields":[],
                "platforms":["linux","windows","darwin"],
                "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
            },
        }

    def candidate(self,authority_id,target=None):
        target=target or self.TARGET
        return {
            "authority_id":authority_id,
            "goal_sha256":hashlib.sha256(self.GOAL.encode("utf-8")).hexdigest(),
            "target_effects":[target],
            "clauses":[{
                "start":0,
                "end":len(self.GOAL),
                "text":self.GOAL,
                "target_effects":[target],
            }],
        }

    def policy(self,same_class=False):
        return {
            "min_distinct_authority_classes":2,
            "authorities":{
                "semantic-a":"family-a",
                "semantic-b":"family-a" if same_class else "family-b",
            },
        }

    def semantic_step(self,candidates=None,policy=None):
        return {
            "semantic_goal_proposals":candidates or [
                self.candidate("semantic-a"),
                self.candidate("semantic-b"),
            ],
            "semantic_authority_policy":policy or self.policy(),
        }

    def test_two_distinct_authority_classes_freeze_goal_contract(self):
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            contract=runtime._semantic_goal_contract(
                self.semantic_step(),{},self.GOAL
            )
        self.assertEqual(contract["status"],"QUORUM_VERIFIED")
        self.assertEqual(contract["target_effects"],[self.TARGET])
        self.assertEqual(contract["authority_classes"],["family-a","family-b"])
        self.assertEqual(contract["authority_ids"],["semantic-a","semantic-b"])

    def test_same_authority_class_does_not_create_independence(self):
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"SEMANTIC_GOAL_QUORUM_INVALID"):
                runtime._semantic_goal_contract(
                    self.semantic_step(policy=self.policy(same_class=True)),
                    {},
                    self.GOAL,
                )

    def test_disagreement_fails_closed_without_quorum(self):
        candidates=[
            self.candidate("semantic-a",self.TARGET),
            self.candidate("semantic-b","other.effect"),
        ]
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"SEMANTIC_GOAL_QUORUM_NOT_REACHED"):
                runtime._semantic_goal_contract(
                    self.semantic_step(candidates=candidates),{},self.GOAL
                )

    def test_unknown_target_effect_is_rejected(self):
        candidates=[
            self.candidate("semantic-a","unknown.effect"),
            self.candidate("semantic-b","unknown.effect"),
        ]
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"SEMANTIC_GOAL_TARGET_UNKNOWN"):
                runtime._semantic_goal_contract(
                    self.semantic_step(candidates=candidates),{},self.GOAL
                )

    def test_duplicate_authority_id_is_rejected(self):
        candidates=[
            self.candidate("semantic-a"),
            self.candidate("semantic-a"),
        ]
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"SEMANTIC_GOAL_AUTHORITY_DUPLICATE"):
                runtime._semantic_goal_contract(
                    self.semantic_step(candidates=candidates),{},self.GOAL
                )

    def test_goal_hash_mismatch_is_rejected(self):
        bad=self.candidate("semantic-a")
        bad["goal_sha256"]="0"*64
        candidates=[bad,self.candidate("semantic-b")]
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"SEMANTIC_GOAL_HASH_MISMATCH"):
                runtime._semantic_goal_contract(
                    self.semantic_step(candidates=candidates),{},self.GOAL
                )

    def test_quorum_can_supply_frozen_targets_to_constrained_capability_proposal(self):
        proposal={
            "goal_sha256":hashlib.sha256(self.GOAL.encode("utf-8")).hexdigest(),
            "clauses":[{
                "start":0,
                "end":len(self.GOAL),
                "text":self.GOAL,
                "target_effects":[self.TARGET],
            }],
            "capability_instances":[{
                "instance_id":"materialize",
                "capability_id":"test.materialize",
                "inputs":{},
            }],
        }
        step={
            "verified_initial_facts":[],
            "semantic_goal_proposals":[
                self.candidate("semantic-a"),
                self.candidate("semantic-b"),
            ],
            "semantic_authority_policy":self.policy(),
            "capability_problem_proposal":proposal,
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            problem=runtime._capability_problem_proposal(step,{},self.GOAL)
        self.assertEqual(problem["target_effects"],[self.TARGET])
        self.assertEqual(problem["_semantic_goal_contract"]["status"],"QUORUM_VERIFIED")

    def test_explicit_frozen_target_must_agree_with_semantic_quorum(self):
        proposal={
            "goal_sha256":hashlib.sha256(self.GOAL.encode("utf-8")).hexdigest(),
            "clauses":[{
                "start":0,
                "end":len(self.GOAL),
                "text":self.GOAL,
                "target_effects":["other.effect"],
            }],
            "capability_instances":[{
                "instance_id":"other",
                "capability_id":"test.other",
                "inputs":{},
            }],
        }
        step={
            "verified_initial_facts":[],
            "required_target_effects":["other.effect"],
            "semantic_goal_proposals":[
                self.candidate("semantic-a"),
                self.candidate("semantic-b"),
            ],
            "semantic_authority_policy":self.policy(),
            "capability_problem_proposal":proposal,
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(
                runtime.Blocker,
                "SEMANTIC_GOAL_CONTRACT_CONFLICTS_WITH_FROZEN_TARGETS",
            ):
                runtime._capability_problem_proposal(step,{},self.GOAL)


if __name__=="__main__":
    unittest.main(verbosity=2)
