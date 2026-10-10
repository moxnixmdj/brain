from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.escape_progress_13_route_manifest_v1 import validate_manifest, validate_repo

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads(
    (ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V1.json").read_text()
)
CLAIM = json.loads(
    (ROOT / "canonical/governance/ESCAPE_PROGRESS_TOTALITY_FROZEN_13_CLAIM_20261010_V3.json").read_text()
)


def reader(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


class EscapeProgress13RouteManifestTests(unittest.TestCase):
    def test_current_manifest_passes_but_cc_r3_remains_open(self):
        out = validate_repo(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["row_count"], 13)
        self.assertEqual(out["gap_a_count"], 9)
        self.assertEqual(out["gap_b_count"], 4)
        self.assertEqual(out["strict_progress_witness_bound_count"], 0)
        self.assertEqual(out["externality_proved_count"], 0)
        self.assertTrue(out["shared_well_founded_progress_measure_bound"])
        self.assertEqual(out["gap_b_specific_action_bindings_proved"], 0)
        self.assertFalse(out["provider_totality_proved"])
        self.assertFalse(out["cc_r3_proved"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_obligation_fails_closed(self):
        m = copy.deepcopy(MANIFEST)
        m["rows"].pop()
        out = validate_manifest(m, CLAIM, reader)
        self.assertFalse(out["pass"])
        self.assertIn("ROW_COUNT_NOT_13", out["errors"])

    def test_stale_evidence_hash_fails_closed(self):
        m = copy.deepcopy(MANIFEST)
        m["rows"][0]["evidence"][1] = "0" * 40
        out = validate_manifest(m, CLAIM, reader)
        self.assertFalse(out["pass"])
        self.assertTrue(any("EVIDENCE_BLOB_STALE" in e for e in out["errors"]))

    def test_externality_or_strict_progress_cannot_be_granted_by_manifest(self):
        m = copy.deepcopy(MANIFEST)
        m["rows"][0]["externality_proved"] = True
        m["rows"][1]["strict_progress_witness_bound"] = True
        out = validate_manifest(m, CLAIM, reader)
        self.assertFalse(out["pass"])
        self.assertTrue(any("EXTERNALITY_MUST_REMAIN_FALSE" in e for e in out["errors"]))
        self.assertTrue(any("STRICT_PROGRESS_CREDIT_NOT_SUPPORTED" in e for e in out["errors"]))

    def test_shared_progress_evidence_hash_drift_fails_closed(self):
        m = copy.deepcopy(MANIFEST)
        m["shared_progress_reduction"]["evidence"][1] = "0" * 40
        out = validate_manifest(m, CLAIM, reader)
        self.assertFalse(out["pass"])
        self.assertIn("SHARED_PROGRESS_EVIDENCE_BLOB_STALE", out["errors"])

    def test_shared_measure_cannot_self_promote_provider_totality(self):
        m = copy.deepcopy(MANIFEST)
        m["shared_progress_reduction"]["provider_totality_proved"] = True
        out = validate_manifest(m, CLAIM, reader)
        self.assertFalse(out["pass"])
        self.assertIn("SHARED_PROGRESS_PROVIDER_TOTALITY_MUST_REMAIN_OPEN", out["errors"])

    def test_shared_measure_cannot_grant_specific_row_credit(self):
        m = copy.deepcopy(MANIFEST)
        m["shared_progress_reduction"]["specific_internal_action_bindings_proved"] = 1
        out = validate_manifest(m, CLAIM, reader)
        self.assertFalse(out["pass"])
        self.assertIn("SHARED_PROGRESS_ROW_CREDIT_MUST_REMAIN_ZERO", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
