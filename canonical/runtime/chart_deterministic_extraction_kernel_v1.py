#!/usr/bin/env python3
"""Deterministic chart-extraction kernel (zero-model; harvested algorithms).

Purpose
-------
Plan `THE_PLAN_20261014_V2.md` Track B3: a general, deterministic, Brain-owned
extraction kernel for raster charts, so that the Chartography solver can be
extended from two question grammars to the enumerated chart-type cells with a
machine-checkable pixel-quantization error bound per extracted value.

Provenance (algorithm harvesting, WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3)
---------------------------------------------------------------------------
Algorithms were recovered by reading the open-source WebPlotDigitizer project
(automeris-io/WebPlotDigitizer, AGPL-3.0, master @ 3a3ecb11606945d0701c8a488777e6861be70056):
  * averaging-window curve tracing (per-column blob scan + neighbour averaging),
  * bar extraction (per-column top/bottom extents grouped into bars),
  * two-anchor axis calibration with log10 scales,
  * X-step-with-interpolation evaluation of a traced curve.
The code below is an independent numpy re-implementation of those procedures
(no source code copied or translated line by line); the donor is absent at
runtime. Donor performance gives zero ownership credit; this module is a
producer, not a proof. Nothing here reads any benchmark case.

Dependencies: numpy (required), Pillow (only for `load_rgb`). Imported lazily so
that the module can be imported for inspection without them.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "AxisMap",
    "fit_axis",
    "load_rgb",
    "color_mask",
    "dominant_colors",
    "trace_series",
    "series_value_at",
    "series_value_at_column",
    "estimate_stroke_width",
    "extract_bars",
    "detect_plot_frame",
    "pie_fractions",
    "QuantizationBound",
    "quantization_bound",
]


def _np():
    import numpy as np  # noqa: WPS433 (lazy on purpose)

    return np


# --------------------------------------------------------------------------
# Axis calibration
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class AxisMap:
    """Monotone map between a pixel coordinate and a data value on one axis.

    `scale` is "linear" or "log" (base-10). For log axes the internal affine
    fit is performed on log10(|value|); `negative` records that the axis holds
    negative magnitudes (as WebPlotDigitizer does)."""

    px0: float
    val0: float
    px1: float
    val1: float
    scale: str = "linear"
    negative: bool = False

    def _t(self, v: float) -> float:
        if self.scale == "log":
            v = -v if self.negative else v
            if v <= 0:
                raise ValueError("log axis requires strictly positive magnitude")
            return math.log10(v)
        return v

    def _t_inv(self, t: float) -> float:
        if self.scale == "log":
            v = 10.0 ** t
            return -v if self.negative else v
        return t

    @property
    def slope(self) -> float:
        """Transformed-value units per pixel."""
        if self.px1 == self.px0:
            raise ValueError("degenerate axis anchors")
        return (self._t(self.val1) - self._t(self.val0)) / (self.px1 - self.px0)

    def px_to_val(self, px: float) -> float:
        return self._t_inv(self._t(self.val0) + (px - self.px0) * self.slope)

    def val_to_px(self, val: float) -> float:
        return self.px0 + (self._t(val) - self._t(self.val0)) / self.slope

    def value_per_pixel(self, px: float) -> float:
        """Local |d value / d pixel| at `px` (exact for linear, derivative for log)."""
        if self.scale == "log":
            return abs(self.px_to_val(px)) * math.log(10.0) * abs(self.slope)
        return abs(self.slope)


def fit_axis(ticks: Sequence[Tuple[float, float]], scale: str = "linear",
             max_rel_residual: float = 0.02) -> Tuple[AxisMap, Dict[str, object]]:
    """Least-squares axis calibration from >= 2 (pixel, value) tick anchors.

    Robustness: if the worst tick's residual (in pixels, relative to the span)
    exceeds `max_rel_residual`, that tick is dropped once and the fit repeated
    (OCR mis-reads of a single tick label are the dominant failure mode).
    Returns the map and a report with residuals and dropped ticks."""
    np = _np()
    pts = [(float(p), float(v)) for p, v in ticks]
    if len(pts) < 2:
        raise ValueError("need at least two tick anchors")
    negative = scale == "log" and all(v < 0 for _, v in pts)

    def transform(v: float) -> float:
        if scale == "log":
            v = -v if negative else v
            if v <= 0:
                raise ValueError("log axis tick with non-positive magnitude")
            return math.log10(v)
        return v

    dropped: List[Tuple[float, float]] = []

    def solve(sample):
        P = np.array([p for p, _ in sample])
        T = np.array([transform(v) for _, v in sample])
        A = np.vstack([P, np.ones_like(P)]).T
        (a, b), *_ = np.linalg.lstsq(A, T, rcond=None)
        pred_px = (T - b) / a if a != 0 else P
        res = np.abs(pred_px - P)
        return a, b, res

    a, b, res = solve(pts)
    span = max(p for p, _ in pts) - min(p for p, _ in pts) or 1.0
    if len(pts) >= 3 and res.max() / span > max_rel_residual:
        worst = int(res.argmax())
        dropped.append(pts[worst])
        pts = [q for i, q in enumerate(pts) if i != worst]
        a, b, res = solve(pts)
    if a == 0:
        raise ValueError("axis fit is degenerate (zero slope)")
    pmin, pmax = min(p for p, _ in pts), max(p for p, _ in pts)
    t0, t1 = a * pmin + b, a * pmax + b
    inv = (lambda t: (-(10.0 ** t) if negative else 10.0 ** t)) if scale == "log" else (lambda t: t)
    amap = AxisMap(pmin, inv(t0), pmax, inv(t1), scale=scale, negative=negative)
    report = {
        "n_ticks_used": len(pts),
        "dropped_ticks": dropped,
        "max_residual_px": float(res.max()),
        "max_residual_rel_span": float(res.max() / span),
    }
    return amap, report


# --------------------------------------------------------------------------
# Image helpers
# --------------------------------------------------------------------------
def load_rgb(path_or_file):
    """Load an image as an (H, W, 3) uint8 numpy array (Pillow)."""
    from PIL import Image  # noqa: WPS433

    np = _np()
    with Image.open(path_or_file) as im:
        return np.asarray(im.convert("RGB")).copy()


def color_mask(rgb, target: Sequence[int], tol: float = 40.0):
    """Boolean (H, W) mask of pixels within Euclidean RGB distance `tol` of `target`."""
    np = _np()
    arr = rgb.astype(np.int32)
    t = np.array(target, dtype=np.int32).reshape(1, 1, 3)
    d2 = ((arr - t) ** 2).sum(axis=2)
    return d2 <= float(tol) ** 2


def dominant_colors(rgb, min_fraction: float = 0.002, bins: int = 8,
                    exclude_gray_chroma: int = 24) -> List[Tuple[Tuple[int, int, int], int]]:
    """Enumerate chromatic colours by coarse RGB quantisation.

    Returns [(mean_rgb, pixel_count)] sorted by count, excluding near-grays
    (max-min channel spread <= `exclude_gray_chroma`), i.e. white background,
    black text, grey grid lines. Used for legend/series discovery."""
    np = _np()
    arr = rgb.reshape(-1, 3).astype(np.int32)
    spread = arr.max(axis=1) - arr.min(axis=1)
    chroma = arr[spread > exclude_gray_chroma]
    if chroma.size == 0:
        return []
    step = 256 // bins
    q = chroma // step
    keys = q[:, 0] * bins * bins + q[:, 1] * bins + q[:, 2]
    uniq, inv, counts = np.unique(keys, return_inverse=True, return_counts=True)
    total = arr.shape[0]
    out = []
    for i, (k, c) in enumerate(zip(uniq, counts)):
        if c / total < min_fraction:
            continue
        mean = chroma[inv == i].mean(axis=0)
        out.append((tuple(int(round(x)) for x in mean), int(c)))
    out.sort(key=lambda t: -t[1])
    return out


# --------------------------------------------------------------------------
# Curve tracing (averaging window) and X-step evaluation
# --------------------------------------------------------------------------
def trace_series(mask, x_step: int = 5, y_step: int = 5) -> List[Tuple[float, float]]:
    """Trace a curve from a boolean mask into sub-pixel (x, y) centre points.

    Procedure (averaging window): for every column, vertical runs of mask
    pixels separated by more than `y_step` rows form distinct blobs whose row
    centres are averaged; blob centres from neighbouring columns within
    (`x_step`, `y_step`) are then merged into one averaged point. Pixel centres
    are used (+0.5)."""
    np = _np()
    H, W = mask.shape
    raw: List[Tuple[float, float]] = []
    for x in range(W):
        rows = np.flatnonzero(mask[:, x])
        if rows.size == 0:
            continue
        # split into blobs where the gap between consecutive rows exceeds y_step
        cuts = np.flatnonzero(np.diff(rows) > y_step)
        for blob in np.split(rows, cuts + 1):
            raw.append((x + 0.5, float(blob.mean()) + 0.5))
    if not raw:
        return []
    used = [False] * len(raw)
    out: List[Tuple[float, float]] = []
    for i, (x0, y0) in enumerate(raw):
        if used[i]:
            continue
        sx, sy, n = x0, y0, 1
        j = i + 1
        while j < len(raw) and raw[j][0] <= x0 + 2 * x_step:
            if not used[j] and abs(raw[j][0] - x0) <= x_step and abs(raw[j][1] - y0) <= y_step:
                sx += raw[j][0]
                sy += raw[j][1]
                n += 1
                used[j] = True
            j += 1
        used[i] = True
        out.append((sx / n, sy / n))
    out.sort()
    return out


def series_value_at(points: Sequence[Tuple[float, float]], x_px: float,
                    max_gap: float = 40.0) -> Optional[float]:
    """Y pixel of a traced series at `x_px` by linear interpolation between the
    nearest traced points on either side (X-step with interpolation). Returns
    None when `x_px` is outside the traced span or the bracketing gap exceeds
    `max_gap` pixels (fail closed rather than extrapolate)."""
    if not points:
        return None
    left = None
    right = None
    for x, y in points:
        if x <= x_px and (left is None or x > left[0]):
            left = (x, y)
        if x >= x_px and (right is None or x < right[0]):
            right = (x, y)
    if left is None or right is None:
        return None
    if right[0] == left[0]:
        return left[1]
    if right[0] - left[0] > max_gap:
        return None
    t = (x_px - left[0]) / (right[0] - left[0])
    return left[1] + t * (right[1] - left[1])


def estimate_stroke_width(mask, percentile: float = 20.0) -> float:
    """Stroke thickness of a one-colour curve: a low percentile of the per-
    column blob heights (gentle segments show the true thickness; steep
    segments and vertices inflate it)."""
    np = _np()
    heights = []
    H, W = mask.shape
    for x in range(W):
        rows = np.flatnonzero(mask[:, x])
        if rows.size == 0:
            continue
        cuts = np.flatnonzero(np.diff(rows) > 2)
        for blob in np.split(rows, cuts + 1):
            heights.append(blob.size)
    if not heights:
        return 1.0
    return float(np.percentile(np.array(heights), percentile))


def _column_blob(mask, x: int, y_step: int, prefer_y: Optional[float]):
    np = _np()
    rows = np.flatnonzero(mask[:, x])
    if rows.size == 0:
        return None
    cuts = np.flatnonzero(np.diff(rows) > y_step)
    blobs = np.split(rows, cuts + 1)
    if prefer_y is not None:
        blob = min(blobs, key=lambda b: abs(float(b.mean()) + 0.5 - prefer_y))
    else:
        blob = max(blobs, key=lambda b: b.size)
    return int(blob[0]), int(blob[-1])


def series_value_at_column(mask, x_px: float, y_step: int = 6, search: int = 2,
                           prefer_y: Optional[float] = None,
                           stroke_width: Optional[float] = None) -> Optional[float]:
    """Y pixel of a one-colour series at column `x_px`, read directly from the
    mask (X-step evaluation without neighbour averaging).

    The column's mask pixels are split into blobs separated by more than
    `y_step` rows; with several blobs (marker + stroke, legend swatch) the one
    nearest `prefer_y` is chosen when given, else the tallest. If the exact
    column is empty, columns within +/-`search` are tried by distance.

    Vertex correction: when the blob is much taller than the stroke width
    (`stroke_width`, default `estimate_stroke_width(mask)`), the column lies on
    a steep segment or a vertex. If both neighbouring columns (at distance
    stroke_width + 2) sit below the blob centre the vertex is a local maximum
    and the centre-line apex is `top + stroke/2`; if both sit above, it is a
    local minimum at `bottom + 1 - stroke/2`; otherwise (monotone steep run)
    the blob centre is already on the centre line. Returns None when nothing
    is found (fail closed)."""
    H, W = mask.shape
    x0 = int(math.floor(x_px))
    order = [x0] + [c for d in range(1, search + 1) for c in (x0 - d, x0 + d)]
    found = None
    for x in order:
        if 0 <= x < W:
            blob = _column_blob(mask, x, y_step, prefer_y)
            if blob is not None:
                found = (x, blob)
                break
    if found is None:
        return None
    x, (top, bottom) = found
    centre = (top + bottom + 1) / 2.0
    sw = estimate_stroke_width(mask) if stroke_width is None else stroke_width
    height = bottom - top + 1
    if height <= 1.5 * sw + 1:
        return centre
    dx = int(math.ceil(sw)) + 2
    nb = []
    for xn in (x - dx, x + dx):
        if 0 <= xn < W:
            b = _column_blob(mask, xn, y_step, centre)
            if b is not None:
                nb.append((b[0] + b[1] + 1) / 2.0)
    def occluded(edge_index: int, edge_value: int) -> bool:
        """A vertex whose extreme edge is a flat line across neighbouring
        columns is cut by an occluder (legend box, other series, axis
        clipping) rather than a curve apex: fail closed."""
        same = 0
        for xn in (x - 2, x - 1, x + 1, x + 2):
            if 0 <= xn < W:
                b = _column_blob(mask, xn, y_step, centre)
                if b is not None and b[edge_index] == edge_value:
                    same += 1
        return same >= 3

    if len(nb) == 2:
        if nb[0] > centre and nb[1] > centre:      # both neighbours lower on the page
            return None if occluded(0, top) else top + sw / 2.0
        if nb[0] < centre and nb[1] < centre:      # both neighbours higher on the page
            return None if occluded(1, bottom) else bottom + 1 - sw / 2.0
    elif len(nb) == 1:                             # series end at a vertex
        if nb[0] > centre:
            return None if occluded(0, top) else top + sw / 2.0
        return None if occluded(1, bottom) else bottom + 1 - sw / 2.0
    return centre


# --------------------------------------------------------------------------
# Bars
# --------------------------------------------------------------------------
@dataclass
class Bar:
    pos: float          # centre along the category axis (pixels)
    lo: float           # smaller pixel coordinate of the bar extent (top for vertical)
    hi: float           # larger pixel coordinate of the bar extent (bottom for vertical)
    width: int          # number of scan lines contributing
    members: List[int] = field(default_factory=list)


def extract_bars(mask, orientation: str = "vertical", del_pos: float = 30.0,
                 del_val: float = 10.0, min_width: int = 3, gap_tol: int = 2) -> List[Bar]:
    """Extract bars from a boolean mask of one bar colour.

    For each scan line perpendicular to the bars (columns for vertical bars),
    the first and last mask pixels give the bar extent; a scan line joins a
    bar when it is contiguous with that bar's last member (gap <= `gap_tol`,
    i.e. a solid fill) and its extents agree with the bar's running average
    within `del_val`; otherwise it may join any bar whose centre is
    within `del_pos` with agreeing extents (hatched / interrupted fills), else
    it starts a new bar. Bars narrower than `min_width` scan lines are
    discarded (legend swatches, text)."""
    np = _np()
    m = mask if orientation == "vertical" else mask.T
    H, W = m.shape
    bars: List[Bar] = []
    for x in range(W):
        rows = np.flatnonzero(m[:, x])
        if rows.size == 0:
            continue
        lo, hi = float(rows[0]), float(rows[-1])
        target = None
        for b in reversed(bars):  # contiguity with any recently extended bar
            if x - b.members[-1] > gap_tol:
                continue
            if abs(b.lo - lo) <= del_val and abs(b.hi - hi) <= del_val:
                target = b
                break
        if target is None:
            for b in bars:
                if (abs(b.pos - x) <= del_pos and abs(b.lo - lo) <= del_val
                        and abs(b.hi - hi) <= del_val):
                    target = b
                    break
        if target is not None:
            n = target.width
            target.pos = (target.pos * n + x) / (n + 1)
            target.lo = (target.lo * n + lo) / (n + 1)
            target.hi = (target.hi * n + hi) / (n + 1)
            target.width = n + 1
            target.members.append(x)
        else:
            bars.append(Bar(pos=float(x), lo=lo, hi=hi, width=1, members=[x]))
    bars = [b for b in bars if b.width >= min_width]
    for b in bars:
        b.pos += 0.5  # pixel centre
    bars.sort(key=lambda b: b.pos)
    return bars


def bar_value(bar: Bar, axis: AxisMap, baseline_px: Optional[float] = None,
              orientation: str = "vertical") -> float:
    """Data value of a bar: the end farthest from the baseline. For vertical
    bars the value end is the top (`lo`) when the bar rises above the baseline
    and the bottom (`hi`) when it hangs below it (negative bars)."""
    if baseline_px is None:
        return axis.px_to_val(bar.lo if orientation == "vertical" else bar.hi)
    if orientation == "vertical":
        end = bar.lo if abs(bar.lo - baseline_px) >= abs(bar.hi - baseline_px) else bar.hi
    else:
        end = bar.hi if abs(bar.hi - baseline_px) >= abs(bar.lo - baseline_px) else bar.lo
    return axis.px_to_val(end)


# --------------------------------------------------------------------------
# Plot frame detection (long dark horizontal / vertical runs)
# --------------------------------------------------------------------------
def detect_plot_frame(rgb, dark_thresh: int = 110, min_run_frac: float = 0.4
                      ) -> Optional[Dict[str, int]]:
    """Locate the x-axis line (bottom-most long dark horizontal run) and the
    y-axis line (left-most long dark vertical run). Returns pixel coordinates
    {"x_axis_row", "y_axis_col", "left", "right", "top", "bottom"} or None."""
    np = _np()
    arr = rgb.astype(np.int32)
    gray = arr.sum(axis=2) // 3
    neutral = (arr.max(axis=2) - arr.min(axis=2)) <= 40   # axis lines are gray/black, not slice colours
    dark = (gray < dark_thresh) & neutral
    H, W = dark.shape

    def longest_run(line) -> Tuple[int, int, int]:
        best = (0, 0, 0)
        start = None
        for i, v in enumerate(list(line) + [False]):
            if v and start is None:
                start = i
            elif not v and start is not None:
                if i - start > best[0]:
                    best = (i - start, start, i - 1)
                start = None
        return best

    rows = [(r,) + longest_run(dark[r]) for r in range(H)]
    rows = [t for t in rows if t[1] >= min_run_frac * W]
    cols = [(c,) + longest_run(dark[:, c]) for c in range(W)]
    cols = [t for t in cols if t[1] >= min_run_frac * H]
    if not rows or not cols:
        return None
    xr = max(rows, key=lambda t: t[0])   # bottom-most
    yc = min(cols, key=lambda t: t[0])   # left-most
    return {
        "x_axis_row": xr[0], "left": xr[2], "right": xr[3],
        "y_axis_col": yc[0], "top": yc[2], "bottom": yc[3],
    }


# --------------------------------------------------------------------------
# Pie / donut
# --------------------------------------------------------------------------
def pie_fractions(rgb, center: Tuple[float, float], radius: float,
                  sample_r: float = 0.6, angle_step_deg: float = 0.25,
                  color_tol: float = 40.0, min_fraction: float = 0.005
                  ) -> List[Dict[str, object]]:
    """Angular fractions of a pie chart.

    1. Palette: chromatic colours inside the disc of radius `radius` (coarse
       quantisation, share >= `min_fraction`) - these are the slice colours.
    2. Sampling: a circle of radius `sample_r * radius` is sampled every
       `angle_step_deg`; each sample is assigned to the nearest palette colour
       within `color_tol`, otherwise ignored (anti-aliased boundaries, wedge
       edge lines, labels).
    3. Run-length encoding of the assigned labels (wrap-around merged) gives
       slice spans; fraction = assigned samples in the run / all assigned.
    Returns [{"rgb", "fraction", "start_deg", "end_deg"}] in angular order."""
    np = _np()
    H, W, _ = rgb.shape
    cx, cy = center
    yy, xx = np.mgrid[0:H, 0:W]
    disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius * radius
    sub = rgb[disc].reshape(-1, 1, 3)
    palette = [c for c, _ in dominant_colors(sub, min_fraction=min_fraction)]
    if not palette:
        return []
    pal = np.array(palette, dtype=np.int32)
    r = radius * sample_r
    n = int(round(360.0 / angle_step_deg))
    labels: List[Optional[int]] = []
    for i in range(n):
        a = math.radians(i * angle_step_deg)
        x = int(round(cx + r * math.cos(a)))
        y = int(round(cy - r * math.sin(a)))
        if not (0 <= x < W and 0 <= y < H):
            labels.append(None)
            continue
        px = rgb[y, x].astype(np.int32)
        d2 = ((pal - px) ** 2).sum(axis=1)
        j = int(d2.argmin())
        labels.append(j if d2[j] <= color_tol * color_tol else None)
    runs: List[List[object]] = []  # [label, count, start_idx]
    for i, lab in enumerate(labels):
        if lab is None:
            continue
        if runs and runs[-1][0] == lab:
            runs[-1][1] += 1
        else:
            runs.append([lab, 1, i])
    if len(runs) > 1 and runs[0][0] == runs[-1][0]:
        last = runs.pop()
        runs[0][1] += last[1]
        runs[0][2] = last[2]
    total = sum(rn[1] for rn in runs)
    if total == 0:
        return []
    # a slice colour may be interrupted by a label/edge: drop sub-threshold runs
    runs = [rn for rn in runs if rn[1] / total >= min_fraction]
    total = sum(rn[1] for rn in runs)
    out = []
    for lab, count, start_idx in runs:
        start = start_idx * angle_step_deg
        out.append({
            "rgb": palette[lab],
            "fraction": count / total,
            "start_deg": start % 360.0,
            "end_deg": (start + count * angle_step_deg) % 360.0,
        })
    return out


def _close(rgb_sum, count, s, tol) -> bool:
    mean = [rgb_sum[k] / count for k in range(3)]
    return sum((mean[k] - s[k]) ** 2 for k in range(3)) <= tol * tol


# --------------------------------------------------------------------------
# Error-bound certificate
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class QuantizationBound:
    value: float
    abs_bound: float
    px: float
    value_per_pixel: float
    pixel_uncertainty: float

    def within(self, tolerance_abs: Optional[float] = None,
               tolerance_rel: Optional[float] = None) -> bool:
        """True iff the whole uncertainty interval satisfies the tolerance."""
        if tolerance_abs is not None and self.abs_bound > tolerance_abs:
            return False
        if tolerance_rel is not None:
            denom = abs(self.value)
            if denom == 0 or self.abs_bound / denom > tolerance_rel:
                return False
        return True


def quantization_bound(axis: AxisMap, px: float, pixel_uncertainty: float = 1.5
                       ) -> QuantizationBound:
    """Certificate for a value read at pixel `px`: |error| <= value_per_pixel
    x pixel_uncertainty, where the default 1.5 px covers half-pixel
    quantisation plus one pixel of anti-aliasing on each side. Axis-anchor
    error (tick OCR) is *not* included and must be certified via `fit_axis`
    residuals."""
    vpp = axis.value_per_pixel(px)
    return QuantizationBound(
        value=axis.px_to_val(px),
        abs_bound=vpp * pixel_uncertainty,
        px=px,
        value_per_pixel=vpp,
        pixel_uncertainty=pixel_uncertainty,
    )
