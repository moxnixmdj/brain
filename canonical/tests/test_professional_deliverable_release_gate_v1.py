from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from canonical.runtime.professional_deliverable_release_gate_v1 import verify

H = "a" * 40


def _pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF")


def _docx(path: Path, *, valid: bool = True) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        if valid:
            zf.writestr("word/document.xml", "<document/>")


def _base(root: Path) -> dict:
    _pdf(root / "report.pdf")
    return {
        "source_authority": [
            {"source_id": "task", "content_sha": H},
            {"source_id": "references", "content_sha": H},
        ],
        "contract": {
            "required_deliverable_ids": ["report"],
            "required_obligation_ids": ["analysis", "recommendation"],
            "required_verification_ids": ["arithmetic"],
            "visual_deliverable_ids": ["report"],
            "audience_fit_required": True,
        },
        "deliverables": [
            {
                "deliverable_id": "report",
                "path": "report.pdf",
                "expected_extension": ".pdf",
                "visual_checks": {
                    "pages_total": 2,
                    "pages_inspected": 2,
                    "render_complete": True,
                    "no_blank_pages": True,
                    "no_cutoff": True,
                    "no_unintended_overlap": True,
                    "legible": True,
                    "visual_receipt_sha": H,
                },
            }
        ],
        "obligations": [
            {"obligation_id": "analysis", "covered": True, "coverage_receipt_sha": H},
            {"obligation_id": "recommendation", "covered": True, "coverage_receipt_sha": H},
        ],
        "verifications": [
            {"verification_id": "arithmetic", "passed": True, "verification_receipt_sha": H}
        ],
        "grounding": {
            "material_claims_present": True,
            "claim_manifest_complete": True,
            "all_material_claims_grounded": True,
            "claim_manifest_receipt_sha": H,
            "grounding_receipt_sha": H,
        },
        "audience_fit": {"passed": True, "receipt_sha": H},
        "final_submission": {
            "all_deliverables_opened_after_last_write": True,
            "receipt_sha": H,
        },
    }


class ProfessionalDeliverableReleaseGateV1Tests(unittest.TestCase):
    def test_complete_release_floor_passes_without_claiming_top(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            out = verify(m, base_dir=td)
            self.assertTrue(out["pass"], out)
            self.assertFalse(out["professional_quality_top"])
            self.assertFalse(out["owner_preference_equivalence"])
            self.assertFalse(out["semantic_premises_verified_by_runtime"])

    def test_missing_required_deliverable_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["deliverables"] = []
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("REQUIRED_DELIVERABLE_MISSING:report", out["errors"])

    def test_unexpected_deliverable_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = _base(root)
            (root / "extra.txt").write_text("x")
            m["deliverables"].append(
                {"deliverable_id": "extra", "path": "extra.txt", "expected_extension": ".txt"}
            )
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("UNEXPECTED_DELIVERABLE:extra", out["errors"])

    def test_corrupt_office_container_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _docx(root / "report.docx", valid=False)
            m = _base(root)
            m["contract"]["visual_deliverable_ids"] = ["report"]
            m["deliverables"][0]["path"] = "report.docx"
            m["deliverables"][0]["expected_extension"] = ".docx"
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertTrue(any(x.startswith("NATIVE_INTEGRITY_FAIL:report:") for x in out["errors"]))

    def test_visual_inspection_must_cover_every_page(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["deliverables"][0]["visual_checks"]["pages_inspected"] = 1
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("VISUAL_INSPECTION_INCOMPLETE:report", out["errors"])

    def test_missing_semantic_obligation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["obligations"] = m["obligations"][:1]
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("REQUIRED_OBLIGATION_MISSING:recommendation", out["errors"])

    def test_ungrounded_material_claims_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["grounding"]["all_material_claims_grounded"] = False
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("MATERIAL_CLAIMS_NOT_ALL_GROUNDED", out["errors"])

    def test_failed_required_calculation_blocks_release(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["verifications"][0]["passed"] = False
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("VERIFICATION_FAILED:arithmetic", out["errors"])

    def test_audience_fit_is_load_bearing_when_declared(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["audience_fit"]["passed"] = False
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("AUDIENCE_FIT_NOT_PROVED", out["errors"])

    def test_fake_receipt_hash_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["final_submission"]["receipt_sha"] = "not-a-hash"
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("FINAL_SUBMISSION_RECEIPT_INVALID", out["errors"])

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            m = _base(Path(td))
            m["deliverables"][0]["path"] = "../report.pdf"
            out = verify(m, base_dir=td)
            self.assertFalse(out["pass"])
            self.assertIn("DELIVERABLE_PATH_ESCAPES_BASE:report", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
