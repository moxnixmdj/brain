#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

CANONICAL=pathlib.Path(__file__).resolve().parents[1]
ROOT=CANONICAL.parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

compiler=load("goal_compiler_test",CANONICAL/"runtime"/"goal_compiler.py")

class GoalCompilerTests(unittest.TestCase):
    def registry(self):
        return json.loads((CANONICAL/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]

    def test_plain_image_only_pdf_goal_selects_verified_ocr(self):
        goal="Extract the visible text from canonical/astra_runtime/tmp/IMAGE_ONLY_OCR_TEST.pdf, which is an image-only PDF."
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["selected_capability"],"pdf.extract.ocr.tesseract")
        self.assertEqual(out["target_effects"],["pdf.extract.ocr"])
        self.assertEqual(out["inputs"]["pdf_path"],"canonical/astra_runtime/tmp/IMAGE_ONLY_OCR_TEST.pdf")

    def test_unknown_goal_fails_closed(self):
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"):
            compiler.compile_goal("Reticulate a quantum banana lattice",self.registry(),ROOT)

    def test_qr_goal_does_not_false_match_ocr(self):
        goal="Generate a QR code image for PROJECT BRAIN and save it as canonical/astra_runtime/tmp/PROJECT_BRAIN_QR.png."
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"):
            compiler.compile_goal(goal,self.registry(),ROOT)

if __name__=="__main__":
    unittest.main(verbosity=2)
