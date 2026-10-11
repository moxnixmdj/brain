from __future__ import annotations

import math
import unittest

from canonical.runtime.bound_capabilities.chart_curve_inverse_query_v1 import (
    CurveInverseQueryError,
    query_curve_x_at_y,
)

RED=[216,24,24]


def axes(*, log_x=False, log_y=False):
    return {
        "x":{
            "scale":"LOG10" if log_x else "LINEAR",
            "transformed_value_from_pixel":[0.01 if log_x else 1.0, 0.0],
        },
        "y":{
            "scale":"LOG10" if log_y else "LINEAR",
            "transformed_value_from_pixel":[-0.01 if log_y else -1.0, 2.0 if log_y else 110.0],
        },
    }


def legend(label="Control", color=RED):
    return {"bindings":[{"label":label,"color_bucket":color}]}


def scene(points, *, rows=None, ax=None):
    if rows is None:
        rows=[{"color_bucket":RED,"column_count":len(points),"x_range":[points[0][0],points[-1][0]],"points":points}]
    return {"plot_box":[10,10,110,110],"axes":ax or axes(),"color_polylines":rows}


class CurveInverseQueryV1Tests(unittest.TestCase):
    def test_linear_inverse(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        out=query_curve_x_at_y(scene(pts),legend(),label="control",y_value=40)
        self.assertAlmostEqual(out["value"],60.0,places=6)
        self.assertEqual(out["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["benchmark_score_authority"])

    def test_case_and_whitespace_normalized_label(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        out=query_curve_x_at_y(scene(pts),legend("Treatment   Arm"),label=" treatment arm ",y_value=40)
        self.assertAlmostEqual(out["value"],60.0,places=6)

    def test_log_x_axis(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        out=query_curve_x_at_y(scene(pts,ax=axes(log_x=True)),legend(),label="Control",y_value=40)
        self.assertAlmostEqual(out["interpolated_pixel_x"],60.0,places=6)
        self.assertAlmostEqual(out["value"],10**0.6,places=6)

    def test_log_y_query(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        out=query_curve_x_at_y(scene(pts,ax=axes(log_y=True)),legend(),label="Control",y_value=10**1.3)
        self.assertAlmostEqual(out["target_pixel_y"],70.0,places=6)
        self.assertAlmostEqual(out["value"],60.0,places=6)

    def test_nonmonotonic_multiple_crossings_fail_closed(self):
        pts=[[20,90],[40,50],[60,90],[80,50],[100,90]]
        with self.assertRaisesRegex(CurveInverseQueryError,"CURVE_NOT_UNIQUELY_INVERTIBLE_AT_QUERY"):
            query_curve_x_at_y(scene(pts),legend(),label="Control",y_value=40,max_interpolation_gap_fraction=1.0)

    def test_horizontal_plateau_at_query_fails_closed(self):
        pts=[[20,80],[40,70],[60,70],[80,60],[100,50]]
        with self.assertRaisesRegex(CurveInverseQueryError,"HORIZONTAL_OR_OVERLAPPING_CURVE_AT_QUERY"):
            query_curve_x_at_y(scene(pts),legend(),label="Control",y_value=40,max_interpolation_gap_fraction=1.0)

    def test_same_color_multiple_series_fail_closed(self):
        p1=[[20,90],[100,50]]
        p2=[[20,80],[100,40]]
        rows=[
            {"color_bucket":RED,"column_count":len(p1),"x_range":[20,100],"points":p1},
            {"color_bucket":RED,"column_count":len(p2),"x_range":[20,100],"points":p2},
        ]
        with self.assertRaisesRegex(CurveInverseQueryError,"CURVE_NOT_UNIQUELY_INVERTIBLE_AT_QUERY:2"):
            query_curve_x_at_y(scene(p1,rows=rows),legend(),label="Control",y_value=40,max_interpolation_gap_fraction=1.0)

    def test_large_gap_fails_closed(self):
        pts=[[20,90],[30,80],[90,20],[100,10]]
        with self.assertRaisesRegex(CurveInverseQueryError,"CURVE_NOT_UNIQUELY_INVERTIBLE_AT_QUERY:0"):
            query_curve_x_at_y(scene(pts),legend(),label="Control",y_value=50,max_interpolation_gap_fraction=0.10)

    def test_outside_plot_fails_closed(self):
        pts=[[20,90],[100,50]]
        with self.assertRaisesRegex(CurveInverseQueryError,"QUERY_Y_OUTSIDE_PLOT"):
            query_curve_x_at_y(scene(pts),legend(),label="Control",y_value=150,max_interpolation_gap_fraction=1.0)

    def test_missing_label_fails_closed(self):
        pts=[[20,90],[100,50]]
        with self.assertRaisesRegex(CurveInverseQueryError,"LEGEND_LABEL_NOT_UNIQUELY_BOUND:0"):
            query_curve_x_at_y(scene(pts),legend(),label="Missing",y_value=40,max_interpolation_gap_fraction=1.0)

    def test_shared_vertex_is_one_crossing(self):
        pts=[[20,90],[60,70],[100,50]]
        out=query_curve_x_at_y(scene(pts),legend(),label="Control",y_value=40,max_interpolation_gap_fraction=1.0)
        self.assertAlmostEqual(out["value"],60.0,places=6)

    def test_one_pixel_resolution_positive(self):
        pts=[[20,90],[100,50]]
        out=query_curve_x_at_y(scene(pts),legend(),label="Control",y_value=40,max_interpolation_gap_fraction=1.0)
        self.assertGreater(out["estimated_one_pixel_value_resolution"],0)
        self.assertTrue(math.isfinite(out["estimated_one_pixel_value_resolution"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
