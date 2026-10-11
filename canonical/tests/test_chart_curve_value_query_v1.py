from __future__ import annotations

import math
import unittest

from canonical.runtime.bound_capabilities.chart_curve_value_query_v1 import (
    CurveValueQueryError,
    query_curve_value,
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


class CurveValueQueryV1Tests(unittest.TestCase):
    def test_linear_curve_value(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        out=query_curve_value(scene(pts),legend(),label="control",x_value=60)
        self.assertAlmostEqual(out["value"],40.0,places=6)
        self.assertEqual(out["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["benchmark_score_authority"])

    def test_case_and_whitespace_normalized_label(self):
        pts=[[x,80.0] for x in range(20,101)]
        out=query_curve_value(scene(pts),legend("Treatment   Arm"),label=" treatment arm ",x_value=50)
        self.assertAlmostEqual(out["value"],30.0,places=6)

    def test_log_y_axis(self):
        pts=[[x,50.0] for x in range(20,101)]
        out=query_curve_value(scene(pts,ax=axes(log_y=True)),legend(),label="Control",x_value=60)
        self.assertAlmostEqual(out["value"],10**1.5,places=6)
        self.assertEqual(out["axis_scales"]["y"],"LOG10")

    def test_log_x_axis(self):
        pts=[[x,70.0] for x in range(20,101)]
        out=query_curve_value(scene(pts,ax=axes(log_x=True)),legend(),label="Control",x_value=10**0.6)
        self.assertAlmostEqual(out["target_pixel_x"],60.0,places=6)
        self.assertAlmostEqual(out["value"],40.0,places=6)

    def test_same_color_multiple_queryable_series_fails_closed(self):
        p1=[[x,70.0] for x in range(20,101)]
        p2=[[x,90.0] for x in range(20,101)]
        rows=[
            {"color_bucket":RED,"column_count":len(p1),"x_range":[20,100],"points":p1},
            {"color_bucket":RED,"column_count":len(p2),"x_range":[20,100],"points":p2},
        ]
        with self.assertRaisesRegex(CurveValueQueryError,"CURVE_NOT_UNIQUELY_QUERYABLE:2"):
            query_curve_value(scene(p1,rows=rows),legend(),label="Control",x_value=60)

    def test_missing_label_fails_closed(self):
        pts=[[x,70.0] for x in range(20,101)]
        with self.assertRaisesRegex(CurveValueQueryError,"LEGEND_LABEL_NOT_UNIQUELY_BOUND:0"):
            query_curve_value(scene(pts),legend(),label="Missing",x_value=60)

    def test_large_gap_fails_closed(self):
        pts=[[20,90],[30,80],[90,50],[100,40]]
        with self.assertRaisesRegex(CurveValueQueryError,"CURVE_NOT_UNIQUELY_QUERYABLE:0"):
            query_curve_value(scene(pts),legend(),label="Control",x_value=60,max_interpolation_gap_fraction=0.10)

    def test_outside_plot_fails_closed(self):
        pts=[[x,70.0] for x in range(20,101)]
        with self.assertRaisesRegex(CurveValueQueryError,"QUERY_X_OUTSIDE_PLOT"):
            query_curve_value(scene(pts),legend(),label="Control",x_value=150)

    def test_vertical_overlap_at_exact_query_fails_closed(self):
        pts=[[20,80],[50,70],[60,30],[60,80],[70,60],[100,50]]
        with self.assertRaisesRegex(CurveValueQueryError,"CURVE_NOT_UNIQUELY_QUERYABLE:0"):
            query_curve_value(scene(pts),legend(),label="Control",x_value=60)

    def test_one_pixel_resolution_positive(self):
        pts=[[x,70.0] for x in range(20,101)]
        out=query_curve_value(scene(pts),legend(),label="Control",x_value=50)
        self.assertGreater(out["estimated_one_pixel_value_resolution"],0)
        self.assertTrue(math.isfinite(out["estimated_one_pixel_value_resolution"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
