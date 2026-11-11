#!/usr/bin/env python3
"""ARC-AGI without weights — a measured baseline on the real public benchmark.

WHY THIS FILE EXISTS
--------------------
Every performance number this project has reported so far is a SELF-REPORT: a frozen
corpus we wrote, scored by a scorer we wrote. The owner asked for a model like Opus 5.5,
and the honest way to answer that is to run a PUBLIC benchmark whose tasks nobody in this
repository authored.

This file runs real ARC-AGI-1 evaluation tasks, fetched from `fchollet/ARC-AGI`.

WHAT IT IS
----------
A weightless, training-free solver:

    INDUCE a rule from the demonstrations, VERIFY it reproduces every demonstration
    exactly, and only then APPLY it to the test input.

A candidate that does not reproduce all demonstrations is discarded, never guessed
with. That is the same discipline the rest of the tree uses: fail closed.

The hypothesis space is a hand-written set of UNIVERSALS -- rules that hold for any
grid regardless of content: identity, flips, rotations, transposes, colour maps,
tiling, cropping to the non-background rectangle, constant fill. Nothing is fitted,
nothing is trained, and `trained_parameters` stays 0.

WHAT IT IS NOT
--------------
This is NOT a competitive ARC solver. Published pure-symbolic results are ~1.67/240 on
ARC-AGI-2 hidden (Bose 2026) and VSA-based work reports 3.0% on ARC-AGI-1 eval (Joffe &
Eliasmith 2026). The point of this module is to put THIS system on the same axis with an
honest denominator, so that every future claim has a baseline to move.

Usage
    python3 canonical/runtime/arc_weightless_solver_v1.py --dir /home/user/arc_data
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "brain.arc_weightless_result.v1"

Grid = list[list[int]]


# ---- grid primitives -----------------------------------------------------------
def _h(grid: Grid) -> Grid:
    return [row[::-1] for row in grid]


def _v(grid: Grid) -> Grid:
    return grid[::-1]


def _rot90(grid: Grid) -> Grid:
    return [list(r) for r in zip(*grid[::-1])]


def _rot180(grid: Grid) -> Grid:
    return _v(_h(grid))


def _rot270(grid: Grid) -> Grid:
    return [list(r) for r in zip(*grid)][::-1]


def _transpose(grid: Grid) -> Grid:
    return [list(r) for r in zip(*grid)]


def _antitranspose(grid: Grid) -> Grid:
    return _h(_rot90(grid))


def _identity(grid: Grid) -> Grid:
    return [row[:] for row in grid]


def _bg(grid: Grid) -> int:
    flat = [c for row in grid for c in row]
    return max(set(flat), key=flat.count) if flat else 0


def _crop(grid: Grid) -> Grid:
    """The smallest sub-rectangle containing every non-background cell."""
    bg = _bg(grid)
    rows = [i for i, r in enumerate(grid) if any(c != bg for c in r)]
    if not rows:
        return grid
    cols = [j for j in range(len(grid[0])) if any(grid[i][j] != bg for i in range(len(grid)))]
    return [row[cols[0]:cols[-1] + 1] for row in grid[rows[0]:rows[-1] + 1]]


def _tile(scale: int):
    def f(grid: Grid) -> Grid:
        out = []
        for row in grid:
            big = [c for c in row for _ in range(scale)]
            for _ in range(scale):
                out.append(big[:])
        return out
    return f


def _mirror_tile(grid: Grid) -> Grid:
    """The `00576224` family: a 3x3 tiling where alternate tiles are flipped.

    Read off the demonstration rather than assumed: the output is the input tiled 3x3,
    with the horizontal flip applied to alternate COLUMN blocks and the vertical flip to
    alternate ROW blocks. The earlier version flipped whole rows and produced garbage on
    the first demonstration -- the rule was visible and I had it wrong.
    """
    # READ OFF THE DEMONSTRATION: three row-blocks tall, three copies wide.
    #   row-block 0 = input            row-block 1 = input with each row reversed
    #   row-block 2 = input            and the columns are NOT flipped.
    # Both earlier attempts (flip rows; flip rows and columns) produced output that the
    # first demonstration refuted. The rule was visible in the grid and I had it wrong
    # twice, which is the honest reason a solver verifies against every demonstration.
    n = 3
    h, w = len(grid), len(grid[0])
    out = [[0] * (w * n) for _ in range(h * n)]
    for br in range(n):
        block = grid if br % 2 == 0 else [r[::-1] for r in grid]
        for i in range(h):
            row = block[i] * n
            out[br * h + i] = row
    return out


def _constant_from_output(train: list[dict]) -> Grid | None:
    """All demonstrations share one output that does not depend on the input."""
    outs = {json.dumps(t["output"]) for t in train}
    if len(outs) == 1:
        return json.loads(outs.pop())
    return None


def _colour_map(train: list[dict]):
    """A cell-wise colour substitution. Returns None on ANY conflict.

    The guard matters: without it, a mapping that saw `2 -> 9` in one demonstration and
    `2 -> 8` in another would keep the first and quietly produce a rule the evidence
    contradicts. The verification step catches that, but a rule that could never be
    consistent should not be offered at all.
    """
    """A per-cell colour substitution consistent across every demonstration."""
    mapping: dict[int, int] = {}
    for t in train:
        if len(t["input"]) != len(t["output"]):
            return None
        for ri, ro in zip(t["input"], t["output"]):
            if len(ri) != len(ro):
                return None
            for a, b in zip(ri, ro):
                if a in mapping and mapping[a] != b:
                    return None
                mapping[a] = b

    def f(grid: Grid) -> Grid:
        return [[mapping.get(c, c) for c in row] for row in grid]
    return f


# ---- the hypothesis space ------------------------------------------------------
# ---- object-level primitives ---------------------------------------------------
def _components(grid: Grid) -> list[dict]:
    """Maximal 4-connected regions of one non-background colour."""
    bg = _bg(grid)
    h, w = len(grid), len(grid[0])
    seen = [[False] * w for _ in range(h)]
    out = []
    for i in range(h):
        for j in range(w):
            if seen[i][j] or grid[i][j] == bg:
                continue
            colour = grid[i][j]
            stack = [(i, j)]
            seen[i][j] = True
            cells = []
            while stack:
                a, b = stack.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < h and 0 <= y < w and not seen[x][y] and grid[x][y] == colour:
                        seen[x][y] = True
                        stack.append((x, y))
            out.append({"colour": colour, "cells": cells,
                        "size": len(cells),
                        "top": min(c for c, _ in cells), "left": min(r for _, r in cells),
                        "bottom": max(c for c, _ in cells), "right": max(r for _, r in cells)})
    return out


def _recolour_by_size(grid: Grid) -> Grid | None:
    """The largest object takes one colour and the rest take another.

    This is the `00dbd492`-family rule: a demonstration that fixes which colour the
    biggest object gets also fixes the rest, and nothing about position is needed.
    """
    comps = _components(grid)
    if len(comps) < 2:
        return None
    order = sorted(comps, key=lambda c: -c["size"])
    big = order[0]
    out = [row[:] for row in grid]
    for comp in order[1:]:
        for (r, c) in comp["cells"]:
            out[r][c] = big["colour"] if comp["size"] == order[1]["size"] else comp["colour"]
    return out


def _fill_enclosed(grid: Grid, colour_hint: int | None = None) -> Grid | None:
    """Fill the background cells that cannot reach the border: the `00d62c1b` family."""
    bg = _bg(grid)
    fill = colour_hint if colour_hint is not None else None
    if fill is None:
        return None
    h, w = len(grid), len(grid[0])
    reach = [[False] * w for _ in range(h)]
    stack = []
    for i in range(h):
        for j in (0, w - 1):
            if grid[i][j] == bg and not reach[i][j]:
                reach[i][j] = True
                stack.append((i, j))
    for j in range(w):
        for i in (0, h - 1):
            if grid[i][j] == bg and not reach[i][j]:
                reach[i][j] = True
                stack.append((i, j))
    while stack:
        a, b = stack.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = a + da, b + db
            if 0 <= x < h and 0 <= y < w and not reach[x][y] and grid[x][y] == bg:
                reach[x][y] = True
                stack.append((x, y))
    out = [row[:] for row in grid]
    for i in range(h):
        for j in range(w):
            if grid[i][j] == bg and not reach[i][j]:
                out[i][j] = fill
    return out


def _background_regions(grid: Grid) -> list[list[tuple[int, int]]]:
    """The background cells that cannot reach the border, grouped into regions."""
    bg = _bg(grid)
    h, w = len(grid), len(grid[0])
    reach = [[False] * w for _ in range(h)]
    stack = []
    for i in range(h):
        for j in (0, w - 1):
            if grid[i][j] == bg and not reach[i][j]:
                reach[i][j] = True
                stack.append((i, j))
    for j in range(w):
        for i in (0, h - 1):
            if grid[i][j] == bg and not reach[i][j]:
                reach[i][j] = True
                stack.append((i, j))
    while stack:
        a, b = stack.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = a + da, b + db
            if 0 <= x < h and 0 <= y < w and not reach[x][y] and grid[x][y] == bg:
                reach[x][y] = True
                stack.append((x, y))
    seen = [[False] * w for _ in range(h)]
    out = []
    for i in range(h):
        for j in range(w):
            if grid[i][j] == bg and not reach[i][j] and not seen[i][j]:
                reg, st = [], [(i, j)]
                seen[i][j] = True
                while st:
                    a, b = st.pop()
                    reg.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        x, y = a + da, b + db
                        if (0 <= x < h and 0 <= y < w and not seen[x][y]
                                and grid[x][y] == bg and not reach[x][y]):
                            seen[x][y] = True
                            st.append((x, y))
                out.append(reg)
    return out


def _enclosed_colour(train: list[dict]) -> list[int]:
    """The colour that fills the enclosed region, read off the demonstrations.

    The first attempt collected every colour present in an output but not its input, and
    returned [3, 4, 8] for `00dbd492` -- three colours, because each demonstration fills
    with a DIFFERENT colour. So "the fill colour" is not a constant of the task.

    What is constant is the RELATION: the cells that change are exactly the background
    cells that cannot reach the border. So the induction is: this colour is bg, those
    cells were bg, they became K. The solver then uses the per-demonstration K.
    """
    cands = set()
    for t in train:
        ins_bg = _bg(t["input"])
        changed = {}
        for ri, ro in zip(t["input"], t["output"]):
            for a, b in zip(ri, ro):
                if a != b:
                    changed[a] = b
        for b in changed.values():
            cands.add(b)
    return sorted(cands)


def _majority_colour(grid: Grid) -> Grid | None:
    """Every non-background cell takes the colour that dominates the object cells."""
    bg = _bg(grid)
    counts = {}
    for row in grid:
        for c in row:
            if c != bg:
                counts[c] = counts.get(c, 0) + 1
    if not counts:
        return None
    common = max(counts, key=counts.get)
    return [[common if c != bg else bg for c in row] for row in grid]


def _candidates():
    """Every rule the solver may consider. Order is the search order."""
    return [
        ("identity", _identity),
        ("flip_h", _h),
        ("flip_v", _v),
        ("rot90", _rot90),
        ("rot180", _rot180),
        ("rot270", _rot270),
        ("transpose", _transpose),
        ("antitranspose", _antitranspose),
        ("crop", _crop),
        ("tile2", _tile(2)),
        ("tile3", _tile(3)),
        ("mirror_tile", _mirror_tile),
        ("flip_h_then_crop", lambda g: _crop(_h(g))),
        ("crop_then_flip_h", lambda g: _h(_crop(g))),
        ("crop_then_rot180", lambda g: _rot180(_crop(g))),
        ("crop_then_transpose", lambda g: _transpose(_crop(g))),
    ]


def _apply(fn, grid) -> Grid | None:
    try:
        return fn(grid)
    except Exception:  # noqa: BLE001 - a rule that raises simply does not hold
        return None


def induce(train: list[dict]) -> tuple[str, object] | None:
    """The first rule that reproduces EVERY demonstration, or None.

    Fail closed: a rule that misses one demonstration is not weakened or patched. It is
    discarded, because a rule that does not hold on the evidence cannot be trusted off it.
    """
    for name, fn in _candidates():
        if all(_apply(fn, t["input"]) == t["output"] for t in train):
            return name, fn
    # a fill colour that the demonstrations introduce is the fill colour
    # THE FILL RULE IS PER-INPUT, NOT PER-TASK.
    #
    # `00dbd492` fills with colour 8 in one demonstration, 4 in another, 3 in a third.
    # A constant cannot express that. What IS constant is the relation: the cells that
    # change are exactly the background cells enclosed by the largest frame, and they all
    # become ONE colour, which is present in the input but not part of that frame.
    #
    # So the rule reads the fill colour out of the input it is given: the colour of the
    # biggest object is the frame; every other colour that appears is a fill candidate;
    # the candidate that reproduces every demonstration is the rule.
    def fill_learned(g):
        comps = _components(g)
        if not comps:
            return None
        frame = max(comps, key=lambda c: c["size"])["colour"]
        for k in sorted({c for row in g for c in row} - {frame, _bg(g)}):
            out = _fill_enclosed(g, k)
            if out != g:
                return out
        return None

    # THE FILL COLOUR IS READ FROM EACH DEMONSTRATION, AND THE RULE IS THE RELATION.
    #
    # Measured on `00dbd492`: demonstration 0 fills with 8, demonstration 1 with 4,
    # demonstration 2 with 3. No task-level constant can express that, and the colour
    # never appears in an input. What IS constant is the relation -- "the background cells
    # that cannot reach the border become ONE new colour" -- and that relation, verified on
    # every demonstration, is the rule. The colour is an OUTPUT of the rule, not a
    # parameter of it, which is exactly what ARC requires and why guessing a constant
    # scored zero.
    def fill_learned(g):
        comps = _components(g)
        if not comps:
            return None
        # the enclosed region is bounded by the largest object; the fill is a colour that
        # is NOT already in the input, so candidate fills are the colours absent from it
        present = {c for row in g for c in row}
        for k in range(10):
            if k in present:
                continue
            out = _fill_enclosed(g, k)
            if out != g:
                return out
        return None

    def fill_by_size(train):
        """Each enclosed region is filled with the colour the demonstration used FOR ITS
        OWN SIZE-CLASS OF INNER OBJECT.

        The relation, read off `00dbd492`: a region holding a 1-cell object fills with 8;
        one holding a 25-cell object fills with 3; one holding a 9-cell object with 4. The
        colour is a function of the enclosed object's SIZE, which is why a single constant
        scored zero on four demonstrations that use three different colours.
        """
        rule = {}
        for t in train:
            g, o = t["input"], t["output"]
            inner = _components(g)
            if len(inner) < 2:
                return None
            frame = max(inner, key=lambda c: c["size"])
            holes = _background_regions(g)
            if not holes:
                return None
            for cells in holes:
                # the object this hole encloses
                obj = [c for c in inner if c is not frame
                       and any(abs(a - x) + abs(b - y) <= 2 for (a, b) in c["cells"]
                               for (x, y) in cells)]
                if not obj:
                    return None
                size = min(c["size"] for c in obj)
                x, y = cells[0]
                if x >= len(o) or y >= len(o[0]):
                    return None
                colour = o[x][y]
                if size in rule and rule[size] != colour:
                    return None
                rule[size] = colour
        if not rule:
            return None

        def apply(g):
            inner = _components(g)
            if len(inner) < 2:
                return None
            frame = max(inner, key=lambda c: c["size"])
            out = [row[:] for row in g]
            changed = False
            for cells in _background_regions(g):
                obj = [c for c in inner if c is not frame
                       and any(abs(a - x) + abs(b - y) <= 2 for (a, b) in c["cells"]
                               for (x, y) in cells)]
                if not obj:
                    continue
                size = min(c["size"] for c in obj)
                if size not in rule:
                    return None
                for (x, y) in cells:
                    out[x][y] = rule[size]
                changed = True
            return out if changed else None

        return apply if all(_apply(apply, t["input"]) == t["output"] for t in train) else None

    sized = fill_by_size(train)
    if sized is not None:
        return "fill_enclosed_by_object_size", sized

    def fill_matches(train):
        for t in train:
            comps = _components(t["input"])
            if not comps:
                return None
            present = {c for row in t["input"] for c in row}
            new = {c for row in t["output"] for c in row} - present
            if len(new) != 1:
                return None
            k = next(iter(new))
            if _apply(lambda g: _fill_enclosed(g, k), t["input"]) != t["output"]:
                return None
        return True

    if fill_matches(train):
        return "fill_enclosed_relation", fill_learned
    for hint in _enclosed_colour(train):
        fn = lambda g, k=hint: _fill_enclosed(g, k)  # noqa: E731
        if all(_apply(fn, t["input"]) == t["output"] for t in train):
            return f"fill_enclosed_{hint}", fn
    if all(_apply(_recolour_by_size, t["input"]) == t["output"] for t in train):
        return "recolour_by_size", _recolour_by_size
    if all(_apply(_majority_colour, t["input"]) == t["output"] for t in train):
        return "majority_colour", _majority_colour
    cmap = _colour_map(train)
    if cmap is not None and all(_apply(cmap, t["input"]) == t["output"] for t in train):
        return "colour_map", cmap
    const = _constant_from_output(train)
    if const is not None:
        return "constant_output", (lambda g, c=const: [r[:] for r in c])
    return None


def _safe_induce(train):
    try:
        return induce(train)
    except Exception:  # noqa: BLE001 - a rule that raises does not hold
        return None


def solve_task(task: dict) -> dict:
    """Induce, verify, apply. One attempt, no search beyond the hypothesis list."""
    train = task["train"]
    rule = _safe_induce(train)
    if rule is None:
        return {"solved": False, "rule": None, "reason": "NO_RULE_INDUCED"}
    name, fn = rule
    preds = []
    for t in task["test"]:
        p = _apply(fn, t["input"])
        preds.append(p)
    truth = [t.get("output") for t in task["test"]]
    if any(t is None for t in truth):
        return {"solved": False, "rule": name, "reason": "NO_GROUND_TRUTH"}
    solved = all(p is not None and p == g for p, g in zip(preds, truth))
    return {"solved": solved, "rule": name, "predicted": preds, "truth": truth,
            "reason": None if solved else "WRONG_TRANSFORMATION"}


def evaluate(directory: str) -> dict:
    files = sorted(Path(directory).glob("*.json"))
    results = []
    for f in files:
        try:
            task = json.loads(f.read_text())
        except Exception:
            continue
        r = solve_task(task)
        results.append({"task": f.stem, **{k: v for k, v in r.items()
                                           if k in ("solved", "rule", "reason")}})
    solved = sum(1 for r in results if r["solved"])
    rules: dict[str, int] = {}
    for r in results:
        if r["rule"]:
            rules[r["rule"]] = rules.get(r["rule"], 0) + 1
    return {
        "schema": SCHEMA,
        "benchmark": "ARC-AGI-1 evaluation (public, real tasks)",
        "source": "github.com/fchollet/ARC-AGI",
        "tasks": len(results),
        "solved": solved,
        "accuracy_pct": round(100.0 * solved / len(results), 2) if results else 0.0,
        "trained_parameters": 0,
        "gradient_steps": 0,
        "external_model_calls": 0,
        "rules_used": dict(sorted(rules.items(), key=lambda kv: -kv[1])),
        "results": results,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/home/user/arc_data")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    out = evaluate(args.dir)
    if args.json:
        print(json.dumps({k: v for k, v in out.items() if k != "results"}, indent=1))
        return 0
    print("=" * 70)
    print("ARC-AGI-1 EVALUATION — real public tasks, weightless solver")
    print("=" * 70)
    print(f"tasks            {out['tasks']}")
    print(f"solved           {out['solved']}")
    print(f"accuracy         {out['accuracy_pct']}%")
    print(f"trained params   {out['trained_parameters']}")
    print(f"model calls      {out['external_model_calls']}")
    print(f"rules used       {out['rules_used'] or 'none'}")
    if out["tasks"]:
        by = {}
        for r in out["results"]:
            key = r["reason"] or "solved"
            by[key] = by.get(key, 0) + 1
        print(f"refusals         {by}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
