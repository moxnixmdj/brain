import sys
import unittest
from pathlib import Path

# m1b_smooth_surface_compiler lives in canonical/runtime and imports its own
# siblings by bare name, so it is only importable with that directory on
# sys.path. Nineteen workflows set PYTHONPATH that way; the plain
# `python -m unittest` and test-corpus-audit invocations do not, so this import
# raised ModuleNotFoundError and every test in this file was silently never run
# -- a test that cannot be imported asserts nothing at all. This is the same
# bootstrap test_capability_composer_v1.py already uses.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

from m1b_smooth_surface_compiler import compile_source


def run_contract(contract):
    out=compile_source(contract)
    if out["status"]!="COMPILED":
        return out,None
    ns={}
    exec(compile(out["source"],"<generated-smooth-cad>","exec"),ns,ns)
    return out,ns["result"]


class M1BSmoothSurfaceCompilerTests(unittest.TestCase):
    def test_spline_revolve_builds_one_smooth_solid(self):
        out,result=run_contract({
            "kind":"spline_revolve",
            "radial_axial_points":[
                [5.0,0.0],
                [8.0,5.0],
                [6.0,10.0],
                [4.0,15.0],
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        self.assertEqual(len(result.solids().vals()),1)
        bb=result.val().BoundingBox()
        self.assertGreater(bb.xlen,14.0)
        self.assertAlmostEqual(bb.ylen,15.0,places=5)

    def test_circle_loft_builds_smooth_variable_radius_solid(self):
        out,result=run_contract({
            "kind":"circle_loft",
            "sections":[
                {"z":0.0,"radius":4.0},
                {"z":5.0,"radius":7.0},
                {"z":12.0,"radius":3.0},
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        self.assertEqual(len(result.solids().vals()),1)
        bb=result.val().BoundingBox()
        self.assertAlmostEqual(bb.zlen,12.0,places=5)
        self.assertGreater(bb.xlen,13.0)

    def test_polygon_loft_builds_one_solid(self):
        out,result=run_contract({
            "kind":"polygon_loft",
            "sections":[
                {"z":0.0,"points":[[-4,-4],[4,-4],[4,4],[-4,4]]},
                {"z":6.0,"points":[[-6,-3],[6,-3],[6,3],[-6,3]]},
                {"z":10.0,"points":[[-3,-2],[3,-2],[3,2],[-3,2]]},
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        self.assertEqual(len(result.solids().vals()),1)
        self.assertAlmostEqual(result.val().BoundingBox().zlen,10.0,places=5)

    def test_nonmonotonic_spline_axis_fails_closed(self):
        out,_=run_contract({
            "kind":"spline_revolve",
            "radial_axial_points":[[5,0],[6,5],[4,4]],
        })
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_unknown_surface_kind_fails_closed(self):
        out,_=run_contract({"kind":"magic_surface"})
        self.assertEqual(out["status"],"FAIL_CLOSED")


if __name__=="__main__":
    unittest.main()
