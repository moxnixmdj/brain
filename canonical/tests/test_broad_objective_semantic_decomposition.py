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

    def test_generic_run_verification_method_language_is_not_explicit_recipe(self):
        objective=(
            "Assess whether a material property differs between two operating regimes. "
            "Use authoritative primary technical evidence and a real executable check. "
            "Autonomously discover and verify relevant sources, choose and run a zero-cost "
            "verification method, identify material scope limitations, independently verify "
            "the consequential result, and produce a decision-quality answer."
        )
        out=self.dec.decompose(objective)
        self.assertEqual(out["status"],"DECOMPOSED",out)

    def test_concrete_run_command_remains_explicit_recipe(self):
        out=self.dec.decompose(
            "Assess whether two measured values differ. Run python verify_values.py"
        )
        self.assertEqual(out["status"],"UNSUPPORTED")
        self.assertEqual(out["reason"],"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE")

    def test_absolute_executable_path_remains_explicit_recipe(self):
        out=self.dec.decompose(
            "Assess whether two measured values differ. Run /usr/bin/python verify_values.py"
        )
        self.assertEqual(out["status"],"UNSUPPORTED",out)
        self.assertEqual(out["reason"],"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE")

    def test_unknown_cli_command_remains_explicit_recipe(self):
        out=self.dec.decompose(
            "Assess whether two measured values differ. Run customtool --verify values.json"
        )
        self.assertEqual(out["status"],"UNSUPPORTED",out)
        self.assertEqual(out["reason"],"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE")

    def test_generic_method_with_concrete_tool_remains_recipe(self):
        out=self.dec.decompose(
            "Assess whether two measured values differ. Run a verification method with python verify.py"
        )
        self.assertEqual(out["status"],"UNSUPPORTED",out)
        self.assertEqual(out["reason"],"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE")

    def test_generic_execute_method_variants_remain_broad(self):
        for objective in [
            "Assess whether two measured values differ. Execute a validation procedure, and independently verify the result.",
            "Evaluate whether two regimes differ. Run an independently chosen verification approach; preserve material limitations.",
        ]:
            out=self.dec.decompose(objective)
            self.assertEqual(out["status"],"DECOMPOSED",out)

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

    def test_grounding_exposes_decomposition_when_all_multiclause_parts_are_unresolved(self):
        objective=(
            "Assess whether a material property differs between two operating regimes. "
            "Use authoritative primary technical evidence and a real executable check. "
            "Identify material scope limitations and independently verify the consequential result."
        )
        out=self.grounding.ground(objective,{})
        self.assertGreater(len(out["clauses"]),1)
        self.assertEqual(out["grounded_clause_count"],0)
        self.assertEqual(
            out["unresolved_clause_indexes"],
            list(range(len(out["clauses"]))),
        )
        self.assertTrue(out["broad_objective_decomposition_available"])
        self.assertEqual(out["broad_objective_decomposition"]["status"],"DECOMPOSED")
        self.assertEqual(out["model_dependency_count"],0)

    def test_spent_http2_input_now_reaches_broad_decomposition_without_reexecution(self):
        objective=(
            "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater "
            "than the protocol's default initial stream flow-control window. Use authoritative primary "
            "technical evidence and a real executable check. Autonomously discover and verify the relevant "
            "specification, determine how to extract and interpret the required limits, choose and run a "
            "zero-cost verification method, identify material protocol-scope or interpretation limitations, "
            "independently verify the consequential result, and produce a decision-quality answer with provenance."
        )
        direct=self.dec.decompose(objective)
        self.assertEqual(direct["status"],"DECOMPOSED",direct)
        out=self.grounding.ground(objective,{})
        self.assertGreater(len(out["clauses"]),1)
        self.assertEqual(out["grounded_clause_count"],0)
        self.assertEqual(
            out["unresolved_clause_indexes"],
            list(range(len(out["clauses"]))),
        )
        self.assertTrue(out["broad_objective_decomposition_available"],out)
        self.assertEqual(out["broad_objective_decomposition"]["status"],"DECOMPOSED")
        self.assertEqual(out["model_dependency_count"],0)

    def test_grounding_keeps_unsupported_goal_unresolved_without_decomposition(self):
        out=self.grounding.ground("Create output.json with one record",{})
        self.assertEqual(out["grounded_clause_count"],0)
        self.assertFalse(out["broad_objective_decomposition_available"])
        self.assertIsNone(out["broad_objective_decomposition"])


if __name__=="__main__":
    unittest.main(verbosity=2)
