#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


runtime=load(
    "project_brain_plain_goal_grounding_runtime_precedence",
    RUNTIME_DIR/"astra_runtime.py",
)
grounding=load(
    "project_brain_plain_goal_grounding_real_registry",
    RUNTIME_DIR/"bound_capabilities"/"plain_goal_bound_grounding.py",
)
verifier=load(
    "project_brain_plain_goal_grounding_real_registry_verify",
    RUNTIME_DIR/"bound_capabilities"/"plain_goal_bound_grounding_verify.py",
)


class PlainGoalGroundingRuntimePrecedenceTests(unittest.TestCase):
    def real_registry(self):
        raw=json.loads(
            (RUNTIME_DIR/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
        )
        return raw["capabilities"]

    def test_fresh_software_quality_goal_grounds_in_real_registry_and_verifies(self):
        goal=(
            "Audit the Python tests with unittest and report passed failed and skipped counts."
        )
        registry=self.real_registry()
        result=grounding.ground(goal,registry)
        self.assertIn("python.tests.audit.unittest",result["candidate_capability_ids"])
        ok,reason=verifier.verify(goal,result,registry)
        self.assertTrue(ok,reason)
        self.assertEqual(result["model_dependency_count"],0)

    def test_fresh_browser_goal_reuses_same_grounding_route(self):
        goal=(
            "Open the rendered browser page at https://example.com and capture a screenshot."
        )
        registry=self.real_registry()
        result=grounding.ground(goal,registry)
        self.assertIn(
            "web.browser.rendered.capture.chromedriver",
            result["candidate_capability_ids"],
        )
        ok,reason=verifier.verify(goal,result,registry)
        self.assertTrue(ok,reason)

    def test_existing_bound_grounding_blocks_external_supplier_discovery(self):
        registry={
            "python.tests.audit.unittest":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["python.tests.audit"],
                "requires":[],
                "keywords":["python","tests","audit","unittest","passed","failed","skipped"],
            },
        }
        goal="Audit the Python tests with unittest and report failed counts."
        mission={"mission_id":"GROUNDING-PRECEDENCE-TEST","goal":goal}
        step={"adapter":"goal","goal_ref":"goal","allow_optional_model_planner":False}

        compile_error=runtime.Blocker(
            "GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
        )
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(runtime,"EVID_DIR",pathlib.Path(td)):
                with mock.patch.object(runtime,"_compile_plain_goal",side_effect=compile_error):
                    with mock.patch.object(
                        runtime,"_load_bound_capability_registry",return_value=registry
                    ):
                        with mock.patch.object(
                            runtime,
                            "_load_auto_capability_acquisition",
                            side_effect=AssertionError(
                                "external acquisition must not be reached after bound grounding"
                            ),
                        ):
                            with self.assertRaisesRegex(
                                runtime.Blocker,
                                "BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_REQUIRED",
                            ):
                                runtime.run_goal(step,mission)

    def test_unmatched_goal_does_not_fake_bound_grounding(self):
        registry=self.real_registry()
        goal="Calibrate the neutrino interferometer phase drift."
        result=grounding.ground(goal,registry)
        self.assertEqual(result["grounded_clause_count"],0)
        self.assertEqual(result["candidate_capability_ids"],[])


if __name__=="__main__":
    unittest.main(verbosity=2)
