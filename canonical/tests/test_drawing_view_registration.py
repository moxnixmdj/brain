import unittest

import cv2
import numpy as np

from canonical.runtime.drawing_view_registration import (
    register_global_axis_deskew,
    register_planar_perspective_from_quad,
)


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


    def test_explicit_planar_perspective_is_rectified(self):
        base = np.full((180, 260), 255, dtype=np.uint8)
        cv2.rectangle(base, (25, 25), (235, 155), 0, 3)
        cv2.line(base, (40, 90), (220, 90), 0, 2)
        cv2.line(base, (130, 40), (130, 140), 0, 2)

        src = np.asarray(
            [[0.0, 0.0], [259.0, 0.0], [259.0, 179.0], [0.0, 179.0]],
            dtype=np.float32,
        )
        warped_quad = np.asarray(
            [[35.0, 20.0], [238.0, 6.0], [255.0, 168.0], [12.0, 176.0]],
            dtype=np.float32,
        )
        h = cv2.getPerspectiveTransform(src, warped_quad)
        warped = cv2.warpPerspective(base, h, (280, 200), borderValue=255)

        out = register_planar_perspective_from_quad(
            warped,
            warped_quad,
            output_size=(260, 180),
        )
        self.assertEqual(out["status"], "REGISTERED")
        recovered = out["registered_image"]
        self.assertEqual(recovered.shape, base.shape)

        # Compare the thresholded structural ink mask rather than requiring
        # pixel identity after two bilinear projective resamplings.
        base_ink = base < 180
        recovered_ink = recovered < 180
        intersection = np.logical_and(base_ink, recovered_ink).sum()
        union = np.logical_or(base_ink, recovered_ink).sum()
        self.assertGreater(intersection / union, 0.70)

    def test_nonconvex_quad_is_rejected(self):
        img = base_three_view()
        with self.assertRaises(ValueError):
            register_planar_perspective_from_quad(
                img,
                [[0, 0], [100, 0], [0, 100], [100, 100]],
            )

    def test_tiny_quad_is_rejected(self):
        img = base_three_view()
        with self.assertRaises(ValueError):
            register_planar_perspective_from_quad(
                img,
                [[0, 0], [1, 0], [1, 1], [0, 1]],
            )


if __name__ == "__main__":
    unittest.main()
