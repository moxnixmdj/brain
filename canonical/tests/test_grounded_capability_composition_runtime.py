#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=ROOT/"runtime"

spec=importlib.util.spec_from_file_location(
    "project_brain_grounded_composition_runtime_integration",
    RUNTIME_DIR/"astra_runtime.py",
)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)


class GroundedCompositionRuntimeIntegrationTests(unittest.TestCase):
    GOAL="Assess knowledge consistency from https://httpbin.org/get?claim=alpha."

    def grounding(self):
        registry=runtime._load_bound_capability_registry()
        cid="knowledge.consistency.assess"
        entry=registry[cid]
        return {
            "schema":"PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1",
            "goal":self.GOAL,
            "goal_sha256":"not_revalidated_here",
            "clauses":[{
                "index":0,"start":0,"end":len(self.GOAL),
                "text":self.GOAL,
                "status":"GROUNDED",
                "candidates":[{
                    "capability_id":cid,
                    "combined_score":10,
                    "lexical":{
                        "score":7,
                        "matched_goal_tokens":["consistency"],
                        "matched_provides":[["consistency","assessment"]],
                        "matched_keywords":[["consistency","consistency"]],
                        "matched_identity":[],
                    },
                    "similarity":{
                        "score":5,
                        "shared_tokens":["consistency"],
                        "sequence_ratio":0.5,
                        "coverage":1,
                    },
                    "matched_distinctive_tokens":["consistency"],
                    "provides":entry["provides"],
                    "requires":entry["requires"],
                }],
                "constraints":[],
                "output_contract":{"paths":[],"extensions":[]},
            }],
            "grounded_clause_count":1,
            "unresolved_clause_indexes":[],
            "candidate_capability_ids":[cid],
            "external_discovery_allowed_for_unresolved_only":True,
            "whole_goal_external_discovery_forbidden_if_any_bound_grounding":True,
            "model_dependency_count":0,
        }

    def test_composition_reuses_existing_proposal_validator_and_two_step_graph(self):
        grounding=self.grounding()
        mission={"mission_id":"GROUNDED-COMPOSITION-INTEGRATION","goal":self.GOAL}
        step={
            "adapter":"goal",
            "goal_ref":"goal",
            "verified_initial_facts":["network.http.available"],
        }
        with tempfile.TemporaryDirectory() as td:
            gp=pathlib.Path(td)/"grounding.json"
            gp.write_text(json.dumps(grounding),encoding="utf-8")
            with mock.patch.object(runtime,"EVID_DIR",pathlib.Path(td)):
                def inspect_only(derived,mission_arg,goal_arg):
                    problem=runtime._capability_problem_proposal(
                        derived,mission_arg,goal_arg
                    )
                    return {"validated_problem":problem}
                with mock.patch.object(
                    runtime,
                    "_run_verified_capability_proposal",
                    side_effect=inspect_only,
                ):
                    result=runtime._compose_grounded_bound_capabilities(
                        step,mission,self.GOAL,gp,grounding
                    )
        problem=result["validated_problem"]
        ids=[x["capability_id"] for x in problem["capability_instances"]]
        self.assertEqual(
            ids,
            ["knowledge.json.fetch.external","knowledge.consistency.assess"],
        )
        self.assertEqual(
            problem["target_effects"],
            ["knowledge.assessment.available"],
        )
        assess=problem["capability_instances"][1]
        self.assertEqual(
            assess["inputs"]["evidence_paths"],
            [{"$effect_result":{
                "effect":"knowledge.observation.available",
                "field":"output_path",
            }}],
        )
        self.assertEqual(
            result["grounding_composition"]["route"],
            "THIN_TARGET_EFFECT_ADAPTER_PLUS_MULTI_VERIFIED_CAPABILITY_V1",
        )
        self.assertEqual(result["grounding_composition"]["model_dependency_count"],0)

    def test_composition_failure_never_falls_through_to_external_acquisition(self):
        grounding=self.grounding()
        grounding["clauses"][0]["status"]="UNRESOLVED"
        grounding["clauses"][0]["candidates"]=[]
        grounding["grounded_clause_count"]=1
        mission={"mission_id":"GROUNDED-COMPOSITION-FAIL","goal":self.GOAL}
        step={"verified_initial_facts":["network.http.available"]}
        with tempfile.TemporaryDirectory() as td:
            gp=pathlib.Path(td)/"grounding.json"
            gp.write_text(json.dumps(grounding),encoding="utf-8")
            with mock.patch.object(runtime,"EVID_DIR",pathlib.Path(td)):
                with mock.patch.object(
                    runtime,"_load_auto_capability_acquisition",
                    side_effect=AssertionError("external acquisition must remain unreachable"),
                ):
                    with self.assertRaisesRegex(
                        runtime.Blocker,
                        "BOUND_CAPABILITY_COMPOSITION_FAILED",
                    ):
                        runtime._compose_grounded_bound_capabilities(
                            step,mission,self.GOAL,gp,grounding
                        )


if __name__=="__main__":
    unittest.main(verbosity=2)
