import unittest

import cv2
import numpy as np

from canonical.runtime.drawing_view_registration import register_global_axis_deskew


def base_three_view():
    img = np.full((300, 400), 255, dtype=np.uint8)
    cv2.rectangle(img, (60, 60), (160, 130), 0, 3)
    cv2.rectangle(img, (240, 60), (340, 130), 0, 3)
    cv2.rectangle(img, (60, 190), (160, 260), 0, 3)
    return img


def rotate(img, angle):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)


class DrawingViewRegistrationTests(unittest.TestCase):
    def test_positive_rotation_is_deskewed(self):
        out = register_global_axis_deskew(rotate(base_three_view(), 8.0))
        self.assertEqual(out["status"], "REGISTERED")
        self.assertAlmostEqual(out["estimated_rotation_deg"], -8.0, delta=1.0)

        again = register_global_axis_deskew(out["registered_image"])
        self.assertEqual(again["status"], "REGISTERED")
        self.assertAlmostEqual(again["estimated_rotation_deg"], 0.0, delta=1.0)

    def test_negative_rotation_is_deskewed(self):
        out = register_global_axis_deskew(rotate(base_three_view(), -7.0))
        self.assertEqual(out["status"], "REGISTERED")
        self.assertAlmostEqual(out["estimated_rotation_deg"], 7.0, delta=1.0)

    def test_rotation_outside_scope_fails_closed(self):
        out = register_global_axis_deskew(
            rotate(base_three_view(), 24.0),
            max_abs_angle_deg=15.0,
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "ROTATION_OUTSIDE_BOUNDED_SCOPE")

    def test_blank_image_fails_closed(self):
        img = np.full((120, 180), 255, dtype=np.uint8)
        out = register_global_axis_deskew(img)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "NO_USABLE_LINES")


if __name__ == "__main__":
    unittest.main()
