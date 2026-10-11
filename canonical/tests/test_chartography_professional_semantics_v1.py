from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from canonical.runtime.chartography_professional_semantics_v1 import (
    ChartographyProfessionalSemanticError,
    _find_legend_row,
    _fit_affine,
    _phase_boundary_intersections,
    _trace_colored_linear_series,
    calibrate_axes,
)


class ProfessionalChartSemanticUnitTests(unittest.TestCase):
    def test_robust_affine_rejects_numeric_annotation_outlier(self):
        a,b,inliers=_fit_affine([(10,0),(30,20),(50,40),(70,60),(45,437)])
        self.assertAlmostEqual(a,1.0,places=6)
        self.assertAlmostEqual(b,-10.0,places=6)
        self.assertEqual(len(inliers),4)

    def test_axis_calibration_from_positioned_ocr(self):
        ocr={
            "page_width":1000,
            "page_height":700,
            "text_items":[
                {"text":"0","box":{"x0":95,"y0":620,"x1_exclusive":105,"y1_exclusive":640}},
                {"text":"20","box":{"x0":255,"y0":620,"x1_exclusive":275,"y1_exclusive":640}},
                {"text":"40","box":{"x0":415,"y0":620,"x1_exclusive":435,"y1_exclusive":640}},
                {"text":"60","box":{"x0":575,"y0":620,"x1_exclusive":595,"y1_exclusive":640}},
                {"text":"80","box":{"x0":735,"y0":620,"x1_exclusive":755,"y1_exclusive":640}},
                {"text":"100","box":{"x0":890,"y0":620,"x1_exclusive":920,"y1_exclusive":640}},
                {"text":"0","box":{"x0":45,"y0":590,"x1_exclusive":55,"y1_exclusive":610}},
                {"text":"2","box":{"x0":45,"y0":410,"x1_exclusive":55,"y1_exclusive":430}},
                {"text":"4","box":{"x0":45,"y0":230,"x1_exclusive":55,"y1_exclusive":250}},
                {"text":"6","box":{"x0":45,"y0":50,"x1_exclusive":55,"y1_exclusive":70}},
                {"text":"437","box":{"x0":300,"y0":280,"x1_exclusive":350,"y1_exclusive":310}},
            ],
        }
        out=calibrate_axes(ocr)
        ax,bx=out["x_value_from_pixel"]
        ay,by=out["y_value_from_pixel"]
        self.assertGreater(ax,0)
        self.assertLess(ay,0)
        self.assertAlmostEqual(ax*100+bx,0,delta=3)
        self.assertAlmostEqual(ay*600+by,0,delta=0.4)


    def test_corrupt_target_legend_digit_resolves_from_redundant_rows(self):
        rows = []
        words = []
        def add(line_no, y, text, parts):
            sid=f"ocr:p1:b1:par1:l{line_no}"
            rows.append({
                "text":text,
                "box":{"x0":100,"y0":y,"x1_exclusive":950,"y1_exclusive":y+20},
                "source_id":sid,
            })
            x=760
            for n,part in enumerate(parts,1):
                words.append({
                    "text":part,
                    "box":{"x0":x,"y0":y,"x1_exclusive":x+45,"y1_exclusive":y+20},
                    "line_source_id":sid,
                    "word_num":n,
                })
                x+=50
        add(1,100,"700 degC / 0.03 K/m",["700","degC","/","0.03","K/m"])
        add(2,140,"900 degC / 0.03 K/m",["900","degC","/","0.03","K/m"])
        add(3,180,"1100 degC / 0.02 K/m",["1100","degC","/","0.02","K/m"])
        add(4,200,"4100 degC / 0.03 K/m",["4100","degC","/","0.03","K/m"])
        add(5,220,"1100 degC / 0.04 K/m",["1100","degC","/","0.04","K/m"])
        ocr={"page_width":1000,"page_height":600,"text_items":rows,"word_items":words}
        out=_find_legend_row(ocr,1100.0,0.03)
        self.assertEqual(out["source_id"],"ocr:p1:b1:par1:l4")
        self.assertGreaterEqual(out["label_box"]["x0"],700)

    def test_dotted_series_selected_among_same_color_competitors(self):
        W,H=420,300
        im=Image.new("RGB",(W,H),"white")
        draw=ImageDraw.Draw(im)
        # x: 50..350 -> 0..100, y: 250..50 -> 0..6
        axes={
            "plot_bbox":(50.0,50.0,350.0,250.0),
            "x_value_from_pixel":(100.0/300.0,-50.0*100.0/300.0),
            "y_value_from_pixel":(-6.0/200.0,7.5),
            "x_range":(0.0,100.0),
            "y_range":(0.0,6.0),
        }
        cyan=(0,190,190)
        def yp(x,data_slope):
            xv=(x-50)*100.0/300.0
            yv=data_slope*xv
            return int(round((7.5-yv)/(6.0/200.0)))
        # solid lower slope
        pts=[(x,yp(x,0.040)) for x in range(50,351)]
        draw.line(pts,fill=cyan,width=3)
        # dashed middle slope
        for x in range(50,351,18):
            draw.line([(x,yp(x,0.050)),(min(350,x+10),yp(min(350,x+10),0.050))],fill=cyan,width=3)
        # dotted higher slope
        for x in range(50,351,12):
            y=yp(x,0.060)
            draw.ellipse((x-1,y-1,x+1,y+1),fill=cyan)
        out=_trace_colored_linear_series(im,axes,cyan,"DOTTED")
        self.assertEqual(out["chosen"]["style"],"DOTTED")
        self.assertAlmostEqual(out["chosen"]["data_slope"],0.060,delta=0.006)

    def test_phase_boundary_intersections_recover_lower_solvus(self):
        W,H=500,400
        im=Image.new("RGB",(W,H),"white")
        draw=ImageDraw.Draw(im)
        axes={
            "plot_bbox":(50.0,50.0,450.0,350.0),
            "x_value_from_pixel":(0.25,-12.5),
            "y_value_from_pixel":(-500.0/300.0,683.3333333333),
            "x_range":(0.0,100.0),
            "y_range":(100.0,600.0),
        }
        def px(xv): return int(round((xv+12.5)/0.25))
        def py(yv): return int(round((683.3333333333-yv)/(500.0/300.0)))
        # Two generic phase boundaries crossing composition 9 at 350 C and 500 C.
        draw.line([(px(0),py(120)),(px(9),py(350)),(px(18),py(430))],fill="black",width=3)
        draw.line([(px(0),py(560)),(px(9),py(500)),(px(18),py(440))],fill="black",width=3)
        vals=_phase_boundary_intersections(im,axes,9.0)
        self.assertTrue(any(abs(v-350.0)<12 for v in vals),vals)
        self.assertTrue(any(abs(v-500.0)<12 for v in vals),vals)
        self.assertAlmostEqual(min(vals),350.0,delta=12)

    def test_fail_closed_insufficient_ticks(self):
        with self.assertRaises(ChartographyProfessionalSemanticError):
            calibrate_axes({"page_width":100,"page_height":100,"text_items":[]})


if __name__=="__main__":
    unittest.main(verbosity=2)
