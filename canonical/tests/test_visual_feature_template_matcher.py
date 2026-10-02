import unittest

import cv2
import numpy as np

from canonical.runtime.visual_feature_template_matcher import match_feature_template


def textured(seed: int, size: int = 96) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 235, dtype=np.uint8)
    for _ in range(70):
        x = int(rng.integers(6, size - 6))
        y = int(rng.integers(6, size - 6))
        radius = int(rng.integers(1, 4))
        tone = int(rng.integers(0, 170))
        cv2.circle(img, (x, y), radius, tone, -1)
    cv2.rectangle(img, (8, 8), (size - 9, size - 9), 40, 2)
    cv2.line(img, (10, size - 20), (size - 15, 14), 80, 2)
    cv2.putText(img, str(seed % 100), (22, 58), cv2.FONT_HERSHEY_SIMPLEX, 1.1, 20, 2, cv2.LINE_AA)
    return img


def warp_into_scene(template: np.ndarray) -> np.ndarray:
    scene = np.full((280, 320), 245, dtype=np.uint8)
    h, w = template.shape
    src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    dst = np.float32([[74, 62], [222, 48], [238, 196], [60, 210]])
    H = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(template, H, (scene.shape[1], scene.shape[0]), borderValue=245)
    mask = cv2.warpPerspective(np.full_like(template, 255), H, (scene.shape[1], scene.shape[0]), borderValue=0)
    scene[mask > 0] = warped[mask > 0]
    return scene


class Tests(unittest.TestCase):
    def test_matches_jit_template_under_perspective_scale_and_rotation(self):
        target = textured(7)
        distractor = textured(19)
        scene = warp_into_scene(target)
        out = match_feature_template(
            scene,
            {"target-symbol": target, "other-symbol": distractor},
            min_good_matches=8,
            min_inliers=7,
            min_inlier_ratio=0.35,
            min_inlier_margin=2,
        )
        self.assertEqual(out["status"], "MATCHED", out)
        self.assertEqual(out["symbol_id"], "target-symbol")
        self.assertGreaterEqual(out["inliers"], 7)
        self.assertFalse(out["semantic_authority"])

    def test_duplicate_reference_is_ambiguous(self):
        target = textured(11)
        scene = warp_into_scene(target)
        out = match_feature_template(
            scene,
            {"a": target, "b": target.copy()},
            min_good_matches=8,
            min_inliers=7,
            min_inlier_ratio=0.35,
            min_inlier_margin=2,
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertEqual(out["error"], "AMBIGUOUS_FEATURE_MATCH")

    def test_blank_scene_fails_closed(self):
        blank = np.full((160, 160), 255, dtype=np.uint8)
        out = match_feature_template(blank, {"x": textured(3)})
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertEqual(out["error"], "SCENE_FEATURES_INSUFFICIENT")

    def test_unrelated_template_does_not_gain_semantic_authority(self):
        scene = warp_into_scene(textured(4))
        out = match_feature_template(
            scene,
            {"wrong": textured(99)},
            min_good_matches=10,
            min_inliers=9,
            min_inlier_ratio=0.55,
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_invalid_template_fails_closed(self):
        scene = warp_into_scene(textured(4))
        bad = np.zeros((10, 10, 3), dtype=np.uint8)
        out = match_feature_template(scene, {"bad": bad})
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertEqual(out["error"], "INVALID_TEMPLATE")

    def test_invalid_threshold_fails_closed(self):
        scene = warp_into_scene(textured(4))
        out = match_feature_template(scene, {"x": textured(4)}, ratio_test=1.1)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertEqual(out["error"], "RATIO_TEST_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
