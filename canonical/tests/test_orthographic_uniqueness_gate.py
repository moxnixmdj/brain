import unittest

from canonical.runtime.orthographic_uniqueness_gate import (
    analyze_orthographic_uniqueness,
    unique_voxel_solution,
)
from canonical.runtime.orthographic_visual_hull import VisualHullError


class OrthographicUniquenessTests(unittest.TestCase):
    def test_single_voxel_is_unique(self):
        r = analyze_orthographic_uniqueness([[1]], [[1]], [[1]])
        self.assertTrue(r.consistent)
        self.assertTrue(r.unique)
        self.assertEqual(r.status, "UNIQUE")
        self.assertEqual(r.possible_voxels, 1)
        self.assertEqual(r.forced_voxels, 1)
        self.assertEqual(r.ambiguous_voxels, 0)

    def test_full_two_cube_is_ambiguous(self):
        top = [[1, 1], [1, 1]]
        front = [[1, 1], [1, 1]]
        right = [[1, 1], [1, 1]]
        r = analyze_orthographic_uniqueness(top, front, right)
        self.assertTrue(r.consistent)
        self.assertFalse(r.unique)
        self.assertEqual(r.status, "AMBIGUOUS")
        self.assertGreater(r.ambiguous_voxels, 0)
        self.assertIsNotNone(r.witness_removed_voxel)

    def test_inconsistent_views_fail_closed(self):
        r = analyze_orthographic_uniqueness([[1]], [[0]], [[1]])
        self.assertFalse(r.consistent)
        self.assertFalse(r.unique)
        self.assertEqual(r.status, "INCONSISTENT")
        self.assertTrue(r.unsupported_projection_pixels)
        with self.assertRaises(VisualHullError):
            unique_voxel_solution([[1]], [[0]], [[1]])

    def test_unique_solver_returns_grid(self):
        grid = unique_voxel_solution([[1]], [[1]], [[1]])
        self.assertEqual(grid, [[[True]]])

    def test_ambiguous_solver_rejects(self):
        top = [[1, 1], [1, 1]]
        front = [[1, 1], [1, 1]]
        right = [[1, 1], [1, 1]]
        with self.assertRaises(VisualHullError):
            unique_voxel_solution(top, front, right)


if __name__ == "__main__":
    unittest.main()
