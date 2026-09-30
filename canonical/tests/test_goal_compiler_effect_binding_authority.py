#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical"/"runtime"/"goal_compiler.py"
spec=importlib.util.spec_from_file_location("project_brain_goal_compiler_effect_binding_test",PATH)
compiler=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=compiler
spec.loader.exec_module(compiler)


class EffectBindingAuthorityTest(unittest.TestCase):
    def test_detects_nested_effect_result_binding(self):
        self.assertTrue(compiler._contains_effect_result_binding({
            "input_path":{"$effect_result":{"effect":"x.ready","field":"input_path"}}
        }))
        self.assertFalse(compiler._contains_effect_result_binding({
            "input_path":"canonical/input.json"
        }))

    def test_direct_compound_compiler_defers_explicit_effect_result_consumer(self):
        registry={
            "producer":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "provides":["x.ready"],
                "requires":[],
                "keywords":["transform"],
                "action_template":{"type":"invoke_capability","args":{"capability_id":"producer"}},
            },
            "consumer":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "provides":["x.verified"],
                "requires":["x.ready"],
                "keywords":["verify"],
                "action_template":{"type":"invoke_capability","args":{"capability_id":"consumer"}},
                "proposal_bindings":{
                    "input_path":{"$effect_result":{"effect":"x.ready","field":"input_path"}},
                    "result_path":{"$effect_result":{"effect":"x.ready","field":"output_path"}},
                },
            },
        }
        compiled=[
            {
                "schema":"PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
                "selected_capability":"producer",
                "inputs":{},
                "target_effects":["x.ready"],
                "score":10,
            },
            {
                "schema":"PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
                "selected_capability":"consumer",
                "inputs":{},
                "target_effects":["x.verified"],
                "score":10,
            },
        ]
        with mock.patch.object(compiler,"_compile_single_goal",side_effect=compiled):
            with self.assertRaises(compiler.GoalCompilationFailure) as ctx:
                compiler._compile_compound_goal(
                    "transform data then independently verify data",
                    ["transform data","independently verify data"],
                    registry,
                    ROOT,
                )
        self.assertEqual(ctx.exception.code,"GOAL_COMPILATION_SUBGOAL_UNRESOLVED")
        self.assertIn("EXPLICIT_EFFECT_RESULT_BINDING_REQUIRES_GROUNDED_COMPOSITION",ctx.exception.detail)
        self.assertIn("ONE_CAUSAL_BINDING_AUTHORITY",ctx.exception.detail)


if __name__=="__main__":
    unittest.main()
