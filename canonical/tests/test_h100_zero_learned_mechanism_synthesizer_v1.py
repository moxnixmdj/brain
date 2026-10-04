from __future__ import annotations

import math
import unittest

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as s


class ZeroLearnedMechanismSynthesizerTests(unittest.TestCase):
    def test_square_law(self):
        rows=[{"a":x,"out":3*x*x+2} for x in range(1,13)]
        d=s.discover(rows,target="out")
        best=d["candidates"][0]
        self.assertEqual(best["family"],"monomial")
        self.assertEqual(best["structural_signature"],"identity|monomial|2")
        self.assertLess(best["nrmse"],1e-10)
        self.assertEqual(d["learned_parameter_bytes"],0)
        self.assertEqual(d["external_learned_capability_calls"],0)

    def test_multivariable_ratio_law(self):
        rows=[
            {"foo":x,"bar":z,"out":5*x*x/z+1}
            for x in [1,2,3,4]
            for z in [1,2,4]
        ]
        d=s.discover(rows,target="out")
        best=d["candidates"][0]
        self.assertEqual(best["feature_expression"],"bar^-1 * foo^2")
        self.assertLess(best["nrmse"],1e-10)

    def test_affine_linear_law(self):
        rows=[
            {"x":x,"z":z,"out":2*x-3*z+4}
            for x in [1,2,3,4,5]
            for z in [2,4,7]
        ]
        d=s.discover(rows,target="out")
        best=d["candidates"][0]
        self.assertEqual(best["family"],"linear")
        self.assertAlmostEqual(best["coefficients"][0],2,places=8)
        self.assertAlmostEqual(best["coefficients"][1],-3,places=8)
        self.assertAlmostEqual(best["intercept"],4,places=8)

    def test_fractional_power_law(self):
        rows=[{"x":x,"out":4*math.sqrt(x)+1} for x in [1,4,9,16,25,36,49,64]]
        d=s.discover(rows,target="out")
        best=d["candidates"][0]
        self.assertEqual(best["feature_expression"],"x^0.5")
        self.assertLess(best["nrmse"],1e-10)

    def test_surface_renaming_preserves_structural_signature(self):
        a=[
            {"foo":x,"bar":z,"out":5*x*x/z+1}
            for x in [1,2,3,4]
            for z in [1,2,4]
        ]
        b=[
            {"u":x,"v":z,"res":2*x*x/z-4}
            for x in [2,3,5,7]
            for z in [1,3,6]
        ]
        ca=s.discover(a,target="out")["candidates"][0]
        cb=s.discover(b,target="res")["candidates"][0]
        m=s.structural_match(ca,cb)
        self.assertTrue(m["match"])
        self.assertTrue(m["surface_variable_names_ignored"])

    def test_irrelevant_distractor_not_selected(self):
        rows=[
            {"x":x,"noise":((-1)**i)*(i+3),"out":7*x*x+1}
            for i,x in enumerate(range(1,13))
        ]
        d=s.discover(rows,target="out")
        self.assertEqual(d["candidates"][0]["feature_expression"],"x^2")

    def test_out_of_grammar_relation_fails_closed(self):
        rows=[{"x":x/3,"out":math.sin(x/3)} for x in range(1,25)]
        d=s.discover(rows,target="out")
        j=s.judge(d,rows)
        self.assertEqual(j["status"],"EXPAND_MECHANISM_LANGUAGE")
        self.assertIsNone(j["candidate"])

    def test_disagreement_generates_probe(self):
        c1={
            "family":"monomial","variables":["x"],"exponents":[1],
            "intercept":0,"scale":1,"target_transform":"identity","target_sign":1,
            "structural_signature":"identity|monomial|1",
        }
        c2={
            "family":"monomial","variables":["x"],"exponents":[2],
            "intercept":0,"scale":1,"target_transform":"identity","target_sign":1,
            "structural_signature":"identity|monomial|2",
        }
        p=s.propose_discriminator([c1,c2],[{"x":1},{"x":2},{"x":3},{"x":4},{"x":5}])
        self.assertEqual(p["status"],"DISCRIMINATOR_FOUND")
        self.assertGreater(p["disagreement"],0)

    def test_nonfinite_input_rejected(self):
        rows=[{"x":i,"out":float(i)} for i in range(1,6)]
        rows[2]["x"]=math.inf
        with self.assertRaises(s.MechanismSynthesisError):
            s.discover(rows,target="out")


if __name__=="__main__":
    unittest.main(verbosity=2)
