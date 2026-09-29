#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("project_brain_grounding_gate_runtime",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)


class PlainGoalGroundingGateTests(unittest.TestCase):
    def test_existing_bound_grounding_blocks_external_acquisition(self):
        goal="Choose the verified local decision route."
        mission={"mission_id":"TEST-BOUND-GROUNDING-GATE","goal":goal}
        evidence_path=ROOT/"astra_runtime"/"evidence"/"TEST-BOUND-GROUNDING-GATE__BOUND_CAPABILITY_GROUNDING.json"
        grounding={
            "schema":"PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1",
            "grounded_clause_count":1,
            "unresolved_clause_indexes":[],
            "candidate_capability_ids":["decision.synthesis.typed.stdlib"],
            "model_dependency_count":0,
        }
        compile_failure=runtime.Blocker(
            "GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
        )
        with mock.patch.object(runtime,"_compile_plain_goal",side_effect=compile_failure), \
             mock.patch.object(
                 runtime,"_ground_plain_goal_to_bound_capabilities",
                 return_value=(evidence_path,grounding),
             ), \
             mock.patch.object(
                 runtime,"_load_auto_capability_acquisition",
                 side_effect=AssertionError("external acquisition must not load"),
             ), \
             mock.patch.object(
                 runtime,"_load_capability_discovery",
                 side_effect=AssertionError("external discovery must not load"),
             ):
            with self.assertRaisesRegex(
                runtime.Blocker,
                "BOUND_CAPABILITY_GROUNDING_AVAILABLE",
            ) as ctx:
                runtime.run_goal({},mission)
        detail=str(ctx.exception)
        self.assertIn("decision.synthesis.typed.stdlib",detail)
        self.assertIn('"external_capability_acquisition_attempted": false',detail.lower())

    def test_grounding_helper_persists_auditable_evidence(self):
        mission={"mission_id":"TEST-BOUND-GROUNDING-EVIDENCE"}
        goal="Create a DOCX document report."
        path=ROOT/"astra_runtime"/"evidence"/"TEST-BOUND-GROUNDING-EVIDENCE__BOUND_CAPABILITY_GROUNDING.json"
        path.unlink(missing_ok=True)
        self.addCleanup(lambda:path.unlink(missing_ok=True))
        evidence_path,result=runtime._ground_plain_goal_to_bound_capabilities(mission,goal)
        self.assertEqual(evidence_path,path)
        self.assertTrue(path.is_file())
        self.assertEqual(result["model_dependency_count"],0)
        self.assertGreaterEqual(result["grounded_clause_count"],1)
        self.assertTrue(result["candidate_capability_ids"])
        self.assertNotIn("leela-zero",result["candidate_capability_ids"])


if __name__=="__main__":
    unittest.main(verbosity=2)
