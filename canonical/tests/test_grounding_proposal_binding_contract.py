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
proposal_binder=load("proposal_binding_generator",CANONICAL/"runtime"/"capability_proposal_generators.py")

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
        grounding=grounder.ground(
            goal,self.registry,
            compiler=compiler,proposal_binder=proposal_binder,root=REPO_ROOT,
            enforce_bindability=True,
        )
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

        verified_initial_facts=["network.http.available"]
        result=composer.compose(
            goal,grounding,self.registry,compiler,REPO_ROOT,
            verified_initial_facts=verified_initial_facts,
        )
        ok,reason=verifier.verify(
            goal,result,grounding,self.registry,
            verified_initial_facts=verified_initial_facts,
        )
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

        consumer=[
            x for x in result["problem"]["capabilities"]
            if x["source_capability_id"]=="knowledge.consistency.assess"
        ][0]
        graph_refs=consumer["inputs"]["evidence_paths"]
        self.assertEqual(len(graph_refs),2,graph_refs)
        aliases=[]
        for ref in graph_refs:
            self.assertEqual(set(ref),{"$effect_result"})
            inner=ref["$effect_result"]
            self.assertEqual(inner["field"],"output_path")
            aliases.append(inner["effect"])
        self.assertEqual(len(set(aliases)),2,aliases)
        self.assertTrue(all(x.startswith("knowledge.observation.available.grounded_clause_") for x in aliases),aliases)

        runtime_refs=actions[2]["args"]["evidence_paths"]
        self.assertEqual(len(runtime_refs),2,runtime_refs)
        for ref in runtime_refs:
            self.assertEqual(set(ref),{"$result"})
            inner=ref["$result"]
            self.assertEqual(inner["field"],"output_path")
            self.assertIsInstance(inner["cycle"],int)

    def test_non_url_semantic_candidate_must_also_bind(self):
        registry={
            "analysis.good":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["analysis.dataset"],
                "requires":[],
                "keywords":["analyze","dataset"],
                "action_template":{"type":"analysis","args":{"mode":"${input.mode}"}},
                "proposal_bindings":{"mode":{"type":"literal","value":"safe"}},
                "result_fields":["status"],
            },
            "analysis.bad":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["analysis.dataset"],
                "requires":[],
                "keywords":["analyze","dataset"],
                "action_template":{"type":"analysis","args":{"source_path":"${input.source_path}"}},
                "result_fields":["status"],
            },
        }
        result=grounder.ground(
            "Analyze the dataset.",
            registry,
            compiler=compiler,proposal_binder=proposal_binder,root=REPO_ROOT,
            enforce_bindability=True,
        )
        clause=result["clauses"][0]
        self.assertEqual(clause["status"],"GROUNDED",clause)
        self.assertEqual(
            [x["capability_id"] for x in clause["candidates"]],
            ["analysis.good"],
        )
        self.assertEqual(
            [x["capability_id"] for x in clause["rejected_unbindable_candidates"]],
            ["analysis.bad"],
        )
        self.assertTrue(result["input_contract_bindability_enforced"])

    def test_downstream_path_consumers_declare_causal_provenance(self):
        expected={
            "decision.synthesis.verify.stdlib":(
                "result_path","decision.synthesis.typed","output_path"
            ),
            "plain_goal.bound_capability.grounding.verify.stdlib":(
                "result_path","plain_goal.bound_capability.grounding","output_path"
            ),
            "knowledge.status.assert":(
                "assessment_path","knowledge.assessment.available","output_path"
            ),
            "knowledge.support.materialize":(
                "assessment_path","knowledge.assessment.available","output_path"
            ),
        }
        for capability_id,(key,effect,field) in expected.items():
            with self.subTest(capability_id=capability_id):
                spec=self.registry[capability_id]["proposal_bindings"][key]
                self.assertEqual(spec["type"],"effect_result")
                self.assertEqual(spec["effect"],effect)
                self.assertEqual(spec["field"],field)
        self.assertEqual(
            self.registry["knowledge.support.materialize"]["proposal_bindings"]["output_path"],
            {"type":"auto_path","suffix":".json"},
        )

    def test_state_fetch_stays_out_of_generic_grounding_without_prior_context(self):
        goal="Fetch JSON from canonical/astra_runtime/state/example.json using url key source_url."
        grounding=grounder.ground(
            goal,self.registry,
            compiler=compiler,proposal_binder=proposal_binder,root=REPO_ROOT,
            enforce_bindability=True,
        )
        self.assertEqual(grounding["grounded_clause_count"],0,grounding)
        clause=grounding["clauses"][0]
        rejected={
            x["capability_id"]:x["error"]
            for x in clause["rejected_unbindable_candidates"]
        }
        self.assertIn("http.json.fetch_from_state",rejected)
        self.assertIn("source_json_path",rejected["http.json.fetch_from_state"])

    def test_state_fetch_dedicated_compiler_path_remains_supported(self):
        subgoal=(
            "Fetch that project's authoritative live PyPI metadata "
            "from the metadata URL recorded in the registry"
        )
        out=compiler._compile_context_url_json_fetch(
            subgoal,
            [
                "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
                "canonical/astra_runtime/tmp/STRUCTURED_SELECTION_TEST.json",
            ],
            self.registry,
            REPO_ROOT,
        )
        self.assertIsNotNone(out)
        action=out["action"]
        self.assertEqual(action["args"]["capability_id"],"http.json.fetch_from_state")
        self.assertEqual(
            action["args"]["source_json_path"],
            "canonical/astra_runtime/tmp/STRUCTURED_SELECTION_TEST.json",
        )
        self.assertEqual(action["args"]["url_key"],"metadata_url")


if __name__=="__main__":
    unittest.main(verbosity=2)
