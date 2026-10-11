"""Bounded typed visual program inventor V1.

This module performs Brain-owned deterministic program induction over an explicit
primitive library. It is intentionally domain-agnostic: callers provide typed
primitives, examples, and bounds. The engine performs complete breadth-first
enumeration within the declared depth/state bounds, semantic deduplication,
minimum-cost ranking, exact example falsification, ambiguity preservation, and
a fail-closed grammar-exhaustion report.

It grants no execution, promotion, benchmark, or terminal credit.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINITE_VISUAL_PROGRAM_INVENTOR_V1"
Grid = tuple[tuple[int, ...], ...]
Transform = Callable[[Grid], Grid | None]


class ProgramInventionError(ValueError):
    pass


@dataclass(frozen=True)
class PrimitiveSpec:
    primitive_id: str
    input_type: str
    output_type: str
    cost: float
    source: Mapping[str, Any]
    apply: Transform


@dataclass(frozen=True)
class Program:
    primitive_ids: tuple[str, ...]
    cost: float

    @property
    def depth(self) -> int:
        return len(self.primitive_ids)

    @property
    def signature(self) -> str:
        return " -> ".join(self.primitive_ids) if self.primitive_ids else "IDENTITY"


def _grid(value: Sequence[Sequence[int]], field: str) -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ProgramInventionError(field.upper() + "_INVALID")
    width: int | None = None
    rows: list[tuple[int, ...]] = []
    for raw_row in value:
        if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes)) or not raw_row:
            raise ProgramInventionError(field.upper() + "_ROW_INVALID")
        row: list[int] = []
        for cell in raw_row:
            if not isinstance(cell, int) or isinstance(cell, bool):
                raise ProgramInventionError(field.upper() + "_CELL_INVALID")
            row.append(cell)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ProgramInventionError(field.upper() + "_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _tolist(grid: Grid) -> list[list[int]]:
    return [list(row) for row in grid]


def _validate_primitives(primitives: Sequence[PrimitiveSpec]) -> dict[str, PrimitiveSpec]:
    if not isinstance(primitives, Sequence) or isinstance(primitives, (str, bytes)) or not primitives:
        raise ProgramInventionError("PRIMITIVES_INVALID")
    out: dict[str, PrimitiveSpec] = {}
    for p in primitives:
        if not isinstance(p, PrimitiveSpec):
            raise ProgramInventionError("PRIMITIVE_SPEC_INVALID")
        if not p.primitive_id or p.primitive_id in out:
            raise ProgramInventionError("PRIMITIVE_ID_INVALID_OR_DUPLICATE")
        if not p.input_type or not p.output_type:
            raise ProgramInventionError("PRIMITIVE_TYPE_INVALID:" + p.primitive_id)
        if isinstance(p.cost, bool) or not isinstance(p.cost, (int, float)) or not isfinite(float(p.cost)) or p.cost <= 0:
            raise ProgramInventionError("PRIMITIVE_COST_INVALID:" + p.primitive_id)
        if not isinstance(p.source, Mapping) or not p.source:
            raise ProgramInventionError("PRIMITIVE_SOURCE_INVALID:" + p.primitive_id)
        if not callable(p.apply):
            raise ProgramInventionError("PRIMITIVE_APPLY_INVALID:" + p.primitive_id)
        out[p.primitive_id] = p
    return out


def _normalize_examples(examples: Sequence[Mapping[str, Any]]) -> tuple[list[Grid], list[Grid]]:
    if not isinstance(examples, Sequence) or isinstance(examples, (str, bytes)) or not examples:
        raise ProgramInventionError("EXAMPLES_INVALID")
    inputs: list[Grid] = []
    outputs: list[Grid] = []
    for i, row in enumerate(examples):
        if not isinstance(row, Mapping) or "input" not in row or "output" not in row:
            raise ProgramInventionError(f"EXAMPLE_{i}_INVALID")
        inputs.append(_grid(row["input"], f"example_{i}_input"))
        outputs.append(_grid(row["output"], f"example_{i}_output"))
    return inputs, outputs


def _apply_program(program: Program, grid: Grid, primitive_map: Mapping[str, PrimitiveSpec]) -> Grid | None:
    value = grid
    current_type = "GRID"
    for primitive_id in program.primitive_ids:
        p = primitive_map[primitive_id]
        if p.input_type != current_type:
            return None
        try:
            value = p.apply(value)
        except Exception:
            return None
        if value is None:
            return None
        if not isinstance(value, tuple) or not value or not isinstance(value[0], tuple):
            return None
        current_type = p.output_type
    return value if current_type == "GRID" else None


def _semantic_key(outputs: Sequence[Grid]) -> tuple[Grid, ...]:
    return tuple(outputs)


def _objective(program: Program) -> tuple[float, int, tuple[str, ...]]:
    return (float(program.cost), program.depth, program.primitive_ids)


def _residual_summary(inputs: Sequence[Grid], targets: Sequence[Grid]) -> dict[str, Any]:
    shape_relations: dict[str, int] = {}
    support_relations: dict[str, int] = {}
    for inp, out in zip(inputs, targets):
        ishape = (len(inp), len(inp[0]))
        oshape = (len(out), len(out[0]))
        if ishape == oshape:
            shape_rel = "SAME_SHAPE"
        elif oshape[0] <= ishape[0] and oshape[1] <= ishape[1]:
            shape_rel = "OUTPUT_NOT_LARGER"
        elif oshape[0] >= ishape[0] and oshape[1] >= ishape[1]:
            shape_rel = "OUTPUT_NOT_SMALLER"
        else:
            shape_rel = "MIXED_SHAPE_CHANGE"
        shape_relations[shape_rel] = shape_relations.get(shape_rel, 0) + 1

        if ishape == oshape:
            in_nonzero = {(r, c) for r, row in enumerate(inp) for c, v in enumerate(row) if v != 0}
            out_nonzero = {(r, c) for r, row in enumerate(out) for c, v in enumerate(row) if v != 0}
            if in_nonzero == out_nonzero:
                support = "SUPPORT_PRESERVED"
            elif in_nonzero.issubset(out_nonzero):
                support = "ADDITION_ONLY_SUPPORT"
            elif out_nonzero.issubset(in_nonzero):
                support = "REMOVAL_ONLY_SUPPORT"
            else:
                support = "SUPPORT_MOVED_OR_MIXED"
            support_relations[support] = support_relations.get(support, 0) + 1
    return {
        "shape_relations": dict(sorted(shape_relations.items())),
        "support_relations": dict(sorted(support_relations.items())),
    }


def invent(
    examples: Sequence[Mapping[str, Any]],
    primitives: Sequence[PrimitiveSpec],
    *,
    max_depth: int = 3,
    max_semantic_states_per_depth: int = 50000,
    max_equivalent_programs_per_semantics: int = 8,
    top_k: int = 16,
) -> dict[str, Any]:
    try:
        primitive_map = _validate_primitives(primitives)
        inputs, targets = _normalize_examples(examples)
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0 or max_depth > 8:
            raise ProgramInventionError("MAX_DEPTH_INVALID")
        if (
            isinstance(max_semantic_states_per_depth, bool)
            or not isinstance(max_semantic_states_per_depth, int)
            or max_semantic_states_per_depth < 1
        ):
            raise ProgramInventionError("MAX_SEMANTIC_STATES_INVALID")
        if (
            isinstance(max_equivalent_programs_per_semantics, bool)
            or not isinstance(max_equivalent_programs_per_semantics, int)
            or max_equivalent_programs_per_semantics < 1
            or max_equivalent_programs_per_semantics > 128
        ):
            raise ProgramInventionError("MAX_EQUIVALENT_PROGRAMS_INVALID")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1 or top_k > 128:
            raise ProgramInventionError("TOP_K_INVALID")
    except ProgramInventionError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": str(exc),
            "terminal_authority": False,
        }

    target_key = _semantic_key(targets)
    exact: list[Program] = []
    state_counts: dict[str, int] = {}
    representative_counts: dict[str, int] = {}
    generated_programs = 0
    pruned_by_semantics = 0
    bound_hit = False

    identity = Program((), 0.0)
    identity_outputs = tuple(inputs)
    if identity_outputs == target_key:
        exact.append(identity)

    frontier: dict[tuple[Grid, ...], list[Program]] = {_semantic_key(inputs): [identity]}

    ordered_primitives = sorted(primitive_map.values(), key=lambda p: (float(p.cost), p.primitive_id))

    for depth in range(1, max_depth + 1):
        next_frontier: dict[tuple[Grid, ...], list[Program]] = {}
        frontier_rows = sorted(
            (
                (semantic, program)
                for semantic, programs in frontier.items()
                for program in programs
            ),
            key=lambda item: _objective(item[1]),
        )
        for previous_outputs, previous_program in frontier_rows:
            if previous_program.depth != depth - 1:
                continue
            for primitive in ordered_primitives:
                if primitive.input_type != "GRID" or primitive.output_type != "GRID":
                    continue
                generated_programs += 1
                program = Program(
                    previous_program.primitive_ids + (primitive.primitive_id,),
                    previous_program.cost + float(primitive.cost),
                )
                outputs: list[Grid] = []
                valid = True
                for grid in previous_outputs:
                    try:
                        out = primitive.apply(grid)
                    except Exception:
                        valid = False
                        break
                    if out is None:
                        valid = False
                        break
                    if not isinstance(out, tuple) or not out or not isinstance(out[0], tuple):
                        valid = False
                        break
                    outputs.append(out)
                if not valid:
                    continue

                key = _semantic_key(outputs)
                bucket = next_frontier.setdefault(key, [])
                if any(p.primitive_ids == program.primitive_ids for p in bucket):
                    continue
                bucket.append(program)
                bucket.sort(key=_objective)
                if len(bucket) > max_equivalent_programs_per_semantics:
                    bucket.pop()
                    pruned_by_semantics += 1
                if key == target_key:
                    exact.append(program)

        if len(next_frontier) > max_semantic_states_per_depth:
            bound_hit = True
            ordered_states = sorted(
                next_frontier.items(),
                key=lambda item: _objective(item[1][0]),
            )
            next_frontier = dict(ordered_states[:max_semantic_states_per_depth])
        state_counts[str(depth)] = len(next_frontier)
        representative_counts[str(depth)] = sum(len(v) for v in next_frontier.values())
        frontier = next_frontier

    unique_exact: dict[tuple[str, ...], Program] = {}
    for program in exact:
        incumbent = unique_exact.get(program.primitive_ids)
        if incumbent is None or _objective(program) < _objective(incumbent):
            unique_exact[program.primitive_ids] = program
    exact_programs = sorted(unique_exact.values(), key=_objective)

    if exact_programs:
        status = "EXACT_PROGRAMS_FOUND"
    elif bound_hit:
        status = "SEARCH_BOUND_REACHED__NO_EXACT_PROGRAM"
    else:
        status = "GRAMMAR_EXHAUSTED__REPRESENTATION_EXPANSION_REQUIRED"

    return {
        "schema": SCHEMA,
        "status": status,
        "example_count": len(inputs),
        "primitive_count": len(primitive_map),
        "max_depth": max_depth,
        "generated_program_count": generated_programs,
        "semantic_states_by_depth": state_counts,
        "structural_representatives_by_depth": representative_counts,
        "max_equivalent_programs_per_semantics": max_equivalent_programs_per_semantics,
        "semantic_dedup_pruned_count": pruned_by_semantics,
        "search_bound_hit": bound_hit,
        "exact_program_count": len(exact_programs),
        "programs": [
            {
                "primitive_ids": list(p.primitive_ids),
                "signature": p.signature,
                "depth": p.depth,
                "cost": p.cost,
            }
            for p in exact_programs[:top_k]
        ],
        "residual_summary": _residual_summary(inputs, targets),
        "next_action": (
            "VERIFY_AND_GENERALIZE_LOWEST_COST_EXACT_PROGRAMS"
            if exact_programs
            else "SYNTHESIZE_SMALLEST_MISSING_REPRESENTATION_OR_PRIMITIVE_CLASS"
        ),
        "candidate_macro": (
            None
            if not exact_programs or exact_programs[0].depth < 2
            else {
                "primitive_ids": list(exact_programs[0].primitive_ids),
                "signature": exact_programs[0].signature,
                "candidate_only": True,
                "requires_independent_generalization": True,
            }
        ),
        "complete_only_within_declared_primitive_depth_and_state_bounds": True,
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "semantic_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }


def predict(
    program: Mapping[str, Any],
    grid: Sequence[Sequence[int]],
    primitives: Sequence[PrimitiveSpec],
) -> dict[str, Any]:
    try:
        primitive_map = _validate_primitives(primitives)
        g = _grid(grid, "prediction_grid")
        ids = program.get("primitive_ids")
        if not isinstance(ids, list) or any(not isinstance(x, str) or x not in primitive_map for x in ids):
            raise ProgramInventionError("PROGRAM_INVALID")
        p = Program(tuple(ids), sum(float(primitive_map[x].cost) for x in ids))
        out = _apply_program(p, g, primitive_map)
    except ProgramInventionError as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": str(exc)}
    if out is None:
        return {"schema": SCHEMA, "status": "UNDEFINED_FOR_INPUT", "prediction": None}
    return {
        "schema": SCHEMA,
        "status": "PREDICTED",
        "prediction": _tolist(out),
        "terminal_authority": False,
    }


def solve(
    examples: Sequence[Mapping[str, Any]],
    test_inputs: Sequence[Sequence[Sequence[int]]],
    primitives: Sequence[PrimitiveSpec],
    *,
    max_depth: int = 3,
    attempts: int = 2,
    max_semantic_states_per_depth: int = 50000,
    max_equivalent_programs_per_semantics: int = 8,
) -> dict[str, Any]:
    result = invent(
        examples,
        primitives,
        max_depth=max_depth,
        max_semantic_states_per_depth=max_semantic_states_per_depth,
        max_equivalent_programs_per_semantics=max_equivalent_programs_per_semantics,
        top_k=128,
    )
    if result.get("status") != "EXACT_PROGRAMS_FOUND":
        return {
            "schema": SCHEMA,
            "status": result.get("status"),
            "invention": result,
            "attempts": [],
            "terminal_authority": False,
        }

    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "ATTEMPTS_INVALID"}

    prediction_sets: list[dict[str, Any]] = []
    seen: set[str] = set()
    import json

    for program in result["programs"]:
        predictions: list[list[list[int]]] = []
        valid = True
        for raw in test_inputs:
            out = predict(program, raw, primitives)
            if out.get("status") != "PREDICTED":
                valid = False
                break
            predictions.append(out["prediction"])
        if not valid:
            continue
        key = json.dumps(predictions, separators=(",", ":"), sort_keys=False)
        if key in seen:
            continue
        seen.add(key)
        prediction_sets.append(
            {
                "program": program,
                "predictions": predictions,
            }
        )
        if len(prediction_sets) >= attempts:
            break

    return {
        "schema": SCHEMA,
        "status": "SOLVED_CANDIDATES" if prediction_sets else "NO_TEST_PREDICTION",
        "invention": result,
        "attempts": prediction_sets,
        "ambiguity_preserved": len(prediction_sets) > 1,
        "terminal_authority": False,
    }
