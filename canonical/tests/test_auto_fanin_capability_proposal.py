#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

generator=load(
    "project_brain_test_fanin_capability_proposal_generator",
    RUNTIME_DIR/"capability_proposal_generators.py",
)


class AutoFanInCapabilityProposalTests(unittest.TestCase):
    TARGET="knowledge.assessment.available"

    def registry(self):
        platforms=["linux","windows","darwin"]
        return {
            "test.observe":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":["network.http.available"],
                "provides":["knowledge.observation.available"],
                "platforms":platforms,
                "cost":1,
                "result_fields":["output_path"],
                "action_template":{
                    "type":"fetch_json_knowledge",
                    "args":{
                        "url":"${input.url}",
                        "output_path":"${input.output_path}",
                    },
                },
                "proposal_bindings":{
                    "url":{"type":"goal_url"},
                    "output_path":{"type":"auto_path","suffix":".json"},
                },
            },
            "test.assess":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":["knowledge.observation.available"],
                "provides":[self.TARGET],
                "platforms":platforms,
                "cost":1,
                "result_fields":["output_path"],
                "action_template":{
                    "type":"assess_knowledge_consistency",
                    "args":{
                        "evidence_paths":"${input.evidence_paths}",
                        "output_path":"${input.output_path}",
                    },
                },
                "proposal_bindings":{
                    "evidence_paths":{
                        "type":"effect_result",
                        "effect":"knowledge.observation.available",
                        "field":"output_path",
                        "container":"list",
                    },
                    "output_path":{"type":"auto_path","suffix":".json"},
                },
            },
        }

    def generate(self,goal):
        return generator.generate(
            "multi-verified-capability-v1",
            goal,
            [self.TARGET],
            ["network.http.available"],
            self.registry(),
            CANONICAL_ROOT.parent,
            RUNTIME_DIR,
        )

    def test_two_distinct_goal_urls_expand_provider_and_alias_fanin(self):
        goal=(
            "Assess observations from https://one.example/a "
            "and https://two.example/b for consistency."
        )
        proposal,evidence=self.generate(goal)
        instances=proposal["capability_instances"]
        self.assertEqual(
            [x["instance_id"] for x in instances],
            ["auto-test-observe-1","auto-test-observe-2","auto-test-assess"],
        )
        self.assertEqual(
            [instances[0]["inputs"]["url"],instances[1]["inputs"]["url"]],
            ["https://one.example/a","https://two.example/b"],
        )
        alias1="knowledge.observation.available.fanin.1"
        alias2="knowledge.observation.available.fanin.2"
        self.assertEqual(
            instances[0]["provides_as"],
            [{"effect":"knowledge.observation.available","as":alias1}],
        )
        self.assertEqual(
            instances[1]["provides_as"],
            [{"effect":"knowledge.observation.available","as":alias2}],
        )
        self.assertEqual(
            instances[2]["requires_as"],
            [
                {"effect":"knowledge.observation.available","as":alias1},
                {"effect":"knowledge.observation.available","as":alias2},
            ],
        )
        self.assertEqual(
            instances[2]["inputs"]["evidence_paths"],
            [
                {"$effect_result":{"effect":alias1,"field":"output_path"}},
                {"$effect_result":{"effect":alias2,"field":"output_path"}},
            ],
        )
        self.assertEqual(
            evidence["expanded_instance_plan"],
            ["auto-test-observe-1","auto-test-observe-2","auto-test-assess"],
        )

    def test_duplicate_goal_url_does_not_fake_independence(self):
        goal=(
            "Assess observations from https://one.example/a "
            "and https://one.example/a for consistency."
        )
        proposal,evidence=self.generate(goal)
        self.assertEqual(
            [x["instance_id"] for x in proposal["capability_instances"]],
            ["auto-test-observe","auto-test-assess"],
        )
        self.assertEqual(evidence["fan_in"],{})

    def test_single_goal_url_preserves_unique_effect_path(self):
        proposal,evidence=self.generate(
            "Assess the observation at https://one.example/a for consistency."
        )
        self.assertEqual(
            [x["instance_id"] for x in proposal["capability_instances"]],
            ["auto-test-observe","auto-test-assess"],
        )
        self.assertNotIn("provides_as",proposal["capability_instances"][0])
        self.assertNotIn("requires_as",proposal["capability_instances"][1])
        self.assertEqual(
            proposal["capability_instances"][1]["inputs"]["evidence_paths"],
            [{"$effect_result":{
                "effect":"knowledge.observation.available",
                "field":"output_path",
            }}],
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
