from __future__ import annotations

import unittest
from PIL import Image,ImageDraw

from canonical.runtime.bound_capabilities.chart_legend_style_binding_v1 import bind_legend_styles


def item(sid,text,x0,y0,x1,y1,conf=92.0):
    return {
        "source_id":sid,"text":text,"confidence_min":conf,
        "box":{"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1},
    }


class ChartLegendStyleBindingV1Tests(unittest.TestCase):
    def base(self):
        im=Image.new("RGB",(360,240),"white");d=ImageDraw.Draw(im)
        d.line((50,30,50,190),fill="black",width=2)
        d.line((50,190,280,190),fill="black",width=2)
        return im,d,[50,30,280,190]

    def test_outside_right_legend_binds_to_matching_plot_style(self):
        im,d,pb=self.base()
        d.line((60,160,120,140,180,120,240,90),fill=(230,30,30),width=4)
        d.rectangle((292,64,310,72),fill=(230,30,30))
        ocr={"text_items":[item("a","Series A",316,60,356,76)]}
        out=bind_legend_styles(im,ocr,pb)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["bindings"][0]["label"],"Series A")
        self.assertEqual(out["bindings"][0]["side"],"LEFT")
        self.assertTrue(out["bindings"][0]["data_evidence"])

    def test_inside_legend_can_bind_when_same_color_has_independent_plot_evidence(self):
        im,d,pb=self.base()
        d.line((60,170,110,145,170,130,230,80),fill=(30,80,230),width=4)
        d.rectangle((190,48,208,56),fill=(30,80,230))
        ocr={"text_items":[item("b","Control",214,44,266,60)]}
        out=bind_legend_styles(im,ocr,pb)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["bindings"][0]["label"],"Control")

    def test_ambiguous_two_swatches_fail_closed(self):
        im,d,pb=self.base()
        d.line((60,160,120,140,180,120,240,90),fill=(230,30,30),width=4)
        d.line((60,150,120,130,180,110,240,80),fill=(30,80,230),width=4)
        d.rectangle((292,61,310,69),fill=(230,30,30))
        d.rectangle((292,71,310,79),fill=(30,80,230))
        ocr={"text_items":[item("a","Series",316,62,356,78)]}
        out=bind_legend_styles(im,ocr,pb,ambiguity_margin_px=8)
        self.assertFalse(out["pass"])
        self.assertIn("AMBIGUOUS_STYLE_SAMPLE",{x["reason"] for x in out["rejected"]})

    def test_numeric_axis_like_label_is_not_bound(self):
        im,d,pb=self.base()
        d.line((60,160,120,140,180,120,240,90),fill=(230,30,30),width=4)
        d.rectangle((292,64,310,72),fill=(230,30,30))
        ocr={"text_items":[item("tick","20",316,60,336,76)]}
        out=bind_legend_styles(im,ocr,pb)
        self.assertFalse(out["pass"])
        self.assertEqual(out["rejected"][0]["reason"],"LABEL_NOT_ELIGIBLE")

    def test_style_without_plot_counterpart_is_rejected(self):
        im,d,pb=self.base()
        d.rectangle((292,64,310,72),fill=(230,30,30))
        ocr={"text_items":[item("a","Series A",316,60,356,76)]}
        out=bind_legend_styles(im,ocr,pb)
        self.assertFalse(out["pass"])
        self.assertIn("NO_STYLE_SAMPLE_WITH_PLOT_EVIDENCE",{x["reason"] for x in out["rejected"]})

    def test_low_confidence_label_is_rejected(self):
        im,d,pb=self.base()
        d.line((60,160,120,140,180,120,240,90),fill=(230,30,30),width=4)
        d.rectangle((292,64,310,72),fill=(230,30,30))
        ocr={"text_items":[item("a","Series A",316,60,356,76,conf=12)]}
        out=bind_legend_styles(im,ocr,pb)
        self.assertFalse(out["pass"])
        self.assertEqual(out["rejected"][0]["reason"],"LOW_OCR_CONFIDENCE")

    def test_zero_model_and_no_domain_authority(self):
        im,d,pb=self.base()
        d.line((60,160,120,140,180,120,240,90),fill=(230,30,30),width=4)
        d.rectangle((292,64,310,72),fill=(230,30,30))
        ocr={"text_items":[item("a","Series A",316,60,356,76)]}
        out=bind_legend_styles(im,ocr,pb)
        self.assertEqual(out["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["domain_semantic_authority"])
        self.assertFalse(out["benchmark_score_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
