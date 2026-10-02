"""Bounded exhaustive typed template/effect-model synthesizer.

This is proposal generation only. Given a finite explicit typed primitive vocabulary,
it enumerates all well-typed linear composition templates up to a declared step bound.
It never assigns truth or terminal authority to generated candidates.
"""
from __future__ import annotations

from itertools import product
import json
import re
from typing import Any

SCHEMA = "BRAIN_BOUNDED_TYPED_TEMPLATE_SYNTHESIZER_V1"


def _fail(error: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "error": error,
        "terminal_authority": False,
    }


def synthesize_templates(
    initial_facts: dict[str, str],
    primitives: list[dict[str, Any]],
    target_type: str,
    *,
    max_steps: int = 3,
    max_candidates: int = 256,
    max_states: int = 10000,
) -> dict[str, Any]:
    """Enumerate all candidates within a finite typed vocabulary and step bound.

    Primitive schema:
      {"id": "name", "inputs": ["type_a", ...], "output": "type_b"}

    A repeated application with the same primitive id and the same bound arguments is
    skipped because, under this pure typed-template contract, it creates no new
    information. If a candidate/state limit is hit, the result is explicitly TRUNCATED
    and cannot be treated as exhaustive.
    """
    if (
        not isinstance(initial_facts, dict)
        or not initial_facts
        or any(
            not isinstance(name, str)
            or not name
            or not isinstance(kind, str)
            or not kind
            for name, kind in initial_facts.items()
        )
    ):
        return _fail("INVALID_INITIAL_FACTS")
    if not isinstance(target_type, str) or not target_type:
        return _fail("INVALID_TARGET_TYPE")
    if not isinstance(max_steps, int) or max_steps < 0 or max_steps > 8:
        return _fail("INVALID_MAX_STEPS")
    if not isinstance(max_candidates, int) or max_candidates < 1:
        return _fail("INVALID_MAX_CANDIDATES")
    if not isinstance(max_states, int) or max_states < 1:
        return _fail("INVALID_MAX_STATES")
    if not isinstance(primitives, list):
        return _fail("INVALID_PRIMITIVES")

    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    for primitive in primitives:
        if not isinstance(primitive, dict):
            return _fail("INVALID_PRIMITIVE")
        pid = primitive.get("id")
        inputs = primitive.get("inputs")
        output = primitive.get("output")
        if not isinstance(pid, str) or not pid or pid in ids:
            return _fail("INVALID_OR_DUPLICATE_PRIMITIVE_ID")
        if (
            not isinstance(inputs, list)
            or any(not isinstance(kind, str) or not kind for kind in inputs)
        ):
            return _fail("INVALID_PRIMITIVE_INPUT_TYPES")
        if not isinstance(output, str) or not output:
            return _fail("INVALID_PRIMITIVE_OUTPUT_TYPE")
        ids.add(pid)
        normalized.append({"id": pid, "inputs": tuple(inputs), "output": output})
    normalized.sort(key=lambda item: item["id"])

    start_symbols = tuple(sorted(initial_facts.items()))
    frontier = [(start_symbols, tuple(), frozenset())]
    seen = {(start_symbols, tuple())}
    results: list[dict[str, Any]] = []
    result_keys: set[str] = set()
    explored_states = 0
    truncated = False

    for depth in range(max_steps + 1):
        next_frontier = []
        for symbols, steps, applied in frontier:
            explored_states += 1
            if explored_states > max_states:
                truncated = True
                break

            for name, kind in symbols:
                if kind != target_type:
                    continue
                candidate = {
                    "steps": [dict(step) for step in steps],
                    "terminal": name,
                    "terminal_type": target_type,
                    "truth_authority": False,
                }
                key = json.dumps(candidate, sort_keys=True, separators=(",", ":"))
                if key in result_keys:
                    continue
                result_keys.add(key)
                results.append(candidate)
                if len(results) >= max_candidates:
                    truncated = True
                    break
            if truncated:
                break
            if depth == max_steps:
                continue

            by_type: dict[str, list[str]] = {}
            for name, kind in symbols:
                by_type.setdefault(kind, []).append(name)

            for primitive in normalized:
                pools = [by_type.get(kind, []) for kind in primitive["inputs"]]
                if any(not pool for pool in pools):
                    continue
                bindings = product(*pools) if pools else [()]
                for args in bindings:
                    application = (primitive["id"], tuple(args))
                    if application in applied:
                        continue
                    safe_id = re.sub(r"[^A-Za-z0-9_]+", "_", primitive["id"]).strip("_") or "p"
                    output_name = f"v{len(steps) + 1}_{safe_id}"
                    if any(name == output_name for name, _ in symbols):
                        suffix = 2
                        while any(
                            name == f"{output_name}_{suffix}" for name, _ in symbols
                        ):
                            suffix += 1
                        output_name = f"{output_name}_{suffix}"

                    step = {
                        "primitive_id": primitive["id"],
                        "args": list(args),
                        "output": output_name,
                        "output_type": primitive["output"],
                    }
                    new_symbols = tuple(
                        sorted(symbols + ((output_name, primitive["output"]),))
                    )
                    new_steps = steps + (tuple(step.items()),)
                    new_applied = frozenset(set(applied) | {application})
                    signature = (new_symbols, tuple(sorted(new_applied)))
                    if signature in seen:
                        continue
                    seen.add(signature)
                    next_frontier.append((new_symbols, new_steps, new_applied))
        if truncated:
            break
        frontier = next_frontier

    results.sort(
        key=lambda candidate: (
            len(candidate["steps"]),
            json.dumps(candidate, sort_keys=True),
        )
    )
    status = (
        "TRUNCATED"
        if truncated
        else ("COMPLETE_WITH_CANDIDATES" if results else "COMPLETE_NO_CANDIDATE")
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "complete_within_declared_bound": not truncated,
        "max_steps": max_steps,
        "candidate_count": len(results),
        "explored_states": explored_states,
        "candidates": results,
        "terminal_authority": False,
        "scope": "FINITE_EXPLICIT_TYPED_PRIMITIVE_VOCABULARY_ONLY",
    }
