#!/usr/bin/env python3
"""Held-out synthetic measurement of the deterministic chart-extraction kernel.

Renders N random charts per family with matplotlib (anti-aliased, ticks, grid,
legend - i.e. realistic raster conditions), with gold values known by
construction, and measures how often the kernel's extracted value (a) lies
inside its own quantisation certificate and (b) satisfies a 5 % relative /
small absolute tolerance. The axis calibration is supplied from the renderer's
true transform: this isolates the *extraction* cells (B3) from the tick-OCR
cell, which is measured separately on the runner where tesseract exists.

Zero benchmark data is touched. Output is a receipt JSON with per-family
rates and the failure census; it is evidence about the kernel, not credit.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import random
import sys
import time
from typing import Dict, List

from canonical.runtime import chart_deterministic_extraction_kernel_v1 as K

PALETTE = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189)]


def _render(fig):
    import numpy as np
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    from PIL import Image
    with Image.open(buf) as im:
        return np.asarray(im.convert("RGB")).copy()


def _axis_maps(ax, fig):
    """True axis calibrations from matplotlib's transform (two anchors each)."""
    h = fig.get_size_inches()[1] * fig.dpi
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    px0, py0 = ax.transData.transform((x0, y0))
    px1, py1 = ax.transData.transform((x1, y1))
    xa = K.AxisMap(px0, x0, px1, x1, scale="log" if ax.get_xscale() == "log" else "linear")
    ya = K.AxisMap(h - py0, y0, h - py1, y1, scale="log" if ax.get_yscale() == "log" else "linear")
    return xa, ya


def run_bars(rng: random.Random, n: int, horizontal: bool = False) -> Dict[str, object]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    hits_cert = hits_tol = total = charts_ok = 0
    failures: List[str] = []
    for i in range(n):
        k = rng.randint(3, 8)
        neg = rng.random() < 0.3
        vals = [round(rng.uniform(-40 if neg else 2, 100), 1) for _ in range(k)]
        color = PALETTE[rng.randrange(len(PALETTE))]
        fig, ax = plt.subplots(figsize=(6.4, 4.8))
        c = tuple(v / 255 for v in color)
        if horizontal:
            ax.barh(range(k), vals, color=c)
        else:
            ax.bar(range(k), vals, color=c)
        if rng.random() < 0.5:
            ax.grid(True, alpha=0.3)
        ax.set_title("synthetic %d" % i)
        fig.canvas.draw()
        rgb = _render(fig)
        xa, ya = _axis_maps(ax, fig)
        plt.close(fig)
        mask = K.color_mask(rgb, color, tol=45)
        axis = xa if horizontal else ya
        base = axis.val_to_px(0.0)
        bars = K.extract_bars(mask, "horizontal" if horizontal else "vertical",
                              del_pos=30, del_val=3, min_width=5)
        if len(bars) != k:
            failures.append(f"chart{i}: expected {k} bars, got {len(bars)}")
            total += k
            continue
        charts_ok += 1
        if horizontal:  # category 0 is the bottom-most bar; pixel order is top->bottom
            bars = list(reversed(bars))
        for b, v in zip(bars, vals):
            got = K.bar_value(b, axis, baseline_px=base, orientation="horizontal" if horizontal else "vertical")
            cert = K.quantization_bound(axis, axis.val_to_px(got), pixel_uncertainty=1.5)
            total += 1
            if abs(got - v) <= cert.abs_bound:
                hits_cert += 1
            if abs(got - v) <= max(0.05 * abs(v), 0.5):
                hits_tol += 1
            else:
                failures.append(f"chart{i}: bar {v} -> {got:.2f}")
    return {"family": "barh" if horizontal else "bar", "charts": n, "charts_all_bars_found": charts_ok,
            "values": total, "within_certificate": hits_cert, "within_5pct_or_0.5": hits_tol,
            "rate_certificate": round(hits_cert / max(total, 1), 4),
            "rate_tolerance": round(hits_tol / max(total, 1), 4), "failures": failures[:20]}


def run_lines(rng: random.Random, n: int, log_y: bool = False) -> Dict[str, object]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    hits_cert = hits_tol = total = none_count = 0
    failures: List[str] = []
    for i in range(n):
        m = rng.randint(6, 25)
        xs = list(range(m))
        if log_y:
            ys = [10 ** rng.uniform(0, 3) for _ in xs]
        else:
            ys = [rng.uniform(0, 100) for _ in xs]
        series = rng.randint(1, 3)
        color = PALETTE[rng.randrange(len(PALETTE))]
        fig, ax = plt.subplots(figsize=(6.4, 4.8))
        ax.plot(xs, ys, color=tuple(v / 255 for v in color), linewidth=rng.choice([1.5, 2.0, 2.5]), label="target")
        others = [p for p in PALETTE if p != color]
        for s in range(series - 1):
            oc = others[s]
            oy = [10 ** rng.uniform(0, 3) for _ in xs] if log_y else [rng.uniform(0, 100) for _ in xs]
            ax.plot(xs, oy, color=tuple(v / 255 for v in oc), linewidth=2.0, label="other%d" % s)
        if log_y:
            ax.set_yscale("log")
        if rng.random() < 0.5:
            ax.grid(True, alpha=0.3)
        ax.legend(loc=rng.choice(["upper left", "upper right", "lower right"]))
        fig.canvas.draw()
        rgb = _render(fig)
        xa, ya = _axis_maps(ax, fig)
        plt.close(fig)
        mask = K.color_mask(rgb, color, tol=45)
        traced = K.trace_series(mask, x_step=4, y_step=6)
        sw = K.estimate_stroke_width(mask)
        # legend swatch is the same colour: restrict evaluation to interior x positions
        for x in xs[1:-1]:
            total += 1
            hint = K.series_value_at(traced, xa.val_to_px(x), max_gap=60)
            ypx = K.series_value_at_column(mask, xa.val_to_px(x), y_step=6, search=2, prefer_y=hint, stroke_width=sw)
            if ypx is None:
                none_count += 1
                failures.append(f"chart{i}: no trace at x={x}")
                continue
            cert = K.quantization_bound(ya, ypx, pixel_uncertainty=2.0)
            v = ys[x]
            if abs(cert.value - v) <= cert.abs_bound:
                hits_cert += 1
            if abs(cert.value - v) <= max(0.05 * abs(v), 0.5):
                hits_tol += 1
            else:
                failures.append(f"chart{i}: x={x} true {v:.2f} got {cert.value:.2f} bound {cert.abs_bound:.2f}")
    return {"family": "line_logy" if log_y else "line", "charts": n, "values": total,
            "no_trace": none_count, "within_certificate": hits_cert, "within_5pct_or_0.5": hits_tol,
            "rate_certificate": round(hits_cert / max(total, 1), 4),
            "rate_tolerance": round(hits_tol / max(total, 1), 4), "failures": failures[:20]}


def run_pies(rng: random.Random, n: int) -> Dict[str, object]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    hits = total = charts_ok = 0
    failures: List[str] = []
    for i in range(n):
        k = rng.randint(2, 5)
        w = [rng.uniform(1, 10) for _ in range(k)]
        s = sum(w)
        fr = [v / s for v in w]
        cols = PALETTE[:k]
        fig, ax = plt.subplots(figsize=(4.8, 4.8))
        ax.pie(fr, colors=[tuple(v / 255 for v in c) for c in cols], startangle=rng.uniform(0, 360))
        fig.canvas.draw()
        rgb = _render(fig)
        plt.close(fig)
        # locate the pie: bounding box of chromatic pixels
        arr = rgb.astype(np.int32)
        chroma = (arr.max(axis=2) - arr.min(axis=2)) > 24
        ys, xs = np.nonzero(chroma)
        if xs.size == 0:
            failures.append(f"chart{i}: no pie found")
            total += k
            continue
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        radius = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2
        parts = K.pie_fractions(rgb, (cx, cy), radius, sample_r=0.6)
        if len(parts) != k:
            failures.append(f"chart{i}: expected {k} slices got {len(parts)}")
            total += k
            continue
        charts_ok += 1
        got = {}
        for p in parts:
            key = min(range(k), key=lambda j: sum((p["rgb"][t] - cols[j][t]) ** 2 for t in range(3)))
            got[key] = p["fraction"]
        for j in range(k):
            total += 1
            if j in got and abs(got[j] - fr[j]) <= 0.01:
                hits += 1
            else:
                failures.append(f"chart{i}: slice {fr[j]:.3f} -> {got.get(j)}")
    return {"family": "pie", "charts": n, "charts_all_slices_found": charts_ok, "values": total,
            "within_1pct_abs": hits, "rate_tolerance": round(hits / max(total, 1), 4), "failures": failures[:20]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    t0 = time.time()
    results = [run_bars(rng, a.n), run_bars(rng, a.n, horizontal=True), run_lines(rng, a.n),
               run_lines(rng, a.n, log_y=True), run_pies(rng, a.n)]
    receipt = {
        "receipt_type": "CHART_KERNEL_SYNTHETIC_MEASUREMENT_V1",
        "credit_claimed": 0,
        "benchmark_data_touched": False,
        "calibration_source": "renderer_true_transform (tick-OCR cell measured separately)",
        "seed": a.seed, "n_per_family": a.n, "elapsed_s": round(time.time() - t0, 2),
        "families": results,
    }
    blob = json.dumps(receipt, sort_keys=True).encode()
    receipt["sha256_of_body"] = hashlib.sha256(blob).hexdigest()
    text = json.dumps(receipt, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text + "\n")
    print(json.dumps([{k: v for k, v in r.items() if k != "failures"} for r in results], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
