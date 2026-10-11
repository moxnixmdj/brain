from __future__ import annotations
import unittest

from canonical.runtime.bound_capabilities.chart_positioned_ocr_axis_binding_v1 import (
    ChartAxisBindingError,
    bind_axes_from_positioned_ocr,
    numeric_tick_candidates,
    robust_axis_calibration,
)


def item(source_id, text, cx, cy, *, conf=90.0, w=12, h=10):
    return {
        "source_id": source_id,
        "text": text,
        "confidence_min": conf,
        "box": {
            "x0": cx - w / 2,
            "y0": cy - h / 2,
            "x1_exclusive": cx + w / 2,
            "y1_exclusive": cy + h / 2,
        },
    }


class ChartPositionedOcrAxisBindingV1Tests(unittest.TestCase):
    def test_numeric_tick_candidates_separate_axes_and_ignore_titles(self):
        ocr = {"text_items": [
            item("x0", "0", 50, 205), item("x1", "10", 100, 205), item("x2", "20", 150, 205),
            item("y0", "0", 35, 190), item("y1", "10", 35, 150), item("y2", "20", 35, 110),
            item("title", "Temperature", 150, 10), item("low_conf", "30", 200, 205, conf=12),
        ]}
        out = numeric_tick_candidates(ocr, [50, 30, 280, 190])
        self.assertEqual([x["source_id"] for x in out["x"]], ["x0", "x1", "x2"])
        self.assertEqual([x["source_id"] for x in out["y"]], ["y2", "y1", "y0"])

    def test_linear_axes_bind_with_outlier_rejected(self):
        ocr = {"text_items": [
            item("x0", "0", 50, 205), item("x1", "10", 100, 205), item("x2", "20", 150, 205),
            item("x_bad", "999", 200, 205, conf=42),
            item("y0", "0", 35, 190), item("y1", "10", 35, 150), item("y2", "20", 35, 110), item("y3", "30", 35, 70),
        ]}
        out = bind_axes_from_positioned_ocr(ocr, [50, 30, 280, 190])
        self.assertEqual(out["status"], "PASS__POSITIONED_OCR_AXIS_BINDING")
        self.assertEqual(out["axes"]["x"]["scale"], "LINEAR")
        self.assertEqual(out["axes"]["y"]["scale"], "LINEAR")
        self.assertIn("x_bad", out["axes"]["x"]["rejected_source_ids"])
        self.assertEqual(out["general_purpose_model_dependency_count"], 0)
        self.assertFalse(out["benchmark_score_authority"])

    def test_log_axis_selected(self):
        rows = [
            {"source_id": "a", "pixel": 50.0, "value": 1.0, "confidence": 90.0},
            {"source_id": "b", "pixel": 100.0, "value": 10.0, "confidence": 90.0},
            {"source_id": "c", "pixel": 150.0, "value": 100.0, "confidence": 90.0},
            {"source_id": "d", "pixel": 200.0, "value": 1000.0, "confidence": 90.0},
        ]
        out = robust_axis_calibration(rows, "INCREASING")
        self.assertEqual(out["scale"], "LOG10")
        self.assertEqual(out["selected_tick_count"], 4)

    def test_conflicting_duplicate_pixel_fails_closed_when_too_few_remain(self):
        rows = [
            {"source_id": "a", "pixel": 50.0, "value": 1.0, "confidence": 90.0},
            {"source_id": "b", "pixel": 50.5, "value": 2.0, "confidence": 91.0},
            {"source_id": "c", "pixel": 100.0, "value": 10.0, "confidence": 90.0},
            {"source_id": "d", "pixel": 150.0, "value": 20.0, "confidence": 90.0},
        ]
        with self.assertRaisesRegex(ChartAxisBindingError, "AXIS_TICKS_INSUFFICIENT"):
            robust_axis_calibration(rows, "INCREASING")

    def test_non_numeric_labels_never_become_ticks(self):
        ocr = {"text_items": [item("a", "10 ms", 100, 205), item("b", "1O", 120, 205)]}
        out = numeric_tick_candidates(ocr, [50, 30, 280, 190])
        self.assertEqual(out, {"x": [], "y": []})


if __name__ == "__main__":
    unittest.main()
