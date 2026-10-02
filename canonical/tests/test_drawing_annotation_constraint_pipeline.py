import unittest
import cv2
import numpy as np

from canonical.runtime.drawing_annotation_constraint_pipeline import compile_annotation_constraints

BOX={"x0":0,"y0":0,"x1_exclusive":10,"y1_exclusive":10}

class DrawingAnnotationConstraintPipelineTests(unittest.TestCase):
    def setUp(self):
        self.img=np.full((80,120),255,dtype=np.uint8)
        cv2.circle(self.img,(60,40),15,0,2)

    def test_compound_feature_fast_path(self):
        o=compile_annotation_constraints(
            self.img,
            text_items=[{"text":"2X DIA 10 THRU","box":BOX,"target_id":"hole1"}],
        )
        self.assertEqual(o["status"],"COMPILED")
        self.assertEqual(o["features"]["hole1"]["diameter"]["value"],10.0)
        self.assertEqual(o["features"]["hole1"]["quantity"],2)

    def test_jit_structural_grammar_transfer(self):
        rules=[{
            "id":"surface_finish","kind":"surface_finish.ra",
            "atoms":[
                {"literal":"SF"},
                {"capture":"roughness","type":"number","min":0},
                {"capture":"units","type":"enum","values":["UM","MM"]}
            ]
        }]
        o=compile_annotation_constraints(
            self.img,
            text_items=[{"text":"SF 3.2 UM","box":BOX,"target_id":"surface1"}],
            jit_rules=rules,
        )
        self.assertEqual(o["status"],"COMPILED")
        self.assertEqual(o["features"]["surface1"]["surface_finish.ra"]["roughness"],3.2)

    def test_jit_alias_semantics(self):
        catalog=[{
            "symbol_id":"MMC","kind":"modifier","aliases":["MAX MATERIAL"],
            "semantics":{"property":"gdt.material_condition","value":"MMC"},
            "source":"synthetic-standard"
        }]
        o=compile_annotation_constraints(
            self.img,
            text_items=[{"text":"MAX MATERIAL","box":BOX,"target_id":"feature1"}],
            jit_catalog_rows=catalog,
        )
        self.assertEqual(o["status"],"COMPILED")
        self.assertEqual(o["features"]["feature1"]["gdt.material_condition"],"MMC")

    def test_conflicting_claims_fail_closed(self):
        o=compile_annotation_constraints(
            self.img,
            text_items=[
                {"text":"DIA 10","box":BOX,"target_id":"hole1","source_id":"a"},
                {"text":"DIA 12","box":BOX,"target_id":"hole1","source_id":"b"},
            ],
        )
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"FEATURE_COMPOSITION_FAILED")

    def test_symbol_template_route(self):
        crop=np.full((20,20),255,dtype=np.uint8)
        cv2.line(crop,(10,2),(10,17),0,2); cv2.line(crop,(2,10),(17,10),0,2)
        circle=np.full((20,20),255,dtype=np.uint8); cv2.circle(circle,(10,10),6,0,2)
        o=compile_annotation_constraints(
            self.img,
            symbol_items=[{"image":crop,"box":BOX,"target_id":"f1"}],
            symbol_templates={"CROSS":crop,"CIRCLE":circle},
            symbol_semantics={"CROSS":{"property":"symbol.kind","value":"CROSS"},"CIRCLE":{"property":"symbol.kind","value":"CIRCLE"}},
        )
        self.assertEqual(o["status"],"COMPILED")
        self.assertEqual(o["features"]["f1"]["symbol.kind"],"CROSS")

    def test_unsupported_text_fails_closed(self):
        o=compile_annotation_constraints(
            self.img,
            text_items=[{"text":"mysterious squiggle","box":BOX,"target_id":"f1"}],
        )
        self.assertEqual(o["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
