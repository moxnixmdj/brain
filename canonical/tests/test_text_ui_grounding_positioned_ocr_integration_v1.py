from __future__ import annotations
import unittest
from canonical.runtime.text_ui_grounding_v1 import compile_click_action

class IntegrationTests(unittest.TestCase):
    def test_verified_positioned_ocr_contract_to_typed_click(self):
        positioned={
            "schema":"PROJECT_BRAIN_POSITIONED_OCR_TSV_BRIDGE_V1",
            "page_width":640,
            "page_height":480,
            "text_items":[
                {
                    "text":"DIA 20",
                    "box":{"x0":10,"y0":20,"x1_exclusive":65,"y1_exclusive":30},
                    "source_id":"ocr:p1:b1:par1:l1",
                    "confidence_min":90.0,
                    "confidence_mean":92.5,
                },
                {
                    "text":"DEPTH 8",
                    "box":{"x0":100,"y0":100,"x1_exclusive":160,"y1_exclusive":112},
                    "source_id":"ocr:p1:b1:par1:l2",
                    "confidence_min":87.5,
                    "confidence_mean":88.0,
                },
            ],
            "terminal_semantic_authority":False,
        }
        out=compile_click_action(positioned,"DEPTH 8")
        self.assertTrue(out["pass"])
        self.assertEqual(out["selected_candidate_id"],"ocr:p1:b1:par1:l2")
        self.assertEqual(out["typed_action"],{"type":"click","x":129,"y":105,"button":"left"})
        self.assertFalse(out["execution_authority"])

    def test_duplicate_verified_ocr_lines_stay_unresolved(self):
        positioned={
            "page_width":640,"page_height":480,
            "text_items":[
                {"text":"OK","box":{"x0":10,"y0":10,"x1_exclusive":40,"y1_exclusive":30},"source_id":"a"},
                {"text":"OK","box":{"x0":200,"y0":200,"x1_exclusive":240,"y1_exclusive":220},"source_id":"b"},
            ],
        }
        out=compile_click_action(positioned,"OK")
        self.assertFalse(out["pass"])
        self.assertIsNone(out["typed_action"])
        self.assertEqual(out["action"],"ACQUIRE_MINIMUM_SPATIAL_OR_CONTEXTUAL_DISCRIMINATOR")

if __name__=="__main__": unittest.main(verbosity=2)
