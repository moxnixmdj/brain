#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"


def load_path(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GroundingComposableAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=load_path(
            BC/"plain_goal_bound_grounding.py",
            "grounding_composable_admission_test",
        )
        cls.compiler=load_path(
            ROOT/"canonical/runtime/goal_compiler.py",
            "grounding_compiler_test",
        )
        cls.binder=load_path(
            ROOT/"canonical/runtime/capability_proposal_generators.py",
            "grounding_binder_test",
        )
        raw=json.loads(
            (ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(
                encoding="utf-8"
            )
        )
        cls.registry=cls.compiler._platform_admissible_registry(raw["capabilities"])

    def test_missing_action_template_is_rejected_at_admission_boundary(self):
        ranked=[{
          "capability_id":"docx.document.verify.ooxml",
          "combined_score":99.0,
          "matched_distinctive_tokens":["document"],
        }]
        admitted,rejected,bound=self.g._admit_bindable_candidates(
            "technical documentation",
            0,ranked,self.registry,self.compiler,self.binder,ROOT,
            {},[],[],
        )
        self.assertEqual(admitted,[])
        self.assertEqual(bound,{})
        self.assertEqual(
            rejected,
            [{
              "capability_id":"docx.document.verify.ooxml",
              "error":"COMPOSITION_ACTION_TEMPLATE_MISSING",
            }],
        )

    def test_fresh_broad_research_goals_remain_unbound_and_decompose(self):
        goals=[
          "Assess whether HTTP cache freshness is distinct from validation according to technical documentation",
          "Determine whether Python technical documentation distinguishes object identity from equality comparison",
          "Compare whether two documented cryptographic properties, preimage resistance and collision resistance, are defined as distinct security properties",
        ]
        for goal in goals:
            result=self.g.ground(
                goal,self.registry,
                compiler=self.compiler,
                proposal_binder=self.binder,
                root=ROOT,
                enforce_bindability=True,
            )
            self.assertEqual(result["grounded_clause_count"],0,result)
            self.assertEqual(result["candidate_capability_ids"],[],result)
            self.assertTrue(result["broad_objective_decomposition_available"],result)
            broad=result["broad_objective_decomposition"]
            self.assertEqual(broad["status"],"DECOMPOSED",broad)
            self.assertEqual(
                [x["role"] for x in broad["roles"]],
                [
                  "SOURCE_DISCOVERY",
                  "EVIDENCE_ACQUISITION",
                  "EVIDENCE_EXTRACTION",
                  "RELATION_EVALUATION",
                  "DECISION_SYNTHESIS_AND_VERIFICATION",
                ],
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
