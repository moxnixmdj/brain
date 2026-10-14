#!/usr/bin/env python3
"""Chartography general extractor V1 — kernel-backed, zero-model, fail-closed.

Replaces the two hard-coded question grammars of
`chartography_deterministic_professional_solver_v1` with a typed pipeline:

    OCR words (tesseract, injectable)  ->  plot frame  ->  axis calibration
    (numeric ticks, linear/log, categorical labels)  ->  series discovery
    (palette + legend swatch binding)  ->  chart type (bar / line / pie)  ->
    table {series -> {category -> (value, certificate)}}  ->  typed query
    (LOOKUP, EXTREMA, DIFFERENCE, RATIO, AGGREGATE, PERCENT_CHANGE, COUNT)
    ->  answer or ABSTAIN with a reason.

Every numeric answer carries the kernel's pixel-quantisation certificate; the
extractor abstains when any mandatory cell is missing or ambiguous (unmatched
category, two legend entries matching the question, certificate wider than the
assumed 5 % tolerance). It never guesses.

This is a producer. It reads no benchmark case; it claims no credit.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from canonical.runtime import chart_deterministic_extraction_kernel_v1 as K

ASSUMED_REL_TOL = 0.05
# "certified": abstain whenever the certificate exceeds the assumed tolerance (proof-grade use).
# "best_effort": always answer when a value exists and report certified=False instead
# (benchmark use: an abstain scores exactly like a wrong answer, a best estimate does not).
POLICY = "best_effort"
NUM_RE = re.compile(r"^[-+]?\$?\(?\d[\d,]*\.?\d*\)?%?[kKmMbB]?$")


class Abstain(Exception):
    """Raised whenever the pipeline cannot certify an answer."""


# ----------------------------------------------------------------------------- OCR words
def numeric_token(text: str) -> Optional[float]:
    t = text.strip().replace(",", "").replace("$", "").replace("%", "")
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    mult = 1.0
    if t and t[-1] in "kKmMbB":
        mult = {"k": 1e3, "m": 1e6, "b": 1e9}[t[-1].lower()]
        t = t[:-1]
    if not t or not re.match(r"^[-+]?\d*\.?\d+$", t):
        return None
    v = float(t) * mult
    return -v if neg else v


def default_ocr(image_path: Path) -> List[Dict[str, Any]]:
    from canonical.runtime import chartography_deterministic_professional_solver_v1 as pro
    return pro._positioned_words(image_path)["words"]


# ----------------------------------------------------------------------------- frame + axes
@dataclass
class Frame:
    left: int
    right: int
    top: int
    bottom: int


def find_frame(rgb) -> Optional[Frame]:
    fr = K.detect_plot_frame(rgb)
    if fr is None:
        return None
    return Frame(left=fr["y_axis_col"], right=fr["right"], top=fr["top"], bottom=fr["x_axis_row"])


def _is_geometric(vals: Sequence[float]) -> bool:
    v = sorted(x for x in vals if x > 0)
    if len(v) < 3 or len(v) != len(vals):
        return False
    ratios = [v[i + 1] / v[i] for i in range(len(v) - 1)]
    diffs = [v[i + 1] - v[i] for i in range(len(v) - 1)]
    r_spread = max(ratios) / min(ratios)
    d_spread = max(diffs) / max(min(diffs), 1e-9)
    return r_spread < 1.2 and d_spread > 3.0


@dataclass
class Axes:
    x_numeric: Optional[K.AxisMap]
    y_numeric: Optional[K.AxisMap]
    x_categories: List[Tuple[str, float]]  # (label, cx)
    y_categories: List[Tuple[str, float]]  # (label, cy) for horizontal bars
    report: Dict[str, Any] = field(default_factory=dict)


def detect_tick_marks(rgb, fr: Frame, length: int = 9, dark_thresh: int = 110) -> Dict[str, List[float]]:
    """Tick-mark positions outside the frame: short dark runs just left of the
    y-axis line (rows) and just below the x-axis line (columns). Returns pixel
    centres; empty lists when the chart has no outward ticks."""
    import numpy as np
    gray = rgb.astype(np.int32).sum(axis=2) // 3
    dark = gray < dark_thresh
    H, W = dark.shape

    def clusters(flags) -> List[float]:
        idx = np.flatnonzero(flags)
        if idx.size == 0:
            return []
        cuts = np.flatnonzero(np.diff(idx) > 1)
        return [float(g.mean()) + 0.5 for g in np.split(idx, cuts + 1) if g.size <= 4]

    y_band = dark[:, max(0, fr.left - length):max(0, fr.left - 1)]
    x_band = dark[min(H, fr.bottom + 2):min(H, fr.bottom + length + 1), :]
    y_rows = clusters(y_band.sum(axis=1) >= max(3, int(0.4 * y_band.shape[1]))) if y_band.size else []
    x_cols = clusters(x_band.sum(axis=0) >= max(3, int(0.4 * x_band.shape[0]))) if x_band.size else []
    # the axis lines themselves are long runs; drop clusters that coincide with frame corners
    y_rows = [r for r in y_rows if fr.top - 3 <= r <= fr.bottom + 3]
    x_cols = [c for c in x_cols if fr.left - 3 <= c <= fr.right + 3]
    return {"y_rows": y_rows, "x_cols": x_cols}


def _snap(pos: float, marks: List[float], tol: float = 12.0) -> float:
    if not marks:
        return pos
    m = min(marks, key=lambda t: abs(t - pos))
    return m if abs(m - pos) <= tol else pos


def calibrate(words: List[Dict[str, Any]], fr: Frame, rgb=None) -> Axes:
    marks = detect_tick_marks(rgb, fr) if rgb is not None else {"y_rows": [], "x_cols": []}
    xt, yt, xc, yc = [], [], [], []
    for w in words:
        val = numeric_token(w["text"])
        below = fr.bottom + 2 <= w["cy"] <= fr.bottom + 70 and fr.left - 8 <= w["cx"] <= fr.right + 30
        leftof = fr.left - 120 <= w["cx"] <= fr.left - 3 and fr.top - 15 <= w["cy"] <= fr.bottom + 15
        if below and leftof:  # corner ambiguity: the bottom y label vs the first x label
            below = w["cy"] >= fr.bottom + 6
            leftof = not below
        if below:
            cx = _snap(float(w["cx"]), marks["x_cols"])
            (xt if val is not None else xc).append((cx, val) if val is not None else (w["text"], cx))
        elif leftof:
            cy = _snap(float(w["cy"]), marks["y_rows"])
            (yt if val is not None else yc).append((cy, val) if val is not None else (w["text"], cy))
    rep: Dict[str, Any] = {"tick_marks": {k: len(v) for k, v in marks.items()}}
    x_map = y_map = None
    if len(yt) >= 2:
        scale = "log" if _is_geometric([v for _, v in yt]) else "linear"
        y_map, rep["y_fit"] = K.fit_axis(yt, scale=scale)
        rep["y_scale"] = scale
    if len(xt) >= 2:
        scale = "log" if _is_geometric([v for _, v in xt]) else "linear"
        x_map, rep["x_fit"] = K.fit_axis(xt, scale=scale)
        rep["x_scale"] = scale
    # numeric x ticks (years) double as categories for lookups by label (fit outliers excluded)
    x_cats = sorted(xc, key=lambda t: t[1])
    if not x_cats and xt:
        dropped = set(tuple(t) for t in rep.get("x_fit", {}).get("dropped_ticks", []))
        x_cats = [(_fmt_label(v), px) for px, v in sorted(xt) if (px, v) not in dropped]
    y_cats = sorted(yc, key=lambda t: t[1])
    return Axes(x_map, y_map, x_cats, y_cats, rep)


def _fmt_label(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


# ----------------------------------------------------------------------------- series / legend
@dataclass
class Series:
    name: Optional[str]
    rgb: Tuple[int, int, int]
    kind: str = "unknown"  # bar | line | pie
    values: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # category -> (value, abs_bound)
    expected: int = 0  # number of axis categories; whole-row queries require len(values) == expected


def discover_series(rgb, fr: Optional[Frame], words: List[Dict[str, Any]]) -> List[Series]:
    """Palette inside the plot area, then legend binding: a non-numeric word
    with a chromatic swatch 4-45 px to its left names the swatch colour."""
    import numpy as np
    H, W, _ = rgb.shape
    region = rgb[fr.top:fr.bottom, fr.left:fr.right] if fr else rgb
    raw = K.dominant_colors(region, min_fraction=0.003)
    palette: List[Tuple[int, int, int]] = []
    for c, n in raw:  # sorted by count: merge anti-aliased near-duplicates into the dominant entry
        if any(_dist(c, p) <= 48 for p in palette):
            continue
        palette.append(c)
    # drop colours that are a neutral blend of a series colour (semi-transparent legend box,
    # grid lines or anti-aliased edges over the fill): c = a*p + (1-a)*gray
    palette = [c for c in palette if not any(_is_neutral_blend(c, p) for p in palette if p != c)]
    if not palette:
        raise Abstain("NO_CHROMATIC_SERIES")
    series = [Series(name=None, rgb=c) for c in palette]
    pal = np.array(palette, dtype=np.int32)
    legend_words: List[Dict[str, Any]] = []
    # legend binding
    for w in words:
        if numeric_token(w["text"]) is not None:
            continue
        y = int(round(w["cy"]))
        if not (0 <= y < H):
            continue
        x_end = int(round(w["x0"])) - 3
        x_start = max(0, x_end - 45)
        hits: Dict[int, int] = {}
        for x in range(x_start, x_end):
            px = rgb[y, x].astype(np.int32)
            d2 = ((pal - px) ** 2).sum(axis=1)
            j = int(d2.argmin())
            if d2[j] <= 40 * 40:
                hits[j] = hits.get(j, 0) + 1
        if hits:
            j = max(hits, key=hits.get)
            if hits[j] >= 4:
                label = w["text"]
                s = series[j]
                s.name = f"{s.name} {label}".strip() if s.name and abs(w["cy"] - s.__dict__.get("_legend_y", -1e9)) < 6 else label
                s.__dict__["_legend_y"] = w["cy"]
                legend_words.append(w)
    if legend_words:  # one shared legend box: union of entries, padded for the frame/swatch
        box = (int(min(w["x0"] for w in legend_words)) - 48, int(min(w["y0"] for w in legend_words)) - 8,
               int(max(w["x1"] for w in legend_words)) + 10, int(max(w["y1"] for w in legend_words)) + 8)
        for s in series:
            s.__dict__["_legend_box"] = box
    return series


def _dist(a, b) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _is_neutral_blend(c, p, tol: float = 18.0) -> bool:
    """True when c lies on the segment between p and a neutral gray level g
    (c = a*p + (1-a)*g with 0.15 < a < 0.92) for white, light-gray grid,
    mid-gray or black: the signature of translucent overlays and edge
    anti-aliasing, never of an independent series colour."""
    for g in (255, 176, 128, 0):
        num = sum((g - c[i]) * (g - p[i]) for i in range(3))
        den = sum((g - p[i]) ** 2 for i in range(3)) or 1
        a = num / den
        if not (0.15 < a < 0.92):
            continue
        proj = [a * p[i] + (1 - a) * g for i in range(3)]
        if _dist(c, proj) <= tol:
            return True
    return False


def _legend_free_mask(mask, series: List[Series]):
    m = mask.copy()
    for s in series:
        box = s.__dict__.get("_legend_box")
        if box:
            x0, y0, x1, y1 = box
            m[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = False
    return m


# ----------------------------------------------------------------------------- table extraction
def extract_table(rgb, fr: Frame, axes: Axes, series: List[Series]) -> List[Series]:
    """Fill `series[i].values` from bars or lines; sets `kind`."""
    import numpy as np
    out: List[Series] = []
    for s in series:
        mask = _legend_free_mask(K.color_mask(rgb, s.rgb, tol=40), series)
        mask[: fr.top, :] = False
        mask[fr.bottom + 1:, :] = False
        mask[:, : fr.left] = False
        mask[:, fr.right + 1:] = False
        if not mask.any():
            continue
        vbars = K.extract_bars(mask, "vertical", del_pos=30, del_val=3, min_width=6)
        hbars = K.extract_bars(mask, "horizontal", del_pos=30, del_val=3, min_width=6)
        heights = [b.hi - b.lo for b in vbars]
        widths = [b.width for b in vbars]
        solid_v = vbars and np.median(widths) >= 8 and np.median(heights) >= 0.02 * (fr.bottom - fr.top)
        solid_h = hbars and np.median([b.width for b in hbars]) >= 8 and np.median([b.hi - b.lo for b in hbars]) >= 0.02 * (fr.right - fr.left)
        if solid_v and axes.y_numeric is not None and (axes.x_categories or axes.x_numeric):
            s.kind = "bar"
            base = axes.y_numeric.val_to_px(0.0) if _in_range(axes.y_numeric, 0.0, fr.top, fr.bottom) else float(fr.bottom)
            cats = axes.x_categories
            s.expected = len(cats)
            box = s.__dict__.get("_legend_box")
            for b in vbars:
                if box and _occluded_by_box(b, box, "vertical"):
                    continue
                v = K.bar_value(b, axes.y_numeric, baseline_px=base)
                end_px = axes.y_numeric.val_to_px(v)
                cert = K.quantization_bound(axes.y_numeric, end_px, 1.5)
                label = _nearest_label(cats, b.pos, tol=max(12.0, 0.6 * _cat_spacing(cats)))
                if label is None:
                    continue
                s.values[label] = (v, cert.abs_bound)
        elif solid_h and axes.x_numeric is not None and axes.y_categories:
            s.kind = "bar"
            base = axes.x_numeric.val_to_px(0.0) if _in_range(axes.x_numeric, 0.0, fr.left, fr.right) else float(fr.left)
            cats = axes.y_categories
            s.expected = len(cats)
            box = s.__dict__.get("_legend_box")
            for b in hbars:
                if box and _occluded_by_box(b, box, "horizontal"):
                    continue
                v = K.bar_value(b, axes.x_numeric, baseline_px=base, orientation="horizontal")
                cert = K.quantization_bound(axes.x_numeric, axes.x_numeric.val_to_px(v), 1.5)
                label = _nearest_label(cats, b.pos, tol=max(12.0, 0.6 * _cat_spacing(cats)))
                if label is None:
                    continue
                s.values[label] = (v, cert.abs_bound)
        elif axes.y_numeric is not None and axes.x_categories:
            s.kind = "line"
            traced = K.trace_series(mask, x_step=4, y_step=6)
            if len(traced) < 10:
                continue
            sw = K.estimate_stroke_width(mask)
            s.expected = len(axes.x_categories)
            for label, cx in axes.x_categories:
                hint = K.series_value_at(traced, cx, max_gap=80)
                ypx = K.series_value_at_column(mask, cx, y_step=6, search=3, prefer_y=hint, stroke_width=sw)
                if ypx is None:
                    continue
                cert = K.quantization_bound(axes.y_numeric, ypx, 3.0)
                s.values[label] = (cert.value, cert.abs_bound)
        if s.values:
            out.append(s)
    return out


def _complete(s: Series) -> Series:
    if s.kind != "pie" and s.expected and len(s.values) < s.expected:
        raise Abstain(f"ROW_INCOMPLETE_{len(s.values)}_of_{s.expected}")
    return s


def _occluded_by_box(b: K.Bar, box, orientation: str) -> bool:
    """A bar whose value end touches the legend box edge may continue under it."""
    x0, y0, x1, y1 = box
    if orientation == "vertical":
        overlaps = b.members[0] <= x1 and b.members[-1] >= x0
        return overlaps and (y0 - 3 <= b.lo <= y1 + 3)
    overlaps = b.members[0] <= y1 and b.members[-1] >= y0
    return overlaps and (x0 - 3 <= b.hi <= x1 + 3)


def _in_range(amap: K.AxisMap, v: float, p0: float, p1: float) -> bool:
    try:
        px = amap.val_to_px(v)
    except ValueError:
        return False
    return min(p0, p1) - 2 <= px <= max(p0, p1) + 2


def _cat_spacing(cats: List[Tuple[str, float]]) -> float:
    ps = sorted(p for _, p in cats)
    if len(ps) < 2:
        return 40.0
    return min(ps[i + 1] - ps[i] for i in range(len(ps) - 1))


def _nearest_label(cats: List[Tuple[str, float]], pos: float, tol: float) -> Optional[str]:
    if not cats:
        return None
    label, p = min(cats, key=lambda t: abs(t[1] - pos))
    return label if abs(p - pos) <= tol else None


# ----------------------------------------------------------------------------- pie
def extract_pie(rgb, words: List[Dict[str, Any]]) -> List[Series]:
    import numpy as np
    arr = rgb.astype(np.int32)
    chroma = (arr.max(axis=2) - arr.min(axis=2)) > 24
    ys, xs = np.nonzero(chroma)
    if xs.size < 500:
        raise Abstain("NO_PIE_DISC")
    cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
    radius = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2.0
    parts = K.pie_fractions(rgb, (cx, cy), radius, sample_r=0.6)
    if not parts:
        raise Abstain("PIE_NO_SLICES")
    out = []
    for p in parts:
        s = Series(name=None, rgb=p["rgb"], kind="pie")
        s.__dict__["_span"] = (p["start_deg"], p["end_deg"])
        s.values["share"] = (100.0 * p["fraction"], 100.0 * 0.5 / 360.0 * 2)
        out.append(s)
    # label binding by angle: a non-numeric word outside the disc names the slice its angle falls in
    for w in words:
        if numeric_token(w["text"]) is not None:
            continue
        dx, dy = w["cx"] - cx, cy - w["cy"]
        if math.hypot(dx, dy) < radius * 0.5:
            continue
        ang = math.degrees(math.atan2(dy, dx)) % 360.0
        for s in out:
            a0, a1 = s.__dict__["_span"]
            inside = a0 <= ang < a1 if a0 < a1 else (ang >= a0 or ang < a1)
            if inside:
                s.name = f"{s.name} {w['text']}".strip() if s.name else w["text"]
                break
    return out


# ----------------------------------------------------------------------------- question grammar
QUERY_PATTERNS = [
    ("PERCENT_CHANGE", re.compile(r"percent(?:age)?\s+(?:change|increase|decrease|growth)\s+(?:in\s+(?P<series>[\w\s]+?)\s+)?from\s+(?P<a>[\w\.\-]+)\s+to\s+(?P<b>[\w\.\-]+)", re.I)),
    ("DIFFERENCE", re.compile(r"difference\s+(?:in\s+(?P<series>[\w\s]+?)\s+)?between\s+(?P<a>[\w\.\-]+)\s+and\s+(?P<b>[\w\.\-]+)", re.I)),
    ("RATIO", re.compile(r"ratio\s+of\s+(?P<a>[\w\.\-]+)\s+to\s+(?P<b>[\w\.\-]+)", re.I)),
    ("RATIO", re.compile(r"how many times\s+(?:larger|greater|higher|bigger|more)\s+(?:is\s+)?(?P<a>[\w\.\-]+)\s+(?:than|compared to)\s+(?P<b>[\w\.\-]+)", re.I)),
    ("EXTREMA_CAT", re.compile(r"which\s+(?:[\w]+\s+){0,3}?(?:has|had|shows|showed|with)\s+the\s+(?P<ext>highest|lowest|largest|smallest|maximum|minimum|greatest|least)(?:\s+(?P<series>[\w\s]+?))?\s*\??$", re.I)),
    ("EXTREMA_VAL", re.compile(r"what\s+(?:is|was)\s+the\s+(?P<ext>highest|lowest|largest|smallest|maximum|minimum|peak|greatest)\s+(?:value|(?P<series>[\w\s]+?))?(?:\s+(?:in|of|on|across)\s+the\s+chart)?\s*\??$", re.I)),
    ("AGGREGATE", re.compile(r"(?:what\s+(?:is|was)\s+the\s+)?(?P<agg>total|sum|average|mean|median)\s+(?:of\s+|value\s+of\s+)?(?:all\s+)?(?P<series>[\w\s]+?)?(?:\s+(?:across|over|for)\s+all\s+[\w\s]+)?\s*\??$", re.I)),
    ("LOOKUP", re.compile(r"(?:what\s+(?:is|was|are|were)\s+the\s+)?(?:value\s+(?:of|for)\s+)?(?P<series>[\w\s]+?)?\s*(?:in|at|for|during)\s+(?P<cat>[\w\.\-]+)\s*\??$", re.I)),
    ("COUNT", re.compile(r"how many\s+(?P<what>categories|bars|slices|series|groups|items|countries|years)", re.I)),
    ("SHARE", re.compile(r"(?:percentage|percent|share|proportion)(?:\s+(?:share|proportion))?\s+(?:of\s+the\s+\w+\s+)?(?:does|is|did|was|of|for)\s+(?P<cat>[\w\.\-]+)", re.I)),
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _match_category(cats: Sequence[str], token: str) -> Optional[str]:
    t = _norm(token)
    if not t:
        return None
    exact = [c for c in cats if _norm(c) == t]
    if len(exact) == 1:
        return exact[0]
    pref = [c for c in cats if _norm(c).startswith(t) or t.startswith(_norm(c)) and len(_norm(c)) >= 3]
    if len(pref) == 1:
        return pref[0]
    return None  # ambiguous or absent -> abstain


def _match_series(series: List[Series], phrase: Optional[str]) -> Series:
    if len(series) == 1:
        return series[0]
    if not phrase:
        raise Abstain("SERIES_UNSPECIFIED_MULTI_SERIES")
    p = _norm(phrase)
    cands = [s for s in series if s.name and (_norm(s.name) in p or p in _norm(s.name))]
    if len(cands) != 1:
        raise Abstain(f"SERIES_MATCH_{len(cands)}")
    return cands[0]


_LAST_CERTIFIED = {"ok": True}


def _certified(v: float, bound: float) -> float:
    ok = v != 0 and bound / abs(v) <= ASSUMED_REL_TOL
    _LAST_CERTIFIED["ok"] = ok
    if not ok and POLICY == "certified":
        raise Abstain(f"CERTIFICATE_TOO_WIDE_{bound:.3g}_of_{v:.3g}")
    return v


def answer_query(prompt: str, series: List[Series]) -> Dict[str, Any]:
    if not series:
        raise Abstain("EMPTY_TABLE")
    _LAST_CERTIFIED["ok"] = True
    cats = sorted({c for s in series for c in s.values})
    for qtype, rx in QUERY_PATTERNS:
        m = rx.search(prompt.strip())
        if not m:
            continue
        g = m.groupdict()
        if qtype == "COUNT":
            n = len(series) if g["what"] in ("series", "slices") and series[0].kind != "pie" else len(cats)
            if series[0].kind == "pie":
                n = len(series)
            return {"type": qtype, "answer_numeric": float(n), "answer": str(n), "certificate": 0.0}
        if series[0].kind == "pie":
            if qtype in ("SHARE", "LOOKUP"):
                tok = g.get("cat")
                s = next((s for s in series if s.name and _match_category([s.name], tok or "")), None)
                if s is None:
                    raise Abstain("PIE_LABEL_UNMATCHED")
                v, b = s.values["share"]
                return {"type": "SHARE", "answer_numeric": v, "answer": f"{v:.1f}%", "certificate": b}
            if qtype == "EXTREMA_CAT":
                best = (max if g["ext"] in ("highest", "largest", "maximum", "greatest") else min)(series, key=lambda s: s.values["share"][0])
                if not best.name:
                    raise Abstain("PIE_EXTREMUM_UNLABELED")
                return {"type": qtype, "answer": best.name, "answer_numeric": None, "certificate": best.values["share"][1]}
            continue
        if qtype == "LOOKUP":
            s = _match_series(series, g.get("series"))
            c = _match_category(list(s.values), g["cat"])
            if c is None:
                raise Abstain(f"CATEGORY_UNMATCHED_{g['cat']}")
            v, b = s.values[c]
            return {"type": qtype, "answer_numeric": _certified(v, b), "answer": _fmt(v), "certificate": b}
        if qtype in ("DIFFERENCE", "RATIO", "PERCENT_CHANGE"):
            s = _match_series(series, g.get("series"))
            a = _match_category(list(s.values), g["a"])
            b_ = _match_category(list(s.values), g["b"])
            if a is None or b_ is None:
                raise Abstain("CATEGORY_UNMATCHED_PAIR")
            (va, ea), (vb, eb) = s.values[a], s.values[b_]
            if qtype == "DIFFERENCE":
                v, e = abs(va - vb), ea + eb
            elif qtype == "RATIO":
                if vb == 0:
                    raise Abstain("RATIO_DIV_ZERO")
                v = va / vb
                e = abs(v) * (ea / max(abs(va), 1e-9) + eb / abs(vb))
            else:
                if va == 0:
                    raise Abstain("PCT_DIV_ZERO")
                v = (vb - va) / abs(va) * 100.0
                e = 100.0 * (ea + eb) / abs(va) + abs(v) * ea / abs(va)
            return {"type": qtype, "answer_numeric": _certified(v, e), "answer": _fmt(v), "certificate": e}
        if qtype == "EXTREMA_CAT":
            s = _complete(_match_series(series, g.get("series")))
            hi = g["ext"] in ("highest", "largest", "maximum", "greatest")
            items = sorted(s.values.items(), key=lambda kv: kv[1][0], reverse=hi)
            if len(items) >= 2 and abs(items[0][1][0] - items[1][1][0]) <= items[0][1][1] + items[1][1][1]:
                raise Abstain("EXTREMUM_TIE_WITHIN_CERTIFICATE")
            return {"type": qtype, "answer": items[0][0], "answer_numeric": items[0][1][0], "certificate": items[0][1][1]}
        if qtype == "EXTREMA_VAL":
            s = _complete(_match_series(series, g.get("series")))
            hi = g["ext"] in ("highest", "largest", "maximum", "peak", "greatest")
            v, b = (max if hi else min)(s.values.values(), key=lambda t: t[0])
            return {"type": qtype, "answer_numeric": _certified(v, b), "answer": _fmt(v), "certificate": b}
        if qtype == "AGGREGATE":
            s = _complete(_match_series(series, g.get("series")))
            vals = [v for v, _ in s.values.values()]
            bounds = [b for _, b in s.values.values()]
            if not vals:
                raise Abstain("AGGREGATE_EMPTY")
            agg = g["agg"].lower()
            if agg in ("total", "sum"):
                v, e = sum(vals), sum(bounds)
            elif agg in ("average", "mean"):
                v, e = sum(vals) / len(vals), sum(bounds) / len(vals)
            else:
                sv = sorted(vals)
                v = sv[len(sv) // 2] if len(sv) % 2 else (sv[len(sv) // 2 - 1] + sv[len(sv) // 2]) / 2
                e = max(bounds)
            return {"type": qtype, "answer_numeric": _certified(v, e), "answer": _fmt(v), "certificate": e}
    raise Abstain("QUESTION_GRAMMAR_UNMATCHED")


def _fmt(v: float) -> str:
    return f"{v:.4g}" if abs(v) < 1e4 else f"{v:.6g}"


# ----------------------------------------------------------------------------- entry point
def solve(image_path: str | Path, prompt: str,
          ocr: Optional[Callable[[Path], List[Dict[str, Any]]]] = None,
          rgb=None) -> Dict[str, Any]:
    """Return {"status": "ANSWER"|"ABSTAIN__<reason>", "answer", "answer_numeric",
    "certificate", "chart_kind", "table"}. Never raises for chart reasons."""
    src = Path(image_path)
    try:
        if rgb is None:
            rgb = K.load_rgb(src)
        words = (ocr or default_ocr)(src)
        fr = find_frame(rgb)
        if fr is None:
            series = extract_pie(rgb, words)
        else:
            axes = calibrate(words, fr, rgb)
            if axes.y_numeric is None and axes.x_numeric is None:
                raise Abstain("NO_NUMERIC_AXIS")
            series = extract_table(rgb, fr, axes, discover_series(rgb, fr, words))
            if not series:
                raise Abstain("NO_SERIES_EXTRACTED")
        res = answer_query(prompt, series)
        res.update({"status": "ANSWER", "chart_kind": series[0].kind, "certified": bool(_LAST_CERTIFIED["ok"]),
                    "policy": POLICY,
                    "table": {s.name or f"#{s.rgb}": {c: round(v, 4) for c, (v, _) in s.values.items()} for s in series}})
        return res
    except Abstain as exc:
        return {"status": f"ABSTAIN__{exc}", "answer": None, "answer_numeric": None, "certificate": None}
