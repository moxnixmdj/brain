#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
TARGET=ROOT/"runtime"/"goal_compiler.py"
spec=importlib.util.spec_from_file_location("project_brain_typed_numeric_goal_compiler",TARGET)
compiler=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=compiler
spec.loader.exec_module(compiler)


class TypedScalarNumericExpressionTests(unittest.TestCase):
    def registry(self):
        return {
            "numeric.expression.sympy.typed":{
                "status":"VERIFIED_BOUND_CAPABILITY_CANDIDATE",
                "incremental_spend_usd":0,
                "provides":["numeric.scalar.expression.evaluate","numeric.scalar.derived"],
            },
            "json.query.jq":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["json.query.transform"],
            },
        }

    def goal(self, expression="stars * (forks ** 0.5)"):
        return (
            "Using the authoritative JSON source https://api.github.com/repos/pallets/click, "
            "extract JSON path stargazers_count as stars and save the knowledge evidence to "
            "canonical/astra_runtime/tmp/TYPED_NUMERIC_STARS.json. "
            "Using the authoritative JSON source https://api.github.com/repos/pallets/click, "
            "extract JSON path forks_count as forks and save the knowledge evidence to "
            "canonical/astra_runtime/tmp/TYPED_NUMERIC_FORKS.json. "
            f"Calculate repository score using score = {expression}. "
            "Determine whether score and stars differ by at most 100000."
        )

    def test_explicit_aliases_bind_expression_and_relation(self):
        compiled=compiler.compile_goal(self.goal(),self.registry(),ROOT)
        self.assertTrue(compiled["clause_coverage_verified"])
        self.assertEqual(
            [a["type"] for a in compiled["controller_actions"]],
            [
                "fetch_json_knowledge","fetch_json_knowledge",
                "invoke_capability","write_json_records","invoke_capability","finish",
            ],
        )
        fetch_a,fetch_b=compiled["compiled_parts"][0:2]
        self.assertEqual(fetch_a["result_alias"],"stars")
        self.assertEqual(fetch_b["result_alias"],"forks")

        expr=compiled["compiled_parts"][2]
        self.assertEqual(expr["mode"],"VERIFIED_BOUND_TYPED_NUMERIC_EXPRESSION")
        self.assertEqual(expr["result_alias"],"score")
        self.assertEqual(expr["result_cycle"],2)
        self.assertEqual(expr["variable_aliases"],["forks","stars"])
        action=compiled["controller_actions"][2]
        self.assertEqual(action["args"]["capability_id"],"numeric.expression.sympy.typed")
        self.assertEqual(action["args"]["variables"]["stars"],{"$result":{"cycle":0,"field":"value"}})
        self.assertEqual(action["args"]["variables"]["forks"],{"$result":{"cycle":1,"field":"value"}})

        relation=compiled["compiled_parts"][3]
        self.assertEqual(relation["producer_aliases"],["score","stars"])
        self.assertEqual(relation["producer_result_cycles"],[2,0])
        relation_record=compiled["controller_actions"][3]["args"]["records"][0]
        self.assertEqual(relation_record["left"],{"$result":{"cycle":2,"field":"value"}})
        self.assertEqual(relation_record["right"],{"$result":{"cycle":0,"field":"value"}})

    def test_unknown_alias_fails_closed(self):
        with self.assertRaisesRegex(
            compiler.GoalCompilationFailure,
            "NUMERIC_EXPRESSION_ALIAS_UNBOUND:missing",
        ):
            compiler.compile_goal(self.goal("stars * missing"),self.registry(),ROOT)

    def test_duplicate_alias_fails_closed_before_expression(self):
        goal=(
            "Using the authoritative JSON source https://one.example/data, "
            "extract JSON path value as x and save the knowledge evidence to canonical/astra_runtime/tmp/A.json. "
            "Using the authoritative JSON source https://two.example/data, "
            "extract JSON path value as x and save the knowledge evidence to canonical/astra_runtime/tmp/B.json. "
            "Calculate result using y = x * 2."
        )
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"RESULT_ALIAS_DUPLICATE:x"):
            compiler.compile_goal(goal,self.registry(),ROOT)

    def test_function_call_is_rejected(self):
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_SYNTAX_REJECTED"):
            compiler.compile_goal(self.goal("sqrt(stars)"),self.registry(),ROOT)

    def test_attribute_and_subscript_are_rejected(self):
        for expression in ("stars.real","forks[0]"):
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_SYNTAX_REJECTED"):
                    compiler.compile_goal(self.goal(expression),self.registry(),ROOT)

    def test_string_literal_is_rejected(self):
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"NUMERIC_EXPRESSION_LITERAL_REJECTED"):
            compiler.compile_goal(self.goal("'3' * stars"),self.registry(),ROOT)


if __name__=="__main__":
    unittest.main(verbosity=2)
