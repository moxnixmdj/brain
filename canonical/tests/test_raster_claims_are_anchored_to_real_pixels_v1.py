"""The raster chart inspectors must be able to say no to a fabricated anchor.

WHY THIS EXISTS
---------------
`chart.raster.curve_value_query.v1`, `chart.raster.curve_x_at_y_query.v1` and
`chart.raster.scene_graph.v1` returned a measurement of an image with a `pass` flag and nothing
re-opened the image, so the flag was the only evidence. `expect_discrimination_v1` classified all
three as dead-and-uncovered for exactly that reason.

The inspectors added to `raw_goal_trace_acceptance_v1` re-open the PNG and check that the pixel the
capability says it measured is really ink of the declared colour, at the declared coordinate, in the
file it names.

This test proves the check can fail: a true anchor is accepted, and a claim moved off the ink, a
claim about an image of the wrong size, and a claim naming a file that is not there are all refused.
A check that cannot fail is the defect being repaired, so a test that only exercises the passing
case would repeat it.
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import raw_goal_trace_acceptance_v1 as R  # noqa: E402


def _chart(path: pathlib.Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (400, 300), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    # A red curve at a known place, plus a frame so the image is a chart at all.
    draw.line([(40, 250), (200, 150), (360, 60)], fill=(220, 40, 40), width=3)
    draw.rectangle([40, 40, 360, 250], outline=(0, 0, 0))
    image.save(path)


INK = (216, 24, 24)  # the bucket the red above falls into: each channel -> ch//48*48+24


class RasterInspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        _chart(self.root / "chart.png")

    def tearDown(self):
        self.tmp.cleanup()

    def _claim(self, **overrides):
        result = {
            "path": "chart.png",
            "color_bucket": list(INK),
            "x_value": 2.0,
            "target_pixel_x": 200,
            "interpolated_pixel_y": 150,
        }
        result.update(overrides)
        return result

    def test_an_anchor_on_the_drawn_curve_is_accepted(self):
        ok, reason, detail = R._inspect_raster_query_x({}, self._claim(), self.root)
        self.assertTrue(ok, reason)
        self.assertGreater(detail["ink_pixels_in_window"], 0)

    def test_an_anchor_moved_off_the_ink_is_refused(self):
        ok, reason, _ = R._inspect_raster_query_x(
            {}, self._claim(target_pixel_x=300, interpolated_pixel_y=240), self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "RASTER_ANCHOR_IS_NOT_INK_OF_THE_DECLARED_COLOUR")

    def test_an_anchor_outside_the_image_is_refused(self):
        ok, reason, _ = R._inspect_raster_query_x({}, self._claim(target_pixel_x=9_000), self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "RASTER_ANCHOR_OUTSIDE_THE_IMAGE")

    def test_a_claim_about_a_missing_file_is_refused(self):
        ok, reason, _ = R._inspect_raster_query_y({}, self._claim(path="no_such_chart.png"), self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "RASTER_INPUT_ABSENT_FROM_DISK")

    def test_the_vertical_query_reads_its_own_anchor_fields(self):
        claim = self._claim(interpolated_pixel_x=200, target_pixel_y=150, y_value=3.0)
        ok, reason, _ = R._inspect_raster_query_y({}, claim, self.root)
        self.assertTrue(ok, reason)
        claim = dict(claim, target_pixel_y=20)
        ok, reason, _ = R._inspect_raster_query_y({}, claim, self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "RASTER_ANCHOR_IS_NOT_INK_OF_THE_DECLARED_COLOUR")

    def test_scene_graph_that_misreports_the_image_size_is_refused(self):
        ok, reason, _ = R._inspect_raster_scene_graph(
            {}, {"path": "chart.png", "image_size": [800, 600], "plot_box": [40, 40, 360, 250]},
            self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "RASTER_SCENE_GRAPH_IMAGE_SIZE_MISMATCH")

    def test_scene_graph_with_a_plot_box_beyond_the_image_is_refused(self):
        ok, reason, _ = R._inspect_raster_scene_graph(
            {}, {"path": "chart.png", "image_size": [400, 300], "plot_box": [0, 0, 4_000, 3_000]},
            self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "RASTER_SCENE_GRAPH_PLOT_BOX_OUTSIDE_THE_IMAGE")

    def test_scene_graph_over_an_inkless_image_is_refused(self):
        from PIL import Image

        Image.new("RGB", (100, 100), (255, 255, 255)).save(self.root / "blank.png")
        ok, reason, _ = R._inspect_raster_scene_graph(
            {}, {"path": "blank.png", "image_size": [100, 100], "plot_box": [10, 10, 90, 90]},
            self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "RASTER_SCENE_GRAPH_REPORTS_NO_INK_BUT_THE_BOX_HAS_NONE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
