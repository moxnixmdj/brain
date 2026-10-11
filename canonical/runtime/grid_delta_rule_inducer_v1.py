"""Grid delta rule inducer V1.

Turns same-shape grid demonstrations into a finite typed classification problem:
which input cells should change to one inferred target color? The selector is
synthesized by the existing Brain-owned G0 finite typed-rule engine, then every
candidate rule is replayed against every training cell before it is accepted.

V1 is intentionally bounded to one changed-to color and finite predicate packs.
It is a reusable rule-induction mechanism, not an ARC answer table.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from itertools import product
from typing import Any, Mapping, Sequence

from canonical.runtime.g0_finite_typed_rule_synthesis import (
    PredicateSpec,
    RuleExample,
    synthesize_minimal_conjunctive_rule,
)

Grid = tuple[tuple[int, ...], ...]
SCHEMA = "PROJECT_BRAIN_GRID_DELTA_RULE_INDUCER_V1"


class GridDeltaRuleError(ValueError):
    pass


def _grid(value: Sequence[Sequence[int]], label: str) -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise GridDeltaRuleError(label.upper() + "_INVALID")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw in value:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
            raise GridDeltaRuleError(label.upper() + "_ROW_INVALID")
        row: list[int] = []
        for v in raw:
            if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 9:
                raise GridDeltaRuleError(label.upper() + "_CELL_INVALID")
            row.append(v)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise GridDeltaRuleError(label.upper() + "_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _shape(g: Grid) -> tuple[int, int]:
    return len(g), len(g[0])


@dataclass(frozen=True)
class CellContext:
    value: int
    row_nz: int
    col_nz: int
    n4: int
    n8: int
    border: bool
    component_area: int


def _component_areas(g: Grid) -> dict[tuple[int, int], int]:
    h, w = _shape(g)
    seen: set[tuple[int, int]] = set()
    out: dict[tuple[int, int], int] = {}
    for r in range(h):
        for c in range(w):
            if g[r][c] == 0 or (r, c) in seen:
                continue
            color = g[r][c]
            q = deque([(r, c)])
            seen.add((r, c))
            cells: list[tuple[int, int]] = []
            while q:
                rr, cc = q.popleft()
                cells.append((rr, cc))
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and g[nr][nc] == color:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            for pos in cells:
                out[pos] = len(cells)
    return out


def _contexts(g: Grid) -> dict[tuple[int, int], CellContext]:
    h, w = _shape(g)
    areas = _component_areas(g)
    result: dict[tuple[int, int], CellContext] = {}
    for r in range(h):
        for c in range(w):
            n4 = 0
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and g[rr][cc] != 0:
                    n4 += 1
            n8 = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and g[rr][cc] != 0:
                        n8 += 1
            result[(r, c)] = CellContext(
                value=g[r][c],
                row_nz=sum(v != 0 for v in g[r]),
                col_nz=sum(g[rr][c] != 0 for rr in range(h)),
                n4=n4,
                n8=n8,
                border=r in (0, h - 1) or c in (0, w - 1),
                component_area=areas.get((r, c), 0),
            )
    return result


def _observed_colors(pairs: Sequence[tuple[Grid, Grid]]) -> list[int]:
    colors = sorted({v for inp, _ in pairs for row in inp for v in row if v != 0})
    return colors[:10]


def _pack_specs(pack: str, colors: Sequence[int]) -> list[PredicateSpec]:
    ids: list[str]
    if pack == "LOCAL":
        ids = [
            "ZERO", "NONZERO",
            "N4_EQ_0", "N4_EQ_1", "N4_EQ_2", "N4_GE_3",
            "N8_EQ_0", "N8_EQ_1", "N8_2_TO_3", "N8_GE_4",
            "BORDER", "INTERIOR",
        ] + [f"COLOR_EQ_{c}" for c in colors[:8]]
    elif pack == "ROWCOL":
        ids = [
            "ZERO", "NONZERO",
            "ROW_NZ_EQ_0", "ROW_NZ_EQ_1", "ROW_NZ_EQ_2", "ROW_NZ_GE_3",
            "COL_NZ_EQ_0", "COL_NZ_EQ_1", "COL_NZ_EQ_2", "COL_NZ_GE_3",
            "BORDER", "INTERIOR",
        ] + [f"COLOR_EQ_{c}" for c in colors[:8]]
    elif pack == "COMPONENT":
        ids = [
            "ZERO", "NONZERO",
            "COMP_AREA_EQ_0", "COMP_AREA_EQ_1", "COMP_AREA_EQ_2", "COMP_AREA_EQ_3",
            "COMP_AREA_4_TO_6", "COMP_AREA_GE_7",
            "BORDER", "INTERIOR",
        ] + [f"COLOR_EQ_{c}" for c in colors[:10]]
    else:
        raise GridDeltaRuleError("PACK_UNSUPPORTED")
    if len(ids) > 20:
        raise GridDeltaRuleError("PACK_TOO_LARGE")
    return [
        PredicateSpec(
            predicate_id=pid,
            predicate_type="grid_cell_bool",
            source={"path": "canonical/runtime/grid_delta_rule_inducer_v1.py", "span": [0, 1]},
            cost=1.0,
        )
        for pid in ids
    ]


def _facts(ctx: CellContext, predicate_ids: Sequence[str]) -> frozenset[str]:
    out: set[str] = set()
    for pid in predicate_ids:
        truth = False
        if pid == "ZERO": truth = ctx.value == 0
        elif pid == "NONZERO": truth = ctx.value != 0
        elif pid == "N4_EQ_0": truth = ctx.n4 == 0
        elif pid == "N4_EQ_1": truth = ctx.n4 == 1
        elif pid == "N4_EQ_2": truth = ctx.n4 == 2
        elif pid == "N4_GE_3": truth = ctx.n4 >= 3
        elif pid == "N8_EQ_0": truth = ctx.n8 == 0
        elif pid == "N8_EQ_1": truth = ctx.n8 == 1
        elif pid == "N8_2_TO_3": truth = 2 <= ctx.n8 <= 3
        elif pid == "N8_GE_4": truth = ctx.n8 >= 4
        elif pid == "BORDER": truth = ctx.border
        elif pid == "INTERIOR": truth = not ctx.border
        elif pid == "ROW_NZ_EQ_0": truth = ctx.row_nz == 0
        elif pid == "ROW_NZ_EQ_1": truth = ctx.row_nz == 1
        elif pid == "ROW_NZ_EQ_2": truth = ctx.row_nz == 2
        elif pid == "ROW_NZ_GE_3": truth = ctx.row_nz >= 3
        elif pid == "COL_NZ_EQ_0": truth = ctx.col_nz == 0
        elif pid == "COL_NZ_EQ_1": truth = ctx.col_nz == 1
        elif pid == "COL_NZ_EQ_2": truth = ctx.col_nz == 2
        elif pid == "COL_NZ_GE_3": truth = ctx.col_nz >= 3
        elif pid == "COMP_AREA_EQ_0": truth = ctx.component_area == 0
        elif pid == "COMP_AREA_EQ_1": truth = ctx.component_area == 1
        elif pid == "COMP_AREA_EQ_2": truth = ctx.component_area == 2
        elif pid == "COMP_AREA_EQ_3": truth = ctx.component_area == 3
        elif pid == "COMP_AREA_4_TO_6": truth = 4 <= ctx.component_area <= 6
        elif pid == "COMP_AREA_GE_7": truth = ctx.component_area >= 7
        elif pid.startswith("COLOR_EQ_"):
            truth = ctx.value == int(pid.removeprefix("COLOR_EQ_"))
        else:
            raise GridDeltaRuleError("UNKNOWN_PREDICATE:" + pid)
        if truth:
            out.add(pid)
    return frozenset(out)


def _rule_ids(rule: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(x["predicate_id"] for x in rule["preconditions"]))


def _matches_rule(ctx: CellContext, rule_ids: Sequence[str], predicate_ids: Sequence[str]) -> bool:
    facts = _facts(ctx, predicate_ids)
    return all(pid in facts for pid in rule_ids)


def _apply_rule(grid: Grid, target: int, rule_ids: Sequence[str], predicate_ids: Sequence[str]) -> Grid:
    contexts = _contexts(grid)
    out = [list(row) for row in grid]
    for (r, c), ctx in contexts.items():
        if _matches_rule(ctx, rule_ids, predicate_ids):
            out[r][c] = target
    return tuple(tuple(row) for row in out)


def _synthesize_target_rules(
    pairs: Sequence[tuple[Grid, Grid]],
    target: int,
    colors: Sequence[int],
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for pack in ("LOCAL", "ROWCOL", "COMPONENT"):
        specs = _pack_specs(pack, colors)
        pids = [x.predicate_id for x in specs]
        all_records: list[tuple[str, frozenset[str], bool]] = []
        for pi, (inp, out) in enumerate(pairs):
            contexts = _contexts(inp)
            for (r, c), ctx in contexts.items():
                positive = inp[r][c] != out[r][c] and out[r][c] == target
                all_records.append((f"t{target}_p{pi}_r{r}_c{c}", _facts(ctx, pids), positive))

        positives = [x for x in all_records if x[2]]
        negatives = [x for x in all_records if not x[2]]
        if not positives or not negatives:
            continue

        chosen: list[tuple[str, frozenset[str], bool]] = []
        seen_pos: set[frozenset[str]] = set()
        for rec in positives:
            if rec[1] not in seen_pos:
                chosen.append(rec)
                seen_pos.add(rec[1])
            if len(chosen) >= 64:
                break
        seen_neg: set[frozenset[str]] = set()
        for rec in negatives:
            if rec[1] not in seen_neg:
                chosen.append(rec)
                seen_neg.add(rec[1])
            if len(chosen) >= 128:
                break

        examples = [
            RuleExample(
                example_id=eid,
                facts=facts,
                positive=positive,
                source={"observation_id": eid},
            )
            for eid, facts, positive in chosen
        ]
        result = synthesize_minimal_conjunctive_rule(
            predicates=specs,
            examples=examples,
            emit={"set_color": target, "pack": pack},
        )
        if result.get("status") not in ("SYNTHESIZED_UNIQUE", "SYNTHESIZED_AMBIGUOUS"):
            continue

        for rule in result["rules"]:
            ids = _rule_ids(rule)
            # Verify the selector itself against every training cell, not merely
            # the bounded sample supplied to the underlying synthesizer.
            selector_ok = True
            for inp, out in pairs:
                contexts = _contexts(inp)
                for (r, c), ctx in contexts.items():
                    should_select = inp[r][c] != out[r][c] and out[r][c] == target
                    if _matches_rule(ctx, ids, pids) != should_select:
                        selector_ok = False
                        break
                if not selector_ok:
                    break
            if selector_ok:
                verified.append(
                    {
                        "pack": pack,
                        "target_color": target,
                        "rule_predicates": list(ids),
                        "cost": rule["cost"],
                        "predicate_ids": pids,
                    }
                )
    return verified


def _apply_rule_set(grid: Grid, rules: Sequence[Mapping[str, Any]]) -> Grid | None:
    contexts = _contexts(grid)
    out = [list(row) for row in grid]
    for (r, c), ctx in contexts.items():
        targets = {
            int(rule["target_color"])
            for rule in rules
            if _matches_rule(
                ctx,
                tuple(rule["rule_predicates"]),
                tuple(rule["predicate_ids"]),
            )
        }
        if len(targets) > 1:
            return None
        if targets:
            out[r][c] = next(iter(targets))
    return tuple(tuple(row) for row in out)


def induce(training_pairs: Sequence[Mapping[str, Sequence[Sequence[int]]]]) -> dict[str, Any]:
    try:
        pairs: list[tuple[Grid, Grid]] = []
        if not isinstance(training_pairs, Sequence) or isinstance(training_pairs, (str, bytes)) or not training_pairs:
            raise GridDeltaRuleError("TRAINING_PAIRS_INVALID")
        for i, raw in enumerate(training_pairs):
            inp = _grid(raw["input"], f"pair_{i}_input")
            out = _grid(raw["output"], f"pair_{i}_output")
            if _shape(inp) != _shape(out):
                return {"schema": SCHEMA, "status": "UNSUPPORTED", "reason": "SHAPE_CHANGE"}
            pairs.append((inp, out))
    except (GridDeltaRuleError, KeyError, TypeError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}

    changed_targets = sorted({
        out[r][c]
        for inp, out in pairs
        for r in range(len(inp))
        for c in range(len(inp[0]))
        if inp[r][c] != out[r][c]
    })
    if not changed_targets:
        return {"schema": SCHEMA, "status": "UNSUPPORTED", "reason": "NO_CHANGE"}

    colors = _observed_colors(pairs)
    per_target: list[list[dict[str, Any]]] = []
    for target in changed_targets:
        rules = _synthesize_target_rules(pairs, target, colors)
        if not rules:
            return {
                "schema": SCHEMA,
                "status": "NO_VERIFIED_RULE",
                "failed_target_color": target,
                "changed_target_colors": changed_targets,
                "terminal_authority": False,
            }
        per_target.append(rules)

    combinations_examined = 0
    verified_sets: list[dict[str, Any]] = []
    for combo in product(*per_target):
        combinations_examined += 1
        if combinations_examined > 512:
            return {
                "schema": SCHEMA,
                "status": "SEARCH_BOUND_EXCEEDED",
                "reason": "RULE_SET_COMBINATION_LIMIT",
                "limit": 512,
                "terminal_authority": False,
            }
        if all(_apply_rule_set(inp, combo) == out for inp, out in pairs):
            verified_sets.append(
                {
                    "rules": [dict(rule) for rule in combo],
                    "cost": sum(float(rule["cost"]) for rule in combo),
                }
            )

    if not verified_sets:
        return {
            "schema": SCHEMA,
            "status": "NO_VERIFIED_RULE_SET",
            "changed_target_colors": changed_targets,
            "terminal_authority": False,
        }

    best_cost = min(x["cost"] for x in verified_sets)
    best = [x for x in verified_sets if x["cost"] == best_cost]
    best.sort(
        key=lambda x: tuple(
            (r["target_color"], r["pack"], tuple(r["rule_predicates"]))
            for r in x["rules"]
        )
    )
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_RULE_SETS",
        "changed_target_colors": changed_targets,
        "minimum_cost": best_cost,
        "rule_sets": best,
        "rule_set_count": len(best),
        "ambiguity_preserved": len(best) > 1,
        "training_full_replay_verified": True,
        "synthesis_engine": "G0_FINITE_TYPED_RULE_SYNTHESIS_001",
        "scope": "SAME_SHAPE_MULTI_TARGET_FINITE_PREDICATE_PACKS",
        "terminal_authority": False,
        "promotion_authority": False,
    }


def predict(rule_set: Mapping[str, Any], grid: Sequence[Sequence[int]]) -> dict[str, Any]:
    try:
        g = _grid(grid, "grid")
        rules = rule_set["rules"]
        out = _apply_rule_set(g, rules)
    except (GridDeltaRuleError, KeyError, TypeError, ValueError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}
    if out is None:
        return {"schema": SCHEMA, "status": "UNDEFINED_CONFLICT", "prediction": None}
    return {
        "schema": SCHEMA,
        "status": "PREDICTED",
        "prediction": [list(row) for row in out],
        "terminal_authority": False,
    }
