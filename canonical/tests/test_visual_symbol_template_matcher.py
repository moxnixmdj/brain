import unittest
import cv2
import numpy as np

from canonical.runtime.visual_symbol_template_matcher import match_symbol

class VisualSymbolTemplateMatcherTests(unittest.TestCase):
    def _cross(self,size=15):
        img=np.full((size,size),255,dtype=np.uint8)
        c=size//2
        cv2.line(img,(c,2),(c,size-3),0,2)
        cv2.line(img,(2,c),(size-3,c),0,2)
        return img

    def _circle(self,size=15):
        img=np.full((size,size),255,dtype=np.uint8)
        cv2.circle(img,(size//2,size//2),size//3,0,2)
        return img

    def test_exact_insert_matches_unique_template(self):
        src=np.full((40,50),255,dtype=np.uint8)
        t=self._cross()
        src[10:25,20:35]=t
        o=match_symbol(src,{"CROSS":t,"CIRCLE":self._circle()},min_score=0.8,min_margin=0.05)
        self.assertEqual(o["status"],"MATCHED")
        self.assertEqual(o["symbol_id"],"CROSS")

    def test_identical_templates_fail_ambiguous(self):
        src=np.full((30,30),255,dtype=np.uint8)
        t=self._cross()
        src[5:20,5:20]=t
        o=match_symbol(src,{"A":t,"B":t},min_score=0.8,min_margin=0.05)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"AMBIGUOUS_MATCH")

    def test_low_score_fails_closed(self):
        src=np.full((30,30),255,dtype=np.uint8)
        cv2.line(src,(2,2),(27,27),0,1)
        o=match_symbol(src,{"CIRCLE":self._circle()},min_score=0.95,min_margin=0.05)
        self.assertEqual(o["status"],"FAIL_CLOSED")

    def test_invalid_template_fails_closed(self):
        src=np.full((30,30),255,dtype=np.uint8)
        o=match_symbol(src,{"BAD":np.zeros((2,2,2),dtype=np.uint8)})
        self.assertEqual(o["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
