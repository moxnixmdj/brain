from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.protocol_implication_batch_reducer_v1 import reduce_batch

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class ProtocolImplicationBatchReducerTests(unittest.TestCase):
    def docs(self):
        return (
            load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"),
            load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"),
            load("canonical/verification/OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        )

    def test_live_batch_exposes_exact_residual_without_claiming_closure(self):
        targets, witnesses, contamination = self.docs()
        out = reduce_batch(targets, witnesses, contamination)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["pair_count"], 99)
        self.assertEqual(out["target_count"], 11)
        self.assertEqual(out["witness_count"], 9)
        self.assertEqual(out["closed_target_count"], 0)
        self.assertEqual(out["residual_target_count"], 11)
        self.assertTrue(all(not row["implied"] for row in out["target_results"]))
        self.assertTrue(all(row["status"] == "TARGET_NOT_IMPLIED" for row in out["pair_results"]))
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_missing_contamination_receipt_fails_closed(self):
        targets, witnesses, contamination = self.docs()
        contamination = copy.deepcopy(contamination)
        contamination["contamination_admissibility_verified"] = False
        out = reduce_batch(targets, witnesses, contamination)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONTAMINATION_ADMISSIBILITY_NOT_INDEPENDENTLY_VERIFIED", out["errors"])

    def test_positive_semantic_claim_is_rejected_by_totalizer_before_algebra(self):
        targets, witnesses, contamination = self.docs()
        witnesses = copy.deepcopy(witnesses)
        witnesses["witnesses"][0]["normalized_target_atoms"] = [
            "invariant:zero_critical_authority_violations"
        ]
        out = reduce_batch(targets, witnesses, contamination)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("POSITIVE_SEMANTIC_BINDING_FORBIDDEN_IN_V1" in e for e in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
