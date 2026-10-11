from __future__ import annotations

from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_INTERNAL_PROOF_ROUTE_COMPLETENESS_V1"


class RouteError(ValueError):
    pass


def classify_hidden_threshold_proof(
    *,
    hidden_worlds: Iterable[str],
    threshold_truth_by_world: Mapping[str, bool],
    identified_world: str | None = None,
) -> dict[str, Any]:
    worlds = list(hidden_worlds)
    if not worlds or len(worlds) != len(set(worlds)):
        raise RouteError("HIDDEN_WORLDS_INVALID")
    if set(threshold_truth_by_world) != set(worlds):
        raise RouteError("THRESHOLD_WORLD_MAP_MISMATCH")

    if identified_world is not None:
        if identified_world not in threshold_truth_by_world:
            raise RouteError("IDENTIFIED_WORLD_UNKNOWN")
        return {
            "schema": SCHEMA,
            "status": "IDENTIFICATION_ROUTE",
            "proved": bool(threshold_truth_by_world[identified_world]),
            "route": "IDENTIFY_SCORE_BEARING_STATE_OR_EQUIVALENT_SUFFICIENT_STATISTIC",
            "countermodel_pair": None,
        }

    truths = [bool(threshold_truth_by_world[w]) for w in worlds]
    if all(truths):
        return {
            "schema": SCHEMA,
            "status": "ROBUST_ROUTE",
            "proved": True,
            "route": "PROVE_THRESHOLD_FOR_ALL_HIDDEN_WORLDS_CONSISTENT_WITH_BOUND_INFORMATION",
            "countermodel_pair": None,
        }
    if not any(truths):
        return {
            "schema": SCHEMA,
            "status": "ROBUST_FAILURE",
            "proved": False,
            "route": "ALL_CONSISTENT_HIDDEN_WORLDS_FAIL_THRESHOLD",
            "countermodel_pair": None,
        }

    pass_world = next(w for w in worlds if threshold_truth_by_world[w])
    fail_world = next(w for w in worlds if not threshold_truth_by_world[w])
    return {
        "schema": SCHEMA,
        "status": "UNIDENTIFIED_AND_NONROBUST",
        "proved": False,
        "route": None,
        "countermodel_pair": [fail_world, pass_world],
        "theorem": (
            "If hidden score-bearing state is not identified and threshold truth is "
            "not invariant over all hidden states consistent with the bound evidence, "
            "the threshold is not entailed by that evidence."
        ),
    }
