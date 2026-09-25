#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL_ROOT / "runtime" / "astra_runtime.py"
spec = importlib.util.spec_from_file_location("astra_runtime", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

class ModelIndependenceTests(unittest.TestCase):
    def test_goal_completes_with_model_planner_forbidden(self):
        mission = {"goal": "Verify model-independent bounded goal execution."}
        step = {
            "goal_ref": "goal",
            "controller_actions": [
                {"type": "search_text", "args": {"query": "MODEL_NON_DEPENDENCE_LAW_V1"}},
                {"type": "read_file", "args": {"path": "canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md"}},
                {"type": "finish", "args": {"summary": "MODEL_INDEPENDENT_GOAL_COMPLETE"}}
            ]
        }
        with mock.patch.object(runtime, "_planner_post", side_effect=AssertionError("model planner must not be called")):
            result = runtime.run_goal(step, mission)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["controller_mode"], "MODEL_INDEPENDENT_ACTION_PLAN")
        self.assertIsNone(result["planner_model_last"])
        self.assertIn("MODEL_INDEPENDENT_GOAL_COMPLETE", result["stdout"])

    def test_registry_inheritance_preserves_declared_result_fields(self):
        fake_registry={
            "test.producer":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "requires":[],
                "provides":["test.value.available"],
                "cost":1,
                "result_fields":["value","output_path"],
                "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
            }
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=fake_registry):
            enriched=runtime._inherit_verified_capabilities({
                "initial_facts":[],
                "target_effects":["test.value.available"],
                "inputs":{},
                "capabilities":[],
            })
        inherited=next(x for x in enriched["capabilities"] if x["id"]=="test.producer")
        self.assertEqual(inherited["result_fields"],["value","output_path"])


    def test_verified_capability_instances_bind_inputs_and_alias_effects(self):
        fake_registry={
            "test.fetch":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "requires":[],
                "provides":["knowledge.observation.available"],
                "cost":1,
                "result_fields":["value","output_path"],
                "action_template":{
                    "type":"fetch_json_knowledge",
                    "args":{
                        "url":"${input.url}",
                        "output_path":"${input.output_path}",
                    },
                },
            }
        }
        problem={
            "initial_facts":[],
            "target_effects":[
                "knowledge.observation.a.available",
                "knowledge.observation.b.available",
            ],
            "inputs":{},
            "capabilities":[],
            "capability_instances":[
                {
                    "instance_id":"observe-a",
                    "capability_id":"test.fetch",
                    "inputs":{"url":"https://a.example/data","output_path":"a.json"},
                    "provides_as":{
                        "knowledge.observation.available":"knowledge.observation.a.available"
                    },
                },
                {
                    "instance_id":"observe-b",
                    "capability_id":"test.fetch",
                    "inputs":{"url":"https://b.example/data","output_path":"b.json"},
                    "provides_as":{
                        "knowledge.observation.available":"knowledge.observation.b.available"
                    },
                },
            ],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=fake_registry):
            enriched=runtime._inherit_verified_capabilities(problem)
        by_id={x["id"]:x for x in enriched["capabilities"]}
        self.assertEqual(set(by_id),{"observe-a","observe-b"})
        self.assertEqual(by_id["observe-a"]["source_capability_id"],"test.fetch")
        self.assertEqual(by_id["observe-a"]["provides"],["knowledge.observation.a.available"])
        self.assertEqual(by_id["observe-b"]["provides"],["knowledge.observation.b.available"])
        self.assertEqual(by_id["observe-a"]["action"]["args"]["url"],"https://a.example/data")
        self.assertEqual(by_id["observe-b"]["action"]["args"]["output_path"],"b.json")
        self.assertEqual(
            {x["instance_id"] for x in enriched["_instantiated_bound_capabilities"]},
            {"observe-a","observe-b"},
        )

    def test_capability_instance_cannot_alias_undeclared_effect(self):
        fake_registry={
            "test.fetch":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "requires":[],
                "provides":["knowledge.observation.available"],
                "cost":1,
                "result_fields":["value"],
                "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
            }
        }
        problem={
            "initial_facts":[],
            "target_effects":["invented.effect"],
            "capabilities":[],
            "capability_instances":[{
                "instance_id":"bad-instance",
                "capability_id":"test.fetch",
                "inputs":{},
                "provides_as":{"not.declared":"invented.effect"},
            }],
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=fake_registry):
            with self.assertRaisesRegex(
                runtime.Blocker,
                "CAPABILITY_INSTANCE_PROVIDES_ALIAS_SOURCE_UNKNOWN:bad-instance:not.declared",
            ):
                runtime._inherit_verified_capabilities(problem)


    def test_anonymous_controller_checkpoints_are_isolated_by_plan_hash(self):
        first=[
            {"type":"read_file","args":{"path":"canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md"}},
            {"type":"finish","args":{"summary":"FIRST"}},
        ]
        second=[
            {"type":"search_text","args":{"query":"MODEL_NON_DEPENDENCE_LAW_V1"}},
            {"type":"finish","args":{"summary":"SECOND"}},
        ]
        first_sha=runtime._controller_plan_sha256(first)
        second_sha=runtime._controller_plan_sha256(second)
        p1=runtime._controller_checkpoint_path({}, {}, plan_sha=first_sha)
        p1_repeat=runtime._controller_checkpoint_path({}, {}, plan_sha=first_sha)
        p2=runtime._controller_checkpoint_path({}, {}, plan_sha=second_sha)
        self.assertEqual(p1,p1_repeat)
        self.assertNotEqual(p1,p2)
        self.assertIn(first_sha[:16],p1.name)
        self.assertIn(second_sha[:16],p2.name)

    def test_anonymous_controller_does_not_resume_completed_checkpoint(self):
        actions=[
            {"type":"read_file","args":{"path":"canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md"}},
            {"type":"finish","args":{"summary":"ANON_RESET_TEST"}},
        ]
        plan_sha=runtime._controller_plan_sha256(actions)
        path=runtime._controller_checkpoint_path({}, {}, plan_sha=plan_sha)
        path.unlink(missing_ok=True)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        checkpoint={
            "schema":"PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
            "mission_id":None,
            "step_id":"goal",
            "plan_sha256":plan_sha,
            "status":"COMPLETE",
            "completed_actions":[
                {"cycle":0,"plan":actions[0],"result":{"type":"read_file","content":"x"}},
                {"cycle":1,"plan":actions[1],"result":{"type":"finish","summary":"ANON_RESET_TEST"}},
            ],
            "next_action_index":2,
            "resume_count":7,
            "test_interrupt_injected":False,
            "created_at_utc":runtime.utc(),
            "updated_at_utc":runtime.utc(),
        }
        runtime.writej(path,checkpoint)
        loaded_path,loaded,resumed=runtime._load_controller_checkpoint({}, {}, actions)
        self.assertEqual(loaded_path,path)
        self.assertFalse(resumed)
        self.assertEqual(loaded["completed_actions"],[])
        self.assertEqual(loaded["next_action_index"],0)
        self.assertEqual(loaded["resume_count"],0)

    def test_unknown_goal_attempts_model_independent_acquisition_without_model_fallback(self):
        class EmptyAuto:
            def dispatch(self,*args,**kwargs):
                raise RuntimeError("NO_TEST_CAPABILITY")
        class EmptyDiscovery:
            def search_all(self,*args,**kwargs):
                return {"candidates":[]}
        with mock.patch.object(runtime, "_planner_post", side_effect=AssertionError("model planner must not be called")), \
             mock.patch.object(runtime, "_load_auto_capability_acquisition", return_value=EmptyAuto()), \
             mock.patch.object(runtime, "_load_capability_discovery", return_value=EmptyDiscovery()), \
             mock.patch.object(runtime, "writej"):
            with self.assertRaisesRegex(runtime.Blocker, "CAPABILITY_ACQUISITION_REQUIRED"):
                runtime.run_goal(
                    {},
                    {"mission_id":"TEST-MODEL-INDEPENDENCE-NO-PLAN","goal":"No implicit model fallback is allowed."}
                )

    def test_model_planner_is_explicit_opt_in_only(self):
        planned = '{"actions":[{"type":"finish","args":{"summary":"OPTIONAL_MODEL_ROUTE_USED"},"why":"explicit opt-in"}]}'
        with mock.patch.object(runtime, "_planner_post", return_value={"text": planned, "model": "stub", "duration_s": 0, "errors": []}):
            result = runtime.run_goal(
                {"allow_optional_model_planner": True, "max_cycles": 1},
                {"goal": "Use optional model route only because this step explicitly opts in."}
            )
        self.assertEqual(result["controller_mode"], "OPTIONAL_MODEL_ADVISORY")
        self.assertEqual(result["planner_model_last"], "stub")
        self.assertIn("OPTIONAL_MODEL_ROUTE_USED", result["stdout"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
