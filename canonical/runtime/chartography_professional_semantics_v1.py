from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from PIL import Image

from canonical.runtime.bound_capabilities.image_ocr_tesseract_positioned import run as run_positioned_ocr

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_PROFESSIONAL_SEMANTICS_V1"


class ChartographyProfessionalSemanticError(ValueError):
    pass


_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _center(box: dict[str, int]) -> tuple[float, float]:
    return (
        (box["x0"] + box["x1_exclusive"] - 1) / 2.0,
        (box["y0"] + box["y1_exclusive"] - 1) / 2.0,
    )


def _pure_number(text: str) -> float | None:
    s = text.strip().replace(",", "")
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", s):
        return None
    try:
        return float(s)
    except Exception:
        return None


def _fit_affine(points: list[tuple[float, float]]) -> tuple[float, float, list[tuple[float, float]]]:
    """Robustly fit value = a * pixel + b with pairwise consensus."""
    if len(points) < 2:
        raise ChartographyProfessionalSemanticError("INSUFFICIENT_AXIS_TICKS")
    vals = [v for _, v in points]
    span = max(vals) - min(vals)
    tol = max(0.75, 0.025 * max(span, 1.0))
    best: tuple[int, float, float, list[tuple[float, float]]] | None = None
    for i in range(len(points)):
        x1, y1 = points[i]
        for j in range(i + 1, len(points)):
            x2, y2 = points[j]
            if abs(x2 - x1) < 1e-9 or abs(y2 - y1) < 1e-12:
                continue
            a = (y2 - y1) / (x2 - x1)
            b = y1 - a * x1
            inliers = [(x, y) for x, y in points if abs((a * x + b) - y) <= tol]
            if len(inliers) < 2:
                continue
            err = sum(abs((a * x + b) - y) for x, y in inliers) / len(inliers)
            cand = (len(inliers), -err, a, inliers)
            if best is None or cand[:2] > best[:2]:
                best = cand
    if best is None:
        raise ChartographyProfessionalSemanticError("AXIS_AFFINE_FIT_FAILED")
    _, _, _, inliers = best
    mx = sum(x for x, _ in inliers) / len(inliers)
    my = sum(y for _, y in inliers) / len(inliers)
    den = sum((x - mx) ** 2 for x, _ in inliers)
    if den <= 0:
        raise ChartographyProfessionalSemanticError("AXIS_AFFINE_DEGENERATE")
    a = sum((x - mx) * (y - my) for x, y in inliers) / den
    b = my - a * mx
    return a, b, inliers


def calibrate_axes(positioned_ocr: dict[str, Any]) -> dict[str, Any]:
    W = int(positioned_ocr["page_width"])
    H = int(positioned_ocr["page_height"])
    xpts: list[tuple[float, float]] = []
    ypts: list[tuple[float, float]] = []
    for item in positioned_ocr.get("text_items", []):
        val = _pure_number(str(item.get("text", "")))
        if val is None:
            continue
        cx, cy = _center(item["box"])
        # Tick labels only. Numeric annotations inside the plot are excluded
        # geometrically rather than semantically.
        if cy >= 0.78 * H and 0.04 * W <= cx <= 0.92 * W:
            xpts.append((cx, val))
        if cx <= 0.16 * W and 0.04 * H <= cy <= 0.94 * H:
            ypts.append((cy, val))

    ax, bx, xin = _fit_affine(xpts)
    ay, by, yin = _fit_affine(ypts)
    if ax <= 0:
        raise ChartographyProfessionalSemanticError("X_AXIS_NOT_INCREASING")
    if ay >= 0:
        raise ChartographyProfessionalSemanticError("Y_AXIS_NOT_RISING_UPWARD")

    xvals = [v for _, v in xin]
    yvals = [v for _, v in yin]
    xmin, xmax = min(xvals), max(xvals)
    ymin, ymax = min(yvals), max(yvals)

    return {
        "x_value_from_pixel": (ax, bx),
        "y_value_from_pixel": (ay, by),
        "x_tick_inliers": xin,
        "y_tick_inliers": yin,
        "x_range": (xmin, xmax),
        "y_range": (ymin, ymax),
        "plot_bbox": (
            (xmin - bx) / ax,
            (ymax - by) / ay,
            (xmax - bx) / ax,
            (ymin - by) / ay,
        ),
    }


def _rgb_dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((int(x) - int(y)) ** 2 for x, y in zip(a, b)))


def _saturation(rgb: tuple[int, int, int]) -> int:
    return max(rgb) - min(rgb)


def _find_matching_ocr_line(ocr: dict[str, Any], tokens: Iterable[str]) -> dict[str, Any]:
    needed = [str(x).lower() for x in tokens if str(x).strip()]
    candidates = []
    for item in ocr.get("text_items", []):
        text = str(item.get("text", "")).lower().replace("°", "")
        score = sum(tok in text for tok in needed)
        if score:
            candidates.append((score, len(text), item))
    if not candidates:
        raise ChartographyProfessionalSemanticError("LEGEND_LABEL_NOT_FOUND")
    score, _, item = max(candidates, key=lambda x: (x[0], x[1]))
    if score < max(1, len(needed) - 1):
        raise ChartographyProfessionalSemanticError("LEGEND_LABEL_AMBIGUOUS")
    return item


def _swatch_observation(im: Image.Image, label_box: dict[str, int]) -> dict[str, Any]:
    rgb = im.convert("RGB")
    W, H = rgb.size
    cy = (label_box["y0"] + label_box["y1_exclusive"]) // 2
    x1 = max(0, label_box["x0"] - 4)
    x0 = max(0, x1 - max(36, int(0.045 * W)))
    y0 = max(0, cy - 8)
    y1 = min(H, cy + 9)
    colored = []
    occupancy = []
    for x in range(x0, x1):
        hit = False
        for y in range(y0, y1):
            p = rgb.getpixel((x, y))
            if _saturation(p) >= 45 and max(p) <= 250:
                colored.append(p)
                hit = True
        occupancy.append(hit)
    if len(colored) < 4:
        raise ChartographyProfessionalSemanticError("LEGEND_SWATCH_COLOR_NOT_FOUND")

    # Coarse quantization makes antialiasing irrelevant.
    buckets = Counter(tuple((v // 24) * 24 for v in p) for p in colored)
    dominant = buckets.most_common(1)[0][0]
    near = [p for p in colored if _rgb_dist(p, dominant) <= 48]
    color = tuple(int(median([p[k] for p in near])) for k in range(3))

    runs = []
    start = None
    for i, on in enumerate(occupancy + [False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append(i - start)
            start = None
    cov = sum(occupancy) / max(1, len(occupancy))
    if cov >= 0.72:
        style = "SOLID"
    elif len(runs) >= 5 and median(runs) <= 3:
        style = "DOTTED"
    else:
        style = "DASHED"

    return {"color": color, "style": style, "coverage": cov, "runs": runs}


def _classify_line_style(xs: set[int], xmin: int, xmax: int) -> str:
    if xmax <= xmin:
        return "UNKNOWN"
    bits = [x in xs for x in range(xmin, xmax + 1)]
    cov = sum(bits) / len(bits)
    runs = []
    start = None
    for i, on in enumerate(bits + [False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append(i - start)
            start = None
    if cov >= 0.70:
        return "SOLID"
    if len(runs) >= 8 and median(runs) <= 4:
        return "DOTTED"
    return "DASHED"


def _trace_colored_linear_series(
    im: Image.Image,
    axes: dict[str, Any],
    target_color: tuple[int, int, int],
    target_style: str,
) -> dict[str, Any]:
    rgb = im.convert("RGB")
    W, H = rgb.size
    x0f, y0f, x1f, y1f = axes["plot_bbox"]
    x0 = max(0, int(round(min(x0f, x1f))))
    x1 = min(W - 1, int(round(max(x0f, x1f))))
    y0 = max(0, int(round(min(y0f, y1f))))
    y1 = min(H - 1, int(round(max(y0f, y1f))))

    ax, bx = axes["x_value_from_pixel"]
    ay, by = axes["y_value_from_pixel"]
    x_origin = (0.0 - bx) / ax if axes["x_range"][0] <= 0 <= axes["x_range"][1] else x0
    y_origin = (0.0 - by) / ay if axes["y_range"][0] <= 0 <= axes["y_range"][1] else y1

    slope_samples = []
    pix = []
    step = 1 if (x1 - x0) < 1400 else 2
    for x in range(x0, x1 + 1, step):
        for y in range(y0, y1 + 1):
            p = rgb.getpixel((x, y))
            if _rgb_dist(p, target_color) <= 58:
                dx = x - x_origin
                if abs(dx) < 8:
                    continue
                s = (y_origin - y) / dx
                if 0 < s < 5:
                    slope_samples.append(s)
                    pix.append((x, y, s))
    if len(slope_samples) < 30:
        raise ChartographyProfessionalSemanticError("SERIES_COLOR_PIXELS_INSUFFICIENT")

    # Quantized slope modes separate same-color solid/dashed/dotted series.
    bins = Counter(round(s, 3) for s in slope_samples)
    candidate_modes = [m for m, _ in bins.most_common(12)]
    candidates = []
    for mode in candidate_modes:
        pts = [(x, y) for x, y, s in pix if abs(s - mode) <= 0.012]
        if len(pts) < 20:
            continue
        xs = {x for x, _ in pts}
        style = _classify_line_style(xs, x0, x1)
        # Regression in data coordinates.
        data = [(ax * x + bx, ay * y + by) for x, y in pts]
        mx = sum(x for x, _ in data) / len(data)
        my = sum(y for _, y in data) / len(data)
        den = sum((x - mx) ** 2 for x, _ in data)
        if den <= 0:
            continue
        a = sum((x - mx) * (y - my) for x, y in data) / den
        b = my - a * mx
        candidates.append({
            "mode": mode,
            "style": style,
            "points": len(pts),
            "x_columns": len(xs),
            "data_slope": a,
            "data_intercept": b,
        })
    if not candidates:
        raise ChartographyProfessionalSemanticError("SERIES_MODE_FIT_FAILED")

    exact = [c for c in candidates if c["style"] == target_style]
    chosen = max(exact or candidates, key=lambda c: (c["x_columns"], c["points"]))
    return {"chosen": chosen, "candidates": candidates}


def _solve_linear_legend_series(image_path: Path, prompt: str, ocr: dict[str, Any], axes: dict[str, Any]) -> dict[str, Any]:
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*deg\s*c\s*/\s*([0-9.]+)\s*k\s*/\s*m",
        prompt,
        flags=re.I,
    )
    if not m:
        m = re.search(
            r"(\d+(?:\.\d+)?)\s*degc\s*/\s*([0-9.]+)\s*k\s*/\s*m",
            prompt,
            flags=re.I,
        )
    target = re.search(r"deform\s+([0-9.]+)\s*met", prompt, flags=re.I)
    if not m or not target:
        raise ChartographyProfessionalSemanticError("LINEAR_LEGEND_PROMPT_PARSE_FAILED")
    temp, gradient = m.group(1), m.group(2)
    y_target = float(target.group(1))

    legend = _find_matching_ocr_line(ocr, [temp, gradient])
    with Image.open(image_path) as im:
        swatch = _swatch_observation(im, legend["box"])
        trace = _trace_colored_linear_series(im, axes, swatch["color"], swatch["style"])

    a = float(trace["chosen"]["data_slope"])
    b = float(trace["chosen"]["data_intercept"])
    if abs(a) < 1e-12:
        raise ChartographyProfessionalSemanticError("SERIES_ZERO_SLOPE")
    x = (y_target - b) / a
    if not (axes["x_range"][0] - 0.05 * abs(axes["x_range"][1] - axes["x_range"][0]) <= x <=
            axes["x_range"][1] + 0.05 * abs(axes["x_range"][1] - axes["x_range"][0])):
        raise ChartographyProfessionalSemanticError("INTERSECTION_OUTSIDE_AXIS_RANGE")
    return {
        "route": "LEGEND_SERIES_TARGET_INTERSECTION",
        "answer": f"{x:.1f}",
        "numeric_answer": x,
        "legend_text": legend["text"],
        "swatch": swatch,
        "trace": trace,
    }


def _dark(rgb: tuple[int, int, int]) -> bool:
    return max(rgb) <= 90 and (max(rgb) - min(rgb)) <= 35


def _phase_boundary_intersections(
    im: Image.Image,
    axes: dict[str, Any],
    composition: float,
) -> list[float]:
    rgb = im.convert("RGB")
    W, H = rgb.size
    ax, bx = axes["x_value_from_pixel"]
    ay, by = axes["y_value_from_pixel"]
    xp = (composition - bx) / ax
    x0f, y0f, x1f, y1f = axes["plot_bbox"]
    px0, px1 = sorted((x0f, x1f))
    py0, py1 = sorted((y0f, y1f))
    # Stay away from plot borders/axes.
    yy0 = max(0, int(py0 + 5))
    yy1 = min(H - 1, int(py1 - 5))
    xx0 = max(0, int(round(xp)) - 3)
    xx1 = min(W - 1, int(round(xp)) + 3)

    ys = []
    for y in range(yy0, yy1 + 1):
        support = 0
        for x in range(xx0, xx1 + 1):
            if _dark(rgb.getpixel((x, y))):
                # local horizontal support distinguishes diagram curves from
                # isolated antialiasing/noise.
                neigh = 0
                for dx in range(-5, 6):
                    xx = x + dx
                    if 0 <= xx < W:
                        for dy in (-1, 0, 1):
                            yy = y + dy
                            if 0 <= yy < H and _dark(rgb.getpixel((xx, yy))):
                                neigh += 1
                support = max(support, neigh)
        if support >= 4:
            ys.append(y)

    if not ys:
        raise ChartographyProfessionalSemanticError("PHASE_BOUNDARY_NOT_FOUND")

    clusters = []
    cur = [ys[0]]
    for y in ys[1:]:
        if y <= cur[-1] + 3:
            cur.append(y)
        else:
            clusters.append(cur)
            cur = [y]
    clusters.append(cur)

    temps = []
    for c in clusters:
        if len(c) < 1:
            continue
        yp = median(c)
        temp = ay * yp + by
        # Ignore tick/axis-adjacent debris and labels at the very bottom/top.
        if axes["y_range"][0] + 0.04 * (axes["y_range"][1] - axes["y_range"][0]) <= temp <= axes["y_range"][1] - 0.02 * (axes["y_range"][1] - axes["y_range"][0]):
            temps.append(float(temp))
    return sorted(temps)


def _solve_binary_phase_precipitation(
    image_path: Path,
    prompt: str,
    axes: dict[str, Any],
) -> dict[str, Any]:
    m = re.search(r"-\s*([0-9.]+)\s*wt\s*%\s*[A-Za-z]+", prompt, flags=re.I)
    if not m:
        m = re.search(r"([0-9.]+)\s*wt\s*%\s*[A-Za-z]+", prompt, flags=re.I)
    if not m:
        raise ChartographyProfessionalSemanticError("PHASE_COMPOSITION_PARSE_FAILED")
    composition = float(m.group(1))
    with Image.open(image_path) as im:
        temps = _phase_boundary_intersections(im, axes, composition)
    if not temps:
        raise ChartographyProfessionalSemanticError("NO_PHASE_INTERSECTIONS")
    # For "precipitate" on cooling from a terminal solid solution, the
    # solid-state solvus is the lowest supported phase-boundary intersection
    # above the plotted minimum. Higher intersections are melting/solidification
    # boundaries and are not precipitation onset.
    onset = min(temps)
    rounded = round(onset / 10.0) * 10.0
    return {
        "route": "BINARY_PHASE_PRECIPITATION_SOLVUS",
        "answer": f"{rounded:.0f}C",
        "numeric_answer": onset,
        "composition_wt_percent": composition,
        "candidate_intersections_c": temps,
    }


def solve_professional_chart(
    image_path: str | Path,
    prompt: str,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    src = Path(image_path)
    if not src.is_file():
        raise FileNotFoundError(src)
    if not isinstance(prompt, str) or not prompt.strip():
        raise ChartographyProfessionalSemanticError("PROMPT_REQUIRED")

    if root is None:
        root = src.parent
        rel = src.name
    else:
        root = Path(root)
        rel = str(src.resolve().relative_to(Path(root).resolve()))

    ocr = run_positioned_ocr({"path": rel, "language": "eng"}, root)
    axes = calibrate_axes(ocr)
    p = " ".join(prompt.lower().split())

    if "deform" in p and "year" in p and ("k/m" in p or "k / m" in p):
        solved = _solve_linear_legend_series(src, prompt, ocr, axes)
    elif "wt" in p and "%" in p and "precipitat" in p:
        solved = _solve_binary_phase_precipitation(src, prompt, axes)
    else:
        raise ChartographyProfessionalSemanticError("UNSUPPORTED_PROFESSIONAL_CHART_SEMANTICS")

    return {
        "schema": SCHEMA,
        "status": "PASS__SUPPORTED_BRAIN_OWNED_PROFESSIONAL_SEMANTICS",
        **solved,
        "axis_calibration": axes,
        "ocr_sensor_capability_id": ocr.get("capability_id"),
        "ocr_terminal_semantic_authority": ocr.get("terminal_semantic_authority"),
        "model_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "brain_owned_semantic_authority": True,
        "scope": (
            "V1_SUPPORTS_LEGEND_BOUND_LINEAR_SERIES_INTERSECTION_AND_"
            "BINARY_PHASE_PRECIPITATION_SOLVUS__FAIL_CLOSED_OTHERWISE"
        ),
        "acceptance_authority": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
