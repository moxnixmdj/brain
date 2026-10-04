from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as mm


class MysteryMechanismSparseSymbolicAdapterV2Tests(unittest.TestCase):
    def test_fresh_exponential_feature(self):
        rows=[{"x":x,"out":1.2+0.7*math.exp(x)}
              for x in (-1.2,-0.7,-0.2,0.15,0.45,0.8,1.1)]
        out=mm.sparse_discover(rows,target="out",max_depth=1)
        self.assertEqual(out["status"],"SPARSE_CANDIDATES_FOUND",out)
        self.assertLess(out["best_candidate"]["loo_nrmse"],1e-8,out["best_candidate"])
        self.assertIn("exp(", mm._sparse_expr(out["best_candidate"]))

    def test_fresh_trigonometric_feature(self):
        rows=[{"angle":x,"out":-0.4+2.3*math.sin(x)}
              for x in (-1.0,-0.6,-0.15,0.2,0.55,0.9,1.25)]
        out=mm.sparse_discover(rows,target="out",max_depth=1)
        self.assertLess(out["best_candidate"]["loo_nrmse"],1e-8,out["best_candidate"])
        self.assertIn("sin(", mm._sparse_expr(out["best_candidate"]))

    def test_exact_safe_division_feature(self):
        points=[(1.0,0.7),(2.0,1.4),(3.0,0.9),(4.0,2.2),(5.0,1.1),(6.0,3.4),(7.0,2.7)]
        rows=[{"x":x,"z":z,"out":2.0+5.0*x/z} for x,z in points]
        out=mm.sparse_discover(rows,target="out",max_depth=1)
        self.assertLess(out["best_candidate"]["loo_nrmse"],1e-8,out["best_candidate"])
        self.assertIn("/(", mm._sparse_expr(out["best_candidate"]))

    def test_reciprocal_feature(self):
        rows=[{"x":x,"out":3.0+4.0/x} for x in (0.4,0.7,1.1,1.8,2.6,3.5,4.8)]
        out=mm.sparse_discover(rows,target="out",max_depth=1)
        self.assertLess(out["best_candidate"]["loo_nrmse"],1e-8,out["best_candidate"])

    def test_exp_domain_guard_fails_feature_not_runtime(self):
        rows=[{"x":x,"out":x*x} for x in (-100.0,-3.0,-1.0,1.0,3.0,10.0,100.0)]
        out=mm.sparse_discover(rows,target="out",max_depth=1)
        self.assertEqual(out["status"],"SPARSE_CANDIDATES_FOUND")
        self.assertTrue(math.isfinite(out["best_candidate"]["loo_nrmse"]))

    def test_v1_budget_and_zero_credit_invariants_preserved(self):
        plan=mm.plan_experiments({"x1":[0.1,10000],"x2":[0.001,0.5]})
        self.assertEqual(plan["active_budget"],5)
        self.assertEqual(len(plan["initial_experiments"])+plan["reserved_count"],5)
        rows=[{"x":x,"out":2*x+1} for x in (1,2,3,4,5)]
        out=mm.solve(rows,bounds={"x":[1,5]},target="out")
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
