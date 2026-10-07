import unittest
from canonical.runtime.terminal_v9_29_surface_factorizer_v1 import (
    ABC, D, ATOMIC, META, factorize,
)

class TestTerminalV929SurfaceFactorizer(unittest.TestCase):
    def test_exact_29_unique_rows(self):
        r=factorize()
        self.assertEqual(r["truth_row_count"],29)
        self.assertEqual(r["unique_truth_row_count"],29)
        self.assertEqual(len(ATOMIC),21)
        self.assertEqual(len(META),8)

    def test_every_row_maps_to_abc(self):
        r=factorize()
        self.assertEqual(r["abc_mapped_row_count"],29)
        self.assertEqual(r["unmapped_rows"],[])
        for surfaces in r["v9_row_surfaces"].values():
            self.assertIn(ABC,surfaces)

    def test_no_semantic_row_deleted(self):
        r=factorize()
        self.assertEqual(r["semantic_rows_deleted"],0)
        self.assertEqual(r["rows_reclassified_from_primitive_to_surface_slices"],29)

    def test_authority_overlap_is_conservative(self):
        r=factorize()
        self.assertIn(D,r["v9_row_surfaces"]["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"])
        self.assertEqual(r["d_overlap_row_count"],1)

    def test_v9_surface_count_is_two(self):
        r=factorize()
        self.assertEqual(r["v9_primitive_proof_surface_count"],2)
        self.assertEqual(set(r["v9_surfaces"]),{ABC,D})

if __name__=="__main__":
    unittest.main()
