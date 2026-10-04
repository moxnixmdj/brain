from __future__ import annotations

import json
import unittest

from canonical.runtime.h100_zero_learned_primitive_repair_v1 import PHASE2
from canonical.runtime.h100_zero_learned_parametric_unary_v1 import ParametricUnaryError, discover


class H100ZeroLearnedPrimitiveRepairTests(unittest.TestCase):
    def test_phase2_is_frozen_to_exact_three_phase1_failures(self):
        d=json.loads(PHASE2.read_text())
        self.assertEqual(d["status"],"FROZEN_BEFORE_REPAIR_OUTCOMES__PHASE2__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT")
        self.assertEqual([x["task_id"] for x in d["tasks"]],["PERIODIC_SINE","EXPONENTIAL","SIGN_STEP"])
        self.assertEqual(d["immutable_outcome_definition"]["holdout_nrmse_max"],1e-7)
        self.assertEqual(d["immutable_outcome_definition"]["solver_internal_nrmse_max"],1e-8)

    def test_route_rejects_multivariable_input(self):
        rows=[
            {"x":float(i),"z":float(i+1),"y":float(i)}
            for i in range(8)
        ]
        with self.assertRaises(ParametricUnaryError):
            discover(rows,target="y")

    def test_phase2_route_is_zero_learned_by_contract(self):
        d=json.loads(PHASE2.read_text())
        r=d["new_route"]
        self.assertEqual(r["persistent_learned_bytes"],0)
        self.assertEqual(r["external_learned_capability_calls"],0)
        self.assertFalse(r["random_search"])


if __name__=="__main__":
    unittest.main(verbosity=2)
