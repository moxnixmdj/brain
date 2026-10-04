from __future__ import annotations

import math
import unittest

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v2 as s


class ZeroLearnedExpressionTreeV2Tests(unittest.TestCase):
    def test_public_mysterymechanism_viscosity_shape_recovered(self):
        rows=[
            {"x1":0.5944,"x2":1.9188,"out":12.2245},
            {"x1":0.5044,"x2":0.2068,"out":10.3732},
            {"x1":0.05,"x2":0.05,"out":4.3715},
            {"x1":0.70,"x2":0.05,"out":30.6686},
            {"x1":0.05,"x2":30.0,"out":2.3912},
            {"x1":0.70,"x2":30.0,"out":16.3743},
            {"x1":0.375,"x2":1.225,"out":5.7241},
        ]
        d=s.discover(
            rows,target="out",
            bounds={"x1":[0.05,0.70],"x2":[0.05,30.0]},
        )
        best=d["candidates"][0]
        self.assertLess(best["nrmse"],0.03)
        self.assertEqual(d["persistent_learned_bytes"],0)
        self.assertEqual(d["external_learned_capability_calls"],0)
        self.assertFalse(d["fresh_reality_authority"])

    def test_public_mysterymechanism_churchill_bernstein_shape_recovered(self):
        rows=[
            {"x1":63.5657,"x2":1.2799,"out":3.3766},
            {"x1":4615.6906,"x2":5.3388,"out":76.4846},
            {"x1":1.0,"x2":0.2,"out":0.1004},
            {"x1":300000.0,"x2":0.2,"out":277.5832},
            {"x1":1.0,"x2":10.0,"out":-1.18},
            {"x1":300000.0,"x2":10.0,"out":1263.4885},
            {"x1":547.7226,"x2":1.4142,"out":13.5045},
        ]
        d=s.discover(
            rows,target="out",
            bounds={"x1":[1.0,300000.0],"x2":[0.2,10.0]},
        )
        best=d["candidates"][0]
        self.assertLess(best["nrmse"],0.03)
        self.assertEqual(d["robust_fit_row_count"],6)

    def test_public_stream_power_shape_does_not_regress(self):
        rows=[
            {"x1":25.5646,"x2":0.1859,"out":0.0012396},
            {"x1":0.1108,"x2":0.0187,"out":-0.0000064},
            {"x1":100.0,"x2":0.05,"out":0.0008841},
            {"x1":10000.0,"x2":0.05,"out":0.0082336},
            {"x1":100.0,"x2":0.5,"out":0.0049850},
            {"x1":10000.0,"x2":0.5,"out":0.0454408},
            {"x1":1000.0,"x2":0.2,"out":0.0078693},
        ]
        d=s.discover(
            rows,target="out",
            bounds={"x1":[0.1,10000.0],"x2":[0.001,0.5]},
        )
        self.assertLess(d["candidates"][0]["nrmse"],0.03)

    def test_exact_synthetic_nested_correction_generalizes(self):
        def law(x,z):
            return (
                2.3
                + 4.7
                * x**0.5
                * (1+(x/940.0)**0.625)**0.8
                * z**(1.0/3.0)
                / (1+(0.4/z)**(2.0/3.0))**0.25
            )
        points=[
            (7.0,0.7),(120.0,3.0),
            (1.0,0.2),(1000.0,0.2),(1.0,10.0),(1000.0,10.0),
            (math.sqrt(1000.0),math.sqrt(2.0)),
            (15.0,0.35),(350.0,7.0),
        ]
        rows=[{"u":x,"v":z,"out":law(x,z)} for x,z in points]
        d=s.discover(
            rows,target="out",
            bounds={"u":[1.0,1000.0],"v":[0.2,10.0]},
        )
        best=d["candidates"][0]
        self.assertEqual(best["family"],"separable_bilinear_tree")
        self.assertLess(best["nrmse"],1e-7)
        self.assertLess(best["loo_nrmse"],1e-6)
        j=s.judge(d,fit_threshold=1e-6,loo_threshold=1e-5)
        self.assertEqual(j["status"],"IDENTIFIED_CANDIDATE_UNVERIFIED")

    def test_public_contract_budget_remains_exact_2d_plus_1(self):
        from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as v1
        p=v1.design_initial_probes({"x1":[0.05,0.7],"x2":[0.05,30.0]})
        self.assertEqual(p["budget"],5)
        self.assertEqual(len(p["points"]),5)

    def test_nonfinite_input_fails_closed(self):
        rows=[
            {"x1":float(i),"x2":float(i+1),"out":float(i*i)}
            for i in range(1,8)
        ]
        rows[3]["x2"]=math.inf
        with self.assertRaises(Exception):
            s.discover(rows,target="out")

    def test_out_of_grammar_sine_is_not_accepted(self):
        rows=[
            {"x1":x/5.0,"x2":z/7.0,"out":math.sin(x/5.0)+math.cos(z/7.0)}
            for x,z in zip(range(1,25),range(25,1,-1))
        ]
        d=s.discover(rows,target="out")
        j=s.judge(d,fit_threshold=0.01,loo_threshold=0.03)
        self.assertEqual(j["status"],"EXPAND_MECHANISM_LANGUAGE")


if __name__=="__main__":
    unittest.main(verbosity=2)
