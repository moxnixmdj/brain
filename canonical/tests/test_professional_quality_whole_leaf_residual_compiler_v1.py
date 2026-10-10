from __future__ import annotations

import unittest

from canonical.runtime.professional_quality_whole_leaf_residual_compiler_v1 import (
    WholeLeafResidualError,
    compile_whole_leaf_residuals,
)


def entry(scope="S1", leaf="PQ::R1::SEMANTIC", **extra):
    out = {
        "scope_id": scope,
        "root_id": "R1",
        "contributes_to_leaf_ids": [leaf],
        "source_receipt": {"path": "canonical/verification/x.json", "git_blob_sha": "abc"},
        "global_leaf_closure": False,
    }
    out.update(extra)
    return out


class WholeLeafResidualCompilerTests(unittest.TestCase):
    def test_bounded_witness_does_not_close_leaf(self):
        out = compile_whole_leaf_residuals([entry()], ["PQ::R1::SEMANTIC"])
        self.assertEqual(out["closed_leaf_count"], 0)
        self.assertEqual(out["open_leaf_count"], 1)
        self.assertEqual(
            out["leaves"][0]["residual"],
            "TOTALITY_OR_CERTIFIED_COMPLETE_UNION_REQUIRED",
        )

    def test_verified_totality_closes_exact_leaf(self):
        e = entry(
            whole_leaf_totality_certificate={
                "independently_verified": True,
                "leaf_id": "PQ::R1::SEMANTIC",
            }
        )
        out = compile_whole_leaf_residuals([e], ["PQ::R1::SEMANTIC"])
        self.assertEqual(out["closed_leaf_count"], 1)

    def test_verified_complete_union_closes_exact_leaf(self):
        e = entry(
            certified_complete_union={
                "independently_verified": True,
                "covers_all_admissible_inputs": True,
                "leaf_id": "PQ::R1::SEMANTIC",
            }
        )
        out = compile_whole_leaf_residuals([e], ["PQ::R1::SEMANTIC"])
        self.assertEqual(out["closed_leaf_count"], 1)

    def test_global_overclaim_without_totality_fails_closed(self):
        e = entry(global_leaf_closure=True)
        with self.assertRaisesRegex(
            WholeLeafResidualError, "UNSUPPORTED_GLOBAL_LEAF_CLOSURE_CLAIM"
        ):
            compile_whole_leaf_residuals([e], ["PQ::R1::SEMANTIC"])

    def test_leaf_universe_mismatch_fails_closed(self):
        with self.assertRaisesRegex(WholeLeafResidualError, "LEAF_UNIVERSE_MISMATCH"):
            compile_whole_leaf_residuals(
                [entry()],
                ["PQ::R1::SEMANTIC", "PQ::R1::EXECUTION"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
