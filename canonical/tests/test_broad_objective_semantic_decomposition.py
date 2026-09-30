#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]


def load(rel,name):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(name,p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BroadObjectiveDecompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dec=load("canonical/runtime/bound_capabilities/broad_objective_decompose.py","broad_dec")
        cls.grounding=load("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","broad_grounding")

    def test_cross_domain_roles_are_generic(self):
        objectives=[
            "Determine whether battery pack energy density improved faster from 2020 to 2025 than from 2015 to 2020",
            "Assess whether reported global mean sea level rise accelerated in the most recent decade relative to the preceding decade",
        ]
        expected=[
            "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
            "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION",
        ]
        for objective in objectives:
            out=self.dec.decompose(objective)
            self.assertEqual(out["status"],"DECOMPOSED")
            self.assertEqual([r["role"] for r in out["roles"]],expected)
            self.assertEqual(out["invented_source_urls"],[])
            self.assertEqual(out["invented_facts"],[])
            self.assertEqual(out["task_specific_literals_added"],[])
            self.assertEqual(out["model_dependency_count"],0)

    def test_explicit_recipe_is_not_reinterpreted(self):
        out=self.dec.decompose(
            "Determine whether values differ using https://example.com/data and extract JSON path value"
        )
        self.assertEqual(out["status"],"UNSUPPORTED")
        self.assertEqual(out["reason"],"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE")

    def test_non_broad_action_goal_is_not_reinterpreted(self):
        out=self.dec.decompose("Create canonical/astra_runtime/tmp/x.json with one record")
        self.assertEqual(out["status"],"UNSUPPORTED")

    def test_grounding_exposes_decomposition_only_after_zero_match(self):
        objective="Compare annual launch counts in the recent five-year period with the preceding five-year period"
        out=self.grounding.ground(objective,{})
        self.assertEqual(out["grounded_clause_count"],0)
        self.assertEqual(out["unresolved_clause_indexes"],[0])
        self.assertTrue(out["broad_objective_decomposition_available"])
        self.assertEqual(out["broad_objective_decomposition"]["status"],"DECOMPOSED")

    def test_grounding_keeps_unsupported_goal_unresolved_without_decomposition(self):
        out=self.grounding.ground("Create output.json with one record",{})
        self.assertEqual(out["grounded_clause_count"],0)
        self.assertFalse(out["broad_objective_decomposition_available"])
        self.assertIsNone(out["broad_objective_decomposition"])


if __name__=="__main__":
    unittest.main(verbosity=2)
