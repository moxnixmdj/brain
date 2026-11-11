#!/usr/bin/env python3
"""Exact minimum-work score-mass cut for LiveBench instruction following.

This solver reuses the already-owned exact scorer algebra in
livebench_if_score_bound_v1. It never reads benchmark rows itself.

For each represented case, the caller supplies:
- total instruction count;
- already-guaranteed followed instruction count;
- exact non-negative work costs for additional *independent case-local*
  instruction proofs that are genuinely available.

Unrepresented population rows receive zero lower-bound score. Unlisted
unresolved instructions are treated as unprovable. The optimizer therefore
cannot manufacture score mass from missing information.

The key leverage is the scorer's completion discontinuity:
  f_n(g) = g/(2n), g<n
  f_n(n) = 1
so the final instruction that completes a case has marginal score
  1/2 + 1/(2n),
not merely 1/(2n).

Under the explicit independent case-local cost model, choosing the cheapest k
additional proofs within a case is optimal for every k. The remaining global
problem is an exact multi-choice knapsack over the Pareto frontier of cases.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable

from canonical.runtime.livebench_if_score_bound_v1 import (
    CaseGuarantee,
    conservative_case_lower_bound,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_EXACT_COMPLETION_CUT_V1"


class ExactCutError(ValueError):
    pass


def exact_number(value: int | str | Fraction) -> Fraction:
    """Parse exact arithmetic only. Binary floats are forbidden fail-closed."""
    if isinstance(value, bool):
        raise ExactCutError("BOOLEAN_NOT_NUMERIC")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ExactCutError("INVALID_EXACT_NUMBER") from exc
    if isinstance(value, float):
        raise ExactCutError("FLOAT_INPUT_FORBIDDEN")
    raise ExactCutError("UNSUPPORTED_NUMERIC_TYPE")


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def threshold_score_mass(population_count: int, threshold_percent: int | str | Fraction) -> Fraction:
    if population_count < 1:
        raise ExactCutError("POPULATION_COUNT_MUST_BE_POSITIVE")
    threshold = exact_number(threshold_percent)
    if threshold < 0 or threshold > 100:
        raise ExactCutError("THRESHOLD_PERCENT_OUT_OF_RANGE")
    return Fraction(population_count, 1) * threshold / 100


def case_score_mass(instruction_count: int, guaranteed_following: int) -> Fraction:
    return conservative_case_lower_bound(
        CaseGuarantee(
            instruction_count=instruction_count,
            guaranteed_following=guaranteed_following,
        )
    )


def completion_marginal_mass(instruction_count: int) -> Fraction:
    """Marginal lower-bound score from g=n-1 to g=n."""
    if instruction_count < 1:
        raise ExactCutError("INSTRUCTION_COUNT_MUST_BE_POSITIVE")
    n = instruction_count
    return case_score_mass(n, n) - case_score_mass(n, n - 1)


@dataclass(frozen=True)
class CaseWork:
    instruction_count: int
    guaranteed_following: int = 0
    additional_checker_costs: tuple[Fraction, ...] = ()

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "CaseWork":
        raw_costs = record.get("additional_checker_costs", ())
        return cls(
            instruction_count=int(record["instruction_count"]),
            guaranteed_following=int(record.get("guaranteed_following", 0)),
            additional_checker_costs=tuple(exact_number(x) for x in raw_costs),
        )

    def validate(self) -> None:
        if self.instruction_count < 1:
            raise ExactCutError("INSTRUCTION_COUNT_MUST_BE_POSITIVE")
        if not 0 <= self.guaranteed_following <= self.instruction_count:
            raise ExactCutError("GUARANTEED_FOLLOWING_OUT_OF_RANGE")
        unresolved = self.instruction_count - self.guaranteed_following
        if len(self.additional_checker_costs) > unresolved:
            raise ExactCutError("TOO_MANY_ADDITIONAL_CHECKER_COSTS")
        if any(cost < 0 for cost in self.additional_checker_costs):
            raise ExactCutError("NEGATIVE_PROOF_COST")


@dataclass(frozen=True)
class _State:
    score_mass: Fraction
    work_cost: Fraction
    choices: tuple[int, ...]


def _case_options(case: CaseWork) -> tuple[tuple[Fraction, Fraction, int], ...]:
    """Return exact Pareto options for 0..m additional independent proofs."""
    case.validate()
    costs = sorted(case.additional_checker_costs)
    options: list[tuple[Fraction, Fraction, int]] = []
    cumulative = Fraction(0, 1)
    for added in range(len(costs) + 1):
        if added:
            cumulative += costs[added - 1]
        score = case_score_mass(
            case.instruction_count,
            case.guaranteed_following + added,
        )
        options.append((score, cumulative, added))
    return tuple(options)


def _pareto_prune(states: Iterable[_State]) -> list[_State]:
    """Delete any state weakly worse in score and cost than another state."""
    best_by_mass: dict[Fraction, _State] = {}
    for state in states:
        current = best_by_mass.get(state.score_mass)
        if current is None or state.work_cost < current.work_cost:
            best_by_mass[state.score_mass] = state
        elif state.work_cost == current.work_cost and state.choices < current.choices:
            best_by_mass[state.score_mass] = state

    ordered = sorted(
        best_by_mass.values(),
        key=lambda s: (s.score_mass, -s.work_cost),
        reverse=True,
    )
    kept_desc: list[_State] = []
    best_cost: Fraction | None = None
    for state in ordered:
        if best_cost is None or state.work_cost < best_cost:
            kept_desc.append(state)
            best_cost = state.work_cost
    return sorted(kept_desc, key=lambda s: (s.score_mass, s.work_cost, s.choices))


def exact_minimum_work_cut(
    cases: Iterable[CaseWork],
    *,
    population_count: int,
    threshold_percent: int | str | Fraction,
) -> dict[str, Any]:
    """Solve the exact minimum-work lower-bound cut under the declared cost model."""
    rows = tuple(cases)
    if population_count < 1:
        raise ExactCutError("POPULATION_COUNT_MUST_BE_POSITIVE")
    if len(rows) > population_count:
        raise ExactCutError("MORE_CASES_THAN_POPULATION")
    target = threshold_score_mass(population_count, threshold_percent)

    states = [_State(Fraction(0, 1), Fraction(0, 1), ())]
    for case in rows:
        options = _case_options(case)
        expanded: list[_State] = []
        for state in states:
            for score, cost, added in options:
                expanded.append(
                    _State(
                        score_mass=state.score_mass + score,
                        work_cost=state.work_cost + cost,
                        choices=state.choices + (added,),
                    )
                )
        states = _pareto_prune(expanded)

    if not states:
        raise ExactCutError("NO_STATES")

    baseline = next(
        state for state in states
        if state.choices == tuple(0 for _ in rows)
    )
    max_reachable = max(states, key=lambda s: s.score_mass)
    feasible = [state for state in states if state.score_mass >= target]

    base_result = {
        "schema": SCHEMA,
        "population_count": population_count,
        "represented_case_count": len(rows),
        "unrepresented_case_count": population_count - len(rows),
        "threshold_percent": fraction_text(exact_number(threshold_percent)),
        "threshold_score_mass": fraction_text(target),
        "baseline_score_mass": fraction_text(baseline.score_mass),
        "maximum_reachable_score_mass": fraction_text(max_reachable.score_mass),
        "pareto_state_count": len(states),
        "score_arithmetic": "EXACT_RATIONAL__NO_FLOAT_EPSILON",
        "completion_marginal_formula": "1/2 + 1/(2n)",
        "unrepresented_rows_lower_bound": "ZERO",
        "unlisted_unresolved_checkers": "UNPROVABLE",
        "cost_model": "INDEPENDENT_CASE_LOCAL_ADDITIONAL_CHECKER_PROOFS",
        "terminal_data_read_by_solver": False,
        "acceptance_credit": False,
    }

    if not feasible:
        return {
            **base_result,
            "feasible": False,
            "minimum_work_cost": None,
            "selected_additional_checkers_by_case": None,
            "proved_score_mass": fraction_text(max_reachable.score_mass),
            "residual_score_mass": fraction_text(max(Fraction(0), target - max_reachable.score_mass)),
            "status": "IMPOSSIBLE_UNDER_DECLARED_PROOF_ACTIONS",
        }

    best = min(
        feasible,
        key=lambda s: (s.work_cost, s.score_mass, s.choices),
    )
    return {
        **base_result,
        "feasible": True,
        "minimum_work_cost": fraction_text(best.work_cost),
        "selected_additional_checkers_by_case": list(best.choices),
        "proved_score_mass": fraction_text(best.score_mass),
        "residual_score_mass": "0",
        "status": "EXACT_MINIMUM_WORK_CUT_FOUND",
    }


def from_records(
    records: Iterable[dict[str, Any]],
    *,
    population_count: int,
    threshold_percent: int | str | Fraction,
) -> dict[str, Any]:
    return exact_minimum_work_cut(
        (CaseWork.from_record(record) for record in records),
        population_count=population_count,
        threshold_percent=threshold_percent,
    )
