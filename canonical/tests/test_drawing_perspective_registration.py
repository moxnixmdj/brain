import unittest

import cv2
import numpy as np

from canonical.runtime.drawing_perspective_registration import (
    detect_unique_dominant_quadrilateral,
    rectify_perspective,
)


class DrawingPerspectiveRegistrationTests(unittest.TestCase):
    def test_explicit_corner_rectification_recovers_frame(self):
        base = np.full((120, 180), 255, dtype=np.uint8)
        cv2.rectangle(base, (10, 10), (169, 109), 0, 3)
        cv2.line(base, (20, 60), (160, 60), 0, 2)

        src = np.float32([[0, 0], [179, 0], [179, 119], [0, 119]])
        dst = np.float32([[18, 10], [165, 3], [175, 112], [7, 118]])
        H = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(base, H, (190, 130), borderValue=255)

        out = rectify_perspective(warped, corners=dst)
        self.assertEqual(out["status"], "REGISTERED")
        reg = out["registered_image"]
        self.assertGreater(reg.shape[0], 90)
        self.assertGreater(reg.shape[1], 140)

    def test_auto_detect_unique_frame(self):
        img = np.full((150, 210), 255, dtype=np.uint8)
        pts = np.array([[20, 20], [190, 12], [200, 135], [10, 140]], dtype=np.int32)
        cv2.polylines(img, [pts], True, 0, 4)
        out = detect_unique_dominant_quadrilateral(img, min_area_fraction=0.30)
        self.assertEqual(out["status"], "DETECTED")
        self.assertEqual(len(out["corners"]), 4)

    def test_no_quad_fails_closed(self):
        img = np.full((80, 100), 255, dtype=np.uint8)
        cv2.circle(img, (50, 40), 20, 0, 2)
        out = detect_unique_dominant_quadrilateral(img)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_bad_explicit_corners_fail_closed(self):
        img = np.full((80, 100), 255, dtype=np.uint8)
        out = rectify_perspective(img, corners=[[0, 0], [1, 1], [2, 2], [3, 3]])
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
