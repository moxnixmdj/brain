import random
import unittest

from canonical.runtime.orthographic_visual_hull import (
    VisualHullError,
    accept_candidate_orthographic_shape,
    hull_signature,
    infer_visual_hull_repairs,
    project_visual_hull,
    reconstruct_visual_hull,
)


class VisualHullTests(unittest.TestCase):
    def test_full_box_reconstructs_exactly(self):
        top = [[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
        front = [[1, 1, 1, 1], [1, 1, 1, 1]]
        right = [[1, 1, 1], [1, 1, 1]]
        vox = reconstruct_visual_hull(top, front, right)
        sig = hull_signature(vox)
        self.assertEqual(sig.occupied_voxels, 24)
        self.assertEqual(sig.bbox_cells, (4, 3, 2))
        self.assertEqual(sig.connected_components, 1)
        self.assertEqual(
            project_visual_hull(vox),
            (
                [[True] * 4 for _ in range(3)],
                [[True] * 4 for _ in range(2)],
                [[True] * 3 for _ in range(2)],
            ),
        )

    def test_top_visible_through_feature_removes_column(self):
        top = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
        front = [[1, 1, 1], [1, 1, 1]]
        right = [[1, 1, 1], [1, 1, 1]]
        vox = reconstruct_visual_hull(top, front, right)
        self.assertFalse(vox[0][1][1])
        self.assertFalse(vox[1][1][1])
        self.assertEqual(hull_signature(vox).occupied_voxels, 16)

    def test_candidate_global_overbuild_is_rejected(self):
        source_top = [[1, 1, 1, 0], [1, 1, 1, 0], [1, 1, 1, 0]]
        source_front = [[1, 1, 1, 0], [1, 1, 1, 0]]
        source_right = [[1, 1, 1], [1, 1, 1]]
        cand_top = [[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
        cand_front = [[1, 1, 1, 1], [1, 1, 1, 1]]
        cand_right = [[1, 1, 1], [1, 1, 1]]
        report = accept_candidate_orthographic_shape(
            source_top,
            source_front,
            source_right,
            cand_top,
            cand_front,
            cand_right,
            min_iou=0.95,
        )
        self.assertFalse(report.passed)
        self.assertTrue(
            any("overbuild" in reason or "bbox" in reason for reason in report.reasons)
        )

    def test_exact_candidate_passes(self):
        top = [[1, 1, 0], [1, 1, 0]]
        front = [[1, 1, 0], [1, 1, 0]]
        right = [[1, 1], [1, 1]]
        report = accept_candidate_orthographic_shape(
            top, front, right, top, front, right
        )
        self.assertTrue(report.passed)
        self.assertEqual(report.reasons, ())

    def test_underbuild_becomes_rectangular_add_region(self):
        source_top = [[1, 1, 1], [1, 1, 1]]
        source_front = [[1, 1, 1], [1, 1, 1]]
        source_right = [[1, 1], [1, 1]]
        cand_top = [[1, 1, 0], [1, 1, 0]]
        cand_front = [[1, 1, 0], [1, 1, 0]]
        cand_right = [[1, 1], [1, 1]]
        repairs = infer_visual_hull_repairs(
            source_top,
            source_front,
            source_right,
            cand_top,
            cand_front,
            cand_right,
        )
        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0].operation, "add")
        self.assertTrue(repairs[0].rectangular)
        self.assertEqual(repairs[0].bbox_min, (2, 0, 0))
        self.assertEqual(repairs[0].bbox_max_exclusive, (3, 2, 2))

    def test_overbuild_becomes_rectangular_cut_region(self):
        source_top = [[1, 1, 0], [1, 1, 0]]
        source_front = [[1, 1, 0], [1, 1, 0]]
        source_right = [[1, 1], [1, 1]]
        cand_top = [[1, 1, 1], [1, 1, 1]]
        cand_front = [[1, 1, 1], [1, 1, 1]]
        cand_right = [[1, 1], [1, 1]]
        repairs = infer_visual_hull_repairs(
            source_top,
            source_front,
            source_right,
            cand_top,
            cand_front,
            cand_right,
        )
        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0].operation, "cut")
        self.assertTrue(repairs[0].rectangular)
        self.assertEqual(repairs[0].bbox_min, (2, 0, 0))

    def test_randomized_differential_reconstruction_1000(self):
        rng = random.Random(20261002)
        for _ in range(1000):
            x = rng.randint(1, 6)
            y = rng.randint(1, 6)
            z = rng.randint(1, 6)
            top = [[rng.random() < 0.65 for _ in range(x)] for _ in range(y)]
            front = [[rng.random() < 0.65 for _ in range(x)] for _ in range(z)]
            right = [[rng.random() < 0.65 for _ in range(y)] for _ in range(z)]
            got = reconstruct_visual_hull(top, front, right)
            expected = [
                [
                    [
                        bool(top[yy][xx] and front[zz][xx] and right[zz][yy])
                        for xx in range(x)
                    ]
                    for yy in range(y)
                ]
                for zz in range(z)
            ]
            self.assertEqual(got, expected)
            pt, pf, pr = project_visual_hull(got)
            for yy in range(y):
                for xx in range(x):
                    self.assertFalse(pt[yy][xx] and not top[yy][xx])
            for zz in range(z):
                for xx in range(x):
                    self.assertFalse(pf[zz][xx] and not front[zz][xx])
            for zz in range(z):
                for yy in range(y):
                    self.assertFalse(pr[zz][yy] and not right[zz][yy])

    def test_randomized_repair_partition_500(self):
        rng = random.Random(9917)
        for _ in range(500):
            x = rng.randint(1, 5)
            y = rng.randint(1, 5)
            z = rng.randint(1, 5)
            st = [[rng.random() < 0.7 for _ in range(x)] for _ in range(y)]
            sf = [[rng.random() < 0.7 for _ in range(x)] for _ in range(z)]
            sr = [[rng.random() < 0.7 for _ in range(y)] for _ in range(z)]
            ct = [[rng.random() < 0.7 for _ in range(x)] for _ in range(y)]
            cf = [[rng.random() < 0.7 for _ in range(x)] for _ in range(z)]
            cr = [[rng.random() < 0.7 for _ in range(y)] for _ in range(z)]
            repairs = infer_visual_hull_repairs(st, sf, sr, ct, cf, cr)
            src = reconstruct_visual_hull(st, sf, sr)
            cand = reconstruct_visual_hull(ct, cf, cr)
            src_n = sum(v for slab in src for row in slab for v in row)
            cand_n = sum(v for slab in cand for row in slab for v in row)
            adds = sum(r.voxel_count for r in repairs if r.operation == "add")
            cuts = sum(r.voxel_count for r in repairs if r.operation == "cut")
            self.assertEqual(cand_n + adds - cuts, src_n)
            self.assertTrue(all(0 < r.fill_ratio <= 1 for r in repairs))

    def test_dimension_mismatch_fails_closed(self):
        with self.assertRaises(VisualHullError):
            reconstruct_visual_hull([[1, 1]], [[1, 1, 1]], [[1]])


if __name__ == "__main__":
    unittest.main()

# candidate verifier trigger is branch-scoped; test content unchanged
