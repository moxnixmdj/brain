from __future__ import annotations
import unittest
from canonical.runtime.escape_o10_minimum_delta_family_projection_v1 import compile_projection

class ProjectionTests(unittest.TestCase):
    def test_current_o10_exact_three_family_partition(self):
        out=compile_projection()
        self.assertEqual(out["active_o_row_count"],10)
        self.assertEqual(out["minimum_delta_family_count"],3)
        self.assertEqual(sum(x["row_count"] for x in out["families"]),10)
        ids=[r["obligation_id"] for f in out["families"] for r in f["rows"]]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(
            {f["family_id"]:f["row_count"] for f in out["families"]},
            {"OWNER_OR_EVALUATOR_INTERFACE":3,"SCOPE_COMPLETENESS":4,"THRESHOLD_OR_DECOMPOSITION_EVIDENCE":3},
        )

    def test_zero_authority(self):
        out=compile_projection()
        for k in ("execution_authority","promotion_authority","acceptance_authority","ownership_authority","terminal_authority"):
            self.assertFalse(out[k])
        self.assertFalse(out["new_primitive_required"])
        self.assertEqual(out["accounting"]["incremental_spend_usd"],0)
        self.assertEqual(out["accounting"]["acceptance_credit_delta"],0)
        self.assertEqual(out["accounting"]["capability_credit_delta"],0)
        self.assertEqual(out["accounting"]["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
