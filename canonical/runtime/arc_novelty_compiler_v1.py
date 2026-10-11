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


def _top_left_bbox_quadrant(grid: Grid) -> Grid | None:
    bbox = _non_background_bbox(grid)
    if bbox is None:
        return None
    cropped = _crop_bbox(grid, bbox)
    h, w = _shape(cropped)
    return tuple(tuple(row[: (w + 1) // 2]) for row in cropped[: (h + 1) // 2])


def _spans(flags: list[bool]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, flag in enumerate([*flags, False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            out.append((start, i))
            start = None
    return out


def _separator_panels(grid: Grid) -> list[Grid]:
    bg = _background(grid)
    h, w = _shape(grid)
    row_spans = _spans([not all(v == bg for v in grid[r]) for r in range(h)])
    col_spans = _spans([not all(grid[r][c] == bg for r in range(h)) for c in range(w)])
    if len(row_spans) * len(col_spans) <= 1:
        return []
    panels: list[Grid] = []
    for r0, r1 in row_spans:
        for c0, c1 in col_spans:
            panels.append(tuple(tuple(grid[r][c0:c1]) for r in range(r0, r1)))
    return panels


def _select_unique_color_panel(grid: Grid) -> Grid | None:
    panels = _separator_panels(grid)
    if not panels:
        return None
    bg = _background(grid)
    palettes = [
        {v for row in panel for v in row if v != bg}
        for panel in panels
    ]
    color_frequency = Counter(color for palette in palettes for color in palette)
    candidates = [
        panel
        for panel, palette in zip(panels, palettes)
        if any(color_frequency[color] == 1 for color in palette)
    ]
    return candidates[0] if len(candidates) == 1 else None


def _split_equal_panels(grid: Grid, orientation: str) -> tuple[Grid, Grid] | None:
    h, w = _shape(grid)
    if orientation == "VERTICAL":
        if w < 3 or w % 2 == 0:
            return None
        c = w // 2
        sep = [grid[r][c] for r in range(h)]
        if len(set(sep)) != 1:
            return None
        left = tuple(tuple(row[:c]) for row in grid)
        right = tuple(tuple(row[c + 1 :]) for row in grid)
        return left, right if _shape(left) == _shape(right) else None
    if orientation == "HORIZONTAL":
        if h < 3 or h % 2 == 0:
            return None
        r = h // 2
        if len(set(grid[r])) != 1:
            return None
        top = tuple(tuple(row) for row in grid[:r])
        bottom = tuple(tuple(row) for row in grid[r + 1 :])
        return top, bottom if _shape(top) == _shape(bottom) else None
    raise ARCNoveltyCompilerError("PANEL_ORIENTATION_INVALID")


def _panel_relation_predict(grid: Grid, orientation: str, mapping: Mapping[str, int]) -> Grid | None:
    split = _split_equal_panels(grid, orientation)
    if split is None:
        return None
    a, b = split
    out: list[tuple[int, ...]] = []
    for r in range(len(a)):
        row: list[int] = []
        for c in range(len(a[0])):
            key = f"{0 if a[r][c] == 0 else 1}{0 if b[r][c] == 0 else 1}"
            if key not in mapping:
                return None
            row.append(int(mapping[key]))
        out.append(tuple(row))
    return tuple(out)


def _infer_panel_relation(
    pairs: Sequence[tuple[Grid, Grid]],
    orientation: str,
) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for inp, out in pairs:
        split = _split_equal_panels(inp, orientation)
        if split is None:
            return None
        a, b = split
        if _shape(out) != _shape(a):
            return None
        for r in range(len(a)):
            for c in range(len(a[0])):
                key = f"{0 if a[r][c] == 0 else 1}{0 if b[r][c] == 0 else 1}"
                target = out[r][c]
                if key in mapping and mapping[key] != target:
                    return None
                mapping[key] = target
    return mapping if mapping else None


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


def _hcat(a: Grid, b: Grid) -> Grid | None:
    if len(a) != len(b):
        return None
    return tuple(tuple(x) + tuple(y) for x, y in zip(a, b))


def _vcat(a: Grid, b: Grid) -> Grid | None:
    if len(a[0]) != len(b[0]):
        return None
    return tuple(tuple(row) for row in (*a, *b))


def _self_kronecker(grid: Grid) -> Grid:
    h, w = _shape(grid)
    out: list[tuple[int, ...]] = []
    zero_block = tuple(tuple(0 for _ in range(w)) for _ in range(h))
    for br in range(h):
        blocks = [grid if grid[br][bc] != 0 else zero_block for bc in range(w)]
        for rr in range(h):
            row: list[int] = []
            for block in blocks:
                row.extend(block[rr])
            out.append(tuple(row))
    return tuple(out)


def _rotational_quad(grid: Grid) -> Grid | None:
    tl = grid
    tr = _rot90(grid)
    bl = _rot270(grid)
    br = _rot180(grid)
    if not (_shape(tl) == _shape(tr) == _shape(bl) == _shape(br)):
        return None
    top = _hcat(tl, tr)
    bottom = _hcat(bl, br)
    return None if top is None or bottom is None else _vcat(top, bottom)


def _repeat_grid(grid: Grid, row_repeats: int, col_repeats: int) -> Grid:
    if row_repeats < 1 or col_repeats < 1:
        raise ARCNoveltyCompilerError("REPEAT_FACTOR_INVALID")
    row_block = tuple(tuple(v for _ in range(col_repeats) for v in row) for row in grid)
    return tuple(row for _ in range(row_repeats) for row in row_block)


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


def _zero_components(grid: Grid) -> list[Component]:
    h, w = _shape(grid)
    seen: set[tuple[int, int]] = set()
    out: list[Component] = []
    for r in range(h):
        for c in range(w):
            color = grid[r][c]
            if color == 0 or (r, c) in seen:
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


def _object_feature(component: Component, feature: str) -> str:
    r0, c0, r1, c1 = component.bbox
    h = r1 - r0 + 1
    w = c1 - c0 + 1
    if feature == "BBOX":
        return f"{h}x{w}"
    if feature == "DENSITY":
        return f"{component.area}/{h*w}"
    raise ARCNoveltyCompilerError("OBJECT_FEATURE_UNSUPPORTED")


def _connect_rows_same_color(grid: Grid) -> Grid:
    out = [list(row) for row in grid]
    for r, row in enumerate(grid):
        positions: dict[int, list[int]] = {}
        for c, value in enumerate(row):
            if value != 0:
                positions.setdefault(value, []).append(c)
        for color, cols in positions.items():
            if len(cols) >= 2:
                for c in range(min(cols), max(cols) + 1):
                    out[r][c] = color
    return tuple(tuple(row) for row in out)


def _connect_cols_same_color(grid: Grid) -> Grid:
    out = [list(row) for row in grid]
    h, w = _shape(grid)
    for c in range(w):
        positions: dict[int, list[int]] = {}
        for r in range(h):
            value = grid[r][c]
            if value != 0:
                positions.setdefault(value, []).append(r)
        for color, rows in positions.items():
            if len(rows) >= 2:
                for r in range(min(rows), max(rows) + 1):
                    out[r][c] = color
    return tuple(tuple(row) for row in out)


def _connect_both_same_color(grid: Grid) -> Grid:
    return _connect_cols_same_color(_connect_rows_same_color(grid))


def _union_grids(a: Grid, b: Grid) -> Grid | None:
    if _shape(a) != _shape(b):
        return None
    out = [list(row) for row in a]
    h, w = _shape(a)
    for r in range(h):
        for c in range(w):
            x, y = a[r][c], b[r][c]
            if x == 0:
                out[r][c] = y
            elif y == 0 or x == y:
                out[r][c] = x
            else:
                return None
    return tuple(tuple(row) for row in out)


def _complete_symmetry(grid: Grid, mode: str) -> Grid | None:
    if mode == "VERTICAL":
        other = _flip_v(grid)
    elif mode == "ROTATE_180":
        other = _rot180(grid)
    else:
        raise ARCNoveltyCompilerError("SYMMETRY_MODE_UNSUPPORTED")
    return _union_grids(grid, other)


def _fill_each_color_bbox(grid: Grid) -> Grid | None:
    out = [list(row) for row in grid]
    colors = sorted({v for row in grid for v in row if v != 0})
    for color in colors:
        pts = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v == color]
        rs = [r for r, _ in pts]
        cs = [c for _, c in pts]
        r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if out[r][c] not in (0, color):
                    return None
                out[r][c] = color
    return tuple(tuple(row) for row in out)


def _connect_same_color_diagonals(grid: Grid) -> Grid | None:
    out = [list(row) for row in grid]
    points: dict[int, list[tuple[int, int]]] = {}
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            if value != 0:
                points.setdefault(value, []).append((r, c))
    for color, pts in points.items():
        for i, (r1, c1) in enumerate(pts):
            for r2, c2 in pts[i + 1 :]:
                dr, dc = r2 - r1, c2 - c1
                if dr == 0 or abs(dr) != abs(dc):
                    continue
                sr = 1 if dr > 0 else -1
                sc = 1 if dc > 0 else -1
                for k in range(abs(dr) + 1):
                    r, c = r1 + k * sr, c1 + k * sc
                    if out[r][c] not in (0, color):
                        return None
                    out[r][c] = color
    return tuple(tuple(row) for row in out)


def _enclosed_zero_cells(grid: Grid) -> set[tuple[int, int]]:
    h, w = _shape(grid)
    outside: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()
    for r in range(h):
        for c in (0, w - 1):
            if grid[r][c] == 0 and (r, c) not in outside:
                outside.add((r, c))
                q.append((r, c))
    for c in range(w):
        for r in (0, h - 1):
            if grid[r][c] == 0 and (r, c) not in outside:
                outside.add((r, c))
                q.append((r, c))
    while q:
        r, c = q.popleft()
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == 0 and (nr, nc) not in outside:
                outside.add((nr, nc))
                q.append((nr, nc))
    return {
        (r, c)
        for r in range(h)
        for c in range(w)
        if grid[r][c] == 0 and (r, c) not in outside
    }


def _infer_enclosed_zero_fill(pairs: Sequence[tuple[Grid, Grid]]) -> int | None:
    target: int | None = None
    for inp, out in pairs:
        if _shape(inp) != _shape(out):
            return None
        holes = _enclosed_zero_cells(inp)
        if not holes:
            return None
        changed = {
            (r, c)
            for r in range(len(inp))
            for c in range(len(inp[0]))
            if inp[r][c] != out[r][c]
        }
        if changed != holes:
            return None
        values = {out[r][c] for r, c in holes}
        if len(values) != 1:
            return None
        value = next(iter(values))
        if target is not None and target != value:
            return None
        target = value
    return target


def _fill_enclosed_zero(grid: Grid, color: int) -> Grid:
    out = [list(row) for row in grid]
    for r, c in _enclosed_zero_cells(grid):
        out[r][c] = color
    return tuple(tuple(row) for row in out)


def _row_col_gravity(grid: Grid, direction: str) -> Grid:
    h, w = _shape(grid)
    out = [[0 for _ in range(w)] for _ in range(h)]
    if direction in ("LEFT", "RIGHT"):
        for r, row in enumerate(grid):
            values = [v for v in row if v != 0]
            start = 0 if direction == "LEFT" else w - len(values)
            for j, value in enumerate(values):
                out[r][start + j] = value
    elif direction in ("UP", "DOWN"):
        for c in range(w):
            values = [grid[r][c] for r in range(h) if grid[r][c] != 0]
            start = 0 if direction == "UP" else h - len(values)
            for j, value in enumerate(values):
                out[start + j][c] = value
    else:
        raise ARCNoveltyCompilerError("GRAVITY_DIRECTION_UNSUPPORTED")
    return tuple(tuple(row) for row in out)


def _visible_color(grid: Grid, r: int, c: int, dr: int, dc: int) -> int:
    h, w = _shape(grid)
    rr, cc = r + dr, c + dc
    while 0 <= rr < h and 0 <= cc < w:
        if grid[rr][cc] != 0:
            return grid[rr][cc]
        rr += dr
        cc += dc
    return -1


def _ray_color_feature(grid: Grid, r: int, c: int) -> str:
    values = [
        _visible_color(grid, r, c, 0, -1),
        _visible_color(grid, r, c, 0, 1),
        _visible_color(grid, r, c, -1, 0),
        _visible_color(grid, r, c, 1, 0),
    ]
    return f"{grid[r][c]}|" + ",".join(str(v) for v in values)


def _infer_ray_color_rule(pairs: Sequence[tuple[Grid, Grid]]) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for inp, out in pairs:
        if _shape(inp) != _shape(out):
            return None
        h, w = _shape(inp)
        for r in range(h):
            for c in range(w):
                key = _ray_color_feature(inp, r, c)
                target = out[r][c]
                if key in mapping and mapping[key] != target:
                    return None
                mapping[key] = target
    return mapping if mapping else None


def _ray_color_predict(grid: Grid, mapping: Mapping[str, int]) -> Grid | None:
    h, w = _shape(grid)
    out: list[tuple[int, ...]] = []
    for r in range(h):
        row: list[int] = []
        for c in range(w):
            key = _ray_color_feature(grid, r, c)
            if key not in mapping:
                return None
            row.append(int(mapping[key]))
        out.append(tuple(row))
    return tuple(out)


def _local_feature(grid: Grid, r: int, c: int, feature: str) -> str:
    h, w = _shape(grid)
    v = grid[r][c]
    cross: list[int] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr, cc = r + dr, c + dc
        cross.append(grid[rr][cc] if 0 <= rr < h and 0 <= cc < w else -1)
    if feature == "COLOR_COUNTS":
        n4 = sum(x not in (0, -1) for x in cross)
        n8 = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] != 0:
                    n8 += 1
        return f"{v}|{n4}|{n8}"
    if feature == "BIN_CROSS":
        bits = ",".join(str(-1 if x == -1 else 0 if x == 0 else 1) for x in cross)
        return f"{0 if v == 0 else 1}|{bits}"
    if feature == "COLOR_ROWCOL_SETS":
        row_set = ",".join(str(x) for x in sorted(set(grid[r])))
        col_set = ",".join(str(x) for x in sorted({grid[rr][c] for rr in range(h)}))
        return f"{v}|R:{row_set}|C:{col_set}"
    raise ARCNoveltyCompilerError("LOCAL_FEATURE_UNSUPPORTED")


def _infer_local_rule(
    pairs: Sequence[tuple[Grid, Grid]],
    feature: str,
) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for inp, out in pairs:
        if _shape(inp) != _shape(out):
            return None
        h, w = _shape(inp)
        for r in range(h):
            for c in range(w):
                key = _local_feature(inp, r, c, feature)
                target = out[r][c]
                if key in mapping and mapping[key] != target:
                    return None
                mapping[key] = target
    return mapping if mapping else None


def _local_rule_predict(grid: Grid, feature: str, mapping: Mapping[str, int]) -> Grid | None:
    h, w = _shape(grid)
    out: list[tuple[int, ...]] = []
    for r in range(h):
        row: list[int] = []
        for c in range(w):
            key = _local_feature(grid, r, c, feature)
            if key not in mapping:
                return None
            row.append(int(mapping[key]))
        out.append(tuple(row))
    return tuple(out)


def _infer_object_recolor(
    pairs: Sequence[tuple[Grid, Grid]],
    feature: str,
) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for inp, out in pairs:
        if _shape(inp) != _shape(out):
            return None
        h, w = _shape(inp)
        for r in range(h):
            for c in range(w):
                if inp[r][c] == 0 and out[r][c] != 0:
                    return None
        for component in _zero_components(inp):
            targets = {out[r][c] for r, c in component.cells}
            if len(targets) != 1:
                return None
            key = _object_feature(component, feature)
            target = next(iter(targets))
            if key in mapping and mapping[key] != target:
                return None
            mapping[key] = target
    return mapping if mapping else None


def _object_recolor_predict(grid: Grid, feature: str, mapping: Mapping[str, int]) -> Grid | None:
    out = [list(row) for row in grid]
    for component in _zero_components(grid):
        key = _object_feature(component, feature)
        if key not in mapping:
            return None
        target = int(mapping[key])
        for r, c in component.cells:
            out[r][c] = target
    return tuple(tuple(row) for row in out)


def _dedupe_adjacent_lines(grid: Grid) -> Grid | None:
    rows: list[tuple[int, ...]] = []
    for row in grid:
        if not rows or tuple(row) != rows[-1]:
            rows.append(tuple(row))
    if not rows:
        return None
    cols = list(zip(*rows))
    kept: list[tuple[int, ...]] = []
    for col in cols:
        t = tuple(col)
        if not kept or t != kept[-1]:
            kept.append(t)
    if not kept:
        return None
    return tuple(tuple(row) for row in zip(*kept))


def _remove_zero_lines(grid: Grid) -> Grid | None:
    rows = [tuple(row) for row in grid if any(v != 0 for v in row)]
    if not rows:
        return None
    keep = [c for c in range(len(rows[0])) if any(row[c] != 0 for row in rows)]
    if not keep:
        return None
    return tuple(tuple(row[c] for c in keep) for row in rows)


_SIMPLE_TRANSFORMS = ("CROP", "DEDUPE", "REMOVE_ZERO", "FLIP_HORIZONTAL")


def _apply_simple_transform(grid: Grid, name: str) -> Grid | None:
    if name == "CROP":
        bbox = _non_background_bbox(grid)
        return None if bbox is None else _crop_bbox(grid, bbox)
    if name == "DEDUPE":
        return _dedupe_adjacent_lines(grid)
    if name == "REMOVE_ZERO":
        return _remove_zero_lines(grid)
    if name == "FLIP_HORIZONTAL":
        return _flip_h(grid)
    raise ARCNoveltyCompilerError("SIMPLE_TRANSFORM_UNSUPPORTED")


def _compose_simple(grid: Grid, first: str, second: str) -> Grid | None:
    mid = _apply_simple_transform(grid, first)
    if mid is None:
        return None
    return _apply_simple_transform(mid, second)


def _shortest_period(sequence: Sequence[Any]) -> int:
    n = len(sequence)
    for p in range(1, n + 1):
        if all(sequence[i] == sequence[i % p] for i in range(n)):
            return p
    return n


def _infer_periodic_extension(
    pairs: Sequence[tuple[Grid, Grid]],
    axis: str,
) -> tuple[int, dict[int, int]] | None:
    target: int | None = None
    recolor: dict[int, int] = {}
    for inp, out in pairs:
        ih, iw = _shape(inp)
        oh, ow = _shape(out)
        if axis == "VERTICAL":
            if ow != iw or oh < ih:
                return None
            current_target = oh
        elif axis == "HORIZONTAL":
            if oh != ih or ow < iw:
                return None
            current_target = ow
        else:
            raise ARCNoveltyCompilerError("PERIODIC_AXIS_UNSUPPORTED")
        if target is not None and target != current_target:
            return None
        target = current_target

        for r in range(ih):
            for c in range(iw):
                src, dst = inp[r][c], out[r][c]
                if src in recolor and recolor[src] != dst:
                    return None
                recolor[src] = dst

    assert target is not None
    for inp, expected in pairs:
        predicted = _periodic_extension_predict(inp, axis, target, recolor)
        if predicted != expected:
            return None
    return target, recolor


def _periodic_extension_predict(
    grid: Grid,
    axis: str,
    target: int,
    recolor: Mapping[int, int],
) -> Grid | None:
    x = _apply_recolor(grid, recolor)
    if axis == "VERTICAL":
        rows = list(x)
        period = _shortest_period(rows)
        return tuple(rows[r % period] for r in range(target))
    if axis == "HORIZONTAL":
        h, w = _shape(x)
        cols = [tuple(x[r][c] for r in range(h)) for c in range(w)]
        period = _shortest_period(cols)
        return tuple(
            tuple(cols[c % period][r] for c in range(target))
            for r in range(h)
        )
    raise ARCNoveltyCompilerError("PERIODIC_AXIS_UNSUPPORTED")


def _shift_row(row: Sequence[int], delta: int) -> tuple[int, ...]:
    w = len(row)
    out = [0] * w
    for c, value in enumerate(row):
        nc = c + delta
        if 0 <= nc < w:
            out[nc] = value
    return tuple(out)


def _infer_row_shift_period(grid: Grid) -> tuple[int, int] | None:
    h, w = _shape(grid)
    candidates: list[tuple[int, int]] = []
    for period in range(1, h + 1):
        for delta in range(-w, w + 1):
            ok = True
            for i in range(h):
                if _shift_row(grid[i % period], (i // period) * delta) != grid[i]:
                    ok = False
                    break
            if ok:
                candidates.append((period, delta))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], abs(x[1]), x[1]))
    return candidates[0]


def _row_shift_period_extend(grid: Grid, target_height: int) -> Grid | None:
    model = _infer_row_shift_period(grid)
    if model is None:
        return None
    period, delta = model
    return tuple(
        _shift_row(grid[i % period], (i // period) * delta)
        for i in range(target_height)
    )


def _infer_row_shift_period_target(
    pairs: Sequence[tuple[Grid, Grid]],
) -> int | None:
    target: int | None = None
    for inp, out in pairs:
        ih, iw = _shape(inp)
        oh, ow = _shape(out)
        if ow != iw or oh < ih:
            return None
        if tuple(out[:ih]) != inp:
            return None
        if target is not None and target != oh:
            return None
        target = oh
        if _row_shift_period_extend(inp, oh) != out:
            return None
    return target


def _shift_grid(grid: Grid, dr: int, dc: int) -> Grid:
    h, w = _shape(grid)
    out = [[0 for _ in range(w)] for _ in range(h)]
    for r in range(h):
        for c in range(w):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w:
                out[nr][nc] = grid[r][c]
    return tuple(tuple(row) for row in out)


def _infer_unique_shift(pairs: Sequence[tuple[Grid, Grid]], limit: int = 5) -> tuple[int, int] | None:
    possible: set[tuple[int, int]] | None = None
    for inp, out in pairs:
        if _shape(inp) != _shape(out):
            return None
        current = {
            (dr, dc)
            for dr in range(-limit, limit + 1)
            for dc in range(-limit, limit + 1)
            if (dr != 0 or dc != 0) and _shift_grid(inp, dr, dc) == out
        }
        possible = current if possible is None else possible & current
        if not possible:
            return None
    return next(iter(possible)) if possible is not None and len(possible) == 1 else None


def _binary_shape_key(grid: Grid) -> str:
    base = tuple(tuple(0 if v == 0 else 1 for v in row) for row in grid)
    variants: list[Grid] = []
    current = base
    for _ in range(4):
        variants.append(current)
        variants.append(_flip_h(current))
        current = _rot90(current)
    def encode(g: Grid) -> str:
        return f"{len(g)}x{len(g[0])}:" + "/".join("".join(str(v) for v in row) for row in g)
    return min(encode(g) for g in variants)


def _infer_shape_label(pairs: Sequence[tuple[Grid, Grid]]) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for inp, out in pairs:
        if _shape(out) != (1, 1):
            return None
        key = _binary_shape_key(inp)
        target = out[0][0]
        if key in mapping and mapping[key] != target:
            return None
        mapping[key] = target
    return mapping if mapping else None


def _shape_label_predict(grid: Grid, mapping: Mapping[str, int]) -> Grid | None:
    key = _binary_shape_key(grid)
    if key not in mapping:
        return None
    return ((int(mapping[key]),),)


def _select_odd_color_component_crop(grid: Grid) -> Grid | None:
    comps = _zero_components(grid)
    if not comps:
        return None
    counts = Counter(c.color for c in comps)
    if not any(v >= 2 for v in counts.values()):
        return None
    odd_colors = {color for color, count in counts.items() if count == 1}
    choices = [c for c in comps if c.color in odd_colors]
    return _crop_bbox(grid, choices[0].bbox) if len(choices) == 1 else None


def _monochrome_frames(grid: Grid) -> list[tuple[int, int, int, int, int]]:
    h, w = _shape(grid)
    frames: list[tuple[int, int, int, int, int]] = []
    for r0 in range(h - 2):
        for c0 in range(w - 2):
            color = grid[r0][c0]
            if color == 0:
                continue
            for c1 in range(c0 + 2, w):
                if any(grid[r0][c] != color for c in range(c0, c1 + 1)):
                    break
                for r1 in range(r0 + 2, h):
                    if grid[r1][c0] != color or grid[r1][c1] != color:
                        continue
                    if any(grid[r][c0] != color or grid[r][c1] != color for r in range(r0, r1 + 1)):
                        continue
                    if any(grid[r1][c] != color for c in range(c0, c1 + 1)):
                        continue
                    frames.append((r0, c0, r1, c1, color))
    return frames


def _select_largest_frame_interior(grid: Grid) -> Grid | None:
    frames = _monochrome_frames(grid)
    if not frames:
        return None
    areas = [(r1 - r0 + 1) * (c1 - c0 + 1) for r0, c0, r1, c1, _ in frames]
    best = max(areas)
    choices = [frame for frame, area in zip(frames, areas) if area == best]
    if len(choices) != 1:
        return None
    r0, c0, r1, c1, _ = choices[0]
    return tuple(tuple(grid[r][c0 + 1 : c1]) for r in range(r0 + 1, r1))


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
    if kind == "GRID_REPEAT":
        return _repeat_grid(grid, int(h["row_repeats"]), int(h["col_repeats"]))
    if kind == "SELF_KRONECKER":
        return _self_kronecker(grid)
    if kind == "ROTATIONAL_QUAD_COMPLETION":
        return _rotational_quad(grid)
    if kind == "MIRROR_EXTEND_HORIZONTAL":
        flipped = _flip_h(grid)
        return _hcat(flipped, grid) if h["side"] == "LEFT" else _hcat(grid, flipped)
    if kind == "MIRROR_EXTEND_VERTICAL":
        flipped = _flip_v(grid)
        return _vcat(flipped, grid) if h["side"] == "UP" else _vcat(grid, flipped)
    if kind == "MIRROR_EXTEND_QUAD":
        top = _hcat(grid, _flip_h(grid))
        bottom = _hcat(_flip_v(grid), _rot180(grid))
        return None if top is None or bottom is None else _vcat(top, bottom)
    if kind == "CROP_NON_BACKGROUND":
        bbox = _non_background_bbox(grid)
        return None if bbox is None else _crop_bbox(grid, bbox)
    if kind == "SELECT_COMPONENT_CROP":
        return _component_crop(grid, h["selector"])
    if kind == "BBOX_TOP_LEFT_QUADRANT":
        return _top_left_bbox_quadrant(grid)
    if kind == "SELECT_SEPARATOR_PANEL_UNIQUE_COLOR":
        return _select_unique_color_panel(grid)
    if kind == "PANEL_CELLWISE_BINARY_RELATION":
        return _panel_relation_predict(grid, h["orientation"], h["mapping"])
    if kind == "OBJECT_PROPERTY_RECOLOR":
        return _object_recolor_predict(grid, h["feature"], h["mapping"])
    if kind == "LOCAL_NEIGHBORHOOD_RULE":
        return _local_rule_predict(grid, h["feature"], h["mapping"])
    if kind == "CONNECT_ALIGNED_SAME_COLOR_BOTH_AXES":
        return _connect_both_same_color(grid)
    if kind == "FILL_ENCLOSED_ZERO_REGION":
        return _fill_enclosed_zero(grid, int(h["color"]))
    if kind == "GLOBAL_SHIFT":
        return _shift_grid(grid, int(h["dr"]), int(h["dc"]))
    if kind == "COLOR_INVARIANT_SHAPE_LABEL":
        return _shape_label_predict(grid, h["mapping"])
    if kind == "SELECT_ODD_COLOR_COMPONENT_CROP":
        return _select_odd_color_component_crop(grid)
    if kind == "EXTRACT_LARGEST_MONOCHROME_FRAME_INTERIOR":
        return _select_largest_frame_interior(grid)
    if kind == "COMPOSED_SIMPLE_TRANSFORM":
        return _compose_simple(grid, h["first"], h["second"])
    if kind == "ROW_COLUMN_GRAVITY":
        return _row_col_gravity(grid, h["direction"])
    if kind == "CARDINAL_VISIBILITY_RULE":
        return _ray_color_predict(grid, h["mapping"])
    if kind == "PERIODIC_EXTENSION":
        mapping = {int(k): int(v) for k, v in h["mapping"].items()}
        return _periodic_extension_predict(grid, h["axis"], int(h["target"]), mapping)
    if kind == "ROW_SHIFT_PERIODIC_EXTENSION":
        return _row_shift_period_extend(grid, int(h["target_height"]))
    if kind == "COMPLETE_SYMMETRY":
        return _complete_symmetry(grid, h["mode"])
    if kind == "FILL_EACH_COLOR_BBOX":
        return _fill_each_color_bbox(grid)
    if kind == "CONNECT_SAME_COLOR_DIAGONALS":
        return _connect_same_color_diagonals(grid)
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

    repeat_factors: set[tuple[int, int]] = set()
    for inp, out in pairs:
        ih, iw = _shape(inp)
        oh, ow = _shape(out)
        if oh % ih == 0 and ow % iw == 0:
            rr, cc = oh // ih, ow // iw
            if rr >= 1 and cc >= 1 and (rr > 1 or cc > 1):
                repeat_factors.add((rr, cc))
    if len(repeat_factors) == 1:
        rr, cc = next(iter(repeat_factors))
        h = {"kind": "GRID_REPEAT", "row_repeats": rr, "col_repeats": cc}
        if _consistent(h, pairs):
            candidates.append(h)

    h = {"kind": "SELF_KRONECKER"}
    if _consistent(h, pairs):
        candidates.append(h)

    h = {"kind": "ROTATIONAL_QUAD_COMPLETION"}
    if _consistent(h, pairs):
        candidates.append(h)

    for side in ("LEFT", "RIGHT"):
        h = {"kind": "MIRROR_EXTEND_HORIZONTAL", "side": side}
        if _consistent(h, pairs):
            candidates.append(h)

    for side in ("UP", "DOWN"):
        h = {"kind": "MIRROR_EXTEND_VERTICAL", "side": side}
        if _consistent(h, pairs):
            candidates.append(h)

    h = {"kind": "MIRROR_EXTEND_QUAD"}
    if _consistent(h, pairs):
        candidates.append(h)

    h = {"kind": "BBOX_TOP_LEFT_QUADRANT"}
    if _consistent(h, pairs):
        candidates.append(h)

    h = {"kind": "SELECT_SEPARATOR_PANEL_UNIQUE_COLOR"}
    if _consistent(h, pairs):
        candidates.append(h)

    for orientation in ("VERTICAL", "HORIZONTAL"):
        mapping = _infer_panel_relation(pairs, orientation)
        if mapping is not None:
            h = {
                "kind": "PANEL_CELLWISE_BINARY_RELATION",
                "orientation": orientation,
                "mapping": dict(sorted(mapping.items())),
            }
            if _consistent(h, pairs):
                candidates.append(h)

    ordered_structural_hypotheses = (
        ("LOCAL_NEIGHBORHOOD_RULE", "COLOR_COUNTS"),
        ("OBJECT_PROPERTY_RECOLOR", "BBOX"),
        ("LOCAL_NEIGHBORHOOD_RULE", "BIN_CROSS"),
        ("OBJECT_PROPERTY_RECOLOR", "DENSITY"),
        ("LOCAL_NEIGHBORHOOD_RULE", "COLOR_ROWCOL_SETS"),
    )
    for kind, feature in ordered_structural_hypotheses:
        if kind == "LOCAL_NEIGHBORHOOD_RULE":
            mapping = _infer_local_rule(pairs, feature)
        else:
            mapping = _infer_object_recolor(pairs, feature)
        if mapping is not None:
            h = {
                "kind": kind,
                "feature": feature,
                "mapping": dict(sorted(mapping.items())),
            }
            if _consistent(h, pairs):
                candidates.append(h)

    h = {"kind": "CONNECT_ALIGNED_SAME_COLOR_BOTH_AXES"}
    if _consistent(h, pairs):
        candidates.append(h)

    fill_color = _infer_enclosed_zero_fill(pairs)
    if fill_color is not None:
        h = {"kind": "FILL_ENCLOSED_ZERO_REGION", "color": fill_color}
        if _consistent(h, pairs):
            candidates.append(h)

    shift = _infer_unique_shift(pairs)
    if shift is not None:
        dr, dc = shift
        h = {"kind": "GLOBAL_SHIFT", "dr": dr, "dc": dc}
        if _consistent(h, pairs):
            candidates.append(h)

    shape_label = _infer_shape_label(pairs)
    if shape_label is not None:
        h = {
            "kind": "COLOR_INVARIANT_SHAPE_LABEL",
            "mapping": dict(sorted(shape_label.items())),
        }
        if _consistent(h, pairs):
            candidates.append(h)

    h = {"kind": "SELECT_ODD_COLOR_COMPONENT_CROP"}
    if _consistent(h, pairs):
        candidates.append(h)

    if all(_shape(out)[0] < _shape(inp)[0] and _shape(out)[1] < _shape(inp)[1] for inp, out in pairs):
        h = {"kind": "EXTRACT_LARGEST_MONOCHROME_FRAME_INTERIOR"}
        if _consistent(h, pairs):
            candidates.append(h)

    for first in _SIMPLE_TRANSFORMS:
        for second in _SIMPLE_TRANSFORMS:
            h = {"kind": "COMPOSED_SIMPLE_TRANSFORM", "first": first, "second": second}
            if _consistent(h, pairs):
                candidates.append(h)

    for direction in ("LEFT", "RIGHT", "UP", "DOWN"):
        h = {"kind": "ROW_COLUMN_GRAVITY", "direction": direction}
        if _consistent(h, pairs):
            candidates.append(h)

    ray_mapping = _infer_ray_color_rule(pairs)
    if ray_mapping is not None:
        h = {"kind": "CARDINAL_VISIBILITY_RULE", "mapping": dict(sorted(ray_mapping.items()))}
        if _consistent(h, pairs):
            candidates.append(h)

    for axis in ("VERTICAL", "HORIZONTAL"):
        periodic = _infer_periodic_extension(pairs, axis)
        if periodic is not None:
            target, mapping = periodic
            h = {
                "kind": "PERIODIC_EXTENSION",
                "axis": axis,
                "target": target,
                "mapping": {str(k): v for k, v in sorted(mapping.items())},
            }
            if _consistent(h, pairs):
                candidates.append(h)

    row_shift_target = _infer_row_shift_period_target(pairs)
    if row_shift_target is not None:
        h = {"kind": "ROW_SHIFT_PERIODIC_EXTENSION", "target_height": row_shift_target}
        if _consistent(h, pairs):
            candidates.append(h)

    for mode in ("VERTICAL", "ROTATE_180"):
        h = {"kind": "COMPLETE_SYMMETRY", "mode": mode}
        if _consistent(h, pairs):
            candidates.append(h)

    h = {"kind": "FILL_EACH_COLOR_BBOX"}
    if _consistent(h, pairs):
        candidates.append(h)

    h = {"kind": "CONNECT_SAME_COLOR_DIAGONALS"}
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
            "WHOLE_GRID_INTEGER_REPEAT",
            "SELF_KRONECKER_REPLICATION",
            "ROTATIONAL_QUADRANT_COMPLETION",
            "HORIZONTAL_MIRROR_EXTENSION",
            "VERTICAL_MIRROR_EXTENSION",
            "TWO_AXIS_MIRROR_QUADRANT_EXTENSION",
            "BOUNDING_BOX_TOP_LEFT_QUADRANT_EXTRACTION",
            "SEPARATOR_PANEL_UNIQUE_COLOR_SELECTION",
            "EQUAL_PANEL_CELLWISE_ZERO_NONZERO_RELATION",
            "LOCAL_NEIGHBORHOOD_OUTPUT_RULE",
            "CONNECTED_OBJECT_PROPERTY_RECOLOR",
            "ALIGNED_SAME_COLOR_LINE_COMPLETION",
            "ENCLOSED_ZERO_REGION_FILL",
            "ROW_COLUMN_CONTEXTUAL_LOCAL_RULE",
            "BOUNDED_GLOBAL_SHIFT",
            "COLOR_INVARIANT_SHAPE_TO_LABEL",
            "ODD_COLOR_COMPONENT_SELECTION",
            "MONOCHROME_FRAME_INTERIOR_EXTRACTION",
            "DEPTH_TWO_SIMPLE_TRANSFORM_COMPOSITION",
            "ROW_COLUMN_GRAVITY",
            "CARDINAL_VISIBILITY_OUTPUT_RULE",
            "PERIODIC_SEQUENCE_EXTENSION",
            "TRANSLATING_PERIODIC_ROW_EXTENSION",
            "SYMMETRY_COMPLETION",
            "PER_COLOR_BOUNDING_BOX_FILL",
            "SAME_COLOR_DIAGONAL_CONNECTION",
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
