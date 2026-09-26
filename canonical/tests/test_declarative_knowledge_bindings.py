#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=CANONICAL_ROOT/"runtime"
PATH=RUNTIME/"goal_compiler.py"
spec=importlib.util.spec_from_file_location("declarative_knowledge_gc",PATH)
gc=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=gc
spec.loader.exec_module(gc)
REG=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]


def compound(status="CONFLICTED", evidence_count=2, freshness=True):
    clauses=[
        "Using an external JSON source https://example.com/a.json, extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/K1.json."
    ]
    if evidence_count >= 2:
        clauses.append(
            "Using an external JSON source https://example.com/b.json, extract JSON path value and save the knowledge evidence to canonical/astra_runtime/tmp/K2.json."
        )
    refs=" ".join(
        f"canonical/astra_runtime/tmp/K{i}.json" for i in range(1,evidence_count+1)
    )
    suffix=" with freshness budget 300 seconds" if freshness else ""
    clauses.append(
        f"Assess the knowledge evidence {refs} and save the assessment to canonical/astra_runtime/tmp/ASSESS.json{suffix}."
    )
    clauses.append(f"Verify that the knowledge status is {status}.")
    return " ".join(clauses)


class DeclarativeKnowledgeBindingTests(unittest.TestCase):
    def test_specialized_handlers_removed(self):
        for name in (
            "_compile_external_json_knowledge_fetch",
            "_compile_knowledge_consistency_assessment",
            "_compile_knowledge_status_assertion",
            "_compile_authoritative_json_knowledge_fetch",
            "_compile_learned_value_record",
            "_compile_knowledge_revalidation",
        ):
            self.assertFalse(hasattr(gc,name),name)

    def test_external_fetch_uses_registry_capability_and_false_authority(self):
        out=gc.compile_goal(compound(),REG,CANONICAL_ROOT.parent)
        first=out["compiled_parts"][0]
        self.assertEqual(first["mode"],"VERIFIED_CAPABILITY")
        self.assertEqual(first["selected_capability"],"knowledge.json.fetch.external")
        self.assertEqual(first["inputs"]["url"],"https://example.com/a.json")
        self.assertEqual(first["inputs"]["json_path"],["value"])
        self.assertEqual(first["inputs"]["authoritative"],False)

    def test_assessment_fanin_and_status_bind_declaratively(self):
        out=gc.compile_goal(compound(),REG,CANONICAL_ROOT.parent)
        assessment=out["compiled_parts"][2]
        status=out["compiled_parts"][3]
        self.assertEqual(assessment["selected_capability"],"knowledge.consistency.assess")
        self.assertEqual(
            assessment["inputs"]["evidence_paths"],
            [
                "canonical/astra_runtime/tmp/K1.json",
                "canonical/astra_runtime/tmp/K2.json",
            ],
        )
        self.assertEqual(assessment["inputs"]["max_age_s"],300)
        self.assertEqual(status["selected_capability"],"knowledge.status.assert")
        self.assertEqual(status["inputs"]["assessment_path"],"canonical/astra_runtime/tmp/ASSESS.json")
        self.assertEqual(status["inputs"]["expected_status"],"CONFLICTED")

    def test_default_freshness_budget_is_bounded(self):
        out=gc.compile_goal(compound(freshness=False),REG,CANONICAL_ROOT.parent)
        self.assertEqual(out["compiled_parts"][2]["inputs"]["max_age_s"],86400)

    def test_single_source_assessment_fails_closed(self):
        with self.assertRaises(gc.GoalCompilationFailure):
            gc.compile_goal(compound(evidence_count=1),REG,CANONICAL_ROOT.parent)

    def test_unknown_status_fails_closed(self):
        with self.assertRaises(gc.GoalCompilationFailure):
            gc.compile_goal(compound(status="MAGICAL"),REG,CANONICAL_ROOT.parent)


    def test_worldbank_plain_goal_preserves_canonical_causal_contract(self):
        goal=(
            "Using the authoritative JSON source https://api.worldbank.org/v2/indicator/SP.POP.TOTL?format=json, "
            "extract JSON path 1.0.sourceNote and save the knowledge evidence to "
            "canonical/astra_runtime/tmp/JIT_WORLDBANK_PLAIN_EVIDENCE.json. "
            "Create canonical/astra_runtime/tmp/JIT_WORLDBANK_PLAIN_USED.json with one record containing "
            "indicator_id SP.POP.TOTL and definition equal to the learned value. "
            "Finally independently re-fetch the authoritative source and verify the learned value is unchanged."
        )
        out=gc.compile_goal(goal,REG,CANONICAL_ROOT.parent)
        self.assertEqual(len(out["controller_actions"]),4)
        fetch,write,revalidate,finish=out["controller_actions"]
        self.assertEqual(fetch["type"],"fetch_json_knowledge")
        self.assertEqual(fetch["args"]["json_path"],[1,0,"sourceNote"])
        self.assertIs(fetch["args"]["authoritative"],True)
        self.assertEqual(write["type"],"write_json_records")
        self.assertEqual(write["args"]["fields"],["indicator_id","definition"])
        self.assertEqual(
            write["args"]["records"],
            [{
                "indicator_id":"SP.POP.TOTL",
                "definition":{"$result":{"cycle":0,"field":"value"}},
            }],
        )
        self.assertEqual(revalidate["type"],"assert_json_knowledge")
        self.assertEqual(
            revalidate["args"]["evidence_path"],
            "canonical/astra_runtime/tmp/JIT_WORLDBANK_PLAIN_EVIDENCE.json",
        )
        self.assertEqual(finish["type"],"finish")

    def test_independent_refetch_and_verify_is_one_clause(self):
        goal=(
            "Using the authoritative JSON source https://example.com/a.json, "
            "extract JSON path a.b and save the knowledge evidence to canonical/astra_runtime/tmp/K.json. "
            "Finally independently re-fetch the authoritative source and verify the learned value is unchanged."
        )
        clauses=gc.decompose_goal(goal)
        self.assertEqual(len(clauses),2)
        self.assertIn("and verify the learned value is unchanged",clauses[1])

    def test_result_reference_binding_requires_prior_effect(self):
        goal=(
            "Create canonical/astra_runtime/tmp/USED.json with one record containing "
            "indicator_id X and definition equal to the learned value."
        )
        with self.assertRaises(gc.GoalCompilationFailure):
            gc.compile_goal(goal,REG,CANONICAL_ROOT.parent)

    def test_revalidation_binding_requires_prior_observation(self):
        goal="Finally independently re-fetch the authoritative source and verify the learned value is unchanged."
        with self.assertRaises(gc.GoalCompilationFailure):
            gc.compile_goal(goal,REG,CANONICAL_ROOT.parent)


if __name__=="__main__":
    unittest.main(verbosity=2)
