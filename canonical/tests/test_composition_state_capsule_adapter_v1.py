#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/"runtime"/"composition_state_capsule_adapter_v1.py"
spec=importlib.util.spec_from_file_location("composition_state_capsule_adapter_test_target",PATH)
adapter=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=adapter
spec.loader.exec_module(adapter)


def contract(capability_id,requires,internal,external,provides,result_fields):
    return {
        "schema":adapter.CONTRACT_SCHEMA,
        "capability_id":capability_id,
        "requires":requires,
        "internal_requires":internal,
        "external_requires":external,
        "provides":provides,
        "result_fields":result_fields,
    }


class CompositionStateCapsuleAdapterTests(unittest.TestCase):
    def provider(self):
        return {
            "type":"read_file",
            "args":{"path":"source.txt"},
            "capability_id":"provider",
            adapter.CONTRACT_KEY:contract(
                "provider",[],[],[],["state.a"],["path","payload"]
            ),
        }

    def consumer(self):
        return {
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
            adapter.CONTRACT_KEY:contract(
                "consumer",["state.a"],["state.a"],[],["state.b"],["status"]
            ),
        }

    def actions(self):
        return [
            self.provider(),
            self.consumer(),
            {"type":"finish","args":{"summary":"DONE"}},
        ]

    def test_capsule_is_authoritative_for_cross_step_value(self):
        actions=self.actions()
        self.assertTrue(adapter.validate_plan(actions))
        capsule=adapter.empty_capsule()
        provider_result={"path":"trusted.json","payload":{"x":1}}
        capsule=adapter.commit_result(capsule,actions[0],provider_result)
        trace=[{
            "cycle":0,
            "plan":actions[0],
            "result":provider_result,
            "composition_capsule_head_hash":capsule["head_hash"],
        }]
        resolved=adapter.resolve_action(actions[1],trace,capsule)
        self.assertEqual(resolved["args"]["path"],"trusted.json")

    def test_tampered_raw_trace_cannot_impersonate_capsule_state(self):
        actions=self.actions()
        capsule=adapter.empty_capsule()
        provider_result={"path":"trusted.json","payload":{"x":1}}
        capsule=adapter.commit_result(capsule,actions[0],provider_result)
        trace=[{
            "cycle":0,
            "plan":actions[0],
            "result":{"path":"evil.json","payload":{"x":1}},
            "composition_capsule_head_hash":capsule["head_hash"],
        }]
        with self.assertRaisesRegex(
            adapter.CompositionAdapterError,
            "RESULT_REFERENCE_PROVIDER_RESULT_HASH_MISMATCH",
        ):
            adapter.resolve_action(actions[1],trace,capsule)

    def test_checkpoint_binding_detects_result_tamper(self):
        actions=self.actions()
        capsule=adapter.empty_capsule()
        provider_result={"path":"trusted.json","payload":{"x":1}}
        capsule=adapter.commit_result(capsule,actions[0],provider_result)
        trace=[{
            "cycle":0,
            "plan":actions[0],
            "result":{"path":"tampered.json","payload":{"x":1}},
            "composition_capsule_head_hash":capsule["head_hash"],
        }]
        checkpoint={"composition_state_capsule":capsule}
        with self.assertRaisesRegex(
            adapter.CompositionAdapterError,
            "COMPOSITION_TRACE_RESULT_HASH_MISMATCH",
        ):
            adapter.bind_checkpoint(actions,checkpoint,trace)

    def test_checkpoint_rewind_rolls_capsule_to_exact_trace_prefix(self):
        actions=self.actions()
        capsule=adapter.empty_capsule()
        provider_result={"path":"trusted.json","payload":{"x":1}}
        capsule=adapter.commit_result(capsule,actions[0],provider_result)
        provider_head=capsule["head_hash"]
        trace0={
            "cycle":0,
            "plan":actions[0],
            "result":provider_result,
            "composition_capsule_head_hash":provider_head,
        }
        consumer_result={"status":"ok"}
        capsule=adapter.commit_result(capsule,actions[1],consumer_result)
        checkpoint={"composition_state_capsule":capsule}
        rebound=adapter.bind_checkpoint(actions,checkpoint,[trace0])
        self.assertEqual(rebound["head_hash"],provider_head)
        self.assertEqual(len(rebound["records"]),1)

    def test_mixed_uncontracted_nonfinish_plan_fails_closed(self):
        actions=self.actions()
        actions[1]={
            "type":"read_file",
            "args":{"path":"x"},
            "capability_id":"consumer",
        }
        with self.assertRaisesRegex(
            adapter.CompositionAdapterError,
            "COMPOSITION_CONTRACT_MISSING",
        ):
            adapter.validate_plan(actions)


if __name__=="__main__":
    unittest.main(verbosity=2)
