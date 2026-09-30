#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME_PATH=ROOT/"canonical"/"runtime"/"astra_runtime.py"

spec=importlib.util.spec_from_file_location("project_brain_astra_failure_evidence_test",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)


class FailureEvidencePreservationTest(unittest.TestCase):
    def test_expectation_failure_preserves_verifier_reason_and_bounded_result(self):
        action={
            "expect":{
                "type":"field_equals",
                "field":"verified",
                "value":True,
            }
        }
        result={
            "adapter":"evidence_decision_verify",
            "verified":False,
            "reason":"INPUT_HASH_MISMATCH",
            "status":"DECIDED",
            "selected_alternative":"PRIVATE_GITHUB_MAIN",
            "input_path":"canonical/tasks/example.json",
            "result_path":"canonical/astra_runtime/tmp/example-result.json",
            "model_dependency_count":0,
            "unrelated_large_payload":"X"*10000,
        }
        with self.assertRaises(runtime.Blocker) as ctx:
            runtime._verify_action_expectation(action,result)
        message=str(ctx.exception)
        self.assertIn("ACTION_EXPECTATION_FAILED:verified:OBSERVED=False",message)
        self.assertIn("REASON=INPUT_HASH_MISMATCH",message)
        self.assertIn('"reason":"INPUT_HASH_MISMATCH"',message)
        self.assertIn('"input_path":"canonical/tasks/example.json"',message)
        self.assertIn('"result_path":"canonical/astra_runtime/tmp/example-result.json"',message)
        self.assertNotIn("unrelated_large_payload",message)
        self.assertLess(len(message),4000)

    def test_success_does_not_emit_failure(self):
        runtime._verify_action_expectation(
            {"expect":{"type":"field_equals","field":"verified","value":True}},
            {"verified":True,"reason":"VERIFIED"},
        )


if __name__=="__main__":
    unittest.main()
