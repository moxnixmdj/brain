"""Exact finite evaluator identified-set dominance.

This module fills the gap between:
- a fully specified evaluator;
- a proved restricted hidden evaluator class; and
- an arbitrary hidden evaluator requiring exact law equality.

It is intentionally finite and fail-closed.  The caller must provide every
currently admissible evaluator world explicitly, with a complete bounded utility
vector over the common finite outcome support.  The runtime does not claim that
the supplied world set is semantically complete; that premise needs an
independent proof receipt before any higher-level promotion.

For a frozen target law P, Brain law Q, and admissible evaluator worlds E:

    delta_e = E_Q[u_e] - E_P[u_e]

The exact identified interval is [min_e delta_e, max_e delta_e].

- min >= 0  => universal noninferiority over the supplied world set.
- max < 0   => universal inferiority over the supplied world set.
- otherwise => the sign is not identified by the current information.

When evaluator worlds carry discrete fact labels, the module can also rank
which fact observation would most strongly collapse the remaining ambiguity.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence


class IdentifiedSetError(ValueError):
    pass


def _f(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise IdentifiedSetError(f"{label}_BOOL_FORBIDDEN")
    try:
        return Fraction(str(value))
    except Exception as exc:
        raise IdentifiedSetError(f"{label}_NOT_EXACT_RATIONAL:{value}") from exc


def _dist(value: Any, label: str) -> dict[str, Fraction]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise IdentifiedSetError(f"{label}_DISTRIBUTION_REQUIRED")
    out: dict[str, Fraction] = {}
    for row in value:
        if not isinstance(row, Mapping):
            raise IdentifiedSetError(f"{label}_ROW_INVALID")
        oid = row.get("id")
        if not isinstance(oid, str) or not oid.strip() or oid in out:
            raise IdentifiedSetError(f"{label}_OUTCOME_ID_INVALID_OR_DUPLICATE")
        p = _f(row.get("probability"), f"{label}_{oid}_PROBABILITY")
        if p < 0:
            raise IdentifiedSetError(f"{label}_{oid}_NEGATIVE_PROBABILITY")
        out[oid] = p
    if sum(out.values(), Fraction(0)) != Fraction(1):
        raise IdentifiedSetError(f"{label}_PROBABILITIES_MUST_SUM_TO_1")
    return out


def _utility(value: Any, support: set[str], world_id: str) -> dict[str, Fraction]:
    if not isinstance(value, Mapping):
        raise IdentifiedSetError(f"WORLD_{world_id}_UTILITY_REQUIRED")
    if set(value) != support:
        missing = sorted(support - set(value))
        extra = sorted(set(value) - support)
        raise IdentifiedSetError(
            f"WORLD_{world_id}_UTILITY_SUPPORT_MISMATCH:missing={missing}:extra={extra}"
        )
    out: dict[str, Fraction] = {}
    for oid in sorted(support):
        u = _f(value[oid], f"WORLD_{world_id}_{oid}_UTILITY")
        if u < 0 or u > 1:
            raise IdentifiedSetError(f"WORLD_{world_id}_{oid}_UTILITY_OUTSIDE_0_1")
        out[oid] = u
    return out


def _verdict(deltas: Sequence[Fraction]) -> str:
    lo = min(deltas)
    hi = max(deltas)
    if lo >= 0:
        return "PASS__UNIVERSAL_NONINFERIORITY_OVER_SUPPLIED_EVALUATOR_SET"
    if hi < 0:
        return "FAIL__UNIVERSAL_INFERIORITY_OVER_SUPPLIED_EVALUATOR_SET"
    return "UNKNOWN__SIGN_NOT_IDENTIFIED"


def _fact_rank(worlds: list[dict[str, Any]], candidate_fact_keys: Sequence[str]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for key in candidate_fact_keys:
        groups: dict[str, list[Fraction]] = {}
        missing = False
        for row in worlds:
            facts = row["facts"]
            if key not in facts:
                missing = True
                break
            value = str(facts[key])
            groups.setdefault(value, []).append(row["delta"])
        if missing or len(groups) < 2:
            continue

        branches = []
        all_decisive = True
        worst_span = Fraction(0)
        unresolved_branches = 0
        for value in sorted(groups):
            ds = groups[value]
            lo, hi = min(ds), max(ds)
            verdict = _verdict(ds)
            decisive = not verdict.startswith("UNKNOWN")
            all_decisive = all_decisive and decisive
            if not decisive:
                unresolved_branches += 1
            span = hi - lo
            worst_span = max(worst_span, span)
            branches.append(
                {
                    "value": value,
                    "lower_delta": str(lo),
                    "upper_delta": str(hi),
                    "verdict": verdict,
                    "world_count": len(ds),
                }
            )

        ranked.append(
            {
                "fact_key": key,
                "all_observation_branches_decisive": all_decisive,
                "unresolved_branch_count": unresolved_branches,
                "worst_branch_interval_width": str(worst_span),
                "branches": branches,
            }
        )

    ranked.sort(
        key=lambda row: (
            0 if row["all_observation_branches_decisive"] else 1,
            row["unresolved_branch_count"],
            Fraction(row["worst_branch_interval_width"]),
            row["fact_key"],
        )
    )
    return ranked


def solve(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise IdentifiedSetError("TASK_INVALID")

    target = _dist(task.get("target_distribution"), "TARGET")
    brain = _dist(task.get("brain_distribution"), "BRAIN")
    support = set(target) | set(brain)

    # Normalize zero-mass support so both laws share one explicit outcome set.
    target = {oid: target.get(oid, Fraction(0)) for oid in support}
    brain = {oid: brain.get(oid, Fraction(0)) for oid in support}

    raw_worlds = task.get("evaluator_worlds")
    if not isinstance(raw_worlds, Sequence) or isinstance(raw_worlds, (str, bytes)) or not raw_worlds:
        raise IdentifiedSetError("EVALUATOR_WORLDS_REQUIRED")

    worlds: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_worlds:
        if not isinstance(raw, Mapping):
            raise IdentifiedSetError("EVALUATOR_WORLD_INVALID")
        world_id = raw.get("world_id")
        if not isinstance(world_id, str) or not world_id.strip() or world_id in seen:
            raise IdentifiedSetError("EVALUATOR_WORLD_ID_INVALID_OR_DUPLICATE")
        seen.add(world_id)
        utility = _utility(raw.get("utility"), support, world_id)
        facts = raw.get("facts", {})
        if not isinstance(facts, Mapping):
            raise IdentifiedSetError(f"WORLD_{world_id}_FACTS_INVALID")
        delta = sum(
            (brain[oid] - target[oid]) * utility[oid]
            for oid in support
        )
        worlds.append(
            {
                "world_id": world_id,
                "utility": utility,
                "facts": {str(k): str(v) for k, v in facts.items()},
                "delta": delta,
            }
        )

    worlds.sort(key=lambda row: row["world_id"])
    deltas = [row["delta"] for row in worlds]
    lo, hi = min(deltas), max(deltas)
    verdict = _verdict(deltas)

    min_world = min(worlds, key=lambda row: (row["delta"], row["world_id"]))
    max_world = max(worlds, key=lambda row: (row["delta"], row["world_id"]))

    candidate_fact_keys = task.get("candidate_fact_keys", [])
    if not isinstance(candidate_fact_keys, Sequence) or isinstance(candidate_fact_keys, (str, bytes)):
        raise IdentifiedSetError("CANDIDATE_FACT_KEYS_INVALID")
    fact_rank = _fact_rank(worlds, [str(x) for x in candidate_fact_keys])

    return {
        "schema": "PROJECT_BRAIN_EVALUATOR_IDENTIFIED_SET_DOMINANCE_RESULT_V1",
        "status": verdict,
        "identified_interval": {
            "lower_delta": str(lo),
            "upper_delta": str(hi),
        },
        "world_count": len(worlds),
        "universal_noninferiority_over_supplied_world_set": lo >= 0,
        "universal_inferiority_over_supplied_world_set": hi < 0,
        "worst_case_world": {
            "world_id": min_world["world_id"],
            "delta": str(min_world["delta"]),
        },
        "best_case_world": {
            "world_id": max_world["world_id"],
            "delta": str(max_world["delta"]),
        },
        "minimum_information_candidates": fact_rank,
        "semantic_world_set_completeness_verified_by_this_runtime": False,
        "boundary": (
            "FINITE_EXPLICIT_EVALUATOR_WORLD_SET_ONLY__"
            "NO_CLAIM_SUPPLIED_WORLD_SET_EXHAUSTS_REAL_HIDDEN_EVALUATOR_SEMANTICS"
        ),
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
