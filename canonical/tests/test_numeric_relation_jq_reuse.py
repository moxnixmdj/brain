#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
TARGET=ROOT/"runtime"/"goal_compiler.py"
spec=importlib.util.spec_from_file_location("project_brain_numeric_relation_goal_compiler",TARGET)
compiler=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=compiler
spec.loader.exec_module(compiler)


class NumericRelationJqReuseTests(unittest.TestCase):
    def registry(self):
        return {
            "json.query.jq":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["json.query.transform"],
                "requires":["json.file.available"],
                "keywords":["json","query","transform","table","structured"],
                "action_template":{
                    "type":"invoke_capability",
                    "args":{
                        "capability_id":"json.query.jq",
                        "input_path":"${input.json_path}",
                        "filter":"${input.jq_filter}",
                        "output_path":"${input.output_path}",
                        "raw_output":True,
                        "require_nonempty":True,
                        "timeout_s":60,
                    },
                    "expect":{"type":"field_equals","field":"output_verified","value":True},
                },
            }
        }

    def compile_relation(self,noun="readings",threshold="1.5"):
        goal=(
            "Using the authoritative JSON source https://one.example/data, "
            "extract JSON path value and save the knowledge evidence to "
            "canonical/astra_runtime/tmp/NUMREL_A.json. "
            "Using the authoritative JSON source https://two.example/data, "
            "extract JSON path value and save the knowledge evidence to "
            "canonical/astra_runtime/tmp/NUMREL_B.json. "
            f"Determine whether the two {noun} differ by at most {threshold}."
        )
        return compiler.compile_goal(goal,self.registry(),ROOT)

    def test_reuses_existing_jq_without_new_numeric_capability(self):
        compiled=self.compile_relation()
        self.assertTrue(compiled["clause_coverage_verified"])
        self.assertEqual(
            [a["type"] for a in compiled["controller_actions"]],
            ["fetch_json_knowledge","fetch_json_knowledge","write_json_records","invoke_capability","finish"],
        )
        relation=compiled["compiled_parts"][2]
        self.assertEqual(relation["mode"],"VERIFIED_BOUND_NUMERIC_RELATION")
        self.assertEqual(relation["selected_capability"],"json.query.jq")
        self.assertEqual(relation["relation"],"ABS_DIFF_LTE")
        self.assertEqual(relation["threshold"],1.5)
        self.assertEqual(relation["producer_result_cycles"],[0,1])
        materialize=compiled["controller_actions"][2]
        record=materialize["args"]["records"][0]
        self.assertEqual(record["left"],{"$result":{"cycle":0,"field":"value"}})
        self.assertEqual(record["right"],{"$result":{"cycle":1,"field":"value"}})
        compute=compiled["controller_actions"][3]
        self.assertEqual(compute["args"]["capability_id"],"json.query.jq")
        self.assertIn("fabs",compute["args"]["filter"])
        self.assertIn("predicate",compute["args"]["filter"])

    def test_domain_wording_and_scientific_notation_do_not_change_route(self):
        compiled=self.compile_relation(noun="temperatures",threshold="2e-1")
        relation=compiled["compiled_parts"][2]
        self.assertEqual(relation["selected_capability"],"json.query.jq")
        self.assertAlmostEqual(relation["threshold"],0.2)

    def test_three_prior_scalars_fail_closed(self):
        goal=(
            "Using the authoritative JSON source https://one.example/data, "
            "extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/NUMREL_A.json. "
            "Using the authoritative JSON source https://two.example/data, "
            "extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/NUMREL_B.json. "
            "Using the authoritative JSON source https://three.example/data, "
            "extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/NUMREL_C.json. "
            "Determine whether the two readings differ by at most 1."
        )
        with self.assertRaisesRegex(
            compiler.GoalCompilationFailure,
            "NUMERIC_RELATION_REQUIRES_EXACTLY_TWO_PRIOR_SCALARS",
        ):
            compiler.compile_goal(goal,self.registry(),ROOT)

    def test_negative_threshold_fails_closed(self):
        with self.assertRaisesRegex(
            compiler.GoalCompilationFailure,
            "NUMERIC_RELATION_THRESHOLD_INVALID",
        ):
            self.compile_relation(threshold="-0.1")


if __name__=="__main__":
    unittest.main(verbosity=2)
