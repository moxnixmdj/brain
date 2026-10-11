from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import (
    ChartSceneGraphError,
    build_scene_graph,
    calibrate_axis,
    color_polylines,
    detect_plot_box,
    saturated_components,
)

class ChartRasterSceneGraphV1Tests(unittest.TestCase):
    def test_linear_axis_selected(self):
        out=calibrate_axis([(50,0),(100,10),(150,20),(200,30)],"INCREASING")
        self.assertEqual(out["scale"],"LINEAR")
        self.assertLess(out["normalized_rmse"],1e-10)

    def test_log_axis_selected(self):
        out=calibrate_axis([(50,1),(100,10),(150,100),(200,1000)],"INCREASING")
        self.assertEqual(out["scale"],"LOG10")
        self.assertLess(out["normalized_rmse"],1e-10)

    def test_decreasing_pixel_axis(self):
        out=calibrate_axis([(190,0),(150,10),(110,20),(70,30)],"DECREASING")
        self.assertEqual(out["scale"],"LINEAR")

    def test_wrong_axis_direction_fails_closed(self):
        with self.assertRaisesRegex(ChartSceneGraphError,"AXIS_DIRECTION_MISMATCH"):
            calibrate_axis([(50,0),(100,10),(150,20)],"DECREASING")

    def _fixture(self, path: Path):
        im=Image.new("RGB",(320,240),"white")
        d=ImageDraw.Draw(im)
        d.line((50,30,50,190),fill="black",width=2)
        d.line((50,190,280,190),fill="black",width=2)
        d.line((60,170,100,150,140,130,180,110,220,90,260,70),fill=(230,30,30),width=3)
        d.rectangle((190,140,205,180),fill=(30,80,220))
        im.save(path)
        return im

    def test_plot_components_and_polyline_are_geometry_only(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"chart.png"
            im=self._fixture(p)
            box=detect_plot_box(im)
            self.assertLessEqual(abs(box[0]-50),2)
            self.assertLessEqual(abs(box[3]-190),2)
            comps=saturated_components(im,box)
            self.assertGreaterEqual(len(comps),2)
            traces=color_polylines(im,box)
            red=[t for t in traces if t["column_count"]>150]
            self.assertTrue(red)
            self.assertLess(red[0]["points"][0][1],190)

    def test_scene_graph_has_no_semantic_authority(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"chart.png"
            self._fixture(p)
            out=build_scene_graph(
                p,
                x_ticks=[(50,0),(100,10),(150,20),(200,30)],
                y_ticks=[(190,0),(150,10),(110,20),(70,30)],
            )
            self.assertEqual(out["status"],"PASS__RASTER_SCENE_GRAPH")
            self.assertEqual(out["axes"]["x"]["scale"],"LINEAR")
            self.assertEqual(out["axes"]["y"]["scale"],"LINEAR")
            self.assertFalse(out["semantic_authority"])
            self.assertFalse(out["domain_semantic_authority"])
            self.assertFalse(out["benchmark_score_authority"])
            self.assertEqual(out["general_purpose_model_dependency_count"],0)
            self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)

if __name__=="__main__":
    unittest.main()
