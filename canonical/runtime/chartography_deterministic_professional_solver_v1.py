from __future__ import annotations

import csv
import io
import math
import re
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

from canonical.runtime.bound_capabilities.image_ocr_tesseract import (
    verify_dependency_surface,
)

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_DETERMINISTIC_PROFESSIONAL_SOLVER_V1"


class ChartographyProfessionalSolverError(ValueError):
    pass


@dataclass(frozen=True)
class AffineAxis:
    pixel_to_value_slope: float
    pixel_to_value_intercept: float
    inlier_count: int
    residual_max: float

    def value(self, pixel: float) -> float:
        return self.pixel_to_value_slope * pixel + self.pixel_to_value_intercept

    def pixel(self, value: float) -> float:
        if abs(self.pixel_to_value_slope) < 1e-12:
            raise ChartographyProfessionalSolverError("AXIS_SLOPE_ZERO")
        return (value - self.pixel_to_value_intercept) / self.pixel_to_value_slope


def _rgb_luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _neutral_dark(rgb: tuple[int, int, int], threshold: int = 225) -> bool:
    return max(rgb) - min(rgb) <= 24 and _rgb_luma(rgb) <= threshold


def _saturated(rgb: tuple[int, int, int]) -> bool:
    return max(rgb) - min(rgb) >= 55 and max(rgb) >= 90


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((int(x) - int(y)) ** 2 for x, y in zip(a, b)))


def _numeric_token(text: str) -> float | None:
    t = text.strip().replace(",", "")
    m = re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)[°º]?[A-Za-z()]*", t)
    if not m:
        return None
    m2 = re.match(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", t)
    return float(m2.group(0)) if m2 else None


def _parse_tsv_words(tsv: str) -> tuple[int, int, list[dict[str, Any]]]:
    reader = csv.DictReader(io.StringIO(tsv), delimiter="\t")
    rows = list(reader)
    pages = [r for r in rows if str(r.get("level")) == "1"]
    if len(pages) != 1:
        raise ChartographyProfessionalSolverError("OCR_PAGE_COUNT_INVALID")
    try:
        width = int(pages[0]["width"])
        height = int(pages[0]["height"])
    except Exception as exc:
        raise ChartographyProfessionalSolverError("OCR_PAGE_GEOMETRY_INVALID") from exc

    words: list[dict[str, Any]] = []
    for r in rows:
        if str(r.get("level")) != "5":
            continue
        text = str(r.get("text") or "").strip()
        if not text:
            continue
        try:
            x0 = int(r["left"])
            y0 = int(r["top"])
            w = int(r["width"])
            h = int(r["height"])
            conf = float(r["conf"])
            line_key = (
                int(r["page_num"]),
                int(r["block_num"]),
                int(r["par_num"]),
                int(r["line_num"]),
            )
            word_num = int(r["word_num"])
        except Exception as exc:
            raise ChartographyProfessionalSolverError("OCR_WORD_GEOMETRY_INVALID") from exc
        if w <= 0 or h <= 0 or x0 < 0 or y0 < 0 or x0 + w > width or y0 + h > height:
            raise ChartographyProfessionalSolverError("OCR_WORD_BOX_OUT_OF_BOUNDS")
        words.append({
            "text": text,
            "x0": x0,
            "y0": y0,
            "x1": x0 + w,
            "y1": y0 + h,
            "cx": x0 + w / 2.0,
            "cy": y0 + h / 2.0,
            "confidence": conf,
            "line_key": line_key,
            "word_num": word_num,
        })
    return width, height, words


def _positioned_words(image_path: str | Path) -> dict[str, Any]:
    verify_dependency_surface()
    src = Path(image_path)
    attempts = []
    parsed = []
    for order, psm in enumerate(("6", "11", "3", "7")):
        proc = subprocess.run(
            ["tesseract", str(src), "stdout", "-l", "eng", "--psm", psm, "tsv"],
            text=True,
            capture_output=True,
            timeout=180,
        )
        if proc.returncode != 0:
            attempts.append({"psm": psm, "returncode": proc.returncode})
            continue
        try:
            w, h, words = _parse_tsv_words(proc.stdout)
        except ChartographyProfessionalSolverError:
            attempts.append({"psm": psm, "returncode": 0, "parse": "FAIL_CLOSED"})
            continue
        score = (len(words), sum(len(x["text"]) for x in words), -order)
        parsed.append((score, psm, w, h, words))
        attempts.append({"psm": psm, "returncode": 0, "word_count": len(words)})
    if not parsed:
        raise ChartographyProfessionalSolverError("OCR_ALL_PSM_FAILED")
    _, psm, w, h, words = max(parsed, key=lambda x: x[0])
    return {"width": w, "height": h, "words": words, "psm": psm, "attempts": attempts}


def _longest_run_containing(flags: list[bool], pivot: int, gap: int = 2) -> tuple[int, int]:
    true_indices = [i for i, v in enumerate(flags) if v]
    if not true_indices:
        raise ChartographyProfessionalSolverError("AXIS_RUN_MISSING")
    groups: list[list[int]] = [[true_indices[0]]]
    for x in true_indices[1:]:
        if x - groups[-1][-1] <= gap + 1:
            groups[-1].append(x)
        else:
            groups.append([x])
    containing = [g for g in groups if g[0] - gap <= pivot <= g[-1] + gap]
    pool = containing or groups
    best = max(pool, key=lambda g: (g[-1] - g[0], len(g)))
    return best[0], best[-1]


def _detect_plot_box(im: Image.Image) -> tuple[int, int, int, int]:
    rgb = im.convert("RGB")
    W, H = rgb.size

    y_candidates = []
    for y in range(int(0.55 * H), int(0.93 * H)):
        count = sum(
            1 for x in range(int(0.06 * W), int(0.82 * W))
            if _neutral_dark(rgb.getpixel((x, y)))
        )
        y_candidates.append((count, y))
    bottom = max(y_candidates)[1]

    x_candidates = []
    for x in range(int(0.05 * W), int(0.28 * W)):
        count = sum(
            1 for y in range(int(0.05 * H), bottom + 1)
            if _neutral_dark(rgb.getpixel((x, y)))
        )
        x_candidates.append((count, x))
    left = max(x_candidates)[1]

    row_flags = []
    for x in range(W):
        row_flags.append(any(
            _neutral_dark(rgb.getpixel((x, yy)))
            for yy in range(max(0, bottom - 1), min(H, bottom + 2))
        ))
    rx0, right = _longest_run_containing(row_flags, left)
    if abs(rx0 - left) > 12:
        left = rx0

    col_flags = []
    for y in range(H):
        col_flags.append(any(
            _neutral_dark(rgb.getpixel((xx, y)))
            for xx in range(max(0, left - 1), min(W, left + 2))
        ))
    top, by1 = _longest_run_containing(col_flags, bottom)
    if abs(by1 - bottom) > 12:
        bottom = by1

    if right - left < 0.35 * W or bottom - top < 0.35 * H:
        raise ChartographyProfessionalSolverError("PLOT_BOX_IMPLAUSIBLE")
    return left, top, right, bottom


def _median(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        raise ChartographyProfessionalSolverError("MEDIAN_EMPTY")
    return float(statistics.median(vals))


def _fit_axis(points: list[tuple[float, float]], direction: str) -> AffineAxis:
    if len(points) < 3:
        raise ChartographyProfessionalSolverError("AXIS_INSUFFICIENT_TICKS")
    slopes = []
    for i, (p1, v1) in enumerate(points):
        for p2, v2 in points[i + 1:]:
            if abs(p2 - p1) < 8 or abs(v2 - v1) < 1e-12:
                continue
            slopes.append((v2 - v1) / (p2 - p1))
    if not slopes:
        raise ChartographyProfessionalSolverError("AXIS_SLOPE_UNAVAILABLE")
    slope0 = _median(slopes)
    if direction == "positive" and slope0 <= 0:
        raise ChartographyProfessionalSolverError("AXIS_DIRECTION_INVALID")
    if direction == "negative" and slope0 >= 0:
        raise ChartographyProfessionalSolverError("AXIS_DIRECTION_INVALID")
    intercept0 = _median(v - slope0 * p for p, v in points)
    vals = [v for _, v in points]
    span = max(vals) - min(vals)
    tol = max(0.75, 0.025 * max(span, 1.0))
    inliers = [(p, v) for p, v in points if abs((slope0 * p + intercept0) - v) <= tol]
    if len(inliers) < 3:
        raise ChartographyProfessionalSolverError("AXIS_ROBUST_FIT_TOO_FEW_INLIERS")
    mp = sum(p for p, _ in inliers) / len(inliers)
    mv = sum(v for _, v in inliers) / len(inliers)
    denom = sum((p - mp) ** 2 for p, _ in inliers)
    if denom <= 0:
        raise ChartographyProfessionalSolverError("AXIS_FIT_DEGENERATE")
    slope = sum((p - mp) * (v - mv) for p, v in inliers) / denom
    intercept = mv - slope * mp
    residual = max(abs(slope * p + intercept - v) for p, v in inliers)
    return AffineAxis(slope, intercept, len(inliers), residual)


def _calibrate_axes(words: list[dict[str, Any]], box: tuple[int, int, int, int]) -> tuple[AffineAxis, AffineAxis, dict[str, Any]]:
    left, top, right, bottom = box
    x_points: list[tuple[float, float]] = []
    y_points: list[tuple[float, float]] = []
    for w in words:
        val = _numeric_token(w["text"])
        if val is None:
            continue
        if bottom + 4 <= w["cy"] <= bottom + 65 and left - 20 <= w["cx"] <= right + 25:
            x_points.append((float(w["cx"]), val))
        if left - 105 <= w["cx"] <= left - 4 and top - 15 <= w["cy"] <= bottom + 15:
            y_points.append((float(w["cy"]), val))

    x_axis = _fit_axis(x_points, "positive")
    y_axis = _fit_axis(y_points, "negative")
    return x_axis, y_axis, {
        "x_tick_candidates": x_points,
        "y_tick_candidates": y_points,
        "x_inliers": x_axis.inlier_count,
        "y_inliers": y_axis.inlier_count,
    }


def _group_legend_rows(words: list[dict[str, Any]], right: int, top: int, bottom: int) -> list[dict[str, Any]]:
    selected = [
        w for w in words
        if w["x0"] >= right + 25 and top <= w["cy"] <= bottom
    ]
    by_line: dict[tuple[int, int, int, int], list[dict[str, Any]]] = {}
    for w in selected:
        by_line.setdefault(tuple(w["line_key"]), []).append(w)
    rows = []
    for key, ws in by_line.items():
        ws = sorted(ws, key=lambda x: (x["word_num"], x["x0"]))
        text = " ".join(x["text"] for x in ws)
        low = text.lower().replace("kim", "k/m")
        if "degc" not in low and "k/m" not in low:
            continue
        tm = re.search(r"(\d{3,4})\s*degc", low)
        gm = re.search(r"(0\.\d+)\s*k\s*/?\s*m", low)
        semantic_words = [
            w for w in ws
            if re.search(r"[A-Za-z0-9]", str(w["text"]))
        ]
        if not semantic_words:
            continue
        rows.append({
            "key": key,
            "text": text,
            "cy": _median(w["cy"] for w in semantic_words),
            "x0": min(w["x0"] for w in semantic_words),
            "temperature": float(tm.group(1)) if tm else None,
            "gradient": float(gm.group(1)) if gm else None,
        })
    return sorted(rows, key=lambda r: r["cy"])


def _repair_legend_target(rows: list[dict[str, Any]], target_temp: float, target_grad: float) -> dict[str, Any]:
    candidates = [r for r in rows if r["gradient"] is not None and abs(r["gradient"] - target_grad) <= 0.002]
    exact = [r for r in candidates if r["temperature"] is not None and abs(r["temperature"] - target_temp) <= 30]
    if len(exact) == 1:
        return exact[0]
    for cand in candidates:
        i = rows.index(cand)
        neighbors = []
        if i > 0:
            neighbors.append(rows[i - 1])
        if i + 1 < len(rows):
            neighbors.append(rows[i + 1])
        same_temp = [
            n for n in neighbors
            if n["temperature"] is not None and abs(n["temperature"] - target_temp) <= 30
        ]
        bracket_grads = sorted(
            n["gradient"] for n in same_temp if n["gradient"] is not None
        )
        if len(same_temp) == 2 and bracket_grads[0] < target_grad < bracket_grads[1]:
            return {**cand, "temperature": target_temp, "temperature_repaired_by_neighbors": True}
    raise ChartographyProfessionalSolverError("LEGEND_TARGET_AMBIGUOUS")


def _dominant_legend_color_and_style(
    im: Image.Image,
    row: dict[str, Any],
    plot_right: int,
) -> tuple[tuple[int, int, int], str, dict[str, Any]]:
    rgb = im.convert("RGB")
    W, H = rgb.size
    text_y = int(round(row["cy"]))
    text_x = int(row["x0"])

    # Legend swatches are normally immediately left of the semantic label, but
    # their stroke center need not share the text's vertical center. Search a
    # bounded 2D pre-label region, then recover the actual colored stroke row.
    x1 = min(W, text_x + 4)
    x0 = max(plot_right + 2, text_x - 105)
    y0 = max(0, text_y - 16)
    y1 = min(H, text_y + 17)
    colored: list[tuple[int, int, tuple[int, int, int]]] = []
    for yy in range(y0, y1):
        for x in range(x0, x1):
            p = rgb.getpixel((x, yy))
            if _saturated(p):
                colored.append((x, yy, p))
    if not colored:
        raise ChartographyProfessionalSolverError(
            f"LEGEND_COLOR_MISSING:{plot_right}:{text_x}:{text_y}:{x0}:{x1}:{y0}:{y1}"
        )

    bins: dict[tuple[int, int, int], list[tuple[int, int, tuple[int, int, int]]]] = {}
    for item in colored:
        p = item[2]
        q = tuple(int(round(v / 16) * 16) for v in p)
        bins.setdefault(q, []).append(item)
    _, pts = max(bins.items(), key=lambda kv: len(kv[1]))
    color = tuple(int(round(_median(item[2][i] for item in pts))) for i in range(3))
    stroke_y = int(round(_median(item[1] for item in pts)))

    occupancy = []
    for x in range(x0, x1):
        occupancy.append(any(
            _color_distance(rgb.getpixel((x, yy)), color) <= 70
            for yy in range(max(0, stroke_y - 2), min(H, stroke_y + 3))
        ))
    runs = []
    n = 0
    for v in occupancy + [False]:
        if v:
            n += 1
        elif n:
            runs.append(n)
            n = 0
    coverage = sum(occupancy) / max(1, len(occupancy))
    max_run = max(runs, default=0)
    if coverage >= 0.72:
        style = "SOLID"
    elif max_run <= 5:
        style = "DOTTED"
    else:
        style = "DASHED"
    return color, style, {
        "search_box": [x0, y0, x1, y1],
        "stroke_y": stroke_y,
        "coverage": coverage,
        "max_run": max_run,
        "run_lengths": runs,
        "colored_pixel_count": len(pts),
    }


def _kmeans_1d(values: list[float], k: int, iterations: int = 40) -> list[float]:
    if k < 1 or len(values) < k:
        raise ChartographyProfessionalSolverError("CLUSTER_INPUT_INVALID")
    vals = sorted(values)
    centers = [vals[round(i * (len(vals) - 1) / max(1, k - 1))] for i in range(k)]
    for _ in range(iterations):
        groups = [[] for _ in centers]
        for v in vals:
            idx = min(range(k), key=lambda i: abs(v - centers[i]))
            groups[idx].append(v)
        new = [(_median(g) if g else centers[i]) for i, g in enumerate(groups)]
        if max(abs(a - b) for a, b in zip(new, centers)) < 1e-9:
            break
        centers = new
    return sorted(centers)


def _classify_plot_style(xs: list[int], left: int, right: int) -> str:
    if not xs:
        return "UNKNOWN"
    present = sorted(set(x for x in xs if left <= x <= right))
    runs = []
    n = 1
    for a, b in zip(present, present[1:]):
        if b == a + 1:
            n += 1
        else:
            runs.append(n)
            n = 1
    runs.append(n)
    coverage = len(present) / max(1, right - left + 1)
    max_run = max(runs)
    if coverage >= 0.70:
        return "SOLID"
    if max_run <= 6:
        return "DOTTED"
    return "DASHED"


def _trace_colored_linear_series(
    im: Image.Image,
    box: tuple[int, int, int, int],
    x_axis: AffineAxis,
    y_axis: AffineAxis,
    color: tuple[int, int, int],
    expected_style: str,
    family_count: int,
) -> dict[str, Any]:
    rgb = im.convert("RGB")
    left, top, right, bottom = box
    x_values = [x_axis.value(left), x_axis.value(right)]
    x_span = abs(max(x_values) - min(x_values))
    slope_points: list[tuple[float, int, float, float]] = []
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            p = rgb.getpixel((x, y))
            if not _saturated(p) or _color_distance(p, color) > 72:
                continue
            xv = x_axis.value(x)
            yv = y_axis.value(y)
            if xv <= min(x_values) + 0.35 * x_span or xv <= 0 or yv <= 0:
                continue
            slope_points.append((yv / xv, x, xv, yv))
    if len(slope_points) < 50:
        raise ChartographyProfessionalSolverError("SERIES_COLOR_PIXELS_INSUFFICIENT")
    k = max(1, min(family_count, 5))
    centers = _kmeans_1d([p[0] for p in slope_points], k)
    groups = [[] for _ in centers]
    for p in slope_points:
        idx = min(range(k), key=lambda i: abs(p[0] - centers[i]))
        groups[idx].append(p)

    candidates = []
    for center, group in zip(centers, groups):
        if len(group) < 15:
            continue
        xs = [p[1] for p in group]
        xv = [p[2] for p in group]
        yv = [p[3] for p in group]
        mx = sum(xv) / len(xv)
        my = sum(yv) / len(yv)
        den = sum((x - mx) ** 2 for x in xv)
        if den <= 0:
            continue
        m = sum((x - mx) * (y - my) for x, y in zip(xv, yv)) / den
        b = my - m * mx
        candidates.append({
            "center": center,
            "slope": m,
            "intercept": b,
            "style": _classify_plot_style(xs, left, right),
            "point_count": len(group),
        })
    matches = [c for c in candidates if c["style"] == expected_style]
    if len(matches) != 1:
        raise ChartographyProfessionalSolverError(
            "SERIES_STYLE_AMBIGUOUS:" + expected_style + ":" + str([(c["style"], round(c["slope"],5)) for c in candidates])
        )
    return {"selected": matches[0], "candidates": candidates}


def _mask_word_boxes(words: list[dict[str, Any]], W: int, H: int, margin: int = 3) -> list[list[bool]]:
    mask = [[False] * W for _ in range(H)]
    for w in words:
        x0 = max(0, int(w["x0"]) - margin)
        y0 = max(0, int(w["y0"]) - margin)
        x1 = min(W, int(w["x1"]) + margin)
        y1 = min(H, int(w["y1"]) + margin)
        for y in range(y0, y1):
            row = mask[y]
            for x in range(x0, x1):
                row[x] = True
    return mask


def _boundary_intersections(
    im: Image.Image,
    words: list[dict[str, Any]],
    box: tuple[int, int, int, int],
    x_axis: AffineAxis,
    y_axis: AffineAxis,
    x_value: float,
) -> list[float]:
    rgb = im.convert("RGB")
    W, H = rgb.size
    left, top, right, bottom = box
    mask = _mask_word_boxes(words, W, H, margin=4)
    xp = int(round(x_axis.pixel(x_value)))
    if not (left + 4 <= xp <= right - 4):
        raise ChartographyProfessionalSolverError("TARGET_X_OUTSIDE_PLOT")

    ys = []
    for y in range(top + 3, bottom - 3):
        hits = 0
        for x in range(max(left + 2, xp - 4), min(right - 1, xp + 5)):
            if mask[y][x]:
                continue
            p = rgb.getpixel((x, y))
            if max(p) - min(p) <= 35 and _rgb_luma(p) <= 120:
                hits += 1
        if hits >= 1:
            ys.append(y)

    clusters: list[list[int]] = []
    for y in ys:
        if not clusters or y - clusters[-1][-1] > 5:
            clusters.append([y])
        else:
            clusters[-1].append(y)
    values = []
    for c in clusters:
        if len(c) < 1:
            continue
        cy = _median(c)
        val = y_axis.value(cy)
        # Keep only genuine interior data intersections.
        ylo = min(y_axis.value(top), y_axis.value(bottom))
        yhi = max(y_axis.value(top), y_axis.value(bottom))
        if ylo + 0.02 * (yhi - ylo) < val < yhi - 0.01 * (yhi - ylo):
            values.append(val)
    # Merge near-duplicate anti-aliased intersections.
    values = sorted(values)
    merged: list[float] = []
    for v in values:
        if not merged or abs(v - merged[-1]) > max(4.0, 0.01 * max(values[-1] - values[0], 1.0)):
            merged.append(v)
        else:
            merged[-1] = (merged[-1] + v) / 2.0
    return merged


def _parse_line_question(prompt: str) -> dict[str, float] | None:
    low = prompt.lower()
    if "how long" not in low:
        return None
    sm = re.search(r"(\d+(?:\.\d+)?)\s*degc\s*/\s*(0\.\d+)\s*k\s*/\s*m", low)
    ym = re.search(r"(\d+(?:\.\d+)?)\s*met(?:re|er)", low)
    if not sm or not ym:
        return None
    return {
        "temperature": float(sm.group(1)),
        "gradient": float(sm.group(2)),
        "target_y": float(ym.group(1)),
    }


def _parse_precipitation_question(prompt: str) -> dict[str, float] | None:
    low = prompt.lower()
    if "precipitat" not in low:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*wt\s*%\s*[a-z]+", low)
    if not m:
        m = re.search(r"-\s*(\d+(?:\.\d+)?)\s*wt\s*%\s*[a-z]+", low)
    if not m:
        return None
    return {"composition": float(m.group(1))}


def solve(image_path: str | Path, prompt: str) -> dict[str, Any]:
    src = Path(image_path)
    if not src.is_file():
        raise ChartographyProfessionalSolverError("IMAGE_NOT_FOUND")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ChartographyProfessionalSolverError("PROMPT_REQUIRED")

    ocr = _positioned_words(src)
    with Image.open(src) as raw:
        im = raw.convert("RGB")
    if im.size != (ocr["width"], ocr["height"]):
        raise ChartographyProfessionalSolverError("OCR_IMAGE_EXTENT_MISMATCH")
    box = _detect_plot_box(im)
    x_axis, y_axis, axis_receipt = _calibrate_axes(ocr["words"], box)

    line_q = _parse_line_question(prompt)
    if line_q is not None:
        rows = _group_legend_rows(ocr["words"], box[2], box[1], box[3])
        target_row = _repair_legend_target(rows, line_q["temperature"], line_q["gradient"])
        color, style, legend_visual = _dominant_legend_color_and_style(im, target_row, box[2])
        same_color_rows = 0
        for row in rows:
            try:
                c, _, _ = _dominant_legend_color_and_style(im, row, box[2])
            except ChartographyProfessionalSolverError:
                continue
            if _color_distance(c, color) <= 75:
                same_color_rows += 1
        traced = _trace_colored_linear_series(
            im, box, x_axis, y_axis, color, style, max(1, same_color_rows)
        )
        selected = traced["selected"]
        if abs(selected["slope"]) < 1e-9:
            raise ChartographyProfessionalSolverError("SERIES_SLOPE_ZERO")
        answer = (line_q["target_y"] - selected["intercept"]) / selected["slope"]
        if not math.isfinite(answer):
            raise ChartographyProfessionalSolverError("LINE_ANSWER_NONFINITE")
        return {
            "schema": SCHEMA,
            "status": "PASS__DETERMINISTIC_PROFESSIONAL_CHART",
            "route": "LEGEND_SERIES_LINEAR_INTERSECTION",
            "answer": f"{answer:.1f} years",
            "answer_numeric": answer,
            "plot_box": box,
            "axis_receipt": axis_receipt,
            "target_series": {
                "requested_temperature": line_q["temperature"],
                "requested_gradient": line_q["gradient"],
                "legend_row": target_row,
                "color": color,
                "style": style,
                "legend_visual": legend_visual,
            },
            "trace": traced,
            "ocr_psm": ocr["psm"],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "general_purpose_model_dependency_count": 0,
            "bounded_learned_components": ["image.extract.ocr.tesseract.positioned.tsv"],
        }

    phase_q = _parse_precipitation_question(prompt)
    if phase_q is not None:
        intersections = _boundary_intersections(
            im, ocr["words"], box, x_axis, y_axis, phase_q["composition"]
        )
        if len(intersections) < 2:
            raise ChartographyProfessionalSolverError(
                "PRECIPITATION_BOUNDARY_INTERSECTIONS_INSUFFICIENT:" + str(intersections)
            )
        # On cooling a binary alloy, precipitation from the terminal solid
        # solution begins at the solvus: the lowest interior phase-boundary
        # intersection at the requested composition, not the liquidus/solidus.
        temperature = min(intersections)
        rounded = int(math.floor(temperature / 10.0 + 0.5) * 10)
        return {
            "schema": SCHEMA,
            "status": "PASS__DETERMINISTIC_PROFESSIONAL_CHART",
            "route": "BINARY_PHASE_DIAGRAM_PRECIPITATION_SOLVUS",
            "answer": f"{rounded}C",
            "answer_numeric": float(rounded),
            "raw_temperature": temperature,
            "composition_wt_percent": phase_q["composition"],
            "boundary_intersections": intersections,
            "plot_box": box,
            "axis_receipt": axis_receipt,
            "ocr_psm": ocr["psm"],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "general_purpose_model_dependency_count": 0,
            "bounded_learned_components": ["image.extract.ocr.tesseract.positioned.tsv"],
        }

    raise ChartographyProfessionalSolverError("UNSUPPORTED_PROFESSIONAL_CHART_QUESTION")


def run(args: dict[str, Any], root: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    src = (base / str(args.get("path") or "")).resolve()
    if src != base and base not in src.parents:
        raise ChartographyProfessionalSolverError("PATH_OUTSIDE_REPOSITORY")
    return solve(src, str(args.get("prompt") or ""))
