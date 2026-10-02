import unittest
import cv2
import numpy as np

from canonical.runtime.calibrated_dense_warp_rectifier import rectify_with_inverse_map

class CalibratedDenseWarpRectifierTests(unittest.TestCase):
    def test_identity_map(self):
        img=np.full((60,80),255,dtype=np.uint8)
        cv2.line(img,(5,30),(74,30),0,2)
        yy,xx=np.indices(img.shape,dtype=np.float32)
        o=rectify_with_inverse_map(img,xx,yy)
        self.assertEqual(o["status"],"REGISTERED")
        self.assertTrue(np.array_equal(o["registered_image"],img))

    def test_smooth_calibrated_nonprojective_map(self):
        h,w=70,90
        img=np.full((h,w),255,dtype=np.uint8)
        cv2.rectangle(img,(10,10),(80,60),0,2)
        yy,xx=np.indices((h,w),dtype=np.float32)
        # Smooth row-dependent horizontal source displacement; Jacobian remains positive.
        mx=xx+2.0*np.sin(yy/18.0)
        my=yy.copy()
        # Permit small border excursion induced by calibration.
        o=rectify_with_inverse_map(img,mx,my,max_out_of_bounds_fraction=0.03)
        self.assertEqual(o["status"],"REGISTERED")
        self.assertEqual(o["registered_image"].shape,img.shape)

    def test_foldover_map_fails_closed(self):
        h,w=30,40
        img=np.full((h,w),255,dtype=np.uint8)
        yy,xx=np.indices((h,w),dtype=np.float32)
        mx=xx.copy()
        # Flip right half only, causing Jacobian orientation inconsistency/fold.
        mx[:,w//2:]=(w-1)-xx[:,w//2:]
        o=rectify_with_inverse_map(img,mx,yy,max_out_of_bounds_fraction=0)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertTrue(
            "LOCAL_MAP_FOLDOVER_ORIENTATION_CHANGE" in o["errors"]
            or "LOCAL_MAP_DEGENERACY" in o["errors"]
        )

    def test_nonfinite_map_fails_closed(self):
        img=np.full((20,20),255,dtype=np.uint8)
        yy,xx=np.indices(img.shape,dtype=np.float32)
        xx[5,5]=np.nan
        o=rectify_with_inverse_map(img,xx,yy)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("MAP_NONFINITE",o["errors"])

if __name__=="__main__":
    unittest.main()
