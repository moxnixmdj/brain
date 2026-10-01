import unittest
import numpy as np
import cv2

from canonical.runtime.drawing_perspective_rectification import rectify_from_quad
from canonical.runtime.drawing_robust_preprocess import robust_ink_mask
from canonical.runtime.gdt_feature_control_parser import parse_feature_control_frame, parse_datum

class M1AHardeningTests(unittest.TestCase):
    def test_perspective_rectification_known_quad(self):
        img=np.full((240,320),255,np.uint8)
        quad=np.array([[40,30],[280,20],[300,210],[25,220]],np.float32)
        cv2.polylines(img,[quad.astype(np.int32)],True,0,3)
        out=rectify_from_quad(img,quad)
        self.assertEqual(out["status"],"RECTIFIED")
        self.assertGreater(out["shape"][0],150)
        self.assertGreater(out["shape"][1],200)
        self.assertFalse(out["terminal_authority"])

    def test_degenerate_quad_fails_closed(self):
        img=np.full((100,100),255,np.uint8)
        out=rectify_from_quad(img,[[1,1],[2,2],[3,3],[4,4]])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_robust_preprocess_uneven_illumination(self):
        h,w=220,320
        x=np.linspace(140,255,w,dtype=np.float32)
        img=np.tile(x,(h,1)).astype(np.uint8)
        cv2.line(img,(30,60),(290,60),20,2)
        cv2.rectangle(img,(80,100),(240,180),30,2)
        out=robust_ink_mask(img)
        self.assertEqual(out["status"],"NORMALIZED",out)
        self.assertGreater(out["ink_fraction"],0.0005)
        self.assertLess(out["ink_fraction"],0.60)

    def test_uniform_image_fails_closed(self):
        out=robust_ink_mask(np.full((100,100),200,np.uint8))
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_position_fcf(self):
        out=parse_feature_control_frame("POSITION | DIA 0.10 MMC | A | B MMC | C")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(out["characteristic"],"POSITION")
        self.assertTrue(out["tolerance"]["diametrical_zone"])
        self.assertEqual(out["tolerance"]["material_condition"],"MMC")
        self.assertEqual([d["datum"] for d in out["datums"]],["A","B","C"])

    def test_parallelism_symbol_fcf(self):
        out=parse_feature_control_frame("∥ | 0.02 mm | A")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(out["characteristic"],"PARALLELISM")

    def test_unknown_gdt_fails_closed(self):
        out=parse_feature_control_frame("MYSTERY | 0.1 | A")
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_datum(self):
        out=parse_datum("DATUM A1")
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["datum"],"A1")

if __name__=="__main__":
    unittest.main()
