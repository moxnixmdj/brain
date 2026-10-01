import unittest

import cv2
import numpy as np

from canonical.runtime.drawing_view_regions import segment_view_regions


class DrawingViewRegionsTests(unittest.TestCase):
    def test_three_separated_views(self):
        img = np.full((240, 360), 255, dtype=np.uint8)
        cv2.rectangle(img, (20, 20), (120, 90), 0, 2)
        cv2.rectangle(img, (210, 20), (330, 90), 0, 2)
        cv2.rectangle(img, (20, 145), (120, 220), 0, 2)
        out = segment_view_regions(img, min_area=100, dilation_px=2, min_regions=3, max_regions=3)
        self.assertEqual(out["status"], "SEGMENTED")
        self.assertEqual(out["region_count"], 3)
        self.assertEqual(out["view_identity"], "UNASSIGNED")

    def test_single_view_allowed_when_declared(self):
        img = np.full((100, 140), 255, dtype=np.uint8)
        cv2.rectangle(img, (20, 20), (120, 80), 0, 2)
        out = segment_view_regions(img, min_regions=1, max_regions=1)
        self.assertEqual(out["status"], "SEGMENTED")

    def test_region_count_fails_closed(self):
        img = np.full((100, 140), 255, dtype=np.uint8)
        cv2.rectangle(img, (20, 20), (120, 80), 0, 2)
        out = segment_view_regions(img, min_regions=3, max_regions=3)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_identity_not_inferred(self):
        img = np.full((180, 260), 255, dtype=np.uint8)
        cv2.rectangle(img, (15, 15), (100, 70), 0, 2)
        cv2.rectangle(img, (150, 100), (240, 165), 0, 2)
        out = segment_view_regions(img, min_regions=2, max_regions=2)
        self.assertEqual(out["view_identity"], "UNASSIGNED")


if __name__ == "__main__":
    unittest.main()
