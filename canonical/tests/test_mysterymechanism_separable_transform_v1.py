from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_separable_transform_v1 as sep


class MysteryMechanismSeparableTransformTests(unittest.TestCase):
    def test_public_viscosity_example_functional_recovery_public_dev_only(self):
        rows=[
            {"x1":0.5944,"x2":1.9188,"out":12.2245},
            {"x1":0.5044,"x2":0.2068,"out":10.3732},
            {"x1":0.05,"x2":0.05,"out":4.3715},
            {"x1":0.70,"x2":0.05,"out":30.6686},
            {"x1":0.05,"x2":30.0,"out":2.3912},
            {"x1":0.70,"x2":30.0,"out":16.3743},
            {"x1":0.375,"x2":1.225,"out":5.7241},
        ]
        out=sep.discover(rows,bounds={"x1":[0.05,0.70],"x2":[0.05,30.0]},target="out",validation_index=-1)
        self.assertEqual(out["status"],"SEPARABLE_CANDIDATE_FOUND__PUBLIC_OR_SYNTHETIC_ONLY",out)
        c=out["candidate"]
        self.assertLess(max(c["fit_nrmse"],c["reserved_validation_nrmse"]),0.03,c)

        # The formula below is the explicitly public development example from
        # Vals, not a validation/test mechanism. It exists only in this test.
        def public_truth(x1,x2):
            return 1.7707*(1+0.9128*x1/(1-x1)**1.9124)*(1+1.6447/(1+math.sqrt(x2)))

        gold=[];pred=[]
        for i in range(9):
            x1=0.05+(0.70-0.05)*i/8
            for j in range(9):
                x2=0.05*((30.0/0.05)**(j/8))
                gold.append(public_truth(x1,x2))
                pred.append(sep.predict(c,{"x1":x1,"x2":x2}))
        mean=sum(gold)/len(gold)
        var=sum((y-mean)**2 for y in gold)/len(gold)
        nmse=sum((a-b)**2 for a,b in zip(gold,pred))/len(gold)/var
        self.assertLess(nmse,0.000697,(nmse,c))
        self.assertFalse(out["private_score_claimed"])
        self.assertEqual(out["acceptance_credit_delta"],0)

    def test_fresh_separable_structure_exact(self):
        def law(x,z):
            f=x/(1-x)**2
            g=1/(1+math.sqrt(z))
            return 1.2+2.5*f+1.7*g+3.1*f*g
        pts=[
            (0.22,2.3),(0.63,0.4),
            (0.05,0.1),(0.8,0.1),(0.05,20.0),(0.8,20.0),
            (0.425,math.sqrt(2.0)),
        ]
        rows=[{"x":x,"z":z,"out":law(x,z)} for x,z in pts]
        out=sep.discover(rows,bounds={"x":[0.05,0.8],"z":[0.1,20.0]},target="out")
        c=out["candidate"]
        self.assertLess(c["fit_nrmse"],1e-8,c)
        self.assertLess(c["reserved_validation_nrmse"],1e-8,c)
        for x,z in ((0.1,0.2),(0.3,1.7),(0.55,7.0),(0.75,16.0)):
            self.assertAlmostEqual(sep.predict(c,{"x":x,"z":z}),law(x,z),places=6)

    def test_boundary_anchors_are_outside_declared_interval(self):
        rows=[
            {"x":x,"z":z,"out":2*x+3*z}
            for x,z in ((1.2,2.2),(1.4,3.1),(1.0,2.0),(2.0,2.0),(1.0,4.0),(2.0,4.0),(1.5,3.0))
        ]
        out=sep.discover(rows,bounds={"x":[1.0,2.0],"z":[2.0,4.0]},target="out")
        c=out["candidate"]
        for d,b in ((c["left"],(1.0,2.0)),(c["right"],(2.0,4.0))):
            if "boundary" in d["kind"]:
                self.assertTrue(float(d["anchor"])<b[0] or float(d["anchor"])>b[1])

    def test_nonfinite_rejected(self):
        rows=[
            {"x":x,"z":z,"out":x+z}
            for x,z in ((1,1),(2,1),(1,2),(2,2),(1.5,1.2),(1.2,1.7),(1.4,1.4))
        ]
        rows[2]["x"]=math.inf
        with self.assertRaises(Exception):
            sep.discover(rows,bounds={"x":[1,2],"z":[1,2]},target="out")


if __name__=="__main__":
    unittest.main(verbosity=2)
