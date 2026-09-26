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


if __name__=="__main__":
    unittest.main(verbosity=2)
