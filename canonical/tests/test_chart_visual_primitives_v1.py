from __future__ import annotations
import pathlib
import tempfile
import unittest

def _write_ppm(path: pathlib.Path) -> None:
    w, h = 400, 300
    px = bytearray([255, 255, 255]) * (w * h)
    def setpx(x, y, rgb):
        if 0 <= x < w and 0 <= y < h:
            i = (y * w + x) * 3
            px[i:i+3] = bytes(rgb)
    for x in range(48, 53):
        for y in range(30, 262):
            setpx(x, y, (0, 0, 0))
    for y in range(247, 252):
        for x in range(50, 360):
            setpx(x, y, (0, 0, 0))
    for y in range(150, 221):
        for x in range(120, 171):
            setpx(x, y, (255, 0, 0))
    for x in range(70, 330):
        y = int(225 - 0.45 * (x - 70))
        for d in range(-2, 3):
            setpx(x, y + d, (0, 0, 0))
    path.write_bytes(f"P6\n{w} {h}\n255\n".encode("ascii") + bytes(px))

class ChartVisualPrimitivesV1Tests(unittest.TestCase):
    def test_synthetic_geometry_and_determinism(self):
        from canonical.runtime.chart_visual_primitives_v1 import extract_visual_primitives
        with tempfile.TemporaryDirectory() as td:
            image = pathlib.Path(td) / "synthetic.ppm"
            _write_ppm(image)
            a = extract_visual_primitives(image, include_ocr=False)
            b = extract_visual_primitives(image, include_ocr=False)
        self.assertEqual(a, b)
        self.assertEqual(a["schema"], "PROJECT_BRAIN_CHART_VISUAL_PRIMITIVES_V1")
        self.assertEqual((a["width"], a["height"]), (400, 300))
        self.assertFalse(a["network_required"])
        self.assertFalse(a["external_model_required"])
        self.assertFalse(a["terminal_semantic_authority"])
        kinds = {x["kind"] for x in a["lines"]}
        self.assertIn("horizontal", kinds)
        self.assertIn("vertical", kinds)
        self.assertIn("oblique", kinds)
        self.assertIsNotNone(a["axes"]["x_axis"])
        self.assertIsNotNone(a["axes"]["y_axis"])
        self.assertGreater(len(a["connected_components"]), 0)
        self.assertGreater(len(a["rectangles"]), 0)
        self.assertGreater(len(a["dominant_hsv_bins"]), 0)

if __name__ == "__main__":
    unittest.main()
