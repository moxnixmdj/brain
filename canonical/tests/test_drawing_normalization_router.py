import unittest
import cv2
import numpy as np

from canonical.runtime.drawing_normalization_router import normalize_drawing

class DrawingNormalizationRouterTests(unittest.TestCase):
    def _drawing(self):
        img=np.full((120,180),255,dtype=np.uint8)
        cv2.rectangle(img,(15,15),(165,105),0,2)
        cv2.line(img,(25,60),(155,60),0,2)
        return img

    def test_none_route_normalizes(self):
        o=normalize_drawing(self._drawing(),{"mode":"NONE"},consensus_min_iou=0.55)
        self.assertEqual(o["status"],"NORMALIZED")
        self.assertGreater(int(o["ink_mask"].sum()),0)
        self.assertEqual(o["receipts"][0]["mode"],"NONE")

    def test_dense_identity_route(self):
        img=self._drawing()
        yy,xx=np.indices(img.shape,dtype=np.float32)
        o=normalize_drawing(
            img,
            {"mode":"CALIBRATED_DENSE","map_x":xx,"map_y":yy,"max_out_of_bounds_fraction":0},
            consensus_min_iou=0.55
        )
        self.assertEqual(o["status"],"NORMALIZED")
        self.assertEqual(o["receipts"][0]["mode"],"CALIBRATED_DENSE")

    def test_projective_explicit_route(self):
        base=self._drawing()
        src=np.float32([[0,0],[179,0],[179,119],[0,119]])
        dst=np.float32([[10,5],[170,2],[177,114],[4,118]])
        H=cv2.getPerspectiveTransform(src,dst)
        warped=cv2.warpPerspective(base,H,(185,125),borderValue=255)
        o=normalize_drawing(
            warped,
            {"mode":"PROJECTIVE_EXPLICIT","corners":dst.tolist()},
            consensus_min_iou=0.50
        )
        self.assertEqual(o["status"],"NORMALIZED")
        self.assertEqual(o["receipts"][0]["mode"],"PROJECTIVE_EXPLICIT")

    def test_invalid_route_fails_closed(self):
        o=normalize_drawing(self._drawing(),{"mode":"MAGIC"})
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"REGISTRATION_MODE_INVALID")

    def test_missing_dense_map_fails_closed(self):
        o=normalize_drawing(self._drawing(),{"mode":"CALIBRATED_DENSE"})
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"CALIBRATION_MAP_MISSING")

if __name__=="__main__":
    unittest.main()
