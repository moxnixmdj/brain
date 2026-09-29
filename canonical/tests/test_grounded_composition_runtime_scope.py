#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "project_brain_grounded_scope_runtime",
    ROOT/"runtime"/"astra_runtime.py",
)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)

class GroundedPlannerScopeTests(unittest.TestCase):
    def test_restricted_problem_does_not_inherit_unrelated_registry_capabilities(self):
        problem={
          "initial_facts":[],
          "target_effects":["grounded.clause.0.satisfied"],
          "restrict_inherited_bound_capabilities":True,
          "capabilities":[{
            "id":"grounded.0.0.local",
            "source_capability_id":"local",
            "requires":[],
            "provides":["effect.local","grounded.clause.0.satisfied"],
            "cost":1,
            "action":{"type":"finish","args":{"summary":"x"}},
            "result_fields":[],
          }],
        }
        registry={
          "unrelated":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "incremental_spend_usd":0,
            "requires":[],
            "provides":["grounded.clause.0.satisfied"],
            "cost":0,
            "action_template":{"type":"finish","args":{"summary":"cheat"}},
            "result_fields":[],
          }
        }
        with mock.patch.object(runtime,"_load_bound_capability_registry",return_value=registry):
            enriched=runtime._inherit_verified_capabilities(problem)
        ids=[x["id"] for x in enriched["capabilities"]]
        self.assertEqual(ids,["grounded.0.0.local"])
        self.assertEqual(enriched["_inherited_bound_capabilities"],[])

if __name__=="__main__":
    unittest.main(verbosity=2)
