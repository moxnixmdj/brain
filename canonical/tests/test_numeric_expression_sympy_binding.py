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

    def compile_chain(self, reverse=False):
        predictor=(
          "Using the authoritative JSON source https://one.example/predictor, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/PREDICTOR_X.json. "
        )
        observed=(
          "Using the authoritative JSON source https://two.example/observed, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/OBSERVED_VALUE.json. "
        )
        prefix=(observed+predictor) if reverse else (predictor+observed)
        goal=(
          prefix+
          "Calculate the derived scalar using predicted = 3.5 * (predictor_x ** 1.5). "
          "Determine whether the predicted and observed scalars differ by at most 2."
        )
        return compiler.compile_goal(goal,self.registry(),ROOT)

    def test_expression_then_relation_uses_semantically_bound_source(self):
        compiled=self.compile_chain()
        parts=compiled["compiled_parts"]
        expr=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"][0]
        rel=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_RELATION"][0]
        self.assertEqual(expr["selected_capability"],"math.numeric_expression.sympy")
        self.assertEqual(expr["variable_names"],["predictor_x"])
        self.assertEqual(expr["producer_result_cycles"],[0])
        self.assertEqual(expr["result_cycle"],2)
        self.assertEqual(rel["producer_result_cycles"],[2,1])
        self.assertEqual(
            expr["variable_bindings"]["predictor_x"]["binding_evidence"]["mode"],
            "SEMANTIC_TOKEN_MATCH",
        )
        actions=compiled["controller_actions"]
        self.assertEqual(
            actions[2]["args"]["variables"]["predictor_x"],
            {"$result":{"cycle":0,"field":"value"}},
        )
        self.assertEqual(actions[3]["type"],"write_json_records")
        self.assertEqual(
            actions[3]["args"]["records"][0]["left"],
            {"$result":{"cycle":2,"field":"value"}},
        )
        self.assertEqual(
            actions[3]["args"]["records"][0]["right"],
            {"$result":{"cycle":1,"field":"value"}},
        )

    def test_source_order_does_not_control_variable_binding(self):
        compiled=self.compile_chain(reverse=True)
        expr=[
            p for p in compiled["compiled_parts"]
            if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"
        ][0]
        rel=[
            p for p in compiled["compiled_parts"]
            if p.get("mode")=="VERIFIED_BOUND_NUMERIC_RELATION"
        ][0]
        self.assertEqual(expr["producer_result_cycles"],[1])
        self.assertEqual(
            compiled["controller_actions"][2]["args"]["variables"]["predictor_x"],
            {"$result":{"cycle":1,"field":"value"}},
        )
        self.assertEqual(rel["producer_result_cycles"],[2,0])

    def test_multiple_variables_bind_by_semantic_provenance(self):
        goal=(
          "Using the authoritative JSON source https://one.example/current, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/POPULATION_2023.json. "
          "Using the authoritative JSON source https://two.example/prior, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/POPULATION_2020.json. "
          "Calculate the annual factor using annual_factor = "
          "(population_2023 / population_2020) ** (1 / 3)."
        )
        compiled=compiler.compile_goal(goal,self.registry(),ROOT)
        expr=[
            p for p in compiled["compiled_parts"]
            if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"
        ][0]
        self.assertEqual(
            {k:v["cycle"] for k,v in expr["variable_bindings"].items()},
            {"population_2023":0,"population_2020":1},
        )

    def test_ambiguous_producer_binding_fails_closed(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/TEMPERATURE_A.json. "
          "Using the authoritative JSON source https://two.example/b, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/TEMPERATURE_B.json. "
          "Calculate the derived scalar using converted = temperature * 1.8."
        )
        with self.assertRaisesRegex(
            compiler.GoalCompilationFailure,
            "NUMERIC_EXPRESSION_PRODUCER_BINDING_AMBIGUOUS",
        ):
            compiler.compile_goal(goal,self.registry(),ROOT)

    def test_unsafe_call_rejected_at_compile_time(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/X.json. "
          "Calculate the derived scalar using predicted = __import__('os').system('id')."
        )
        with self.assertRaisesRegex(
            compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_AST_NODE_REJECTED"
        ):
            compiler.compile_goal(goal,self.registry(),ROOT)

    def test_attribute_rejected_at_compile_time(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/X.json. "
          "Calculate the derived scalar using predicted = x.real."
        )
        with self.assertRaisesRegex(
            compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_AST_NODE_REJECTED"
        ):
            compiler.compile_goal(goal,self.registry(),ROOT)

    def test_exponent_bound_fails_closed(self):
        goal=(
          "Using the authoritative JSON source https://one.example/a, "
          "extract JSON path value and save the knowledge evidence to "
          "canonical/astra_runtime/tmp/X.json. "
          "Calculate the derived scalar using predicted = x ** 100."
        )
        with self.assertRaisesRegex(
            compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_EXPONENT_LIMIT"
        ):
            compiler.compile_goal(goal,self.registry(),ROOT)


if __name__=="__main__":
    unittest.main(verbosity=2)
