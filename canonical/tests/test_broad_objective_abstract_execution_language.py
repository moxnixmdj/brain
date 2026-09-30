#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load():
    path=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
    spec=importlib.util.spec_from_file_location("broad_objective_abstract_execution",path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class BroadObjectiveAbstractExecutionLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dec=load()

    def test_abstract_run_requirement_remains_broad(self):
        objective=(
            "Assess whether two measured limits differ. Use authoritative evidence and "
            "choose and run a zero-cost verification method"
        )
        out=self.dec.decompose(objective)
        self.assertEqual(out["status"],"DECOMPOSED")
        self.assertEqual(out["question_shape"],"BOOLEAN_ASSESSMENT")
        self.assertEqual(out["model_dependency_count"],0)

    def test_abstract_execute_requirement_remains_broad(self):
        objective=(
            "Determine whether two independently reported quantities agree and execute "
            "an independently selected verification check"
        )
        out=self.dec.decompose(objective)
        self.assertEqual(out["status"],"DECOMPOSED")

    def test_concrete_python_recipe_still_fails_closed(self):
        out=self.dec.decompose(
            "Assess whether two outputs differ and run python verify.py"
        )
        self.assertEqual(out["status"],"UNSUPPORTED")
        self.assertEqual(
            out["reason"],"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE"
        )

    def test_concrete_relative_script_recipe_still_fails_closed(self):
        out=self.dec.decompose(
            "Determine whether two outputs differ and execute ./verify.sh"
        )
        self.assertEqual(out["status"],"UNSUPPORTED")
        self.assertEqual(
            out["reason"],"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE"
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
