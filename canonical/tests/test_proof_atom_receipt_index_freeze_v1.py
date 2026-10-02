from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.proof_atom_receipt_index_v1 import build_index

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "canonical/state/PROOF_ATOM_RECEIPT_INDEX_LIVE_FREEZE_20261002_V1.json"


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_frozen_live_index_exists_and_matches_current_corpus(self):
        self.assertTrue(FREEZE.exists(), "live full-Brain receipt index has not been frozen")
        frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
        live = build_index(
            _load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
            _load("canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json"),
            root=ROOT,
        )
        self.assertEqual(frozen["schema"], "PROJECT_BRAIN_PROOF_ATOM_RECEIPT_INDEX_LIVE_FREEZE_V1")
        self.assertEqual(frozen["status"], "FROZEN__ZERO_CREDIT__CURRENT_CORPUS_EXACT_MATCH")
        self.assertEqual(frozen["payload"], live)
        self.assertEqual(live["canonical_atom_count"], 40)
        self.assertEqual(live["capability_credit_delta"], 0)
        self.assertEqual(live["family_credit_delta"], 0)
        self.assertFalse(live["execution_authority"])
        self.assertFalse(live["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
