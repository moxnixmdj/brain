from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_COMPONENTWISE_TOP_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_COMPONENTWISE_TOP_INPUT_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "common_top_exists": False,
        "target_preference_erasure_candidate": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _q(value: Any) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("BOOLEAN_NOT_NUMERIC")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str) and value.strip():
        return Fraction(value.strip())
    raise ValueError("VALUE_MUST_BE_INTEGER_OR_EXACT_RATIONAL_STRING")


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Find an action that reaches every declared dimension optimum simultaneously.

    This is a computation layer only. It does not establish that the declared
    dimensions are complete or independently trustworthy.
    """
    if not isinstance(payload, Mapping) or payload.get("schema") != INPUT_SCHEMA:
        return _fail("INPUT_SCHEMA_INVALID")

    dimensions = payload.get("dimensions")
    actions = payload.get("actions")
    if not isinstance(dimensions, list) or not dimensions:
        return _fail("DIMENSIONS_INVALID")
    if not isinstance(actions, list) or not actions:
        return _fail("ACTIONS_INVALID")

    dirs: dict[str, str] = {}
    for i, row in enumerate(dimensions):
        if not isinstance(row, Mapping):
            return _fail("DIMENSION_NOT_OBJECT", index=i)
        did = row.get("id")
        direction = row.get("direction")
        if not isinstance(did, str) or not did or did in dirs:
            return _fail("DIMENSION_ID_INVALID_OR_DUPLICATE", index=i)
        if direction not in {"MAX", "MIN"}:
            return _fail("DIMENSION_DIRECTION_INVALID", dimension=did)
        dirs[did] = direction

    vals: dict[str, dict[str, Fraction]] = {}
    for i, row in enumerate(actions):
        if not isinstance(row, Mapping):
            return _fail("ACTION_NOT_OBJECT", index=i)
        aid = row.get("id")
        raw = row.get("values")
        if not isinstance(aid, str) or not aid or aid in vals:
            return _fail("ACTION_ID_INVALID_OR_DUPLICATE", index=i)
        if not isinstance(raw, Mapping) or set(raw) != set(dirs):
            return _fail("ACTION_DIMENSION_SET_MISMATCH", action=aid)
        try:
            vals[aid] = {d: _q(raw[d]) for d in dirs}
        except Exception as exc:
            return _fail("ACTION_VALUE_INVALID", action=aid, error=str(exc))

    per_dimension: dict[str, dict[str, Any]] = {}
    common: set[str] | None = None
    for d, direction in dirs.items():
        column = {a: vals[a][d] for a in vals}
        optimum = max(column.values()) if direction == "MAX" else min(column.values())
        tops = sorted(a for a, value in column.items() if value == optimum)
        per_dimension[d] = {
            "direction": direction,
            "optimum": str(optimum),
            "top_action_ids": tops,
        }
        top_set = set(tops)
        common = top_set if common is None else common & top_set

    common_ids = sorted(common or set())
    if not common_ids:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "NO_COMMON_COMPONENTWISE_TOP",
            "common_top_exists": False,
            "common_top_action_ids": [],
            "per_dimension": per_dimension,
            "target_preference_erasure_candidate": False,
            "meaning": (
                "NO_DECLARED_ACTION_ATTAINS_EVERY_DECLARED_DIMENSION_OPTIMUM; "
                "HIDDEN_MONOTONE_WEIGHTINGS_MAY_SELECT_DIFFERENT_PARETO_ACTIONS."
            ),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    # Every common-top action reaches the optimum coordinate for every dimension.
    # Therefore it weakly componentwise-dominates every declared action.
    dominance = {}
    for top in common_ids:
        dominated = []
        for other in sorted(vals):
            ok = True
            for d, direction in dirs.items():
                if direction == "MAX" and vals[top][d] < vals[other][d]:
                    ok = False
                if direction == "MIN" and vals[top][d] > vals[other][d]:
                    ok = False
            if ok:
                dominated.append(other)
        dominance[top] = dominated

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "COMMON_COMPONENTWISE_TOP_FOUND",
        "common_top_exists": True,
        "common_top_action_ids": common_ids,
        "per_dimension": per_dimension,
        "componentwise_dominance": dominance,
        "target_preference_erasure_candidate": True,
        "theorem": (
            "IF_THE_DECLARED_DIMENSION_SET_IS_SOUND_COMPLETE_FOR_ALL_LOAD_BEARING "
            "OUTCOME_DIMENSIONS_AND_TARGET_UTILITY_IS_MONOTONE_IN_EACH_DECLARED "
            "DIRECTION, ANY_COMMON_TOP_ACTION_IS_WEAKLY_NONINFERIOR_TO_EVERY "
            "DECLARED_ACTION UNDER_EVERY_SUCH_TARGET_UTILITY."
        ),
        "boundary": (
            "THIS_RUNTIME_PROVES_ONLY_THE_FINITE_COMPONENTWISE_FACT; DIMENSION "
            "COMPLETENESS, AUTHENTICATED_VALUES, ACTION_SPACE_COMPLETENESS, "
            "RESOURCE/SAFETY/AUTHORITY, OWNERSHIP, AND DEPLOYMENT REMAIN EXTERNAL "
            "PREMISES."
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
