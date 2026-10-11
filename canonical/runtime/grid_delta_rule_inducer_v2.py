"""Adaptive grid delta rule inducer V2.

V2 replaces V1's fixed predicate bins with task-derived finite predicate atoms.
It enumerates structural attribute packs that fit the verified G0 synthesizer's
20-predicate bound, synthesizes minimum conjunctive selectors, and full-replays
every candidate against every training cell.

No benchmark task IDs, answer tables, or hidden/test information participate in
predicate generation or rule selection.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, fields
from itertools import combinations
from typing import Any, Mapping, Sequence

from canonical.runtime.g0_finite_typed_rule_synthesis import (
    PredicateSpec,
    RuleExample,
    synthesize_minimal_conjunctive_rule,
)

Grid = tuple[tuple[int, ...], ...]
SCHEMA = "PROJECT_BRAIN_GRID_DELTA_RULE_INDUCER_V2"
MAX_PACKS = 192


class GridDeltaRuleV2Error(ValueError):
    pass


def _grid(value: Sequence[Sequence[int]], label: str) -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise GridDeltaRuleV2Error(label.upper() + "_INVALID")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw in value:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
            raise GridDeltaRuleV2Error(label.upper() + "_ROW_INVALID")
        row: list[int] = []
        for v in raw:
            if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 9:
                raise GridDeltaRuleV2Error(label.upper() + "_CELL_INVALID")
            row.append(v)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise GridDeltaRuleV2Error(label.upper() + "_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _shape(g: Grid) -> tuple[int, int]:
    return len(g), len(g[0])


@dataclass(frozen=True)
class Context:
    value: int
    n4: int
    n8: int
    row_nz: int
    col_nz: int
    row_same_color: int
    col_same_color: int
    color_frequency: int
    border: int
    component_area: int
    component_h: int
    component_w: int
    component_rel_r: int
    component_rel_c: int
    component_touches_border: int


ATTRIBUTES = tuple(f.name for f in fields(Context))


def _component_metadata(g: Grid) -> dict[tuple[int, int], tuple[int, int, int, int, int, int]]:
    h, w = _shape(g)
    seen: set[tuple[int, int]] = set()
    out: dict[tuple[int, int], tuple[int, int, int, int, int, int]] = {}
    for r in range(h):
        for c in range(w):
            color = g[r][c]
            if color == 0 or (r, c) in seen:
                continue
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
            rs = [x[0] for x in cells]
            cs = [x[1] for x in cells]
            r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
            ch, cw = r1 - r0 + 1, c1 - c0 + 1
            touches = int(r0 == 0 or c0 == 0 or r1 == h - 1 or c1 == w - 1)
            for rr, cc in cells:
                out[(rr, cc)] = (len(cells), ch, cw, rr - r0, cc - c0, touches)
    return out


def _contexts(g: Grid) -> dict[tuple[int, int], Context]:
    h, w = _shape(g)
    comp = _component_metadata(g)
    color_counts = Counter(v for row in g for v in row)
    result: dict[tuple[int, int], Context] = {}
    for r in range(h):
        for c in range(w):
            value = g[r][c]
            n4 = sum(
                0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] != 0
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
            )
            n8 = sum(
                0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] != 0
                for dr in (-1, 0, 1)
                for dc in (-1, 0, 1)
                if not (dr == 0 and dc == 0)
            )
            meta = comp.get((r, c), (0, 0, 0, -1, -1, 0))
            result[(r, c)] = Context(
                value=value,
                n4=int(n4),
                n8=int(n8),
                row_nz=sum(v != 0 for v in g[r]),
                col_nz=sum(g[rr][c] != 0 for rr in range(h)),
                row_same_color=sum(v == value for v in g[r]),
                col_same_color=sum(g[rr][c] == value for rr in range(h)),
                color_frequency=color_counts[value],
                border=int(r in (0, h - 1) or c in (0, w - 1)),
                component_area=meta[0],
                component_h=meta[1],
                component_w=meta[2],
                component_rel_r=meta[3],
                component_rel_c=meta[4],
                component_touches_border=meta[5],
            )
    return result


def _atom_id(attribute: str, value: int) -> str:
    return f"{attribute.upper()}_EQ_{value}"


def _parse_atom(pid: str) -> tuple[str, int]:
    prefix, raw = pid.rsplit("_EQ_", 1)
    return prefix.lower(), int(raw)


def _all_attribute_values(context_sets: Sequence[Mapping[tuple[int, int], Context]]) -> dict[str, list[int]]:
    values: dict[str, set[int]] = {a: set() for a in ATTRIBUTES}
    for contexts in context_sets:
        for ctx in contexts.values():
            for a in ATTRIBUTES:
                values[a].add(int(getattr(ctx, a)))
    return {a: sorted(vs) for a, vs in values.items()}


def _candidate_packs(attribute_values: Mapping[str, Sequence[int]]) -> list[tuple[str, ...]]:
    attrs = [a for a in ATTRIBUTES if 0 < len(attribute_values[a]) <= 20]
    packs: list[tuple[str, ...]] = []
    # Preserve structural coverage before richer conjunctions: every admissible
    # singleton, then every admissible pair, only then triples. This prevents a
    # cheap-cardinality sort from starving semantically distinct attributes.
    for size in (1, 2, 3):
        tier: list[tuple[str, ...]] = []
        for subset in combinations(attrs, size):
            count = sum(len(attribute_values[a]) for a in subset)
            if count <= 20:
                tier.append(subset)
        tier.sort(key=lambda p: (sum(len(attribute_values[a]) for a in p), p))
        packs.extend(tier)
        if len(packs) >= MAX_PACKS:
            break
    return packs[:MAX_PACKS]


def _specs(pack: Sequence[str], attribute_values: Mapping[str, Sequence[int]]) -> list[PredicateSpec]:
    out: list[PredicateSpec] = []
    for attr in pack:
        for value in attribute_values[attr]:
            pid = _atom_id(attr, int(value))
            out.append(
                PredicateSpec(
                    predicate_id=pid,
                    predicate_type="grid_cell_attribute_equality",
                    source={"path": "canonical/runtime/grid_delta_rule_inducer_v2.py", "span": [0, 1]},
                    cost=1.0,
                )
            )
    if not out or len(out) > 20:
        raise GridDeltaRuleV2Error("PREDICATE_PACK_SIZE_INVALID")
    return out


def _facts(ctx: Context, predicate_ids: Sequence[str]) -> frozenset[str]:
    result: set[str] = set()
    for pid in predicate_ids:
        attr, expected = _parse_atom(pid)
        if int(getattr(ctx, attr)) == expected:
            result.add(pid)
    return frozenset(result)


def _rule_ids(rule: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(x["predicate_id"] for x in rule["preconditions"]))


def _matches(ctx: Context, rule: Mapping[str, Any]) -> bool:
    predicate_ids = tuple(rule["predicate_ids"])
    facts = _facts(ctx, predicate_ids)
    return all(pid in facts for pid in rule["rule_predicates"])


def _synthesize_for_target(
    pairs: Sequence[tuple[Grid, Grid]],
    input_contexts: Sequence[Mapping[tuple[int, int], Context]],
    target: int,
    packs: Sequence[tuple[str, ...]],
    attribute_values: Mapping[str, Sequence[int]],
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []

    for pack in packs:
        specs = _specs(pack, attribute_values)
        pids = [p.predicate_id for p in specs]
        records: list[tuple[str, frozenset[str], bool]] = []
        for pi, ((inp, out), contexts) in enumerate(zip(pairs, input_contexts)):
            for (r, c), ctx in contexts.items():
                positive = inp[r][c] != out[r][c] and out[r][c] == target
                records.append((f"t{target}_p{pi}_r{r}_c{c}", _facts(ctx, pids), positive))

        positives = [x for x in records if x[2]]
        negatives = [x for x in records if not x[2]]
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

        result = synthesize_minimal_conjunctive_rule(
            predicates=specs,
            examples=[
                RuleExample(eid, facts, positive, {"observation_id": eid})
                for eid, facts, positive in chosen
            ],
            emit={"set_color": target, "attributes": list(pack)},
        )
        if result.get("status") not in ("SYNTHESIZED_UNIQUE", "SYNTHESIZED_AMBIGUOUS"):
            continue

        for synthesized in result["rules"]:
            ids = _rule_ids(synthesized)
            candidate = {
                "target_color": target,
                "attributes": list(pack),
                "predicate_ids": pids,
                "rule_predicates": list(ids),
                "cost": float(synthesized["cost"]),
            }
            valid = True
            for (inp, out), contexts in zip(pairs, input_contexts):
                for (r, c), ctx in contexts.items():
                    should = inp[r][c] != out[r][c] and out[r][c] == target
                    if _matches(ctx, candidate) != should:
                        valid = False
                        break
                if not valid:
                    break
            if valid:
                verified.append(candidate)

    return verified


def _selected_positions(grid: Grid, rule: Mapping[str, Any]) -> frozenset[tuple[int, int]]:
    contexts = _contexts(grid)
    return frozenset(pos for pos, ctx in contexts.items() if _matches(ctx, rule))


def _consensus_predict(
    grid: Grid,
    target_rule_options: Sequence[Mapping[str, Any]],
) -> tuple[str, Grid | None]:
    selected_by_target: dict[int, frozenset[tuple[int, int]]] = {}
    for group in target_rule_options:
        target = int(group["target_color"])
        options = group["rules"]
        selections = {_selected_positions(grid, rule) for rule in options}
        if len(selections) != 1:
            return "AMBIGUOUS_PREDICTION", None
        selected_by_target[target] = next(iter(selections))

    occupied: dict[tuple[int, int], int] = {}
    for target, positions in selected_by_target.items():
        for pos in positions:
            if pos in occupied and occupied[pos] != target:
                return "UNDEFINED_CONFLICT", None
            occupied[pos] = target

    out = [list(row) for row in grid]
    for (r, c), target in occupied.items():
        out[r][c] = target
    return "PREDICTED", tuple(tuple(row) for row in out)


def induce(training_pairs: Sequence[Mapping[str, Sequence[Sequence[int]]]]) -> dict[str, Any]:
    try:
        pairs: list[tuple[Grid, Grid]] = []
        if not isinstance(training_pairs, Sequence) or isinstance(training_pairs, (str, bytes)) or not training_pairs:
            raise GridDeltaRuleV2Error("TRAINING_PAIRS_INVALID")
        for i, raw in enumerate(training_pairs):
            inp = _grid(raw["input"], f"pair_{i}_input")
            out = _grid(raw["output"], f"pair_{i}_output")
            if _shape(inp) != _shape(out):
                return {"schema": SCHEMA, "status": "UNSUPPORTED", "reason": "SHAPE_CHANGE"}
            pairs.append((inp, out))
    except (GridDeltaRuleV2Error, KeyError, TypeError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}

    targets = sorted({
        out[r][c]
        for inp, out in pairs
        for r in range(len(inp))
        for c in range(len(inp[0]))
        if inp[r][c] != out[r][c]
    })
    if not targets:
        return {"schema": SCHEMA, "status": "UNSUPPORTED", "reason": "NO_CHANGE"}

    contexts = [_contexts(inp) for inp, _ in pairs]
    attribute_values = _all_attribute_values(contexts)
    packs = _candidate_packs(attribute_values)
    if not packs:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "NO_ADMISSIBLE_PREDICATE_PACK"}

    target_rule_options: list[dict[str, Any]] = []
    for target in targets:
        rules = _synthesize_for_target(pairs, contexts, target, packs, attribute_values)
        if not rules:
            return {
                "schema": SCHEMA,
                "status": "NO_VERIFIED_RULE",
                "failed_target_color": target,
                "changed_target_colors": targets,
                "predicate_pack_count": len(packs),
                "terminal_authority": False,
            }
        min_cost = min(float(rule["cost"]) for rule in rules)
        best = [rule for rule in rules if float(rule["cost"]) == min_cost]
        # Remove byte-identical rule descriptions without collapsing genuinely
        # different predicates that only happen to agree on training examples.
        seen: set[tuple[Any, ...]] = set()
        deduped: list[dict[str, Any]] = []
        for rule in sorted(
            best,
            key=lambda x: (tuple(x["attributes"]), tuple(x["rule_predicates"])),
        ):
            key = (
                tuple(rule["attributes"]),
                tuple(rule["predicate_ids"]),
                tuple(rule["rule_predicates"]),
                int(rule["target_color"]),
            )
            if key not in seen:
                seen.add(key)
                deduped.append(rule)
        target_rule_options.append({
            "target_color": target,
            "minimum_cost": min_cost,
            "rules": deduped,
            "rule_option_count": len(deduped),
        })

    # Every retained rule was already proven to select exactly the target's
    # changed cells on every training example, so their cross-target union is
    # training-exact without materializing the Cartesian product.
    for inp, out in pairs:
        status, predicted = _consensus_predict(inp, target_rule_options)
        if status != "PREDICTED" or predicted != out:
            return {
                "schema": SCHEMA,
                "status": "INTERNAL_VERIFICATION_FAILURE",
                "reason": status,
                "terminal_authority": False,
            }

    total_min_cost = sum(float(x["minimum_cost"]) for x in target_rule_options)
    ambiguity_count = sum(int(x["rule_option_count"]) > 1 for x in target_rule_options)
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_FACTORIZED_RULE_OPTIONS",
        "changed_target_colors": targets,
        "minimum_cost": total_min_cost,
        "target_rule_options": target_rule_options,
        "ambiguous_target_count": ambiguity_count,
        "ambiguity_preserved": ambiguity_count > 0,
        "training_full_replay_verified": True,
        "predicate_pack_count": len(packs),
        "attribute_universe": list(ATTRIBUTES),
        "synthesis_engine": "G0_FINITE_TYPED_RULE_SYNTHESIS_001",
        "scope": "SAME_SHAPE_MULTI_TARGET_ADAPTIVE_ATTRIBUTE_EQUALITY_PACKS",
        "terminal_authority": False,
        "promotion_authority": False,
    }


def predict(result: Mapping[str, Any], grid: Sequence[Sequence[int]]) -> dict[str, Any]:
    try:
        g = _grid(grid, "grid")
        status, out = _consensus_predict(g, result["target_rule_options"])
    except (GridDeltaRuleV2Error, KeyError, TypeError, ValueError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}
    if status != "PREDICTED" or out is None:
        return {"schema": SCHEMA, "status": status, "prediction": None}
    return {
        "schema": SCHEMA,
        "status": "PREDICTED",
        "prediction": [list(row) for row in out],
        "terminal_authority": False,
    }
