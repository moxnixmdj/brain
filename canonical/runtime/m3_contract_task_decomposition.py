"""Exact bounded M3 task decomposition from explicit pre/postcondition contracts.

Dependencies need not be predeclared. Given explicit initial facts, required outputs,
and verified step contracts, this module finds a minimum-cost executable plan and
derives a dependency graph from the selected steps.

Unknown step semantics, implicit facts, or open-ended planning remain out of scope
and fail closed. This is a bounded decision primitive, not terminal capability credit.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import isfinite
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ContractStep:
    task_id: str
    requires: frozenset[str]
    produces: frozenset[str]
    cost: float = 1.0
    available: bool = True
    verified: bool = True


def _valid_fact_set(values: Iterable[str]) -> tuple[frozenset[str] | None, str | None]:
    try:
        vals = list(values)
    except Exception:
        return None, "FACT_SET_NOT_ITERABLE"
    if any(not isinstance(x, str) or not x.strip() for x in vals):
        return None, "FACT_IDENTITIES_INVALID"
    return frozenset(vals), None


def _validate_steps(steps: Sequence[ContractStep]) -> tuple[list[ContractStep], str | None]:
    if not isinstance(steps, Sequence):
        return [], "STEPS_NOT_SEQUENCE"
    if len(steps) > 20:
        return [], "TOO_MANY_STEPS_FOR_EXACT_BOUNDED_SEARCH"

    ids = [s.task_id for s in steps]
    if any(not isinstance(x, str) or not x.strip() for x in ids) or len(ids) != len(set(ids)):
        return [], "TASK_IDENTITIES_INVALID_OR_DUPLICATE"

    eligible: list[ContractStep] = []
    for s in steps:
        req, req_err = _valid_fact_set(s.requires)
        prod, prod_err = _valid_fact_set(s.produces)
        if req_err or prod_err or not prod:
            return [], f"STEP_CONTRACT_INVALID:{s.task_id}"
        if (
            not isinstance(s.cost, (int, float))
            or isinstance(s.cost, bool)
            or not isfinite(float(s.cost))
            or float(s.cost) < 0
        ):
            return [], f"STEP_COST_INVALID:{s.task_id}"
        if s.available and s.verified:
            eligible.append(
                ContractStep(
                    task_id=s.task_id,
                    requires=req,
                    produces=prod,
                    cost=float(s.cost),
                    available=True,
                    verified=True,
                )
            )
    return sorted(eligible, key=lambda s: s.task_id), None


def compile_task_plan(
    *,
    initial_facts: Iterable[str],
    required_outputs: Iterable[str],
    steps: Sequence[ContractStep],
) -> dict:
    initial, err = _valid_fact_set(initial_facts)
    if err:
        return {"status": "FAIL_CLOSED", "reason": err, "terminal_authority": False}
    required, err = _valid_fact_set(required_outputs)
    if err or not required:
        return {
            "status": "FAIL_CLOSED",
            "reason": err or "REQUIRED_OUTPUTS_EMPTY",
            "terminal_authority": False,
        }

    eligible, step_err = _validate_steps(steps)
    if step_err:
        return {"status": "FAIL_CLOSED", "reason": step_err, "terminal_authority": False}

    if required.issubset(initial):
        return {
            "status": "PASS",
            "task_ids": [],
            "dependencies": {},
            "total_cost": 0.0,
            "unresolved_outputs": [],
            "reason": "REQUIRED_OUTPUTS_ALREADY_SATISFIED",
            "terminal_authority": False,
            "semantic_authority": False,
        }

    # Exact Dijkstra search over monotonic fact states.
    # Priority is minimum cost, then minimum task count, then lexicographic task sequence.
    start = frozenset(initial)
    heap: list[tuple[float, int, tuple[str, ...], frozenset[str]]] = [(0.0, 0, (), start)]
    best: dict[frozenset[str], tuple[float, int, tuple[str, ...]]] = {start: (0.0, 0, ())}
    goal: tuple[float, int, tuple[str, ...], frozenset[str]] | None = None

    while heap:
        cost, count, seq, facts = heappop(heap)
        if best.get(facts) != (cost, count, seq):
            continue
        if required.issubset(facts):
            goal = (cost, count, seq, facts)
            break

        used = set(seq)
        for step in eligible:
            if step.task_id in used:
                continue
            if not step.requires.issubset(facts):
                continue
            new_facts = facts | step.produces
            if new_facts == facts:
                continue
            new_seq = seq + (step.task_id,)
            candidate = (cost + step.cost, count + 1, new_seq)
            prior = best.get(new_facts)
            if prior is None or candidate < prior:
                best[new_facts] = candidate
                heappush(heap, (candidate[0], candidate[1], candidate[2], new_facts))

    if goal is None:
        all_reachable = frozenset().union(*(s.produces for s in eligible)) | initial if eligible else initial
        return {
            "status": "ESCALATE",
            "reason": "NO_VERIFIED_EXECUTABLE_CONTRACT_PLAN",
            "unresolved_outputs": sorted(required - all_reachable),
            "terminal_authority": False,
            "semantic_authority": False,
        }

    total_cost, _, seq, _ = goal
    by_id = {s.task_id: s for s in eligible}

    # Derive direct dependency support from the selected plan. Initial facts have no task dependency.
    available_facts = set(initial)
    fact_producer: dict[str, str] = {}
    dependencies: dict[str, list[str]] = {}
    for tid in seq:
        step = by_id[tid]
        deps: set[str] = set()
        for fact in sorted(step.requires):
            if fact in initial:
                continue
            producer = fact_producer.get(fact)
            if producer is None:
                # This should be unreachable because the plan was executable.
                return {
                    "status": "FAIL_CLOSED",
                    "reason": f"INTERNAL_DEPENDENCY_DERIVATION_GAP:{tid}:{fact}",
                    "terminal_authority": False,
                }
            deps.add(producer)
        dependencies[tid] = sorted(deps)
        for fact in sorted(step.produces):
            if fact not in available_facts:
                fact_producer[fact] = tid
            available_facts.add(fact)

    return {
        "status": "PASS",
        "task_ids": list(seq),
        "dependencies": dependencies,
        "total_cost": total_cost,
        "unresolved_outputs": [],
        "reason": "MIN_COST_EXECUTABLE_PLAN__THEN_MIN_TASK_COUNT__THEN_LEXICOGRAPHIC_SEQUENCE",
        "scope": "EXPLICIT_PRECONDITION_POSTCONDITION_CONTRACTS__DEPENDENCIES_NEED_NOT_BE_PREDECLARED",
        "terminal_authority": False,
        "semantic_authority": False,
    }
