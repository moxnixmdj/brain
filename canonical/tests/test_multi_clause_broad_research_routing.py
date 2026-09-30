#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
MODULE=ROOT/"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"

def load_module():
    spec=importlib.util.spec_from_file_location("test_multi_clause_broad_grounding",MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

class MultiClauseBroadResearchRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod=load_module()

    def test_all_unresolved_multi_clause_broad_goal_routes_to_decomposer(self):
        goal=(
            "Assess whether Alpha metric is greater than Beta metric. "
            "Use authoritative technical evidence and independently verify the result."
        )
        out=self.mod.ground(goal,{})
        self.assertEqual(out["grounded_clause_count"],0,out)
        self.assertEqual(out["unresolved_clause_indexes"],[0,1],out)
        self.assertTrue(out["broad_objective_decomposition_available"],out)
        broad=out["broad_objective_decomposition"]
        self.assertEqual(broad["status"],"DECOMPOSED",broad)
        self.assertEqual(broad["question_shape"],"BOOLEAN_ASSESSMENT",broad)

    def test_non_broad_multi_clause_goal_stays_fail_closed(self):
        out=self.mod.ground("Write a report. Verify the report.",{})
        self.assertEqual(out["grounded_clause_count"],0,out)
        self.assertFalse(out["broad_objective_decomposition_available"],out)
        self.assertIsNone(out["broad_objective_decomposition"],out)

    def test_existing_bound_clause_keeps_precedence(self):
        registry={
            "metric.assess.bound":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["metric assessment"],
                "requires":[],
                "keywords":["assess alpha metric greater beta"],
                "result_fields":[],
            }
        }
        goal=(
            "Assess whether Alpha metric is greater than Beta metric. "
            "Preserve unresolved caveats."
        )
        out=self.mod.ground(goal,registry)
        self.assertGreater(out["grounded_clause_count"],0,out)
        self.assertFalse(out["broad_objective_decomposition_available"],out)
        self.assertIsNone(out["broad_objective_decomposition"],out)

if __name__=="__main__":
    unittest.main(verbosity=2)
