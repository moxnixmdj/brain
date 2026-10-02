import unittest
import cv2
import numpy as np

from canonical.runtime.drawing_sheet_quad import detect_planar_sheet_quad


class DrawingSheetQuadTests(unittest.TestCase):
    def test_detects_perspective_sheet(self):
        img=np.full((260,360),40,dtype=np.uint8)
        quad=np.asarray([[55,35],[310,20],[330,225],[35,235]],dtype=np.int32)
        cv2.fillConvexPoly(img,quad,240)
        cv2.rectangle(img,(110,90),(250,160),20,3)
        out=detect_planar_sheet_quad(img,min_area_fraction=0.30)
        self.assertEqual(out["status"],"DETECTED")
        got=out["quad"]
        expected=np.asarray([[55,35],[310,20],[330,225],[35,235]],dtype=np.float32)
        self.assertLess(float(np.max(np.linalg.norm(got-expected,axis=1))),8.0)

    def test_blank_fails_closed(self):
        img=np.full((180,260),255,dtype=np.uint8)
        out=detect_planar_sheet_quad(img)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"NO_DOMINANT_CONVEX_QUAD")

    def test_small_quad_below_fraction_fails(self):
        img=np.full((200,300),20,dtype=np.uint8)
        cv2.rectangle(img,(20,20),(90,80),240,-1)
        out=detect_planar_sheet_quad(img,min_area_fraction=0.20)
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_two_similar_quads_fail_ambiguous(self):
        img=np.full((220,420),20,dtype=np.uint8)
        cv2.rectangle(img,(20,20),(195,200),240,-1)
        cv2.rectangle(img,(225,20),(400,200),240,-1)
        out=detect_planar_sheet_quad(img,min_area_fraction=0.15)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"AMBIGUOUS_MULTIPLE_QUADS")


if __name__=="__main__":
    unittest.main()
