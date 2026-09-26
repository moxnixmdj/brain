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
    "project_brain_test_multi_capability_proposal_generator",
    RUNTIME_DIR/"capability_proposal_generators.py",
)


class AutoMultiCapabilityProposalTests(unittest.TestCase):
    GOAL="Assess the knowledge consistency of the observation available from https://example.test/data."
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
                        "json_path":"${input.json_path}",
                        "output_path":"${input.output_path}",
                        "authoritative":"${input.authoritative}",
                    },
                },
                "proposal_bindings":{
                    "json_path":{"type":"literal","value":[]},
                    "authoritative":{"type":"literal","value":False},
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
                "result_fields":["output_path","status"],
                "action_template":{
                    "type":"assess_knowledge_consistency",
                    "args":{
                        "evidence_paths":"${input.evidence_paths}",
                        "output_path":"${input.output_path}",
                        "max_age_s":"${input.max_age_s}",
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
                    "max_age_s":{"type":"literal","value":None},
                },
            },
        }

    def generate(self,registry=None,initial=None):
        return generator.generate(
            "multi-verified-capability-v1",
            self.GOAL,
            [self.TARGET],
            ["network.http.available"] if initial is None else initial,
            registry or self.registry(),
            CANONICAL_ROOT.parent,
            RUNTIME_DIR,
        )

    def test_planner_synthesizes_two_step_graph_and_effect_valueflow(self):
        proposal,evidence=self.generate()
        self.assertEqual(
            [x["capability_id"] for x in proposal["capability_instances"]],
            ["test.observe","test.assess"],
        )
        observe,assess=proposal["capability_instances"]
        self.assertEqual(observe["inputs"]["url"],"https://example.test/data")
        self.assertEqual(observe["inputs"]["json_path"],[])
        self.assertFalse(observe["inputs"]["authoritative"])
        self.assertTrue(observe["inputs"]["output_path"].endswith(".json"))
        self.assertEqual(
            assess["inputs"]["evidence_paths"],
            [{"$effect_result":{
                "effect":"knowledge.observation.available",
                "field":"output_path",
            }}],
        )
        self.assertIsNone(assess["inputs"]["max_age_s"])
        self.assertTrue(assess["inputs"]["output_path"].endswith(".json"))
        self.assertEqual(
            evidence["capability_plan"],
            ["test.observe","test.assess"],
        )

    def test_missing_initial_fact_fails_closed_at_graph_planning(self):
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "CAPABILITY_GRAPH_PLAN_FAILED",
        ):
            self.generate(initial=[])

    def test_effect_binding_requires_declared_producer_result_field(self):
        registry=self.registry()
        registry["test.observe"]["result_fields"]=[]
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "PROPOSAL_EFFECT_RESULT_FIELD_UNDECLARED",
        ):
            self.generate(registry=registry)

    def test_binding_metadata_cannot_name_non_placeholder_input(self):
        registry=self.registry()
        registry["test.assess"]["proposal_bindings"]["invented"]={
            "type":"literal","value":"x",
        }
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "PROPOSAL_BINDING_UNKNOWN_INPUT",
        ):
            self.generate(registry=registry)

    def test_paid_provider_is_not_plannable(self):
        registry=self.registry()
        registry["test.observe"]["incremental_spend_usd"]=0.01
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "CAPABILITY_GRAPH_PLAN_FAILED",
        ):
            self.generate(registry=registry)

    def test_unknown_multi_generator_fails_closed(self):
        with self.assertRaisesRegex(
            generator.CapabilityProposalFailure,
            "CAPABILITY_PROPOSAL_GENERATOR_UNKNOWN",
        ):
            generator.generate(
                "not-a-generator",
                self.GOAL,[self.TARGET],["network.http.available"],
                self.registry(),CANONICAL_ROOT.parent,RUNTIME_DIR,
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
