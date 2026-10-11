from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from canonical.runtime import professional_artifact_visual_observer_v1 as observer


def _page(path: Path, *, blank: bool = False) -> None:
    im = Image.new("RGB", (400, 300), "white")
    if not blank:
        d = ImageDraw.Draw(im)
        d.rectangle((40, 40, 260, 55), fill="black")
        d.rectangle((40, 85, 330, 100), fill="black")
    im.save(path)


def _ocr(*, low_conf: bool = False, crop: bool = False, overlap: bool = False):
    first = {"x0": 40, "y0": 40, "x1_exclusive": 260, "y1_exclusive": 56}
    second = {"x0": 40, "y0": 85, "x1_exclusive": 330, "y1_exclusive": 101}
    if crop:
        first["x0"] = 0
    if overlap:
        second = {"x0": 60, "y0": 42, "x1_exclusive": 240, "y1_exclusive": 58}
    conf = 20.0 if low_conf else 92.0
    return {
        "page_width": 400,
        "page_height": 300,
        "text_items": [
            {"text": "Line one", "box": first, "confidence_mean": conf},
            {"text": "Line two", "box": second, "confidence_mean": 91.0},
        ],
    }


class ProfessionalArtifactVisualObserverV1Tests(unittest.TestCase):
    def test_clean_page_passes_bounded_technical_observation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "page.png"
            _page(p)
            out = observer.analyze_page(p, _ocr())
            self.assertTrue(out["pass"], out)
            self.assertTrue(all(out["gates"].values()))
            self.assertFalse(out["professional_quality_top"])
            self.assertFalse(out["owner_preference_equivalence"])

    def test_blank_page_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "page.png"
            _page(p, blank=True)
            o = {"page_width": 400, "page_height": 300, "text_items": []}
            out = observer.analyze_page(p, o, require_text=False)
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["gates"]["PAGE_NOT_BLANK"])

    def test_required_text_cannot_be_replaced_by_nonwhite_pixels(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "page.png"
            _page(p)
            o = {"page_width": 400, "page_height": 300, "text_items": []}
            out = observer.analyze_page(p, o, require_text=True)
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["gates"]["TEXT_PRESENT_WHEN_REQUIRED"])

    def test_text_touching_hard_crop_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "page.png"
            _page(p)
            out = observer.analyze_page(p, _ocr(crop=True))
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["gates"]["TEXT_NOT_TOUCHING_HARD_CROP"])

    def test_major_ocr_line_overlap_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "page.png"
            _page(p)
            out = observer.analyze_page(p, _ocr(overlap=True))
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["gates"]["NO_MAJOR_OCR_LINE_OVERLAP"])

    def test_low_ocr_confidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "page.png"
            _page(p)
            out = observer.analyze_page(p, _ocr(low_conf=True))
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["gates"]["OCR_LINE_CONFIDENCE_BOUNDED"])

    def test_ocr_geometry_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "page.png"
            _page(p)
            o = _ocr()
            o["page_width"] = 399
            with self.assertRaisesRegex(
                observer.ProfessionalArtifactVisualObserverError,
                "OCR_PAGE_GEOMETRY_MISMATCH",
            ):
                observer.analyze_page(p, o)

    def test_run_uses_brain_generated_observer_not_manifest_checkbox(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "report.png"
            _page(p)
            with patch.object(observer, "_observe_ocr", return_value=_ocr()):
                out = observer.run({"path": "report.png"}, root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["page_count"], 1)
            self.assertEqual(out["pages"][0]["line_count"], 2)
            self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"], 0)

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(
                observer.ProfessionalArtifactVisualObserverError,
                "PATH_OUTSIDE_REPOSITORY",
            ):
                observer.run({"path": "../outside.png"}, td)


if __name__ == "__main__":
    unittest.main(verbosity=2)
