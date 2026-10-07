import unittest
from canonical.runtime.v9_abc_residual_role_matrix_v1 import (
    B0,B1,B2,B4,B7,D,ATOMIC,META,ROWS,compile_matrix,
)

class TestV9ABCResidualRoleMatrix(unittest.TestCase):
    def test_exact_canonical_29(self):
        out=compile_matrix()
        self.assertEqual(out["truth_row_count"],29)
        self.assertEqual(len(ATOMIC),21)
        self.assertEqual(len(META),8)
        self.assertEqual(len(ROWS),29)

    def test_five_active_roles_only(self):
        out=compile_matrix()
        self.assertEqual(set(out["active_abc_roles"]),{B0,B1,B2,B4,B7})
        self.assertEqual(out["active_role_count"],5)

    def test_every_row_has_active_abc_role_or_conservative_overlap(self):
        for row,roles in ROWS.items():
            self.assertTrue(set(roles)&{B0,B1,B2,B4,B7},row)

    def test_shared_reach_counts(self):
        out=compile_matrix()
        self.assertEqual(out["role_row_counts"],{
            B0:9,B1:11,B2:20,B4:14,B7:9,
        })
        self.assertEqual(out["priority_order_by_shared_row_reach"][0],B2)

    def test_only_authority_row_overlaps_d(self):
        out=compile_matrix()
        self.assertEqual(out["d_overlap_rows"],["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"])
        self.assertEqual(out["d_overlap_count"],1)

    def test_no_semantic_deletion(self):
        self.assertEqual(compile_matrix()["semantic_rows_deleted"],0)

if __name__=="__main__":
    unittest.main()
