from __future__ import annotations

import math
import unittest

from canonical.runtime.bound_capabilities.chart_direct_curve_label_family_rank_v1 import (
    DirectCurveLabelError,
    bind_direct_curve_labels,
    rank_direct_labeled_curve_family,
)


RED = [216, 24, 24]
BLUE = [24, 72, 216]


def item(source_id, text, x0, y0, x1, y1, conf=92.0):
    return {
        "source_id": source_id,
        "text": text,
        "confidence_min": conf,
        "box": {
            "x0": x0,
            "y0": y0,
            "x1_exclusive": x1,
            "y1_exclusive": y1,
        },
    }


def axes(*, log_y=False):
    return {
        "x": {
            "scale": "LINEAR",
            "transformed_value_from_pixel": [1.0, 0.0],
        },
        "y": {
            "scale": "LOG10" if log_y else "LINEAR",
            "transformed_value_from_pixel": [-0.01 if log_y else -1.0, 2.0 if log_y else 110.0],
        },
    }


def polyline(y, color, *, x0=20, x1=100):
    return {
        "color_bucket": color,
        "column_count": x1 - x0 + 1,
        "x_range": [x0, x1],
        "points": [[x, float(y)] for x in range(x0, x1 + 1)],
    }


def scene(rows, *, ax=None):
    return {
        "plot_box": [10, 10, 110, 110],
        "axes": ax or axes(),
        "color_polylines": rows,
    }


class DirectCurveLabelFamilyRankV1Tests(unittest.TestCase):
    def test_right_endpoint_direct_labels_bind_uniquely(self):
        s = scene([polyline(40, RED), polyline(70, BLUE)])
        ocr = {
            "text_items": [
                item("h", "Upper band", 102, 36, 126, 46),
                item("l", "Lower band", 102, 66, 126, 76),
            ]
        }
        out = bind_direct_curve_labels(s, ocr)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["binding_count"], 2)
        self.assertEqual(
            {row["label"]: row["polyline_index"] for row in out["bindings"]},
            {"Upper band": 0, "Lower band": 1},
        )
        self.assertTrue(all(row["endpoint_side"] == "END" for row in out["bindings"]))

    def test_left_endpoint_direct_label_can_bind(self):
        s = scene([polyline(55, RED)])
        ocr = {"text_items": [item("a", "Series A", 2, 50, 18, 60)]}
        out = bind_direct_curve_labels(s, ocr)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["bindings"][0]["endpoint_side"], "START")

    def test_numeric_axis_like_text_is_rejected(self):
        s = scene([polyline(55, RED)])
        ocr = {"text_items": [item("n", "20", 102, 50, 120, 60)]}
        out = bind_direct_curve_labels(s, ocr)
        self.assertFalse(out["pass"])
        self.assertEqual(out["rejected"][0]["reason"], "LABEL_NOT_ELIGIBLE")

    def test_far_label_is_not_bound(self):
        s = scene([polyline(55, RED)])
        ocr = {"text_items": [item("a", "Series A", 180, 50, 210, 60)]}
        out = bind_direct_curve_labels(s, ocr)
        self.assertFalse(out["pass"])
        self.assertEqual(out["rejected"][0]["reason"], "LABEL_OUTSIDE_DIRECT_BINDING_REGION")

    def test_ambiguous_nearby_curve_endpoints_fail_closed(self):
        s = scene([polyline(50, RED), polyline(54, BLUE)])
        ocr = {"text_items": [item("a", "Series A", 102, 48, 126, 56)]}
        out = bind_direct_curve_labels(s, ocr, ambiguity_margin_px=5.0)
        self.assertFalse(out["pass"])
        self.assertEqual(out["rejected"][0]["reason"], "AMBIGUOUS_NEARBY_CURVE_ENDPOINTS")

    def test_multiple_labels_for_same_curve_fail_closed(self):
        s = scene([polyline(55, RED)])
        ocr = {
            "text_items": [
                item("a", "Series A", 102, 50, 126, 58),
                item("b", "Treatment", 102, 54, 130, 62),
            ]
        }
        out = bind_direct_curve_labels(s, ocr)
        self.assertFalse(out["pass"])
        self.assertEqual(
            {r["reason"] for r in out["rejected"]},
            {"MULTIPLE_DIRECT_LABELS_FOR_ONE_CURVE"},
        )

    def _bound_two(self, *, same_color=False, ax=None):
        rows = [
            polyline(40, RED),
            polyline(70, RED if same_color else BLUE),
        ]
        s = scene(rows, ax=ax)
        ocr = {
            "text_items": [
                item("h", "High", 102, 36, 122, 46),
                item("l", "Low", 102, 66, 122, 76),
            ]
        }
        return s, bind_direct_curve_labels(s, ocr)

    def test_family_rank_high_to_low(self):
        s, bound = self._bound_two()
        out = rank_direct_labeled_curve_family(s, bound, x_value=60)
        self.assertTrue(out["pass"])
        self.assertEqual([r["label"] for r in out["ranked_curves"]], ["High", "Low"])
        self.assertAlmostEqual(out["ranked_curves"][0]["value"], 70.0)
        self.assertAlmostEqual(out["ranked_curves"][1]["value"], 40.0)

    def test_nearest_family_query(self):
        s, bound = self._bound_two()
        out = rank_direct_labeled_curve_family(
            s, bound, x_value=60, nearest_y_value=43.0
        )
        self.assertEqual(out["nearest_curve"]["label"], "Low")
        self.assertAlmostEqual(out["nearest_curve"]["absolute_value_distance"], 3.0)

    def test_same_color_curves_remain_distinct_by_direct_binding(self):
        s, bound = self._bound_two(same_color=True)
        self.assertTrue(bound["pass"], bound)
        out = rank_direct_labeled_curve_family(s, bound, x_value=60)
        self.assertEqual([r["polyline_index"] for r in out["ranked_curves"]], [0, 1])

    def test_log_y_family_rank(self):
        s, bound = self._bound_two(ax=axes(log_y=True))
        out = rank_direct_labeled_curve_family(s, bound, x_value=60)
        self.assertGreater(out["ranked_curves"][0]["value"], out["ranked_curves"][1]["value"])
        self.assertAlmostEqual(out["ranked_curves"][0]["value"], 10 ** 1.6, places=6)
        self.assertEqual(out["axis_scales"]["y"], "LOG10")

    def test_nearest_exact_tie_fails_closed(self):
        s, bound = self._bound_two()
        with self.assertRaisesRegex(DirectCurveLabelError, "NEAREST_CURVE_TIE"):
            rank_direct_labeled_curve_family(
                s, bound, x_value=60, nearest_y_value=55.0
            )

    def test_large_curve_gap_fails_closed(self):
        rows = [
            {
                "color_bucket": RED,
                "column_count": 2,
                "x_range": [20, 100],
                "points": [[20, 40.0], [100, 40.0]],
            }
        ]
        s = scene(rows)
        bound = {
            "bindings": [
                {
                    "label": "High",
                    "polyline_index": 0,
                    "color_bucket": RED,
                }
            ]
        }
        with self.assertRaisesRegex(
            DirectCurveLabelError, "CURVE_INTERPOLATION_GAP_TOO_LARGE"
        ):
            rank_direct_labeled_curve_family(
                s, bound, x_value=60, max_interpolation_gap_fraction=0.10
            )

    def test_zero_model_and_no_benchmark_authority(self):
        s, bound = self._bound_two()
        self.assertEqual(bound["cognition_dependency_class"], "MODEL_INDEPENDENT")
        self.assertEqual(
            bound["external_general_purpose_model_runtime_dependency_count"], 0
        )
        self.assertFalse(bound["benchmark_score_authority"])
        out = rank_direct_labeled_curve_family(s, bound, x_value=60)
        self.assertEqual(out["cognition_dependency_class"], "MODEL_INDEPENDENT")
        self.assertEqual(
            out["external_general_purpose_model_runtime_dependency_count"], 0
        )
        self.assertFalse(out["benchmark_score_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
