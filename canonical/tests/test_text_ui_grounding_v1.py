from __future__ import annotations
import unittest
from canonical.runtime.text_ui_grounding_v1 import *

def ocr(items,w=800,h=600):
    return {"page_width":w,"page_height":h,"text_items":items}

def item(text,x0,y0,x1,y1,sid):
    return {"text":text,"source_id":sid,"box":{"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1},"confidence_mean":95.0}

class Tests(unittest.TestCase):
    def test_unique_exact_label_grounded(self):
        out=resolve_unique_text_target(ocr([item("Save",100,100,180,140,"a")]),"save")
        self.assertTrue(out["pass"])
        self.assertEqual(out["click_point"],{"x":139,"y":119})
    def test_nfkc_casefold_and_space_normalization(self):
        out=resolve_unique_text_target(ocr([item("  SAVE   AS  ",1,2,101,22,"a")]),"save as")
        self.assertTrue(out["pass"])
    def test_duplicate_label_never_guesses(self):
        out=resolve_unique_text_target(ocr([item("OK",1,1,20,20,"a"),item("OK",100,100,140,120,"b")]),"ok")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__TEXT_TARGET_AMBIGUOUS")
        self.assertIsNone(compile_click_action(ocr([item("OK",1,1,20,20,"a"),item("OK",100,100,140,120,"b")]),"ok")["typed_action"])
    def test_missing_target_never_guesses(self):
        out=resolve_unique_text_target(ocr([item("Cancel",1,1,50,20,"a")]),"Save")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__TEXT_TARGET_NOT_OBSERVED")
    def test_out_of_bounds_ocr_fails_closed(self):
        with self.assertRaisesRegex(TextGroundingError,"BOX_OUT_OF_BOUNDS"):
            compile_candidates(ocr([item("Save",790,10,810,30,"a")]),"save")
    def test_noninteger_geometry_fails_closed(self):
        bad={"page_width":800,"page_height":600,"text_items":[{"text":"Save","box":{"x0":1.5,"y0":1,"x1_exclusive":20,"y1_exclusive":20}}]}
        with self.assertRaisesRegex(TextGroundingError,"BOX_COORD_INVALID"):
            compile_candidates(bad,"save")
    def test_token_mode_is_explicit_and_bounded(self):
        out=resolve_unique_text_target(ocr([item("File Save Close",1,1,100,30,"a")]),"save",match_mode="token")
        self.assertTrue(out["pass"])
        with self.assertRaisesRegex(TextGroundingError,"MATCH_MODE_INVALID"):
            compile_candidates(ocr([]),"x",match_mode="fuzzy")
    def test_substring_does_not_match_exact(self):
        out=resolve_unique_text_target(ocr([item("Save As",1,1,100,30,"a")]),"save")
        self.assertFalse(out["pass"])
    def test_click_action_is_typed_not_python(self):
        out=compile_click_action(ocr([item("Apply",20,40,80,60,"a")]),"apply")
        self.assertEqual(out["typed_action"],{"type":"click","x":49,"y":49,"button":"left"})
        self.assertNotIn("command",out["typed_action"])
    def test_candidate_set_digest_stable(self):
        src=ocr([item("Save",1,1,40,20,"a")])
        a=compile_candidates(src,"save")
        b=compile_candidates(src,"SAVE")
        self.assertEqual(a["candidate_set_sha256"],b["candidate_set_sha256"])
    def test_source_id_fallback_deterministic(self):
        src={"page_width":100,"page_height":100,"text_items":[{"text":"X","box":{"x0":1,"y0":1,"x1_exclusive":10,"y1_exclusive":10}}]}
        out=resolve_unique_text_target(src,"x")
        self.assertEqual(out["selected_candidate_id"],"text_item:0")
    def test_no_authority_inflation(self):
        out=resolve_unique_text_target(ocr([item("Go",1,1,30,20,"a")]),"go")
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["terminal_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
