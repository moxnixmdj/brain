"""Conservative ARC solver combining V16 direct hypotheses with program invention.

Policy:
1. Preserve unique V16 candidate output bundles in their existing order.
2. If fewer than two distinct candidate bundles are available, fill remaining
   attempt slots with the generic program inventor.
3. Never evict a distinct incumbent V16 bundle to make room for invention.

This guarantees no loss from replacing an already distinct incumbent attempt.
It is an integration adapter only and grants no benchmark or promotion credit.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from canonical.runtime import arc_novelty_compiler_v1 as arc
from canonical.runtime import arc_visual_program_invention_adapter_v1 as inventor

SCHEMA = "PROJECT_BRAIN_ARC_CONSERVATIVE_COMBINED_SOLVER_V1"


def _bundle_key(predictions: list[list[list[int]]]) -> str:
    return json.dumps(predictions, separators=(",", ":"), sort_keys=False)


def _direct_bundles(task: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train = task.get("train")
    test = task.get("test")
    if not isinstance(train, list) or not train or not isinstance(test, list) or not test:
        return [], {"status": "FAIL_CLOSED", "reason": "TASK_INVALID"}

    compiled = arc.compile_hypotheses(train)
    bundles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, hypothesis in enumerate(compiled.get("hypotheses", [])):
        predictions: list[list[list[int]]] = []
        valid = True
        for row in test:
            out = arc.predict(hypothesis, row["input"])
            if out.get("status") != "PREDICTED":
                valid = False
                break
            predictions.append(out["prediction"])
        if not valid:
            continue
        key = _bundle_key(predictions)
        if key in seen:
            continue
        seen.add(key)
        bundles.append(
            {
                "source": "ARC_V16_DIRECT",
                "rank": index,
                "kind": hypothesis.get("kind"),
                "predictions": predictions,
            }
        )
    return bundles, compiled


def solve_task(
    task: Mapping[str, Any],
    *,
    attempts: int = 2,
    max_depth: int = 3,
    max_semantic_states_per_depth: int = 4000,
    max_equivalent_programs_per_semantics: int = 4,
    max_grid_cells: int = 10000,
) -> dict[str, Any]:
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "ATTEMPTS_INVALID"}

    direct, compiled = _direct_bundles(task)
    selected = direct[:attempts]
    seen = {_bundle_key(row["predictions"]) for row in selected}
    inventor_used = False
    invention_result: dict[str, Any] | None = None

    if len(selected) < attempts:
        inventor_used = True
        invention_result = inventor.solve_task(
            task,
            max_depth=max_depth,
            attempts=max(attempts * 4, 8),
            max_semantic_states_per_depth=max_semantic_states_per_depth,
            max_equivalent_programs_per_semantics=max_equivalent_programs_per_semantics,
            max_grid_cells=max_grid_cells,
        )
        if invention_result.get("status") == "SOLVED_CANDIDATES":
            for row in invention_result["program_invention"].get("attempts", []):
                predictions = row.get("predictions")
                if not isinstance(predictions, list):
                    continue
                key = _bundle_key(predictions)
                if key in seen:
                    continue
                seen.add(key)
                selected.append(
                    {
                        "source": "PROGRAM_INVENTOR",
                        "program": row.get("program"),
                        "predictions": predictions,
                    }
                )
                if len(selected) >= attempts:
                    break

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_ATTEMPTS" if selected else "NO_CANDIDATE_ATTEMPTS",
        "attempts": selected,
        "direct_unique_bundle_count": len(direct),
        "inventor_used": inventor_used,
        "direct_compile_status": compiled.get("status"),
        "program_invention_status": None if invention_result is None else invention_result.get("status"),
        "incumbent_preservation_rule": "NO_DISTINCT_V16_BUNDLE_EVICTED_FOR_PROGRAM_INVENTION",
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }


def score_public_task(
    task: Mapping[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    result = solve_task(task, **kwargs)
    test = task.get("test", [])
    expected = [row.get("output") for row in test]
    attempts = result.get("attempts", [])
    exact = bool(expected) and all(
        any(
            len(candidate.get("predictions", [])) > i
            and candidate["predictions"][i] == expected[i]
            for candidate in attempts
        )
        for i in range(len(expected))
    )
    return {**result, "exact_task_solved": bool(exact)}
