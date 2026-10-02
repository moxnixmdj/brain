from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.objective_route_certificate_verifier import (
    MANIFEST,
    validate,
    validate_manifest,
)


class ObjectiveRouteCertificateVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.manifest = json.loads((self.root / MANIFEST).read_text(encoding="utf-8"))

    def test_live_common_certificate_basis_passes(self):
        out = validate(self.root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["route_count"], 3)
        self.assertFalse(out["semantic_projection_authorized"])
        self.assertTrue(out["residual_validation_required"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["terminal_results_observed"], 0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"], 0)

    def test_binding_blob_drift_fails_closed(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["routes"][0]["binding_blob_sha"] = "0" * 40
        out = validate_manifest(self.root, manifest)
        self.assertFalse(out["pass"])
        self.assertIn(
            "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001:BINDING_SHA_MISMATCH",
            out["errors"],
        )

    def test_duplicate_behavior_fails_closed(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["routes"].append(copy.deepcopy(manifest["routes"][0]))
        out = validate_manifest(self.root, manifest)
        self.assertFalse(out["pass"])
        self.assertIn(
            "BEHAVIOR_ID_DUPLICATE:BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
            out["errors"],
        )

    def test_kernel_drift_fails_closed(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["selection_kernel"]["blob_sha"] = "f" * 40
        out = validate_manifest(self.root, manifest)
        self.assertFalse(out["pass"])
        self.assertIn("SELECTION_KERNEL_SHA_MISMATCH", out["errors"])


if __name__ == "__main__":
    unittest.main()
