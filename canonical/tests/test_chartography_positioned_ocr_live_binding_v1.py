from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime import live_integrated_brain_v1


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
CAPABILITY_ID = "image.extract.ocr.tesseract.positioned.tsv"


class ChartographyPositionedOcrLiveBindingTests(unittest.TestCase):
    def test_registry_declares_exact_verified_positioned_ocr(self):
        doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
        row = doc["capabilities"][CAPABILITY_ID]
        self.assertEqual(row["status"], "VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(row["adapter_module"], "image_ocr_tesseract_positioned")
        self.assertTrue(row["verification"]["independent_verified"])
        self.assertEqual(
            row["verification"]["exact_runtime_blob_sha"],
            "19f3087489ce7f6f935fc7baaebdc8cd672f4b62",
        )
        self.assertFalse(row["source"]["donor_runtime_required"])
        self.assertFalse(row["source"]["external_frontier_model_required"])

    def test_live_verified_registry_discovers_positioned_ocr(self):
        registry = live_integrated_brain_v1.load_verified_registry()
        self.assertIn(CAPABILITY_ID, registry)
        row = registry[CAPABILITY_ID]
        self.assertEqual(row["adapter_module"], "image_ocr_tesseract_positioned")


if __name__ == "__main__":
    unittest.main()
