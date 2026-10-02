import unittest, numpy as np, cv2
from canonical.runtime.declarative_engineering_notation import compile_catalog, resolve_tokens
from canonical.runtime.visual_symbol_template_matcher import match_symbol

class Tests(unittest.TestCase):
    def test_catalog_and_longest_alias(self):
        c=compile_catalog([
            {"symbol_id":"RUN","kind":"control","aliases":["RUNOUT"]},
            {"symbol_id":"TOTAL","kind":"control","aliases":["TOTAL RUNOUT"]},
        ])
        self.assertEqual(c["status"],"COMPILED",c)
        out=resolve_tokens("TOTAL RUNOUT",c)
        self.assertEqual([x["symbol_id"] for x in out["tokens"]],["TOTAL"])

    def test_alias_collision_fails(self):
        c=compile_catalog([
            {"symbol_id":"A","kind":"x","aliases":["SYM"]},
            {"symbol_id":"B","kind":"y","aliases":["SYM"]},
        ])
        self.assertEqual(c["status"],"FAIL_CLOSED")

    def test_template_match(self):
        t=np.full((40,40),255,np.uint8); cv2.line(t,(5,20),(35,20),0,3)
        img=np.full((60,60),255,np.uint8); cv2.line(img,(15,30),(45,30),0,3)
        alt=np.full((40,40),255,np.uint8); cv2.line(alt,(20,5),(20,35),0,3)
        out=match_symbol(img,{"H":t,"V":alt},min_score=0.5,min_margin=0.05)
        self.assertEqual(out["status"],"MATCHED",out); self.assertEqual(out["symbol_id"],"H")

    def test_template_low_score_fails(self):
        t=np.full((20,20),255,np.uint8); cv2.circle(t,(10,10),6,0,2)
        img=np.full((50,50),255,np.uint8); cv2.line(img,(5,5),(45,45),0,2)
        out=match_symbol(img,{"C":t},min_score=0.95,min_margin=0.05)
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_identical_templates_ambiguous(self):
        t=np.full((20,20),255,np.uint8); cv2.rectangle(t,(4,4),(15,15),0,2)
        img=np.full((30,30),255,np.uint8); img[5:25,5:25]=t
        out=match_symbol(img,{"A":t,"B":t},min_score=0.5,min_margin=0.1)
        self.assertEqual(out["status"],"FAIL_CLOSED"); self.assertEqual(out["error"],"AMBIGUOUS_MATCH")

if __name__=="__main__": unittest.main()
