"""Deterministic ARC novelty compiler V1.

Purpose
-------
Convert raw ARC-style integer grids into explicit scene structure plus a bounded
set of falsifiable transformation hypotheses. This module deliberately does not
claim universal ARC coverage. It supplies the missing upstream bridge required
by downstream Brain machinery that already knows how to preserve, rank, test,
verify, and replan over explicit hypotheses.

Design laws
-----------
* raw grids in, structured hypotheses out;
* preserve ambiguity instead of ranking unsupported guesses;
* every emitted hypothesis must reproduce every supplied training pair exactly;
* fail closed on malformed grids;
* declare the grammar boundary explicitly so bounded success cannot masquerade
  as open-world completeness.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ARC_NOVELTY_COMPILER_V1"
Grid = tuple[tuple[int, ...], ...]


class ARCNoveltyCompilerError(ValueError):
    pass


def _grid(value: Sequence[Sequence[int]], label: str = "grid") -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ARCNoveltyCompilerError(label.upper() + "_INVALID")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw_row in value:
        if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes)) or not raw_row:
            raise ARCNoveltyCompilerError(label.upper() + "_ROW_INVALID")
        row: list[int] = []
        for cell in raw_row:
            if not isinstance(cell, int) or isinstance(cell, bool) or not 0 <= cell <= 9:
                raise ARCNoveltyCompilerError(label.upper() + "_CELL_INVALID")
            row.append(cell)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ARCNoveltyCompilerError(label.upper() + "_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _tolist(grid: Grid) -> list[list[int]]:
    return [list(row) for row in grid]


def _shape(grid: Grid) -> tuple[int, int]:
    return len(grid), len(grid[0])


def _background(grid: Grid) -> int:
    counts = Counter(cell for row in grid for cell in row)
    return min(counts, key=lambda c: (-counts[c], c))


def _rot90(grid: Grid) -> Grid:
    return tuple(tuple(row) for row in zip(*grid[::-1]))


def _rot180(grid: Grid) -> Grid:
    return tuple(tuple(reversed(row)) for row in reversed(grid))


def _rot270(grid: Grid) -> Grid:
    return tuple(tuple(row) for row in zip(*grid))[::-1]


def _flip_h(grid: Grid) -> Grid:
    return tuple(tuple(reversed(row)) for row in grid)


def _flip_v(grid: Grid) -> Grid:
    return tuple(reversed(grid))


def _transpose(grid: Grid) -> Grid:
    return tuple(tuple(row) for row in zip(*grid))


def _anti_transpose(grid: Grid) -> Grid:
    return _rot180(_transpose(grid))


_GEOMETRIES = {
    "IDENTITY": lambda g: g,
    "ROTATE_90": _rot90,
    "ROTATE_180": _rot180,
    "ROTATE_270": _rot270,
    "FLIP_HORIZONTAL": _flip_h,
    "FLIP_VERTICAL": _flip_v,
    "TRANSPOSE": _transpose,
    "ANTI_TRANSPOSE": _anti_transpose,
}


@dataclass(frozen=True)
class Component:
    color: int
    cells: tuple[tuple[int, int], ...]
    bbox: tuple[int, int, int, int]

    @property
    def area(self) -> int:
        return len(self.cells)

    @property
    def normalized_cells(self) -> tuple[tuple[int, int], ...]:
        r0, c0, _, _ = self.bbox
        return tuple((r - r0, c - c0) for r, c in self.cells)


def _components(grid: Grid, background: int | None = None) -> list[Component]:
    bg = _background(grid) if background is None else background
    h, w = _shape(grid)
    seen: set[tuple[int, int]] = set()
    out: list[Component] = []
    for r in range(h):
        for c in range(w):
            color = grid[r][c]
            if color == bg or (r, c) in seen:
                continue
            q = deque([(r, c)])
            seen.add((r, c))
            cells: list[tuple[int, int]] = []
            while q:
                rr, cc = q.popleft()
                cells.append((rr, cc))
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and grid[nr][nc] == color:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            cells.sort()
            rs = [x[0] for x in cells]
            cs = [x[1] for x in cells]
            out.append(Component(color, tuple(cells), (min(rs), min(cs), max(rs), max(cs))))
    out.sort(key=lambda x: (x.color, x.bbox, x.cells))
    return out


def _crop_bbox(grid: Grid, bbox: tuple[int, int, int, int]) -> Grid:
    r0, c0, r1, c1 = bbox
    return tuple(tuple(grid[r][c0 : c1 + 1]) for r in range(r0, r1 + 1))


def _non_background_bbox(grid: Grid) -> tuple[int, int, int, int] | None:
    bg = _background(grid)
    cells = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v != bg]
    if not cells:
        return None
    rs = [x[0] for x in cells]
    cs = [x[1] for x in cells]
    return min(rs), min(cs), max(rs), max(cs)


def describe_scene(value: Sequence[Sequence[int]]) -> dict[str, Any]:
    grid = _grid(value)
    bg = _background(grid)
    comps = _components(grid, bg)
    return {
        "shape": list(_shape(grid)),
        "background": bg,
        "colors": sorted(set(cell for row in grid for cell in row)),
        "components": [
            {
                "component_id": f"c{i}",
                "color": c.color,
                "area": c.area,
                "bbox": list(c.bbox),
                "normalized_cells": [list(x) for x in c.normalized_cells],
            }
            for i, c in enumerate(comps)
        ],
    }


def _apply_recolor(grid: Grid, mapping: Mapping[int, int]) -> Grid:
    return tuple(tuple(mapping.get(v, v) for v in row) for row in grid)


def _scale_pixels(grid: Grid, row_factor: int, col_factor: int) -> Grid:
    if row_factor < 1 or col_factor < 1:
        raise ARCNoveltyCompilerError("SCALE_FACTOR_INVALID")
    rows: list[tuple[int, ...]] = []
    for row in grid:
        expanded = tuple(v for v in row for _ in range(col_factor))
        for _ in range(row_factor):
            rows.append(expanded)
    return tuple(rows)


def _infer_recolor(pairs: Sequence[tuple[Grid, Grid]]) -> dict[int, int] | None:
    mapping: dict[int, int] = {}
    for inp, out in pairs:
        if _shape(inp) != _shape(out):
            return None
        for r in range(len(inp)):
            for c in range(len(inp[0])):
                src, dst = inp[r][c], out[r][c]
                old = mapping.get(src)
                if old is not None and old != dst:
                    return None
                mapping[src] = dst
    return mapping if mapping else None


def _component_crop(grid: Grid, which: str) -> Grid | None:
    comps = _components(grid)
    if not comps:
        return None
    if which == "LARGEST":
        best_area = max(c.area for c in comps)
        choices = [c for c in comps if c.area == best_area]
    elif which == "SMALLEST":
        best_area = min(c.area for c in comps)
        choices = [c for c in comps if c.area == best_area]
    else:
        raise AssertionError(which)
    if len(choices) != 1:
        return None
    return _crop_bbox(grid, choices[0].bbox)


def _predict(h: Mapping[str, Any], grid: Grid) -> Grid | None:
    kind = h["kind"]
    if kind == "GLOBAL_GEOMETRY":
        return _GEOMETRIES[h["operator"]](grid)
    if kind == "RECOLOR":
        mapping = {int(k): int(v) for k, v in h["mapping"].items()}
        return _apply_recolor(grid, mapping)
    if kind == "PIXEL_SCALE":
        return _scale_pixels(grid, int(h["row_factor"]), int(h["col_factor"]))
    if kind == "CROP_NON_BACKGROUND":
        bbox = _non_background_bbox(grid)
        return None if bbox is None else _crop_bbox(grid, bbox)
    if kind == "SELECT_COMPONENT_CROP":
        return _component_crop(grid, h["selector"])
    raise ARCNoveltyCompilerError("HYPOTHESIS_KIND_UNSUPPORTED")


def _consistent(h: Mapping[str, Any], pairs: Sequence[tuple[Grid, Grid]]) -> bool:
    for inp, expected in pairs:
        predicted = _predict(h, inp)
        if predicted is None or predicted != expected:
            return False
    return True


def compile_hypotheses(
    training_pairs: Sequence[Mapping[str, Sequence[Sequence[int]]]],
) -> dict[str, Any]:
    if not isinstance(training_pairs, Sequence) or isinstance(training_pairs, (str, bytes)) or not training_pairs:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TRAINING_PAIRS_INVALID"}

    pairs: list[tuple[Grid, Grid]] = []
    scenes: list[dict[str, Any]] = []
    try:
        for i, raw in enumerate(training_pairs):
            if not isinstance(raw, Mapping) or "input" not in raw or "output" not in raw:
                raise ARCNoveltyCompilerError(f"PAIR_{i}_INVALID")
            inp = _grid(raw["input"], f"pair_{i}_input")
            out = _grid(raw["output"], f"pair_{i}_output")
            pairs.append((inp, out))
            scenes.append({"pair_index": i, "input": describe_scene(inp), "output": describe_scene(out)})
    except ARCNoveltyCompilerError as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": str(exc)}

    candidates: list[dict[str, Any]] = []

    for operator in _GEOMETRIES:
        h = {"kind": "GLOBAL_GEOMETRY", "operator": operator}
        if _consistent(h, pairs):
            candidates.append(h)

    recolor = _infer_recolor(pairs)
    if recolor is not None:
        h = {"kind": "RECOLOR", "mapping": {str(k): v for k, v in sorted(recolor.items())}}
        if _consistent(h, pairs):
            candidates.append(h)

    scale_factors: set[tuple[int, int]] = set()
    for inp, out in pairs:
        ih, iw = _shape(inp)
        oh, ow = _shape(out)
        if oh % ih == 0 and ow % iw == 0:
            rf, cf = oh // ih, ow // iw
            if rf >= 1 and cf >= 1 and (rf > 1 or cf > 1):
                scale_factors.add((rf, cf))
    if len(scale_factors) == 1:
        rf, cf = next(iter(scale_factors))
        h = {"kind": "PIXEL_SCALE", "row_factor": rf, "col_factor": cf}
        if _consistent(h, pairs):
            candidates.append(h)

    crop = {"kind": "CROP_NON_BACKGROUND"}
    if _consistent(crop, pairs):
        candidates.append(crop)

    for selector in ("LARGEST", "SMALLEST"):
        h = {"kind": "SELECT_COMPONENT_CROP", "selector": selector}
        if _consistent(h, pairs):
            candidates.append(h)

    seen: set[str] = set()
    emitted: list[dict[str, Any]] = []
    import json

    for h in candidates:
        key = json.dumps(h, sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        hid = f"arc-h{len(emitted):03d}"
        emitted.append(
            {
                "id": hid,
                **h,
                "plausible": True,
                "falsifiable": True,
                "support_pairs": len(pairs),
                "training_exact_match": True,
            }
        )

    return {
        "schema": SCHEMA,
        "status": "HYPOTHESES" if emitted else "NO_HYPOTHESIS_IN_DECLARED_GRAMMAR",
        "training_pair_count": len(pairs),
        "scenes": scenes,
        "hypotheses": emitted,
        "hypothesis_count": len(emitted),
        "grammar": [
            "GLOBAL_DIHEDRAL_GEOMETRY",
            "POSITIONWISE_DETERMINISTIC_RECOLOR",
            "EXACT_INTEGER_PIXEL_SCALE",
            "NON_BACKGROUND_BOUNDING_BOX_CROP",
            "UNIQUE_LARGEST_OR_SMALLEST_COMPONENT_CROP",
        ],
        "completeness_scope": "COMPLETE_ONLY_RELATIVE_TO_DECLARED_V1_HYPOTHESIS_GRAMMAR",
        "open_world_complete": False,
        "ranking_performed": False,
        "terminal_authority": False,
        "semantic_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
    }


def predict(hypothesis: Mapping[str, Any], grid: Sequence[Sequence[int]]) -> dict[str, Any]:
    try:
        g = _grid(grid)
        out = _predict(hypothesis, g)
    except (ARCNoveltyCompilerError, KeyError, TypeError, ValueError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}
    if out is None:
        return {"schema": SCHEMA, "status": "UNDEFINED_FOR_INPUT", "prediction": None}
    return {"schema": SCHEMA, "status": "PREDICTED", "prediction": _tolist(out), "terminal_authority": False}
