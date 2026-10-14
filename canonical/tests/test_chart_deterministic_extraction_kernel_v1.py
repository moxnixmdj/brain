"""Synthetic-gold tests for the deterministic chart-extraction kernel.

Every test draws a chart with Pillow from known numbers (gold known by
construction, no benchmark data involved) and checks that the kernel recovers
the numbers within the kernel's own pixel-quantisation certificate."""
import math
import unittest

try:
    import numpy as np  # noqa: F401
    from PIL import Image, ImageDraw
    HAVE_DEPS = True
except Exception:  # pragma: no cover - environment without numpy/Pillow
    HAVE_DEPS = False

from canonical.runtime import chart_deterministic_extraction_kernel_v1 as K


def _blank(w=600, h=400):
    im = Image.new("RGB", (w, h), (255, 255, 255))
    return im, ImageDraw.Draw(im)


def _axes(d, left=50, right=550, top=50, bottom=350):
    d.line([(left, bottom), (right, bottom)], fill=(0, 0, 0), width=2)
    d.line([(left, top), (left, bottom)], fill=(0, 0, 0), width=2)


class AxisTests(unittest.TestCase):
    def test_linear_roundtrip(self):
        a = K.AxisMap(50, 0.0, 550, 100.0)
        self.assertAlmostEqual(a.px_to_val(300), 50.0)
        self.assertAlmostEqual(a.val_to_px(25.0), 175.0)
        self.assertAlmostEqual(a.value_per_pixel(300), 0.2)

    def test_log_axis(self):
        a = K.AxisMap(100, 1.0, 400, 1000.0, scale="log")
        self.assertAlmostEqual(a.px_to_val(250), 10 ** 1.5, places=6)
        self.assertAlmostEqual(a.val_to_px(10.0), 200.0)
        # inverted pixel direction (values grow upward = decreasing row index)
        b = K.AxisMap(350, 1.0, 50, 100.0, scale="log")
        self.assertAlmostEqual(b.px_to_val(200), 10.0)

    @unittest.skipUnless(HAVE_DEPS, "numpy required")
    def test_fit_axis_drops_single_bad_tick(self):
        ticks = [(100, 0.0), (200, 10.0), (250, 80.0), (300, 20.0), (400, 30.0)]
        amap, rep = K.fit_axis(ticks)
        self.assertEqual(rep["dropped_ticks"], [(250.0, 80.0)])
        self.assertAlmostEqual(amap.px_to_val(350), 25.0, places=6)
        self.assertLess(rep["max_residual_px"], 1e-6)


@unittest.skipUnless(HAVE_DEPS, "numpy + Pillow required")
class RasterTests(unittest.TestCase):
    def test_detect_plot_frame(self):
        im, d = _blank()
        _axes(d)
        fr = K.detect_plot_frame(np.asarray(im))
        self.assertIsNotNone(fr)
        self.assertIn(fr["x_axis_row"], (349, 350, 351))
        self.assertIn(fr["y_axis_col"], (49, 50, 51))

    def test_line_chart_values_within_certificate(self):
        im, d = _blank()
        _axes(d)
        xa = K.AxisMap(50, 0.0, 550, 100.0)          # x: 0..100
        ya = K.AxisMap(350, 0.0, 50, 100.0)          # y: 0..100 (row 350 = 0)
        f = lambda x: 50 + 35 * math.sin(x / 12.0)  # noqa: E731
        pts = [(xa.val_to_px(x), ya.val_to_px(f(x))) for x in range(0, 101)]
        d.line(pts, fill=(30, 90, 220), width=2)
        rgb = np.asarray(im)
        mask = K.color_mask(rgb, (30, 90, 220), tol=60)
        series = K.trace_series(mask, x_step=4, y_step=6)
        self.assertGreater(len(series), 100)
        checked = 0
        for x in (5, 17, 33, 50, 64, 81, 95):
            ypx = K.series_value_at(series, xa.val_to_px(x))
            self.assertIsNotNone(ypx, f"no trace at x={x}")
            cert = K.quantization_bound(ya, ypx, pixel_uncertainty=2.0)
            self.assertLessEqual(abs(cert.value - f(x)), cert.abs_bound,
                                 f"x={x}: got {cert.value:.3f} true {f(x):.3f} bound {cert.abs_bound:.3f}")
            self.assertTrue(cert.within(tolerance_rel=0.05))
            checked += 1
        self.assertEqual(checked, 7)

    def test_bar_chart_positive_and_negative(self):
        im, d = _blank()
        ya = K.AxisMap(250, 0.0, 50, 100.0)  # 2 px per unit, baseline row 250
        d.line([(50, 250), (550, 250)], fill=(0, 0, 0), width=1)
        gold = [30.0, -10.0, 55.0, 80.0, 5.0]
        for i, v in enumerate(gold):
            x0 = 80 + i * 90
            top, bot = sorted([ya.val_to_px(v), 250.0])
            d.rectangle([x0, top, x0 + 40, bot], fill=(200, 40, 40))
        rgb = np.asarray(im)
        mask = K.color_mask(rgb, (200, 40, 40), tol=40)
        bars = K.extract_bars(mask, "vertical", del_pos=30, del_val=4, min_width=5)
        self.assertEqual(len(bars), 5)
        for b, v in zip(bars, gold):
            got = K.bar_value(b, ya, baseline_px=250.0)
            end_px = ya.val_to_px(got)
            cert = K.quantization_bound(ya, end_px, pixel_uncertainty=1.5)
            self.assertLessEqual(abs(got - v), cert.abs_bound, f"bar {v}: got {got}")
            self.assertLessEqual(cert.abs_bound, 0.75)

    def test_pie_fractions(self):
        im, d = _blank(400, 400)
        gold = [(0.5, (220, 60, 60)), (0.3, (60, 160, 60)), (0.2, (60, 60, 220))]
        start = 0.0
        for frac, col in gold:
            d.pieslice([50, 50, 350, 350], start, start + 360 * frac, fill=col)
            start += 360 * frac
        rgb = np.asarray(im)
        parts = K.pie_fractions(rgb, center=(200, 200), radius=150)
        self.assertEqual(len(parts), 3)
        by_col = {p["rgb"]: p["fraction"] for p in parts}
        for frac, col in gold:
            key = min(by_col, key=lambda c: sum((c[k] - col[k]) ** 2 for k in range(3)))
            self.assertLess(abs(by_col[key] - frac), 0.01, f"{col}: {by_col[key]} vs {frac}")

    def test_dominant_colors_excludes_grays(self):
        im, d = _blank(200, 200)
        d.rectangle([10, 10, 90, 190], fill=(200, 40, 40))
        d.rectangle([110, 10, 190, 190], fill=(30, 90, 220))
        d.line([(0, 100), (200, 100)], fill=(0, 0, 0), width=3)
        cols = K.dominant_colors(np.asarray(im))
        self.assertEqual(len(cols), 2)
        self.assertTrue(all(max(c) - min(c) > 24 for c, _ in cols))


if __name__ == "__main__":
    unittest.main()
