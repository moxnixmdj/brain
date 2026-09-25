#!/usr/bin/env python3
import hashlib
import importlib.util
import pathlib
import sys
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

goal_ir=load("goal_ir_test_target",CANONICAL_ROOT/"runtime"/"goal_ir.py")
planner=load("capability_planner_goal_ir_test_target",CANONICAL_ROOT/"runtime"/"capability_planner.py")


class GoalIRTests(unittest.TestCase):
    def registry(self):
        return {
          "learn-value":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "requires":[],
            "provides":["knowledge.value.available"],
            "result_fields":["value"],
            "cost":1,
            "input_contract":{
              "url":{"kind":"goal_input","key":"source_url"}
            },
            "action_template":{
              "type":"fetch_json_knowledge",
              "args":{"url":"${input.url}"}
            },
          },
          "write-value":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "requires":["knowledge.value.available"],
            "provides":["record.written"],
            "result_fields":["output_path"],
            "cost":1,
            "input_contract":{
              "value":{
                "kind":"effect_result",
                "effect":"knowledge.value.available",
                "field":"value"
              },
              "output_path":{"kind":"goal_input","key":"output_path"}
            },
            "action_template":{
              "type":"write_json_records",
              "args":{
                "output_path":"${input.output_path}",
                "records":[{"claim":"${input.value}"}]
              }
            },
          }
        }

    def ir(self,goal):
        return {
          "schema":"PROJECT_BRAIN_GOAL_IR_V1",
          "goal_sha256":hashlib.sha256(goal.encode("utf-8")).hexdigest(),
          "initial_facts":[],
          "target_effects":["record.written"],
          "inputs":{
            "source_url":"https://example.test/value",
            "output_path":"canonical/astra_runtime/tmp/OUT.json"
          },
          "clauses":[{
            "index":0,
            "start":0,
            "end":len(goal),
            "text":goal,
            "target_effects":["record.written"]
          }]
        }

    def test_goal_ir_builds_registry_only_valueflow_problem(self):
        goal="Fetch the value and write the resulting record."
        problem=goal_ir.build_capability_problem(goal,self.ir(goal),self.registry())
        out=planner.plan_actions(problem)
        self.assertEqual(out["planning"]["plan"],["learn-value","write-value"])
        self.assertEqual(
            out["actions"][1]["args"]["records"][0]["claim"],
            {"$result":{"cycle":0,"field":"value"}},
        )

    def test_goal_ir_rejects_goal_hash_mismatch(self):
        goal="Fetch the value."
        ir=self.ir(goal)
        ir["goal_sha256"]="0"*64
        with self.assertRaisesRegex(goal_ir.GoalIRFailure,"GOAL_IR_GOAL_HASH_MISMATCH"):
            goal_ir.build_capability_problem(goal,ir,self.registry())

    def test_goal_ir_rejects_uncovered_nonwhitespace_text(self):
        goal="Fetch value then write it."
        ir=self.ir(goal)
        ir["clauses"]=[{
          "index":0,"start":0,"end":11,"text":goal[:11],
          "target_effects":["record.written"]
        }]
        with self.assertRaisesRegex(goal_ir.GoalIRFailure,"GOAL_IR_TEXT_UNCOVERED"):
            goal_ir.build_capability_problem(goal,ir,self.registry())

    def test_goal_ir_cannot_invent_unknown_capability(self):
        goal="Fetch the value."
        ir=self.ir(goal)
        ir["capability_allowlist"]=["not.real"]
        with self.assertRaisesRegex(goal_ir.GoalIRFailure,"GOAL_IR_CAPABILITY_UNKNOWN:not.real"):
            goal_ir.build_capability_problem(goal,ir,self.registry())

    def test_effect_binding_must_match_registry_requirement(self):
        goal="Fetch the value."
        registry=self.registry()
        registry["write-value"]["requires"]=[]
        ir=self.ir(goal)
        with self.assertRaisesRegex(goal_ir.GoalIRFailure,"GOAL_IR_EFFECT_NOT_REQUIRED"):
            goal_ir.build_capability_problem(goal,ir,registry)

    def test_proposer_cannot_supply_executable_actions(self):
        goal="Fetch the value."
        ir=self.ir(goal)
        ir["actions"]=[{"type":"shell","args":{"command":"echo unsafe"}}]
        problem=goal_ir.build_capability_problem(goal,ir,self.registry())
        self.assertNotIn("actions",problem)
        self.assertTrue(all(x["action"]["type"]!="shell" for x in problem["capabilities"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
