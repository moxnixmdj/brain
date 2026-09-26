#!/usr/bin/env python3
import hashlib
import importlib.util
import pathlib
import sys
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

semantic=load(
    "project_brain_test_semantic_authorities",
    RUNTIME_DIR/"semantic_authorities.py",
)
runtime=load(
    "project_brain_test_semantic_authority_runtime",
    RUNTIME_DIR/"astra_runtime.py",
)


class DeterministicSemanticAuthorityTests(unittest.TestCase):
    GOAL="Materialize the supported fact."
    TARGET="knowledge.fact.materialized"

    def registry(self):
        return {
            "knowledge.support.materialize":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":["knowledge.assessment.available"],
                "provides":[self.TARGET],
                "keywords":["knowledge","supported","materialize","fact","actionable"],
                "cost":1,
                "platforms":["linux","windows","darwin"],
                "action_template":{
                    "type":"materialize_supported_knowledge",
                    "args":{"assessment_path":"${input.assessment_path}"}
                },
            },
            "knowledge.consistency.assess":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "requires":["knowledge.observation.available"],
                "provides":["knowledge.assessment.available"],
                "keywords":["knowledge","consistency","corroboration","conflict","freshness","assessment"],
                "cost":1,
                "platforms":["linux","windows","darwin"],
                "action_template":{
                    "type":"assess_knowledge_consistency",
                    "args":{"evidence_paths":"${input.evidence_paths}"}
                },
            },
        }

    def test_independent_registry_effect_authority_selects_target(self):
        out=semantic.generate(
            "registry-effect-lexical-v1",self.GOAL,self.registry(),
            runtime_dir=RUNTIME_DIR,
        )
        self.assertEqual(out["target_effects"],[self.TARGET])
        self.assertEqual(out["clauses"][0]["text"],self.GOAL)
        self.assertEqual(
            out["goal_sha256"],
            hashlib.sha256(self.GOAL.encode("utf-8")).hexdigest(),
        )

    def test_compiler_score_authority_selects_same_target_without_compiling_actions(self):
        out=semantic.generate(
            "compiler-score-v1",self.GOAL,self.registry(),
            runtime_dir=RUNTIME_DIR,
        )
        self.assertEqual(out["target_effects"],[self.TARGET])
        self.assertEqual(
            out["_authority_evidence"]["method"],
            "GOAL_COMPILER_GENERIC_SCORE_V1",
        )

    def test_nonzero_spend_capability_is_not_semantic_candidate(self):
        registry=self.registry()
        registry["paid.magic"]={
            "status":"VERIFIED_BOUND_CAPABILITY",
            "incremental_spend_usd":1,
            "requires":[],
            "provides":["magic.effect"],
            "keywords":["magic"],
            "action_template":{"type":"finish","args":{"summary":"unused"}},
        }
        with self.assertRaisesRegex(
            semantic.SemanticAuthorityFailure,
            "NO_VERIFIED_EFFECT_MATCH",
        ):
            semantic.generate(
                "registry-effect-lexical-v1",
                "Perform magic.",
                registry,
                runtime_dir=RUNTIME_DIR,
            )

    def test_runtime_quorum_can_be_generated_without_supplied_proposals(self):
        step={
            "semantic_goal_authority_generators":[
                "registry-effect-lexical-v1",
                "compiler-score-v1",
            ],
            "semantic_authority_policy":{
                "min_distinct_authority_classes":2,
                "authorities":{
                    "registry-effect-lexical-v1":"independent-registry-lexical",
                    "compiler-score-v1":"existing-compiler-score",
                },
            },
        }
        with mock.patch.object(
            runtime,"_load_bound_capability_registry",return_value=self.registry()
        ):
            contract=runtime._semantic_goal_contract(step,{},self.GOAL)
        self.assertEqual(contract["status"],"QUORUM_VERIFIED")
        self.assertEqual(contract["target_effects"],[self.TARGET])
        self.assertEqual(
            contract["generated_authorities"],
            ["compiler-score-v1","registry-effect-lexical-v1"],
        )

    def test_generator_disagreement_or_failure_cannot_be_hidden_by_one_authority(self):
        registry=self.registry()
        step={
            "semantic_goal_authority_generators":[
                "registry-effect-lexical-v1",
                "compiler-score-v1",
            ],
            "semantic_authority_policy":{
                "min_distinct_authority_classes":2,
                "authorities":{
                    "registry-effect-lexical-v1":"independent-registry-lexical",
                    "compiler-score-v1":"existing-compiler-score",
                },
            },
        }
        with mock.patch.object(
            runtime,"_load_bound_capability_registry",return_value=registry
        ), mock.patch.object(
            runtime,"_load_semantic_authorities"
        ) as loader:
            fake=mock.Mock()
            fake.generate.side_effect=[
                {
                    "authority_id":"registry-effect-lexical-v1",
                    "goal_sha256":hashlib.sha256(self.GOAL.encode()).hexdigest(),
                    "target_effects":[self.TARGET],
                    "clauses":[{
                        "start":0,"end":len(self.GOAL),"text":self.GOAL,
                        "target_effects":[self.TARGET],
                    }],
                },
                RuntimeError("second authority unavailable"),
            ]
            loader.return_value=fake
            with self.assertRaisesRegex(runtime.Blocker,"SEMANTIC_GOAL_QUORUM_NOT_REACHED"):
                runtime._semantic_goal_contract(step,{},self.GOAL)


if __name__=="__main__":
    unittest.main(verbosity=2)
