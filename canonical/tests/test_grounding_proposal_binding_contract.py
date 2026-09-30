#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

CANONICAL=pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT=CANONICAL.parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

compiler=load("proposal_binding_goal_compiler",CANONICAL/"runtime"/"goal_compiler.py")
grounder=load("proposal_binding_grounder",CANONICAL/"runtime"/"bound_capabilities"/"plain_goal_bound_grounding.py")
composer=load("proposal_binding_composer",CANONICAL/"runtime"/"bound_capabilities"/"grounded_executable_composition.py")
verifier=load("proposal_binding_verifier",CANONICAL/"runtime"/"bound_capabilities"/"grounded_executable_composition_verify.py")
planner=load("proposal_binding_planner",CANONICAL/"runtime"/"capability_planner.py")

class GroundingProposalBindingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=json.loads((CANONICAL/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))
        cls.registry=compiler._platform_admissible_registry(raw["capabilities"])

    def test_two_literal_urls_bind_fetches_and_fanin_consumer(self):
        goal=(
            "Fetch JSON from https://example.invalid/alpha.json. "
            "Fetch JSON from https://example.invalid/beta.json. "
            "Assess knowledge consistency."
        )
        grounding=grounder.ground(goal,self.registry)
        self.assertEqual(grounding["unresolved_clause_indexes"],[],grounding)
        self.assertEqual(len(grounding["clauses"]),3,grounding)

        for clause in grounding["clauses"][:2]:
            ids=[x["capability_id"] for x in clause["candidates"]]
            self.assertIn("knowledge.json.fetch.external",ids,clause)
            self.assertNotIn("http.json.fetch_from_state",ids,clause)
            selected=[
                x for x in clause["candidates"]
                if x["capability_id"]=="knowledge.json.fetch.external"
            ][0]
            self.assertTrue(selected["binding_affordance"]["url_consumable"])

        result=composer.compose(goal,grounding,self.registry,compiler,REPO_ROOT)
        ok,reason=verifier.verify(goal,result,grounding,self.registry)
        self.assertTrue(ok,reason)
        self.assertEqual(result["model_dependency_count"],0)

        planned=planner.plan_actions(result["problem"])
        actions=[x for x in planned["actions"] if x.get("type")!="finish"]
        self.assertEqual(len(actions),3,planned)
        self.assertEqual([x["type"] for x in actions],[
            "fetch_json_knowledge",
            "fetch_json_knowledge",
            "assess_knowledge_consistency",
        ])
        self.assertEqual(actions[0]["args"]["url"],"https://example.invalid/alpha.json")
        self.assertEqual(actions[1]["args"]["url"],"https://example.invalid/beta.json")
        self.assertEqual(actions[0]["args"]["json_path"],[])
        self.assertEqual(actions[1]["args"]["json_path"],[])
        self.assertIs(actions[0]["args"]["authoritative"],False)
        self.assertIs(actions[1]["args"]["authoritative"],False)

        out0=actions[0]["args"]["output_path"]
        out1=actions[1]["args"]["output_path"]
        self.assertNotEqual(out0,out1)
        self.assertTrue(out0.startswith("canonical/astra_runtime/tmp/auto_proposal/"),out0)
        self.assertTrue(out1.startswith("canonical/astra_runtime/tmp/auto_proposal/"),out1)

        refs=actions[2]["args"]["evidence_paths"]
        self.assertEqual(len(refs),2,refs)
        aliases=[]
        for ref in refs:
            self.assertEqual(set(ref),{"$effect_result"})
            inner=ref["$effect_result"]
            self.assertEqual(inner["field"],"output_path")
            aliases.append(inner["effect"])
        self.assertEqual(len(set(aliases)),2,aliases)
        self.assertTrue(all(x.startswith("knowledge.observation.available.grounded_clause_") for x in aliases),aliases)

    def test_plain_state_fetch_remains_valid_when_goal_supplies_state_path(self):
        goal="Fetch JSON from canonical/astra_runtime/state/example.json using url key source_url."
        grounding=grounder.ground(goal,self.registry)
        ids=[
            x["capability_id"]
            for clause in grounding["clauses"]
            for x in clause["candidates"]
        ]
        self.assertIn("http.json.fetch_from_state",ids,grounding)

if __name__=="__main__":
    unittest.main(verbosity=2)
