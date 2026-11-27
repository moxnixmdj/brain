"""Zero-learned-state MDL-style program induction kernel.

The kernel searches deterministic primitive compositions in increasing description
length and returns the shortest exact program fitting the supplied examples.
It contains no trainable parameters. A learned task solution is represented as an
explicit program and can be verified or compiled without changing this kernel.

This is intentionally a narrow semantic-induction primitive, not a claim of
open-world or frontier-level unknown-domain adaptation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import heapq
import json
from typing import Any, Callable, Iterable, Mapping, Sequence


class ProgramInductionError(ValueError):
    pass


@dataclass(frozen=True)
class Primitive:
    primitive_id: str
    cost: int
    fn: Callable[[Any], Any]


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        return repr(value)


def _validate_primitives(primitives: Sequence[Primitive]) -> dict[str, Primitive]:
    if not isinstance(primitives, Sequence) or not primitives:
        raise ProgramInductionError("PRIMITIVES_REQUIRED")
    out: dict[str, Primitive] = {}
    for primitive in primitives:
        if not isinstance(primitive, Primitive):
            raise ProgramInductionError("PRIMITIVE_INVALID")
        pid = primitive.primitive_id.strip()
        if not pid or pid in out:
            raise ProgramInductionError("PRIMITIVE_ID_INVALID_OR_DUPLICATE")
        if (
            isinstance(primitive.cost, bool)
            or not isinstance(primitive.cost, int)
            or primitive.cost <= 0
        ):
            raise ProgramInductionError("PRIMITIVE_COST_INVALID:" + pid)
        if not callable(primitive.fn):
            raise ProgramInductionError("PRIMITIVE_FN_NOT_CALLABLE:" + pid)
        out[pid] = Primitive(pid, primitive.cost, primitive.fn)
    return out


def _validate_examples(examples: Sequence[tuple[Any, Any]]) -> list[tuple[Any, Any]]:
    if not isinstance(examples, Sequence) or not examples:
        raise ProgramInductionError("EXAMPLES_REQUIRED")
    out = []
    for row in examples:
        if not isinstance(row, tuple) or len(row) != 2:
            raise ProgramInductionError("EXAMPLE_MUST_BE_INPUT_OUTPUT_TUPLE")
        out.append(row)
    return out


def execute(
    program: Sequence[str],
    value: Any,
    primitives: Mapping[str, Primitive],
) -> Any:
    state = value
    for pid in program:
        primitive = primitives.get(pid)
        if primitive is None:
            raise ProgramInductionError("UNKNOWN_PRIMITIVE:" + str(pid))
        state = primitive.fn(state)
    return state


def _run_examples(
    program: tuple[str, ...],
    examples: Sequence[tuple[Any, Any]],
    primitives: Mapping[str, Primitive],
) -> tuple[bool, tuple[str, ...], tuple[str, ...]] | None:
    outputs = []
    targets = []
    try:
        for inp, expected in examples:
            outputs.append(_canonical(execute(program, inp, primitives)))
            targets.append(_canonical(expected))
    except Exception:
        return None
    return outputs == targets, tuple(outputs), tuple(targets)


def _registry_fingerprint(primitives: Mapping[str, Primitive]) -> str:
    rows = [
        {"primitive_id": p.primitive_id, "cost": p.cost}
        for p in sorted(primitives.values(), key=lambda x: x.primitive_id)
    ]
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def synthesize(
    *,
    examples: Sequence[tuple[Any, Any]],
    primitives: Sequence[Primitive],
    max_description_length: int,
    max_programs_evaluated: int = 100000,
) -> dict[str, Any]:
    """Return the minimum-description-length exact program if one is found.

    Search is uniform-cost over primitive description length. Semantic states that
    produce identical outputs on all training examples are expanded only from their
    cheapest representative. Because every suffix is deterministic, a more
    expensive program with the same training outputs cannot lead to a cheaper exact
    solution than the representative.
    """
    ex = _validate_examples(examples)
    registry = _validate_primitives(primitives)
    if (
        isinstance(max_description_length, bool)
        or not isinstance(max_description_length, int)
        or max_description_length < 0
    ):
        raise ProgramInductionError("MAX_DESCRIPTION_LENGTH_INVALID")
    if (
        isinstance(max_programs_evaluated, bool)
        or not isinstance(max_programs_evaluated, int)
        or max_programs_evaluated < 1
    ):
        raise ProgramInductionError("MAX_PROGRAMS_EVALUATED_INVALID")

    primitive_order = sorted(registry)
    heap: list[tuple[int, int, tuple[str, ...]]] = [(0, 0, ())]
    queued = {()}
    best_signature_cost: dict[tuple[str, ...], int] = {}
    evaluated = 0
    pruned = 0

    while heap and evaluated < max_programs_evaluated:
        cost, depth, program = heapq.heappop(heap)
        if cost > max_description_length:
            break

        run = _run_examples(program, ex, registry)
        evaluated += 1
        if run is None:
            continue
        exact, outputs, _targets = run
        if exact:
            return {
                "schema": "PROJECT_BRAIN_MDL_PROGRAM_INDUCTION_RESULT_V1",
                "status": "EXACT_PROGRAM_FOUND",
                "program": list(program),
                "description_length": cost,
                "program_depth": depth,
                "programs_evaluated": evaluated,
                "semantic_states_pruned": pruned,
                "registry_fingerprint": _registry_fingerprint(registry),
                "persistent_learned_state_bytes": 0,
                "frontier_or_external_model_required": False,
                "minimality_within_declared_search_space": True,
            }

        prior = best_signature_cost.get(outputs)
        if prior is not None and prior <= cost:
            pruned += 1
            continue
        best_signature_cost[outputs] = cost

        for pid in primitive_order:
            primitive = registry[pid]
            new_cost = cost + primitive.cost
            if new_cost > max_description_length:
                continue
            candidate = program + (pid,)
            if candidate in queued:
                continue
            queued.add(candidate)
            heapq.heappush(heap, (new_cost, depth + 1, candidate))

    return {
        "schema": "PROJECT_BRAIN_MDL_PROGRAM_INDUCTION_RESULT_V1",
        "status": "NO_EXACT_PROGRAM_WITHIN_DECLARED_SEARCH",
        "program": None,
        "description_length": None,
        "programs_evaluated": evaluated,
        "semantic_states_pruned": pruned,
        "registry_fingerprint": _registry_fingerprint(registry),
        "persistent_learned_state_bytes": 0,
        "frontier_or_external_model_required": False,
        "minimality_within_declared_search_space": False,
    }


def verify(
    *,
    program: Sequence[str],
    examples: Sequence[tuple[Any, Any]],
    primitives: Sequence[Primitive],
) -> dict[str, Any]:
    ex = _validate_examples(examples)
    registry = _validate_primitives(primitives)
    run = _run_examples(tuple(program), ex, registry)
    if run is None:
        passed = False
    else:
        passed = bool(run[0])
    return {
        "schema": "PROJECT_BRAIN_MDL_PROGRAM_VERIFICATION_V1",
        "pass": passed,
        "case_count": len(ex),
        "program": list(program),
        "registry_fingerprint": _registry_fingerprint(registry),
        "persistent_learned_state_bytes": 0,
    }


def compile_program(
    *,
    program: Sequence[str],
    primitives: Sequence[Primitive],
) -> dict[str, Any]:
    registry = _validate_primitives(primitives)
    total = 0
    normalized = []
    for pid in program:
        if pid not in registry:
            raise ProgramInductionError("UNKNOWN_PRIMITIVE:" + str(pid))
        total += registry[pid].cost
        normalized.append(pid)
    return {
        "schema": "PROJECT_BRAIN_COMPILED_DETERMINISTIC_CAPABILITY_PROGRAM_V1",
        "program": normalized,
        "description_length": total,
        "registry_fingerprint": _registry_fingerprint(registry),
        "persistent_learned_state_bytes": 0,
        "requires_retraining_for_reuse": False,
        "promotion_authority": False,
    }
