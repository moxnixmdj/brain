from __future__ import annotations

import unittest

from canonical.runtime.protocol_implication_batch_reducer_v1 import reduce_batch


def target_doc():
    return {
        "targets": [{
            "predicate_id": "T",
            "family": "F",
            "atom_sources": [{"atom": "A", "sources": [{"literal": "target atom A"}]}],
            "metric_requirement_sources": [],
        }]
    }


def witness_doc():
    return {
        "witness_normalization_verified": True,
        "witnesses": [{
            "witness_id": "W",
            "source_predicate_id": "P",
            "independent_or_objective": True,
            "normalized_target_atoms": [],
            "semantic_implications": [],
            "normalized_metric_bounds": {},
            "target_atom_binding_receipts": {},
            "metric_binding_receipts": {},
        }],
    }


class Tests(unittest.TestCase):
    def test_scope_safe_v2_blocks_pair_without_explicit_scope_relation(self):
        out = reduce_batch(
            target_doc(),
            witness_doc(),
            {"contamination_admissibility_verified": True},
        )
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["pair_count"], 1)
        self.assertEqual(out["closed_target_count"], 0)
        row = out["pair_results"][0]
        self.assertEqual(row["status"], "TARGET_SCOPE_NOT_COVERED")
        self.assertFalse(row["implies_target"])
        self.assertTrue(row["scope_relation_missing"])
        self.assertEqual(row["missing_atoms"], ["A"])

    def test_contamination_gate_still_fails_closed(self):
        out = reduce_batch(
            target_doc(),
            witness_doc(),
            {"contamination_admissibility_verified": False},
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONTAMINATION_ADMISSIBILITY_NOT_INDEPENDENTLY_VERIFIED", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
