"""Zero-learned-state ARC solver V2.

V2 keeps V1 frozen and adds a small bank of generic, deterministic hypothesis
classes motivated by spent-development failures and reusable ARC-DSL concepts.
A hypothesis is allowed to predict a test grid only if the same program class
exactly explains every training input/output pair.

Persistent learned state: 0 bytes.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.arc_zero_learned_solver_v1 import (
    ARCZeroLearnedError,
    solve_with_trace as solve_v1_with_trace,
)

Grid = list[list[int]]
Pair = Mapping[str, Any]


@dataclass(frozen=True)
class Candidate:
    name: str
    cost: int
    apply: Callable[[Grid], Grid]


def _grid(value: Any) -> Grid:
    if not isinstance(value, list) or not value:
        raise ARCZeroLearnedError("GRID_INVALID")
    if any(not isinstance(row, list) or not row for row in value):
        raise ARCZeroLearnedError("GRID_INVALID")
    width = len(value[0])
    if any(len(row) != width for row in value):
        raise ARCZeroLearnedError("GRID_NOT_RECTANGULAR")
    out = []
    for row in value:
        rr = []
        for cell in row:
            if isinstance(cell, bool) or not isinstance(cell, int) or not 0 <= cell <= 9:
                raise ARCZeroLearnedError("GRID_CELL_INVALID")
            rr.append(cell)
        out.append(rr)
    return out


def _same(a: Grid, b: Grid) -> bool:
    return a == b


def _shape(g: Grid) -> tuple[int, int]:
    return len(g), len(g[0])


def _copy(g: Grid) -> Grid:
    return [row[:] for row in g]


def _fits(candidate: Candidate, train: Sequence[Pair]) -> bool:
    try:
        return all(
            _same(candidate.apply(_grid(pair["input"])), _grid(pair["output"]))
            for pair in train
        )
    except Exception:
        return False


def _components(
    g: Grid,
    *,
    include: Callable[[int], bool],
) -> list[set[tuple[int, int]]]:
    h, w = _shape(g)
    seen: set[tuple[int, int]] = set()
    out = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or not include(g[r][c]):
                continue
            q = deque([(r, c)])
            seen.add((r, c))
            comp: set[tuple[int, int]] = set()
            while q:
                x, y = q.popleft()
                comp.add((x, y))
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if (
                        0 <= nx < h
                        and 0 <= ny < w
                        and (nx, ny) not in seen
                        and include(g[nx][ny])
                    ):
                        seen.add((nx, ny))
                        q.append((nx, ny))
            out.append(comp)
    return out


def _periodic_repair_one(g: Grid) -> Grid | None:
    h, w = _shape(g)
    best: tuple[int, int, int, Grid] | None = None
    # 0 is treated as an unknown/hole only inside this hypothesis class.
    for pr in range(1, min(h, 12) + 1):
        for pc in range(1, min(w, 12) + 1):
            values: dict[tuple[int, int], int] = {}
            conflict = False
            observed_nonzero = 0
            for r in range(h):
                for c in range(w):
                    value = g[r][c]
                    if value == 0:
                        continue
                    observed_nonzero += 1
                    key = (r % pr, c % pc)
                    prior = values.get(key)
                    if prior is not None and prior != value:
                        conflict = True
                        break
                    values[key] = value
                if conflict:
                    break
            if conflict or not values or observed_nonzero == h * w:
                continue

            out = _copy(g)
            filled = 0
            unresolved = 0
            for r in range(h):
                for c in range(w):
                    if out[r][c] != 0:
                        continue
                    value = values.get((r % pr, c % pc))
                    if value is None:
                        unresolved += 1
                    else:
                        out[r][c] = value
                        filled += 1
            if filled == 0:
                continue
            # Prefer smaller description: period area, then unresolved holes.
            score = pr * pc + unresolved * 1000
            row = (score, pr, pc, out)
            if best is None or row[:3] < best[:3]:
                best = row
    return None if best is None else best[3]


def periodic_repair_candidate(train: Sequence[Pair]) -> Candidate | None:
    candidate = Candidate(
        "PERIODIC_REPAIR",
        3,
        lambda g: _periodic_repair_one(g) or _copy(g),
    )
    return candidate if _fits(candidate, train) else None


def color_key_swap_candidate(train: Sequence[Pair]) -> Candidate | None:
    def apply(g: Grid) -> Grid:
        h, w = _shape(g)
        if h < 2 or w < 2:
            return _copy(g)
        a, b = g[0][0], g[0][1]
        c, d = g[1][0], g[1][1]
        if 0 in (a, b, c, d) or len({a, b, c, d}) != 4:
            return _copy(g)
        mapping = {a: b, b: a, c: d, d: c}
        out = [
            [mapping.get(value, value) for value in row]
            for row in g
        ]
        # The 2x2 legend is declarative and remains unchanged.
        out[0][0], out[0][1] = a, b
        out[1][0], out[1][1] = c, d
        return out

    candidate = Candidate("TOPLEFT_2X2_PAIRWISE_COLOR_KEY", 2, apply)
    return candidate if _fits(candidate, train) else None


def motif_substitution_candidate(train: Sequence[Pair]) -> Candidate | None:
    rh: int | None = None
    rw: int | None = None
    mapping: dict[int, tuple[tuple[int, ...], ...]] = {}
    try:
        for pair in train:
            inp = _grid(pair["input"])
            out = _grid(pair["output"])
            ih, iw = _shape(inp)
            oh, ow = _shape(out)
            if oh % ih or ow % iw:
                return None
            this_rh, this_rw = oh // ih, ow // iw
            if this_rh < 1 or this_rw < 1:
                return None
            if rh is None:
                rh, rw = this_rh, this_rw
            elif (rh, rw) != (this_rh, this_rw):
                return None
            for r in range(ih):
                for c in range(iw):
                    block = tuple(
                        tuple(out[r * rh + dr][c * rw + dc] for dc in range(rw))
                        for dr in range(rh)
                    )
                    color = inp[r][c]
                    prior = mapping.get(color)
                    if prior is not None and prior != block:
                        return None
                    mapping[color] = block
    except Exception:
        return None

    if rh is None or rw is None or (rh == 1 and rw == 1) or not mapping:
        return None

    def apply(g: Grid) -> Grid:
        ih, iw = _shape(g)
        out = [[0 for _ in range(iw * rw)] for _ in range(ih * rh)]
        for r in range(ih):
            for c in range(iw):
                block = mapping.get(g[r][c])
                if block is None:
                    raise ARCZeroLearnedError("MOTIF_FOR_COLOR_UNKNOWN")
                for dr in range(rh):
                    for dc in range(rw):
                        out[r * rh + dr][c * rw + dc] = block[dr][dc]
        return out

    candidate = Candidate("CELL_TO_BLOCK_MOTIF_SUBSTITUTION", 3, apply)
    return candidate if _fits(candidate, train) else None


def macrogrid_extract_candidate(train: Sequence[Pair]) -> Candidate | None:
    def apply(g: Grid) -> Grid:
        counts = Counter(cell for row in g for cell in row)
        nonzero = [value for value in counts if value != 0]
        if not nonzero:
            return _copy(g)
        # Canvas/background may be surrounded by large zero margins. Choose the
        # most common nonzero color so zero does not accidentally become the
        # "object field" and swallow the real canvas.
        dominant = max(sorted(nonzero), key=lambda x: (counts[x], -x))
        excluded = {0, dominant}

        comps = _components(g, include=lambda value: value not in excluded)
        objects = []
        for comp in comps:
            colors = {g[r][c] for r, c in comp}
            if len(colors) != 1:
                raise ARCZeroLearnedError("MACRO_OBJECT_NOT_UNIFORM")
            color = next(iter(colors))
            rs = [r for r, _ in comp]
            cs = [c for _, c in comp]
            r0, r1 = min(rs), max(rs)
            c0, c1 = min(cs), max(cs)
            # Require filled rectangles so arbitrary noisy objects do not qualify.
            if len(comp) != (r1 - r0 + 1) * (c1 - c0 + 1):
                raise ARCZeroLearnedError("MACRO_OBJECT_NOT_RECTANGLE")
            objects.append((r0, c0, color, r1 - r0 + 1, c1 - c0 + 1))

        if not objects:
            return _copy(g)
        dims = {(x[3], x[4]) for x in objects}
        if len(dims) != 1:
            raise ARCZeroLearnedError("MACRO_OBJECT_DIMS_INCONSISTENT")
        rows = sorted({x[0] for x in objects})
        cols = sorted({x[1] for x in objects})
        if len(rows) < 1 or len(cols) < 1:
            return _copy(g)
        ri = {value: i for i, value in enumerate(rows)}
        ci = {value: i for i, value in enumerate(cols)}
        out = [[0 for _ in cols] for _ in rows]
        for r0, c0, color, _, _ in objects:
            out[ri[r0]][ci[c0]] = color
        return out

    candidate = Candidate("UNIFORM_OBJECT_MACROGRID_EXTRACTION", 3, apply)
    return candidate if _fits(candidate, train) else None


def marker_line_candidate(train: Sequence[Pair]) -> Candidate | None:
    def make(marker: int) -> Candidate:
        def apply(g: Grid) -> Grid:
            h, w = _shape(g)
            points = [(r, c) for r in range(h) for c in range(w) if g[r][c] == marker]
            point_set = set(points)
            line_cells: set[tuple[int, int]] = set()
            # Only opposite-edge marker pairs define a line. Same-edge pairs
            # are merely multiple independent line endpoints, not instructions
            # to draw along the boundary.
            for r in range(h):
                if (r, 0) in point_set and (r, w - 1) in point_set:
                    for c in range(w):
                        line_cells.add((r, c))
            for c in range(w):
                if (0, c) in point_set and (h - 1, c) in point_set:
                    for r in range(h):
                        line_cells.add((r, c))
            if not line_cells:
                return _copy(g)

            out = _copy(g)
            # Any nonzero non-marker 4-connected object touched by a marker line
            # is promoted wholesale to the marker color.
            comps = _components(g, include=lambda value: value not in (0, marker))
            for comp in comps:
                if comp & line_cells:
                    for r, c in comp:
                        out[r][c] = marker
            for r, c in line_cells:
                out[r][c] = marker
            return out

        return Candidate(f"MARKER_LINE_PROPAGATION_COLOR_{marker}", 3, apply)

    candidates = []
    for marker in range(1, 10):
        candidate = make(marker)
        if _fits(candidate, train):
            candidates.append(candidate)
    return min(candidates, key=lambda x: (x.cost, x.name)) if candidates else None


def _v1_candidate(train: Sequence[Pair]) -> Candidate | None:
    # V1 itself performs its own exact training-fit search. Bind the resulting
    # program behavior as one candidate only if it predicts every train output.
    if not train:
        return None
    probes = []
    for pair in train:
        others = [p for p in train if p is not pair] or list(train)
        trace = solve_v1_with_trace(others, pair["input"])
        if trace.get("prediction") != pair["output"]:
            return None
        probes.append(trace)
    # Leave V1 to solve the actual test using all demonstrations.
    return Candidate("V1_GENERIC_GRID_TRANSFORM", 4, lambda g: g)


def fit_candidates(train: Sequence[Pair]) -> list[Candidate]:
    candidates = []
    for fitter in (
        color_key_swap_candidate,
        motif_substitution_candidate,
        macrogrid_extract_candidate,
        marker_line_candidate,
        periodic_repair_candidate,
    ):
        candidate = fitter(train)
        if candidate is not None:
            candidates.append(candidate)
    return sorted(candidates, key=lambda x: (x.cost, x.name))


def solve_with_trace(
    train_pairs: Sequence[Pair],
    test_input: Any,
) -> dict[str, Any]:
    if not isinstance(train_pairs, Sequence) or not train_pairs:
        raise ARCZeroLearnedError("TRAIN_PAIRS_REQUIRED")
    train = list(train_pairs)
    test = _grid(test_input)

    candidates = fit_candidates(train)
    if candidates:
        winner = candidates[0]
        prediction = winner.apply(test)
        return {
            "schema": "PROJECT_BRAIN_ARC_ZERO_LEARNED_SOLVER_RESULT_V2",
            "status": "PREDICTION",
            "strategy": winner.name,
            "strategy_cost": winner.cost,
            "candidate_count": len(candidates),
            "prediction": prediction,
            "persistent_learned_state_bytes": 0,
        }

    # Preserve V1 as a fallback only after no V2 strategy explains all examples.
    v1 = solve_v1_with_trace(train, test)
    return {
        "schema": "PROJECT_BRAIN_ARC_ZERO_LEARNED_SOLVER_RESULT_V2",
        "status": v1.get("status"),
        "strategy": "V1_FALLBACK",
        "prediction": v1.get("prediction"),
        "persistent_learned_state_bytes": 0,
        "v1_trace": v1,
    }


def solve(train_pairs: Sequence[Pair], test_input: Any) -> Grid | None:
    return solve_with_trace(train_pairs, test_input).get("prediction")
