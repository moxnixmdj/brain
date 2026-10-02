"""Feature-based visual template grounding with fail-closed ambiguity handling.

Reference templates are external/JIT knowledge. Matching capability is Brain-owned and
generic. This complements exact correlation matching by tolerating scale, rotation,
and moderate perspective change using ORB features plus RANSAC homography.

No semantic meaning is invented: the returned symbol_id is only the identity attached
to the supplied reference template. Low-support, geometrically invalid, or ambiguous
matches fail closed.
"""
from __future__ import annotations

from typing import Any, Mapping
import math

import cv2
import numpy as np

SCHEMA = "BRAIN_VISUAL_FEATURE_TEMPLATE_MATCHER_V1"


def _valid_image(img: Any) -> bool:
    return (
        isinstance(img, np.ndarray)
        and img.ndim == 2
        and img.dtype == np.uint8
        and img.size > 0
        and img.shape[0] >= 24
        and img.shape[1] >= 24
    )


def _features(img: np.ndarray):
    orb = cv2.ORB_create(
        nfeatures=1600,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=12,
        patchSize=31,
        fastThreshold=5,
    )
    return orb.detectAndCompute(img, None)


def _quad_area(points: np.ndarray) -> float:
    pts = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    if pts.shape != (4, 2) or not np.all(np.isfinite(pts)):
        return 0.0
    return float(abs(cv2.contourArea(pts)))


def match_feature_template(
    image: np.ndarray,
    templates: Mapping[str, np.ndarray],
    *,
    ratio_test: float = 0.75,
    ransac_reproj_threshold: float = 4.0,
    min_good_matches: int = 10,
    min_inliers: int = 8,
    min_inlier_ratio: float = 0.45,
    min_inlier_margin: int = 3,
) -> dict[str, Any]:
    if not _valid_image(image):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "SCENE_IMAGE_INVALID"}
    if not isinstance(templates, Mapping) or not templates:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NO_TEMPLATES"}
    if not (0.5 <= ratio_test < 1.0):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "RATIO_TEST_INVALID"}
    if not (isinstance(ransac_reproj_threshold, (int, float)) and math.isfinite(float(ransac_reproj_threshold)) and ransac_reproj_threshold > 0):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "RANSAC_THRESHOLD_INVALID"}
    for name, value in (
        ("min_good_matches", min_good_matches),
        ("min_inliers", min_inliers),
        ("min_inlier_margin", min_inlier_margin),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": f"{name.upper()}_INVALID"}
    if not (0.0 < min_inlier_ratio <= 1.0):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "MIN_INLIER_RATIO_INVALID"}

    scene_kp, scene_desc = _features(image)
    if scene_desc is None or scene_kp is None or len(scene_kp) < min_good_matches:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "SCENE_FEATURES_INSUFFICIENT",
            "scene_keypoints": 0 if scene_kp is None else len(scene_kp),
        }

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    candidates: list[dict[str, Any]] = []

    for symbol_id, template in templates.items():
        if not isinstance(symbol_id, str) or not symbol_id.strip() or not _valid_image(template):
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "INVALID_TEMPLATE"}

        tpl_kp, tpl_desc = _features(template)
        if tpl_desc is None or tpl_kp is None or len(tpl_kp) < min_good_matches:
            continue

        try:
            pairs = matcher.knnMatch(tpl_desc, scene_desc, k=2)
        except cv2.error:
            continue

        good = []
        for pair in pairs:
            if len(pair) != 2:
                continue
            m, n = pair
            if m.distance < ratio_test * n.distance:
                good.append(m)

        if len(good) < max(4, min_good_matches):
            continue

        src = np.float32([tpl_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([scene_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        try:
            homography, mask = cv2.findHomography(
                src,
                dst,
                cv2.RANSAC,
                float(ransac_reproj_threshold),
            )
        except cv2.error:
            continue

        if homography is None or mask is None or not np.all(np.isfinite(homography)):
            continue

        inliers = int(mask.ravel().sum())
        inlier_ratio = inliers / len(good)
        if inliers < min_inliers or inlier_ratio < min_inlier_ratio:
            continue

        h, w = template.shape
        corners = np.float32(
            [[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]]
        ).reshape(-1, 1, 2)
        try:
            projected = cv2.perspectiveTransform(corners, homography).reshape(4, 2)
        except cv2.error:
            continue

        area = _quad_area(projected)
        if area < 16.0:
            continue

        ih, iw = image.shape
        slack = 0.15 * max(ih, iw)
        xs = projected[:, 0]
        ys = projected[:, 1]
        if (
            np.min(xs) < -slack
            or np.max(xs) > iw - 1 + slack
            or np.min(ys) < -slack
            or np.max(ys) > ih - 1 + slack
        ):
            continue

        candidates.append(
            {
                "symbol_id": symbol_id,
                "good_matches": len(good),
                "inliers": inliers,
                "inlier_ratio": float(inlier_ratio),
                "projected_quad": [[float(x), float(y)] for x, y in projected],
                "area": area,
            }
        )

    if not candidates:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_GEOMETRICALLY_SUPPORTED_MATCH",
            "terminal_authority": False,
        }

    candidates.sort(
        key=lambda c: (
            -c["inliers"],
            -c["inlier_ratio"],
            -c["good_matches"],
            c["symbol_id"],
        )
    )
    best = candidates[0]

    if len(candidates) > 1:
        second = candidates[1]
        if best["inliers"] - second["inliers"] < min_inlier_margin:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "error": "AMBIGUOUS_FEATURE_MATCH",
                "best_symbol_id": best["symbol_id"],
                "best_inliers": best["inliers"],
                "second_symbol_id": second["symbol_id"],
                "second_inliers": second["inliers"],
                "terminal_authority": False,
            }

    return {
        "schema": SCHEMA,
        "status": "MATCHED",
        **best,
        "candidate_count": len(candidates),
        "semantic_authority": False,
        "knowledge_boundary": "SYMBOL_IDENTITY_COMES_ONLY_FROM_SUPPLIED_JIT_REFERENCE_TEMPLATE",
        "scope": "JIT_REFERENCE_VISUAL_IDENTITY_MATCHING_WITH_ORB_RANSAC_SCALE_ROTATION_PERSPECTIVE_TOLERANCE_AND_AMBIGUITY_GATE",
        "terminal_authority": False,
    }
