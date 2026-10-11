from __future__ import annotations
import unittest

from canonical.runtime.bound_capabilities.chart_direct_curve_family_v1 import (
    DirectCurveFamilyError,
    bind_right_endpoint_curve_labels,
    query_direct_curve_family,
)

RED=[216,24,24]
BLUE=[24,72,216]
GREEN=[24,168,72]

def axes():
    return {
      "x":{"scale":"LINEAR","transformed_value_from_pixel":[1.0,0.0]},
      "y":{"scale":"LINEAR","transformed_value_from_pixel":[-1.0,110.0]},
    }

def line(color,y):
    pts=[[x,float(y)] for x in range(20,101)]
    return {"color_bucket":color,"column_count":len(pts),"x_range":[20,100],"points":pts}

def scene(rows):
    return {"plot_box":[10,10,110,110],"axes":axes(),"color_polylines":rows}

def item(sid,text,x0,y0,x1,y1,conf=95):
    return {"source_id":sid,"text":text,"confidence_min":conf,
            "box":{"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1}}

class DirectCurveFamilyV1Tests(unittest.TestCase):
    def test_right_endpoint_labels_bind_and_rank(self):
        sc=scene([line(RED,30),line(BLUE,60),line(GREEN,90)])
        ocr={"text_items":[
          item("a","P90",102,25,126,35),
          item("b","P50",102,55,126,65),
          item("c","P10",102,85,126,95),
        ]}
        b=bind_right_endpoint_curve_labels(sc,ocr)
        self.assertEqual(b["binding_count"],3,b)
        out=query_direct_curve_family(sc,b,x_value=50,target_y=52)
        self.assertEqual([r["label"] for r in out["ranked_high_to_low"]],["P90","P50","P10"])
        self.assertEqual(out["nearest_to_target_y"]["label"],"P50")
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["domain_semantic_authority"])

    def test_numeric_direct_labels_allowed_by_endpoint_geometry(self):
        sc=scene([line(RED,40),line(BLUE,80)])
        ocr={"text_items":[item("a","90",102,35,118,45),item("b","10",102,75,118,85)]}
        b=bind_right_endpoint_curve_labels(sc,ocr)
        self.assertEqual({x["label"] for x in b["bindings"]},{"90","10"})

    def test_bottom_axis_like_numeric_label_not_considered(self):
        sc=scene([line(RED,40),line(BLUE,80)])
        ocr={"text_items":[item("tick","100",90,118,110,130)]}
        b=bind_right_endpoint_curve_labels(sc,ocr)
        self.assertFalse(b["pass"])

    def test_ambiguous_label_near_two_endpoints_fails_closed(self):
        sc=scene([line(RED,50),line(BLUE,52)])
        ocr={"text_items":[item("a","Arm",102,46,124,56)]}
        b=bind_right_endpoint_curve_labels(sc,ocr,ambiguity_margin_px=3)
        self.assertFalse(b["pass"])
        self.assertIn("AMBIGUOUS_NEARBY_CURVE_ENDPOINT",{x["reason"] for x in b["rejected"]})

    def test_one_polyline_multiple_labels_fails_closed(self):
        sc=scene([line(RED,50)])
        ocr={"text_items":[item("a","A",102,45,118,51),item("b","B",102,50,118,56)]}
        b=bind_right_endpoint_curve_labels(sc,ocr,ambiguity_margin_px=0)
        self.assertFalse(b["pass"])
        self.assertIn("POLYLINE_BOUND_TO_MULTIPLE_LABELS",{x["reason"] for x in b["rejected"]})

    def test_rank_tie_fails_closed(self):
        sc=scene([line(RED,40),line(BLUE,41)])
        binding={"bindings":[
          {"label":"A","polyline_index":0},
          {"label":"B","polyline_index":1},
        ]}
        with self.assertRaisesRegex(DirectCurveFamilyError,"CURVE_FAMILY_RANK_TIE_OR_UNREADABLE"):
            query_direct_curve_family(sc,binding,x_value=50,tie_tolerance_px=1.5)

    def test_nearest_target_tie_fails_closed(self):
        sc=scene([line(RED,40),line(BLUE,60)])
        binding={"bindings":[{"label":"A","polyline_index":0},{"label":"B","polyline_index":1}]}
        # target semantic y=60 maps to pixel 50: exactly between y=40 and y=60 pixels.
        with self.assertRaisesRegex(DirectCurveFamilyError,"NEAREST_CURVE_TIE_OR_UNREADABLE"):
            query_direct_curve_family(sc,binding,x_value=50,target_y=60)

    def test_duplicate_label_binding_fails_closed(self):
        sc=scene([line(RED,40),line(BLUE,60)])
        binding={"bindings":[{"label":"A","polyline_index":0},{"label":" a ","polyline_index":1}]}
        with self.assertRaisesRegex(DirectCurveFamilyError,"DIRECT_BINDING_NOT_ONE_TO_ONE"):
            query_direct_curve_family(sc,binding,x_value=50)

    def test_large_member_gap_fails_closed(self):
        sparse={"color_bucket":RED,"column_count":3,"x_range":[20,100],"points":[[20,40],[30,40],[100,40]]}
        sc=scene([sparse,line(BLUE,60)])
        binding={"bindings":[{"label":"A","polyline_index":0},{"label":"B","polyline_index":1}]}
        with self.assertRaisesRegex(DirectCurveFamilyError,"FAMILY_MEMBER_INTERPOLATION_GAP_TOO_LARGE"):
            query_direct_curve_family(sc,binding,x_value=50,max_interpolation_gap_fraction=.10)

    def test_low_confidence_label_rejected(self):
        sc=scene([line(RED,40),line(BLUE,80)])
        ocr={"text_items":[item("a","A",102,35,118,45,conf=10)]}
        b=bind_right_endpoint_curve_labels(sc,ocr)
        self.assertFalse(b["pass"])
        self.assertEqual(b["rejected"][0]["reason"],"LOW_OCR_CONFIDENCE")

if __name__=="__main__":
    unittest.main(verbosity=2)
