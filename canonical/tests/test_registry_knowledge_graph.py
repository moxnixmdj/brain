#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=CANONICAL_ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("astra_runtime_registry_knowledge_test",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)

PLANNER_PATH=CANONICAL_ROOT/"runtime"/"capability_planner.py"
pspec=importlib.util.spec_from_file_location("capability_planner_registry_knowledge_test",PLANNER_PATH)
planner=importlib.util.module_from_spec(pspec)
sys.modules[pspec.name]=planner
pspec.loader.exec_module(planner)


class RegistryKnowledgeGraphTests(unittest.TestCase):
    def problem(self):
        return {
            "initial_facts":["network.http.available"],
            "target_effects":["knowledge.fact.materialized"],
            "inputs":{},
            "capabilities":[],
            "capability_instances":[
                {
                    "instance_id":"observe-a",
                    "capability_id":"knowledge.json.fetch.external",
                    "inputs":{
                        "url":"https://a.example/data",
                        "json_path":["value"],
                        "output_path":"a.json",
                        "authoritative":False,
                    },
                    "provides_as":{
                        "knowledge.observation.available":"knowledge.observation.a.available"
                    },
                },
                {
                    "instance_id":"observe-b",
                    "capability_id":"knowledge.json.fetch.external",
                    "inputs":{
                        "url":"https://b.example/data",
                        "json_path":["value"],
                        "output_path":"b.json",
                        "authoritative":False,
                    },
                    "provides_as":{
                        "knowledge.observation.available":"knowledge.observation.b.available"
                    },
                },
                {
                    "instance_id":"assess-two",
                    "capability_id":"knowledge.consistency.assess",
                    "inputs":{
                        "evidence_paths":[
                            {"$effect_result":{"effect":"knowledge.observation.a.available","field":"output_path"}},
                            {"$effect_result":{"effect":"knowledge.observation.b.available","field":"output_path"}},
                        ],
                        "output_path":"assessment.json",
                        "max_age_s":None,
                    },
                    "requires_as":[
                        {"effect":"knowledge.observation.available","as":"knowledge.observation.a.available"},
                        {"effect":"knowledge.observation.available","as":"knowledge.observation.b.available"},
                    ],
                },
                {
                    "instance_id":"materialize-fact",
                    "capability_id":"knowledge.support.materialize",
                    "inputs":{
                        "assessment_path":{
                            "$effect_result":{
                                "effect":"knowledge.assessment.available",
                                "field":"output_path",
                            }
                        },
                        "field_name":"claim",
                        "output_path":"fact.json",
                    },
                },
            ],
        }

    def test_registry_only_graph_expands_to_verified_instances(self):
        enriched=runtime._inherit_verified_capabilities(self.problem())
        by_id={x["id"]:x for x in enriched["capabilities"]}
        for iid,cid in {
            "observe-a":"knowledge.json.fetch.external",
            "observe-b":"knowledge.json.fetch.external",
            "assess-two":"knowledge.consistency.assess",
            "materialize-fact":"knowledge.support.materialize",
        }.items():
            self.assertIn(iid,by_id)
            self.assertEqual(by_id[iid]["source_capability_id"],cid)
        self.assertEqual(
            by_id["assess-two"]["requires"],
            ["knowledge.observation.a.available","knowledge.observation.b.available"],
        )

    def test_registry_only_graph_plans_and_wires_all_runtime_values(self):
        enriched=runtime._inherit_verified_capabilities(self.problem())
        planned=planner.plan_actions(enriched)
        self.assertEqual(
            planned["planning"]["plan"],
            ["observe-a","observe-b","assess-two","materialize-fact"],
        )
        actions=planned["actions"]
        self.assertEqual(
            actions[2]["args"]["evidence_paths"],
            [
                {"$result":{"cycle":0,"field":"output_path"}},
                {"$result":{"cycle":1,"field":"output_path"}},
            ],
        )
        self.assertEqual(
            actions[3]["args"]["assessment_path"],
            {"$result":{"cycle":2,"field":"output_path"}},
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
