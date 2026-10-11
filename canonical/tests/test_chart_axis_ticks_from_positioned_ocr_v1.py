from __future__ import annotations
import unittest
from canonical.runtime.bound_capabilities.chart_axis_ticks_from_positioned_ocr_v1 import AxisTickObservationError,extract_axis_ticks,parse_axis_number

def w(text,x0,y0,x1,y1,conf=90):
    return {"text":text,"box":{"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1},"confidence":conf}

class AxisTickObservationV1Tests(unittest.TestCase):
    def test_numeric_normalization(self):
        self.assertEqual(parse_axis_number("1,000")["value"],1000.0)
        self.assertEqual(parse_axis_number("2.5K")["value"],2500.0)
        self.assertEqual(parse_axis_number("$30")["value"],30.0)
        self.assertEqual(parse_axis_number("(40)")["value"],-40.0)
        p=parse_axis_number("50%"); self.assertEqual(p["value"],50.0); self.assertEqual(p["unit_suffix"],"%")
        self.assertIsNone(parse_axis_number("Series 10"))
    def test_geometry_selects_axes_and_rejects_plot_distractor(self):
        words=[w("0",90,205,110,225),w("10",190,205,220,225),w("20",290,205,320,225),w("0",35,185,55,205),w("50",25,105,55,125),w("100",10,25,55,45),w("999",180,100,230,120),w("legend",250,20,310,40)]
        out=extract_axis_ticks(words,[60,20,340,200])
        self.assertEqual([r["value"] for r in out["x_ticks"]],[0.0,10.0,20.0])
        self.assertEqual([r["value"] for r in out["y_ticks"]],[100.0,50.0,0.0])
        self.assertNotIn(999.0,[r["value"] for r in out["x_ticks"]+out["y_ticks"]])
        self.assertFalse(out["semantic_authority"]); self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
    def test_duplicate_pixel_prefers_higher_confidence(self):
        words=[w("10",100,205,120,225,40),w("11",101,205,121,225,95),w("20",200,205,220,225,90),w("30",300,205,320,225,90)]
        out=extract_axis_ticks(words,[50,20,350,200]); self.assertEqual(out["x_ticks"][0]["value"],11.0)
    def test_magnitude_suffix_calibration_value(self):
        words=[w("1K",80,205,110,225),w("2K",180,205,210,225),w("3K",280,205,310,225)]
        out=extract_axis_ticks(words,[50,20,350,200]); self.assertEqual([p[1] for p in out["x_calibration_points"]],[1000.0,2000.0,3000.0])
    def test_bad_box_fails_closed(self):
        with self.assertRaisesRegex(AxisTickObservationError,"WORD_BOX_INVALID"): extract_axis_ticks([w("10",100,200,90,220)],[50,20,350,200])
    def test_bad_plot_box_fails_closed(self):
        with self.assertRaisesRegex(AxisTickObservationError,"PLOT_BOX_INVALID"): extract_axis_ticks([], [10,10,5,20])
if __name__=="__main__": unittest.main()
