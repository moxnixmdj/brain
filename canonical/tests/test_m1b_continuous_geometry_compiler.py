import math
import unittest

from m1b_continuous_geometry_compiler import compile_contract
from cad_partspec_generator import normalize_to_mm, spec_to_code


def execute_spec(spec):
    source=spec_to_code(spec)
    ns={}
    exec(compile(source,"<generated-cad>","exec"),ns,ns)
    return source,ns["result"]


class M1BContinuousGeometryCompilerTests(unittest.TestCase):
    def test_arc_profile_builds_real_continuous_solid(self):
        out=compile_contract({
            "units":"mm",
            "geometry":{
                "kind":"profile_extrude",
                "start":[0,0],
                "segments":[
                    {"kind":"line","end":[20,0]},
                    {"kind":"arc","mid":[25,5],"end":[20,10]},
                    {"kind":"line","end":[0,10]},
                    {"kind":"line","end":[0,0]},
                ],
                "depth":5.0,
            },
            "dimensions":[
                {"name":"overall_depth","nominal":5.0,"tol_plus":0.001,"tol_minus":0.001}
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        source,result=execute_spec(out["partspec"])
        self.assertIn("threePointArc",source)
        solids=result.solids().vals()
        self.assertEqual(len(solids),1)
        bb=result.val().BoundingBox()
        self.assertAlmostEqual(bb.zlen,5.0,places=6)
        self.assertGreater(bb.xlen,20.0)

    def test_revolved_steps_execute(self):
        out=compile_contract({
            "geometry":{
                "kind":"revolved_steps",
                "segments":[
                    {"z_start":0.0,"z_end":8.0,"outer_diameter":20.0},
                    {"z_start":8.0,"z_end":15.0,"outer_diameter":12.0,"inner_diameter":4.0},
                ]
            }
        })
        self.assertEqual(out["status"],"COMPILED")
        _,result=execute_spec(out["partspec"])
        self.assertEqual(len(result.solids().vals()),1)
        bb=result.val().BoundingBox()
        self.assertAlmostEqual(bb.zlen,15.0,places=6)
        self.assertAlmostEqual(bb.xlen,20.0,places=6)

    def test_multibody_sphere_cylinder_continuous_surfaces_execute(self):
        out=compile_contract({
            "geometry":{
                "kind":"multibody",
                "bodies":[
                    {"shape":"box","operation":"add","x":0,"y":0,"z":0,"dx":20,"dy":20,"dz":5},
                    {"shape":"cylinder","operation":"add","x":10,"y":10,"z":5,"diameter":8,"length":10,"axis":"z"},
                    {"shape":"sphere","operation":"add","x":10,"y":10,"z":15,"diameter":8},
                ]
            }
        })
        self.assertEqual(out["status"],"COMPILED")
        _,result=execute_spec(out["partspec"])
        self.assertEqual(len(result.solids().vals()),1)

    def test_submillimetre_tolerance_preserved_without_quantization(self):
        out=compile_contract({
            "units":"mm",
            "geometry":{"kind":"circle_extrude","diameter":10.0004,"depth":2.0003},
            "dimensions":[
                {"name":"overall_depth","nominal":2.0003,"tol_plus":0.0002,"tol_minus":0.0001},
                {"name":"overall_diameter","nominal":10.0004,"tol_plus":0.00005,"tol_minus":0.00007},
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        iv=out["dimension_intervals"]
        self.assertAlmostEqual(iv["overall_depth"]["lower"],2.0002,places=12)
        self.assertAlmostEqual(iv["overall_depth"]["upper"],2.0005,places=12)
        self.assertAlmostEqual(iv["overall_diameter"]["lower"],10.00033,places=12)
        self.assertAlmostEqual(iv["overall_diameter"]["upper"],10.00045,places=12)
        source,result=execute_spec(out["partspec"])
        bb=result.val().BoundingBox()
        self.assertAlmostEqual(bb.zlen,2.0003,places=6)
        self.assertAlmostEqual(bb.xlen,10.0004,places=6)

    def test_inch_tolerances_normalize_to_mm_exact_scale(self):
        out=compile_contract({
            "units":"in",
            "geometry":{"kind":"circle_extrude","diameter":1.0,"depth":0.25},
            "dimensions":[
                {"name":"overall_depth","nominal":0.25,"tol_plus":0.001,"tol_minus":0.002}
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        mm=normalize_to_mm(out["partspec"])
        d=mm.dimensions[0]
        self.assertAlmostEqual(d.nominal,6.35,places=12)
        self.assertAlmostEqual(d.tol_plus,0.0254,places=12)
        self.assertAlmostEqual(d.tol_minus,0.0508,places=12)

    def test_unidentified_geometry_kind_fails_closed(self):
        out=compile_contract({"geometry":{"kind":"mystery_nurbs"}})
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any("unsupported geometry kind" in e for e in out["errors"]))


if __name__=="__main__":
    unittest.main()
