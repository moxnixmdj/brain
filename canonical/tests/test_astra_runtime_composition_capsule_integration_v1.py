#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("astra_runtime_capsule_integration_test_target",PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)

CONTRACT_KEY="_brain_composition_contract"
SCHEMA="PROJECT_BRAIN_CAPABILITY_ACTION_STATE_CONTRACT_V1"


def contract(capability_id,requires,internal,external,provides,result_fields):
    return {
        "schema":SCHEMA,
        "capability_id":capability_id,
        "requires":requires,
        "internal_requires":internal,
        "external_requires":external,
        "provides":provides,
        "result_fields":result_fields,
    }


class AstraRuntimeCapsuleIntegrationTests(unittest.TestCase):
    def test_contracted_controller_routes_cross_step_value_through_capsule(self):
        actions=[
            {
                "type":"read_file",
                "args":{"path":"seed.txt"},
                "capability_id":"provider",
                CONTRACT_KEY:contract(
                    "provider",[],[],[],["state.a"],["path","payload"]
                ),
            },
            {
                "type":"read_file",
                "args":{
                    "path":{
                        "$result":{
                            "cycle":0,
                            "effect":"state.a",
                            "field":"path",
                        }
                    }
                },
                "capability_id":"consumer",
                CONTRACT_KEY:contract(
                    "consumer",["state.a"],["state.a"],[],["state.b"],["status"]
                ),
            },
            {"type":"finish","args":{"summary":"CAPSULE_PATH_COMPLETE"}},
        ]
        mission={"mission_id":"TEST-COMPOSITION-CAPSULE-INTEGRATION"}
        step={"id":"goal","controller_actions":actions}

        plan_sha=runtime._controller_plan_sha256(actions)
        checkpoint=runtime._controller_checkpoint_path(step,mission,plan_sha=plan_sha)
        checkpoint.unlink(missing_ok=True)
        self.addCleanup(lambda: checkpoint.unlink(missing_ok=True))

        observed=[]
        def fake_goal_action(action):
            observed.append(action)
            if action.get("type")=="finish":
                return {"type":"finish","summary":action["args"]["summary"]}
            if action.get("capability_id")=="provider":
                return {"path":"trusted.json","payload":{"v":1}}
            if action.get("capability_id")=="consumer":
                if action["args"]["path"]!="trusted.json":
                    raise AssertionError("consumer did not receive capsule-authoritative state")
                return {"status":"ok"}
            raise AssertionError("unexpected action")

        with mock.patch.object(runtime,"_goal_action",side_effect=fake_goal_action):
            result=runtime._run_model_independent_goal(
                step,mission,"exercise contracted composition"
            )

        self.assertEqual(result["returncode"],0)
        self.assertTrue(result["composition_state_capsule"]["enabled"])
        self.assertEqual(result["composition_state_capsule"]["record_count"],2)
        self.assertEqual(observed[1]["args"]["path"],"trusted.json")
        self.assertIn("composition_capsule_head_hash",result["trace"][0])
        self.assertIn("composition_capsule_head_hash",result["trace"][1])
        self.assertNotIn("composition_capsule_head_hash",result["trace"][2])


if __name__=="__main__":
    unittest.main(verbosity=2)
