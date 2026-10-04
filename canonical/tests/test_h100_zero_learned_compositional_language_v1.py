from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.h100_zero_learned_compositional_language_v1 import (
    compile_compositional_roles,
)

PRE = (
    Path(__file__).resolve().parents[1]
    / "governance"
    / "H100_ZERO_LEARNED_COMPOSITIONAL_LANGUAGE_PREEXPOSURE_V1.json"
)


class H100ZeroLearnedCompositionalLanguageTests(unittest.TestCase):
    def test_all_preexposed_tasks_exact(self):
        doc = json.loads(PRE.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["tasks"]), 12)
        for task in doc["tasks"]:
            out = compile_compositional_roles(task["text"])
            self.assertEqual(out["status"], task["expected_status"], (task["task_id"], out))
            self.assertEqual(out["inputs"], task["expected_inputs"], (task["task_id"], out))
            self.assertEqual(out["target"], task["expected_target"], (task["task_id"], out))
            self.assertEqual(out["persistent_learned_bytes"], 0)
            self.assertEqual(out["external_frontier_model_calls"], 0)
            self.assertEqual(out["external_learned_capability_calls"], 0)

    def test_negated_edge_never_creates_input(self):
        out = compile_compositional_roles("a does not predict b. b is the response.")
        self.assertEqual(out["status"], "ABSTAIN_DIRECTION_NOT_IDENTIFIED")
        self.assertEqual(out["inputs"], [])

    def test_positive_and_negative_same_role_abstains(self):
        out = compile_compositional_roles("x is a predictor. x is not a predictor. y is the response.")
        self.assertEqual(out["status"], "ABSTAIN_CONTRADICTION")

    def test_metadata_correction_removes_prior_input(self):
        out = compile_compositional_roles(
            "x and z are predictors. The latter is metadata. y is the response."
        )
        self.assertEqual(out["status"], "ROLES_IDENTIFIED")
        self.assertEqual(out["inputs"], ["x"])
        self.assertEqual(out["target"], "y")

    def test_reference_failure_is_fail_closed(self):
        out = compile_compositional_roles("x and y are variables. it is the response.")
        self.assertEqual(out["status"], "ABSTAIN_REFERENCE_AMBIGUOUS")

    def test_unrelated_unsupported_clause_does_not_create_semantics(self):
        out = compile_compositional_roles(
            "x is a predictor. y is the response. the apparatus is blue."
        )
        self.assertEqual(out["status"], "ROLES_IDENTIFIED")
        self.assertEqual(out["inputs"], ["x"])
        self.assertEqual(out["target"], "y")


if __name__ == "__main__":
    unittest.main(verbosity=2)
