#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=CANONICAL_ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("astra_runtime_untrusted_proposal_test",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)


class UntrustedCapabilityProposalTests(unittest.TestCase):
    def registry(self,spend=0):
        return {
            "test.fetch":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":spend,
                "requires":["network.http.available"],
                "provides":["knowledge.observation.available"],
                "cost":1,
                "result_fields":["output_path","value"],
                "platforms":["linux","windows","darwin"],
                "action_template":{
                    "type":"fetch_json_knowledge",
                    "args":{
                        "url":"${input.url}",
                        "json_path":"${input.json_path}",
                        "output_path":"${input.output_path}",
                        "authoritative":False,
                    },
                },
            }
        }

    def step(self,proposal):
        return {
            "verified_initial_facts":["network.http.available"],
            "required_target_effects":["knowledge.observation.a.available"],
            "capability_problem_proposal":proposal,
        }

    def test_proposal_can_only_reference_verified_capability_and_frozen_goal_contract(self):
        proposal={
            "finish_summary":"SAFE_PROPOSAL_COMPLETE",
            "capability_instances":[{
                "instance_id":"observe-a",
                "capability_id":"test.fetch",
                "inputs":{
                    "url":"https://example.test/data",
                    "json_path":["value"],
                    "output_path":"a.json",
                },
                "provides_as":{
                    "knowledge.observation.available":"knowledge.observation.a.available"
                },
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            out=runtime._capability_problem_proposal(self.step(proposal),{})
        self.assertEqual(out["initial_facts"],["network.http.available"])
        self.assertEqual(out["target_effects"],["knowledge.observation.a.available"])
        self.assertEqual(out["capabilities"],[])
        self.assertEqual(out["_proposal_contract"],"VERIFIED_REGISTRY_REFERENCES_ONLY")
        self.assertEqual(out["capability_instances"][0]["capability_id"],"test.fetch")

    def test_proposal_cannot_redefine_initial_facts_or_target_effects(self):
        proposal={
            "initial_facts":["fabricated.root"],
            "target_effects":["easy.fake.success"],
            "capability_instances":[{
                "instance_id":"observe-a",
                "capability_id":"test.fetch",
                "inputs":{"url":"https://example.test","json_path":[],"output_path":"a.json"},
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"CAPABILITY_PROPOSAL_TOP_LEVEL_FIELD_REJECTED"):
                runtime._capability_problem_proposal(self.step(proposal),{})

    def test_proposal_cannot_inject_raw_capability_or_action(self):
        proposal={
            "capabilities":[{
                "id":"invented",
                "action":{"type":"finish","args":{"summary":"fake"}},
            }],
            "capability_instances":[{
                "instance_id":"observe-a",
                "capability_id":"test.fetch",
                "inputs":{"url":"https://example.test","json_path":[],"output_path":"a.json"},
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"CAPABILITY_PROPOSAL_TOP_LEVEL_FIELD_REJECTED"):
                runtime._capability_problem_proposal(self.step(proposal),{})

    def test_proposal_cannot_reference_unverified_or_unknown_capability(self):
        proposal={
            "capability_instances":[{
                "instance_id":"bad",
                "capability_id":"unknown.capability",
                "inputs":{},
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"CAPABILITY_PROPOSAL_SOURCE_NOT_VERIFIED"):
                runtime._capability_problem_proposal(self.step(proposal),{})

    def test_proposal_rejects_nonzero_incremental_spend_capability(self):
        proposal={
            "capability_instances":[{
                "instance_id":"paid",
                "capability_id":"test.fetch",
                "inputs":{"url":"https://example.test","json_path":[],"output_path":"a.json"},
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry(spend=0.01)):
            with self.assertRaisesRegex(runtime.Blocker,"CAPABILITY_PROPOSAL_NONZERO_SPEND_REJECTED"):
                runtime._capability_problem_proposal(self.step(proposal),{})

    def test_proposal_allows_effect_result_but_rejects_raw_result_reference(self):
        allowed={
            "capability_instances":[{
                "instance_id":"observe-a",
                "capability_id":"test.fetch",
                "inputs":{
                    "url":"https://example.test",
                    "json_path":[],
                    "output_path":{"$effect_result":{"effect":"prior.effect","field":"output_path"}},
                },
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            out=runtime._capability_problem_proposal(self.step(allowed),{})
        self.assertIn("$effect_result",out["capability_instances"][0]["inputs"]["output_path"])

        rejected={
            "capability_instances":[{
                "instance_id":"observe-a",
                "capability_id":"test.fetch",
                "inputs":{
                    "url":"https://example.test",
                    "json_path":[],
                    "output_path":{"$result":{"cycle":999,"field":"value"}},
                },
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=self.registry()):
            with self.assertRaisesRegex(runtime.Blocker,"CAPABILITY_PROPOSAL_SPECIAL_VALUE_REJECTED"):
                runtime._capability_problem_proposal(self.step(rejected),{})


if __name__=="__main__":
    unittest.main(verbosity=2)
