from __future__ import annotations

import unittest

from canonical.runtime.terminal_condition_restriction_cell_compiler_v1 import (
    ConditionRestrictionError,
    compile_condition_cells,
)


MATRIX = {
    "shared_condition_matrix": [
        {"condition": "CYBERSECURITY", "mapped_family_union": ["CODING", "AGENCY"]},
        {"condition": "LONG_CONTEXT", "mapped_family_union": ["CODING"]},
    ]
}


def proof(**overrides):
    p = {
        "proof_id": "p1",
        "family": "CODING",
        "proof_class": "POINTWISE_UNIVERSAL",
        "covered_conditions": ["CYBERSECURITY"],
        "independent_or_objective": True,
        "scope_complete": True,
        "source_path": "canonical/verification/x.json",
        "source_sha": "1" * 40,
    }
    p.update(overrides)
    return p


class ConditionRestrictionCompilerTests(unittest.TestCase):
    def test_exact_condition_family_pointwise_closes(self):
        r = compile_condition_cells(MATRIX, [proof()])
        self.assertEqual(r["closed_cells"], 1)
        self.assertEqual(r["open_cells"], 2)

    def test_family_match_without_condition_scope_stays_open(self):
        r = compile_condition_cells(MATRIX, [proof(covered_conditions=[])])
        self.assertEqual(r["closed_cells"], 0)

    def test_aggregate_proof_stays_open(self):
        r = compile_condition_cells(MATRIX, [proof(proof_class="AGGREGATE_MEAN")])
        self.assertEqual(r["closed_cells"], 0)

    def test_scope_incomplete_stays_open(self):
        r = compile_condition_cells(MATRIX, [proof(scope_complete=False)])
        self.assertEqual(r["closed_cells"], 0)

    def test_non_independent_stays_open(self):
        r = compile_condition_cells(MATRIX, [proof(independent_or_objective=False)])
        self.assertEqual(r["closed_cells"], 0)

    def test_bad_sha_stays_open(self):
        r = compile_condition_cells(MATRIX, [proof(source_sha="not-a-sha")])
        self.assertEqual(r["closed_cells"], 0)

    def test_objective_ceiling_can_close(self):
        r = compile_condition_cells(MATRIX, [proof(proof_class="OBJECTIVE_CEILING")])
        self.assertEqual(r["closed_cells"], 1)

    def test_exhaustive_per_case_can_close(self):
        r = compile_condition_cells(MATRIX, [proof(proof_class="EXHAUSTIVE_FINITE_PER_CASE")])
        self.assertEqual(r["closed_cells"], 1)

    def test_wrong_family_stays_open(self):
        r = compile_condition_cells(MATRIX, [proof(family="OTHER")])
        self.assertEqual(r["closed_cells"], 0)

    def test_missing_matrix_fails_closed(self):
        with self.assertRaises(ConditionRestrictionError):
            compile_condition_cells({}, [proof()])


if __name__ == "__main__":
    unittest.main(verbosity=2)
