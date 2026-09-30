#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
TARGET=ROOT/"runtime"/"goal_compiler.py"
spec=importlib.util.spec_from_file_location("project_brain_numeric_expression_compiler",TARGET)
compiler=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=compiler
spec.loader.exec_module(compiler)


class TypedScalarExpressionCompilerTests(unittest.TestCase):
    def registry(self):
        return {
          "math.numeric_expression.sympy":{
            "status":"CANDIDATE_BOUND_CAPABILITY",
            "incremental_spend_usd":0,
            "provides":["numeric.scalar.expression.evaluate"],
          },
          "json.query.jq":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "incremental_spend_usd":0,
            "provides":["json.query.transform"],
          },
        }

    def compile_chain(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/A.json. "
          "Using the authoritative JSON source https://two.example/b, extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/B.json. "
          "Calculate the derived scalar using predicted = 3.5 * (x ** 1.5). "
          "Determine whether the predicted and observed scalars differ by at most 2."
        )
        return compiler.compile_goal(goal,self.registry(),ROOT)

    def test_expression_then_relation_uses_derived_and_unused_source(self):
        compiled=self.compile_chain()
        parts=compiled["compiled_parts"]
        expr=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"][0]
        rel=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_RELATION"][0]
        self.assertEqual(expr["selected_capability"],"math.numeric_expression.sympy")
        self.assertEqual(expr["variable_names"],["x"])
        self.assertEqual(expr["producer_result_cycles"],[0])
        self.assertEqual(expr["result_cycle"],2)
        self.assertEqual(rel["producer_result_cycles"],[2,1])
        actions=compiled["controller_actions"]
        self.assertEqual(actions[2]["args"]["variables"]["x"],{"$result":{"cycle":0,"field":"value"}})
        self.assertEqual(actions[3]["type"],"write_json_records")
        self.assertEqual(actions[3]["args"]["records"][0]["left"],{"$result":{"cycle":2,"field":"value"}})
        self.assertEqual(actions[3]["args"]["records"][0]["right"],{"$result":{"cycle":1,"field":"value"}})

    def test_unsafe_call_rejected_at_compile_time(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/A.json. "
          "Calculate the derived scalar using predicted = __import__('os').system('id')."
        )
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_AST_NODE_REJECTED"):
            compiler.compile_goal(goal,self.registry(),ROOT)

    def test_attribute_rejected_at_compile_time(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/A.json. "
          "Calculate the derived scalar using predicted = x.real."
        )
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_AST_NODE_REJECTED"):
            compiler.compile_goal(goal,self.registry(),ROOT)

    def test_exponent_bound_fails_closed(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/A.json. "
          "Calculate the derived scalar using predicted = x ** 100."
        )
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_EXPONENT_LIMIT"):
            compiler.compile_goal(goal,self.registry(),ROOT)


if __name__=="__main__":
    unittest.main(verbosity=2)
