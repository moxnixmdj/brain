#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=ROOT/"runtime"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

composition=load(
    "project_brain_grounded_composition_test",
    RUNTIME_DIR/"bound_capabilities"/"grounded_capability_composition.py",
)

class GroundedCapabilityCompositionTests(unittest.TestCase):
    def registry(self):
        p=["linux","windows","darwin"]
        return {
            "observe":{
                "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
                "requires":["network.http.available"],
                "provides":["knowledge.observation.available"],
                "platforms":p,"cost":1,"result_fields":["output_path"],
                "keywords":["knowledge","observation","fetch"],
                "action_template":{
                    "type":"fetch_json_knowledge",
                    "args":{
                        "url":"${input.url}",
                        "output_path":"${input.output_path}",
                    },
                },
                "proposal_bindings":{
                    "url":{"type":"goal_url"},
                    "output_path":{"type":"auto_path","suffix":".json"},
                },
            },
            "assess":{
                "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
                "requires":["knowledge.observation.available"],
                "provides":["knowledge.assessment.available"],
                "platforms":p,"cost":1,"result_fields":["output_path","status"],
                "keywords":["knowledge","assessment","consistency"],
                "action_template":{
                    "type":"assess_knowledge_consistency",
                    "args":{
                        "evidence_paths":"${input.evidence_paths}",
                        "output_path":"${input.output_path}",
                    },
                },
                "proposal_bindings":{
                    "evidence_paths":{
                        "type":"effect_result",
                        "effect":"knowledge.observation.available",
                        "field":"output_path",
                        "container":"list",
                    },
                    "output_path":{"type":"auto_path","suffix":".json"},
                },
            },
            "assess-alt":{
                "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
                "requires":["knowledge.observation.available"],
                "provides":["knowledge.assessment.available"],
                "platforms":p,"cost":3,"result_fields":["output_path"],
                "keywords":["knowledge","assessment","consistency"],
                "action_template":{
                    "type":"assess_knowledge_consistency",
                    "args":{
                        "evidence_paths":"${input.evidence_paths}",
                        "output_path":"${input.output_path}",
                    },
                },
                "proposal_bindings":{
                    "evidence_paths":{
                        "type":"effect_result",
                        "effect":"knowledge.observation.available",
                        "field":"output_path",
                        "container":"list",
                    },
                    "output_path":{"type":"auto_path","suffix":".json"},
                },
            },
            "conflict":{
                "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
                "requires":[],"provides":["unrelated.effect"],"platforms":p,
                "cost":1,"result_fields":[],"keywords":["assessment"],
                "action_template":{"type":"list_tree","args":{"prefix":"canonical"}},
            },
        }

    def candidate(self,cid,provides):
        return {
            "capability_id":cid,
            "combined_score":10,
            "lexical":{
                "score":7,
                "matched_goal_tokens":["assessment"],
                "matched_provides":[["assessment","assessment"]],
                "matched_keywords":[],
                "matched_identity":[],
            },
            "similarity":{
                "score":5,"shared_tokens":["assessment"],
                "sequence_ratio":0.5,"coverage":1,
            },
            "matched_distinctive_tokens":["assessment"],
            "provides":provides,
            "requires":self.registry()[cid]["requires"],
        }

    def grounding(self,candidates,status=None):
        return {
            "schema":"PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1",
            "goal":"Assess knowledge consistency from https://example.test/data.",
            "goal_sha256":"unused-by-composition-layer",
            "clauses":[{
                "index":0,"start":0,"end":60,
                "text":"Assess knowledge consistency from https://example.test/data",
                "status":status or ("GROUNDED" if len(candidates)==1 else "AMBIGUOUS_BOUNDED"),
                "candidates":candidates,
                "constraints":[],
                "output_contract":{"paths":[],"extensions":[]},
            }],
            "grounded_clause_count":1,
            "unresolved_clause_indexes":[],
            "candidate_capability_ids":sorted(x["capability_id"] for x in candidates),
            "external_discovery_allowed_for_unresolved_only":True,
            "whole_goal_external_discovery_forbidden_if_any_bound_grounding":True,
            "model_dependency_count":0,
        }

    def test_unique_grounded_effect_drives_existing_two_step_planner(self):
        reg=self.registry()
        grounding=self.grounding([
            self.candidate("assess",["knowledge.assessment.available"])
        ])
        proposal,evidence=composition.compose(
            "Assess knowledge consistency from https://example.test/data.",
            grounding,["network.http.available"],reg,ROOT.parent,RUNTIME_DIR,
        )
        self.assertEqual(evidence["target_effects"],["knowledge.assessment.available"])
        self.assertEqual(
            [x["capability_id"] for x in proposal["capability_instances"]],
            ["observe","assess"],
        )
        self.assertFalse(evidence["new_planner_implemented"])
        self.assertEqual(
            proposal["capability_instances"][1]["inputs"]["evidence_paths"],
            [{"$effect_result":{
                "effect":"knowledge.observation.available",
                "field":"output_path",
            }}],
        )

    def test_ambiguous_providers_with_same_effect_preserve_effect_and_delegate_provider_choice(self):
        reg=self.registry()
        grounding=self.grounding([
            self.candidate("assess",["knowledge.assessment.available"]),
            self.candidate("assess-alt",["knowledge.assessment.available"]),
        ])
        proposal,evidence=composition.compose(
            "Assess knowledge consistency from https://example.test/data.",
            grounding,["network.http.available"],reg,ROOT.parent,RUNTIME_DIR,
        )
        self.assertEqual(evidence["target_effects"],["knowledge.assessment.available"])
        self.assertIn(
            proposal["capability_instances"][-1]["capability_id"],
            {"assess","assess-alt"},
        )
        self.assertEqual(
            proposal["capability_instances"][-1]["capability_id"],
            "assess",
        )

    def test_conflicting_candidate_effects_fail_closed(self):
        reg=self.registry()
        a=self.candidate("assess",["knowledge.assessment.available"])
        b=self.candidate("conflict",["unrelated.effect"])
        b["lexical"]["matched_provides"]=[["assessment","unrelated"]]
        grounding=self.grounding([a,b])
        with self.assertRaisesRegex(
            composition.CompositionError,
            "GROUNDING_TARGET_EFFECT_AMBIGUOUS",
        ):
            composition.derive_target_effects(grounding,reg)

    def test_unresolved_clause_fails_closed(self):
        grounding=self.grounding([],status="UNRESOLVED")
        grounding["grounded_clause_count"]=0
        grounding["unresolved_clause_indexes"]=[0]
        with self.assertRaisesRegex(
            composition.CompositionError,
            "GROUNDING_UNRESOLVED_CLAUSE",
        ):
            composition.derive_target_effects(grounding,self.registry())

    def test_tampered_provides_fail_closed(self):
        c=self.candidate("assess",["tampered.effect"])
        grounding=self.grounding([c])
        with self.assertRaisesRegex(
            composition.CompositionError,
            "GROUNDING_CANDIDATE_PROVIDES_MISMATCH",
        ):
            composition.derive_target_effects(grounding,self.registry())

    def test_model_backed_grounding_rejected(self):
        grounding=self.grounding([
            self.candidate("assess",["knowledge.assessment.available"])
        ])
        grounding["model_dependency_count"]=1
        with self.assertRaisesRegex(
            composition.CompositionError,
            "GROUNDING_MODEL_DEPENDENCY_NONZERO",
        ):
            composition.derive_target_effects(grounding,self.registry())


if __name__=="__main__":
    unittest.main(verbosity=2)
