from __future__ import annotations
import unittest

from canonical.runtime.bound_capabilities.chart_curve_x_at_y_query_v1 import (
    CurveXAtYQueryError,
    query_curve_x_at_y,
)

RED=[216,24,24]

def axes(*,log_x=False,log_y=False):
    return {
      "x":{"scale":"LOG10" if log_x else "LINEAR","transformed_value_from_pixel":[0.01 if log_x else 1.0,0.0]},
      "y":{"scale":"LOG10" if log_y else "LINEAR","transformed_value_from_pixel":[-0.01 if log_y else -1.0,2.0 if log_y else 110.0]},
    }

def row(points):
    return {"color_bucket":RED,"column_count":len(points),"x_range":[points[0][0],points[-1][0]],"points":points}

def scene(rows,ax=None):
    return {"plot_box":[10,10,110,110],"axes":ax or axes(),"color_polylines":rows}

def legend():
    return {"bindings":[{"label":"Control","color_bucket":RED}]}

class CurveXAtYQueryV1Tests(unittest.TestCase):
    def test_monotonic_linear_curve(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        out=query_curve_x_at_y(scene([row(pts)]),legend(),label="control",y_value=40)
        self.assertAlmostEqual(out["value"],60.0,places=6)
        self.assertEqual(out["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertFalse(out["domain_semantic_authority"])

    def test_exact_vertex_is_one_crossing(self):
        pts=[[20,90],[40,80],[60,70],[80,60],[100,50]]
        out=query_curve_x_at_y(scene([row(pts)]),legend(),label="Control",y_value=40)
        self.assertAlmostEqual(out["value"],60.0,places=6)

    def test_log_x_result(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        out=query_curve_x_at_y(scene([row(pts)],ax=axes(log_x=True)),legend(),label="Control",y_value=40)
        self.assertAlmostEqual(out["value"],10**0.6,places=6)
        self.assertEqual(out["axis_scales"]["x"],"LOG10")

    def test_log_y_query(self):
        pts=[[x,100-0.5*x] for x in range(20,101)]
        ax=axes(log_y=True)
        target=10**1.3
        out=query_curve_x_at_y(scene([row(pts)],ax=ax),legend(),label="Control",y_value=target)
        self.assertAlmostEqual(out["interpolated_pixel_x"],60.0,places=6)

    def test_multiple_crossings_fail_closed(self):
        pts=[[20,80],[40,40],[60,80],[80,40],[100,80]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE"):
            query_curve_x_at_y(scene([row(pts)]),legend(),label="Control",y_value=50)

    def test_horizontal_overlap_at_target_fails_closed(self):
        pts=[[20,80],[40,70],[80,70],[100,50]]
        # Linear y axis: value 40 maps to pixel 70.
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_OVERLAPS_TARGET_Y_OVER_INTERVAL"):
            query_curve_x_at_y(scene([row(pts)]),legend(),label="Control",y_value=40)

    def test_same_color_multiple_series_crossings_fail_closed(self):
        a=[[20,90],[100,50]]
        b=[[20,80],[100,40]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE"):
            query_curve_x_at_y(scene([row(a),row(b)]),legend(),label="Control",y_value=40)

    def test_coincident_crossings_from_two_polylines_still_fail_closed(self):
        a=[[20,90],[100,50]]
        b=[[20,90],[100,50]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE:2"):
            query_curve_x_at_y(scene([row(a),row(b)]),legend(),label="Control",y_value=40)

    def test_large_gap_fails_closed(self):
        pts=[[20,90],[30,80],[90,40],[100,30]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE:0"):
            query_curve_x_at_y(scene([row(pts)]),legend(),label="Control",y_value=50,max_segment_gap_fraction=0.10)

    def test_y_outside_plot_fails_closed(self):
        pts=[[20,90],[100,50]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"QUERY_Y_OUTSIDE_PLOT"):
            query_curve_x_at_y(scene([row(pts)]),legend(),label="Control",y_value=500)

    def test_missing_label_fails_closed(self):
        pts=[[20,90],[100,50]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"LEGEND_LABEL_NOT_UNIQUELY_BOUND"):
            query_curve_x_at_y(scene([row(pts)]),{"bindings":[]},label="Control",y_value=40)

if __name__=="__main__":
    unittest.main(verbosity=2)
