#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("project_brain_grounding_bound_integration",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)

class PlainGoalGroundingBoundIntegrationTests(unittest.TestCase):
    def test_registry_producer_and_independent_verifier_are_callable(self):
        registry=json.loads(
            (ROOT/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
        )["capabilities"]
        producer="plain_goal.bound_capability.grounding.stdlib"
        verifier="plain_goal.bound_capability.grounding.verify.stdlib"
        self.assertEqual(registry[producer]["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(registry[verifier]["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(registry[producer]["verification"]["model_dependency_count"],0)
        self.assertEqual(registry[verifier]["verification"]["model_dependency_count"],0)

        goal="Audit the Python tests with unittest and report passed failed and skipped counts."
        rel="canonical/astra_runtime/tmp/BOUND_GROUNDING_REGISTRY_INTEGRATION.json"
        path=pathlib.Path.cwd()/rel
        path.unlink(missing_ok=True)
        self.addCleanup(lambda:path.unlink(missing_ok=True))

        produced=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":producer,
                "goal":goal,
                "output_path":rel,
            },
        })
        self.assertTrue(produced["output_verified"],produced)
        self.assertEqual(produced["model_dependency_count"],0)
        self.assertIn("python.tests.audit.unittest",produced["candidate_capability_ids"])

        verified=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":verifier,
                "goal":goal,
                "result_path":rel,
            },
        })
        self.assertTrue(verified["verified"],verified)
        self.assertTrue(verified["producer_independent"])
        self.assertEqual(verified["model_dependency_count"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
