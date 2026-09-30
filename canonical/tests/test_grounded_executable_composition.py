#!/usr/bin/env python3
import copy
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT=ROOT.parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

composition=load(
    "project_brain_grounded_composition_test",
    ROOT/"runtime"/"bound_capabilities"/"grounded_executable_composition.py",
)
verifier=load(
    "project_brain_grounded_composition_verify_test",
    ROOT/"runtime"/"bound_capabilities"/"grounded_executable_composition_verify.py",
)
planner=load(
    "project_brain_capability_planner_composition_test",
    ROOT/"runtime"/"capability_planner.py",
)

class FakeCompiler:
    class GoalCompilationFailure(RuntimeError):
        pass
    @staticmethod
    def _bind_inputs(goal,root,entry,context_paths=None,future_clauses=None):
        required=entry.get("_test_inputs") or {}
        return copy.deepcopy(required)

class GroundedExecutableCompositionTests(unittest.TestCase):
    def registry(self):
        return {
          "produce.alpha":{
            "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
            "requires":[],"provides":["artifact.alpha.ready"],"cost":2,
            "action_template":{"type":"invoke_capability","args":{"capability_id":"produce.alpha","output_path":"${input.output_path}"}},
            "result_fields":["output_path"],"_test_inputs":{"output_path":"out/a.json"},
          },
          "produce.alpha.fast":{
            "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
            "requires":[],"provides":["artifact.alpha.ready"],"cost":1,
            "action_template":{"type":"invoke_capability","args":{"capability_id":"produce.alpha.fast","output_path":"${input.output_path}"}},
            "result_fields":["output_path"],"_test_inputs":{"output_path":"out/a.json"},
          },
          "verify.alpha":{
            "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
            "requires":["artifact.alpha.ready"],"provides":["artifact.alpha.verified"],"cost":1,
            "action_template":{"type":"invoke_capability","args":{"capability_id":"verify.alpha","path":"out/a.json"}},
            "result_fields":["verified"],
          },
          "unrelated.beta":{
            "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
            "requires":[],"provides":["artifact.beta.ready"],"cost":1,
            "action_template":{"type":"invoke_capability","args":{"capability_id":"unrelated.beta"}},
            "result_fields":[],
          },
        }

    def grounding(self, ambiguous=False, non_equivalent=False):
        first=[
          {"capability_id":"produce.alpha","matched_distinctive_tokens":["alpha"]},
        ]
        status="GROUNDED"
        if ambiguous:
            status="AMBIGUOUS_BOUNDED"
            first.append({
              "capability_id":"unrelated.beta" if non_equivalent else "produce.alpha.fast",
              "matched_distinctive_tokens":["alpha"],
            })
        return {
          "schema":"PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1",
          "goal":"Create alpha then verify alpha",
          "goal_sha256":"g",
          "clauses":[
            {"index":0,"text":"Create alpha","status":status,"candidates":first,"output_contract":{"paths":["out/a.json"]}},
            {"index":1,"text":"verify alpha","status":"GROUNDED","candidates":[{"capability_id":"verify.alpha","matched_distinctive_tokens":["alpha"]}],"output_contract":{"paths":[]}},
          ],
          "grounded_clause_count":2,
          "unresolved_clause_indexes":[],
          "candidate_capability_ids":["produce.alpha","verify.alpha"],
          "input_contract_bindability_enforced":True,
          "model_dependency_count":0,
        }

    def test_semantic_only_grounding_is_not_composition_ready(self):
        goal="Create alpha then verify alpha"
        g=self.grounding()
        g["input_contract_bindability_enforced"]=False
        with self.assertRaisesRegex(
            composition.CompositionError,
            "GROUNDING_INPUT_CONTRACT_BINDABILITY_NOT_ENFORCED",
        ):
            composition.compose(goal,g,self.registry(),FakeCompiler,REPO_ROOT)

    def test_dependency_chain_plans_and_keeps_original_effects(self):
        goal="Create alpha then verify alpha"
        g=self.grounding()
        g["goal"]=goal
        import hashlib
        g["goal_sha256"]=hashlib.sha256(goal.encode()).hexdigest()
        result=composition.compose(goal,g,self.registry(),FakeCompiler,REPO_ROOT)
        ok,reason=verifier.verify(goal,result,g,self.registry())
        self.assertTrue(ok,reason)
        self.assertTrue(result["problem"]["restrict_inherited_bound_capabilities"])
        planned=planner.plan_actions(result["problem"])
        ids=[x.get("capability_id") for x in planned["actions"] if x.get("type")!="finish"]
        self.assertEqual(ids,["grounded.0.0.produce.alpha","grounded.1.0.verify.alpha"])
        self.assertEqual(planned["planning"]["target_effects"],[
          "grounded.clause.0.satisfied","grounded.clause.1.satisfied"
        ])

    def test_effect_equivalent_ambiguity_is_preserved_for_planner(self):
        goal="Create alpha then verify alpha"
        g=self.grounding(ambiguous=True)
        import hashlib
        g["goal"]=goal; g["goal_sha256"]=hashlib.sha256(goal.encode()).hexdigest()
        result=composition.compose(goal,g,self.registry(),FakeCompiler,REPO_ROOT)
        self.assertEqual(len(result["clauses"][0]["candidate_instance_ids"]),2)
        self.assertIn("artifact.alpha.ready",result["clauses"][0]["common_candidate_effects"])
        planned=planner.plan_actions(result["problem"])
        ids=[x.get("capability_id") for x in planned["actions"] if x.get("type")!="finish"]
        self.assertEqual(ids[0],"grounded.0.1.produce.alpha.fast")

    def test_non_equivalent_ambiguity_fails_closed(self):
        goal="Create alpha then verify alpha"
        g=self.grounding(ambiguous=True,non_equivalent=True)
        with self.assertRaisesRegex(composition.CompositionError,"AMBIGUOUS_CANDIDATES_NOT_EFFECT_EQUIVALENT"):
            composition.compose(goal,g,self.registry(),FakeCompiler,REPO_ROOT)

    def test_unresolved_clause_fails_closed(self):
        goal="Create alpha"
        g=self.grounding()
        g["clauses"][0]["status"]="UNRESOLVED"
        g["clauses"][0]["candidates"]=[]
        g["unresolved_clause_indexes"]=[0]
        with self.assertRaisesRegex(composition.CompositionError,"UNRESOLVED_GROUNDED_CLAUSES"):
            composition.compose(goal,g,self.registry(),FakeCompiler,REPO_ROOT)

    def test_independent_verifier_rejects_tampered_action(self):
        goal="Create alpha then verify alpha"
        g=self.grounding()
        import hashlib
        g["goal"]=goal; g["goal_sha256"]=hashlib.sha256(goal.encode()).hexdigest()
        result=composition.compose(goal,g,self.registry(),FakeCompiler,REPO_ROOT)
        bad=copy.deepcopy(result)
        bad["problem"]["capabilities"][0]["action"]["args"]["capability_id"]="unrelated.beta"
        ok,reason=verifier.verify(goal,bad,g,self.registry())
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("ACTION_MISMATCH:"),reason)

if __name__=="__main__":
    unittest.main(verbosity=2)
