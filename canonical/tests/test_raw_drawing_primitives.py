import unittest

import cv2
import numpy as np

from canonical.runtime.raw_drawing_primitives import extract_primitives, normalize_ink_mask


class RawDrawingPrimitiveTests(unittest.TestCase):
    def test_clean_rectangle_normalizes_and_detects_lines(self):
        img = np.full((120, 160), 255, dtype=np.uint8)
        cv2.rectangle(img, (20, 25), (140, 95), 0, 2)
        out = extract_primitives(img, min_line_length=40, line_threshold=15)
        self.assertEqual(out["status"], "EXTRACTED")
        self.assertGreater(out["ink_pixels"], 0)
        self.assertIsNotNone(out["ink_bbox"])
        self.assertGreaterEqual(len(out["lines"]), 4)

    def test_color_input_supported(self):
        img = np.full((80, 100, 3), 255, dtype=np.uint8)
        cv2.line(img, (10, 40), (90, 40), (0, 0, 0), 2)
        mask = normalize_ink_mask(img)
        self.assertEqual(mask.shape, (80, 100))
        self.assertGreater(int(mask.sum()), 0)

    def test_blank_image_is_explicit(self):
        img = np.full((40, 50), 255, dtype=np.uint8)
        out = extract_primitives(img)
        self.assertEqual(out["ink_pixels"], 0)
        self.assertIsNone(out["ink_bbox"])
        self.assertEqual(out["lines"], [])

    def test_bad_shape_fails(self):
        with self.assertRaises(ValueError):
            normalize_ink_mask(np.zeros((2, 3, 4, 5), dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()
