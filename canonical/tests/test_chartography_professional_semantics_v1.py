from __future__ import annotations

import unittest

from canonical.runtime.chartography_professional_semantics_v1 import (
    ChartographyProfessionalSemanticError,
    _fit_affine,
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

    def test_fail_closed_insufficient_ticks(self):
        with self.assertRaises(ChartographyProfessionalSemanticError):
            calibrate_axes({"page_width":100,"page_height":100,"text_items":[]})


if __name__=="__main__":
    unittest.main(verbosity=2)
