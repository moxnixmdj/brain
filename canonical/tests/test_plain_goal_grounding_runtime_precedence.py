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
        evidence_root=CANONICAL_ROOT/"astra_runtime"/"evidence"
        evidence_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_root) as td:
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


    def test_multi_clause_broad_research_routes_before_external_package_acquisition(self):
        goal=(
            "Assess whether the maximum rated operating temperature is greater than "
            "the default recommended operating temperature. "
            "Use authoritative primary technical evidence and a real executable check. "
            "Autonomously discover and verify the relevant documentation, choose and run "
            "a zero-cost verification method, identify material limitations, independently "
            "verify the consequential result, and produce a decision-quality answer with provenance."
        )
        registry=self.real_registry()
        grounded=grounding.ground(goal,registry)
        self.assertEqual(grounded["grounded_clause_count"],0,grounded)
        self.assertTrue(grounded["broad_objective_decomposition_available"],grounded)

        mission={"mission_id":"BROAD-RESEARCH-ROUTING-PRECEDENCE-TEST","goal":goal}
        step={"adapter":"goal","goal_ref":"goal","allow_optional_model_planner":False}
        compile_error=runtime.Blocker(
            "GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
        )
        frontend={
            "status":"SOURCE_DISCOVERY_BLOCKED",
            "provenance_verified_candidate_count":0,
            "authority_identity_verified_candidate_count":0,
            "relevance_verified_candidate_count":0,
            "claim_relation_evaluated_count":0,
            "next_required_capability":"MODEL_INDEPENDENT_OPEN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1",
        }
        evidence_root=CANONICAL_ROOT/"astra_runtime"/"evidence"
        evidence_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_root) as td:
            td=pathlib.Path(td)
            grounding_path=td/"grounding.json"
            frontend_path=td/"frontend.json"
            with mock.patch.object(runtime,"EVID_DIR",td), \
                 mock.patch.object(runtime,"_compile_plain_goal",side_effect=compile_error), \
                 mock.patch.object(
                     runtime,
                     "_ground_plain_goal_to_bound_capabilities",
                     return_value=(grounding_path,grounded),
                 ), \
                 mock.patch.object(
                     runtime,
                     "_run_open_research_source_frontend",
                     return_value=(frontend_path,frontend),
                 ) as frontend_call, \
                 mock.patch.object(
                     runtime,
                     "_load_auto_capability_acquisition",
                     side_effect=AssertionError(
                         "package acquisition must not load for decomposed broad research"
                     ),
                 ):
                with self.assertRaisesRegex(
                    runtime.Blocker,
                    "OPEN_ENDED_RESEARCH_SOURCE_FRONTEND_BLOCKED",
                ):
                    runtime.run_goal(step,mission)
                frontend_call.assert_called_once()


if __name__=="__main__":
    unittest.main(verbosity=2)
