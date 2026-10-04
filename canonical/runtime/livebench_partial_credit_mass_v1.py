#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PARTIAL_CREDIT_MASS_V1"
POPULATION_COUNT = 200
THRESHOLD_PERCENT = 65.7
THRESHOLD_MASS = POPULATION_COUNT * THRESHOLD_PERCENT / 100.0


@dataclass(frozen=True)
class CaseBound:
    instruction_count: int
    proved_followed_count: int
    proved_all_followed: bool = False

    def validate(self) -> None:
        if self.instruction_count < 1:
            raise ValueError("INSTRUCTION_COUNT_MUST_BE_POSITIVE")
        if not 0 <= self.proved_followed_count <= self.instruction_count:
            raise ValueError("PROVED_FOLLOWED_COUNT_OUT_OF_RANGE")
        if self.proved_all_followed and self.proved_followed_count != self.instruction_count:
            raise ValueError("ALL_FOLLOWED_REQUIRES_FULL_COUNT")

    def lower_bound(self) -> float:
        self.validate()
        if self.proved_all_followed:
            return 1.0
        return self.proved_followed_count / (2.0 * self.instruction_count)


def case_lower_bound(instruction_count: int, proved_followed_count: int, proved_all_followed: bool = False) -> float:
    return CaseBound(instruction_count, proved_followed_count, proved_all_followed).lower_bound()


def aggregate_certificate(cases: Iterable[CaseBound], population_count: int = POPULATION_COUNT, threshold_percent: float = THRESHOLD_PERCENT) -> dict[str, Any]:
    rows = list(cases)
    if population_count < 1:
        raise ValueError("POPULATION_COUNT_MUST_BE_POSITIVE")
    if len(rows) > population_count:
        raise ValueError("MORE_CASE_BOUNDS_THAN_POPULATION")
    threshold_mass = population_count * float(threshold_percent) / 100.0
    proved_mass = sum(row.lower_bound() for row in rows)
    unresolved = population_count - len(rows)
    max_possible_mass = proved_mass + unresolved
    forced_pass = proved_mass + 1e-12 >= threshold_mass
    forced_fail = max_possible_mass + 1e-12 < threshold_mass
    return {
        "schema": SCHEMA,
        "population_count": population_count,
        "threshold_percent": float(threshold_percent),
        "threshold_mass": threshold_mass,
        "proved_case_count": len(rows),
        "unresolved_case_count": unresolved,
        "proved_score_mass_lower_bound": proved_mass,
        "full_population_percent_lower_bound": 100.0 * proved_mass / population_count,
        "full_population_score_mass_upper_bound": max_possible_mass,
        "forced_pass": forced_pass,
        "forced_fail": forced_fail,
        "residual_mass_to_force_pass": max(0.0, threshold_mass - proved_mass),
        "hard_nonclaim": "UNRESOLVED_CASES_RECEIVE_ZERO_IN_THE_LOWER_BOUND; THIS_CERTIFICATE_DOES_NOT_INFER_THEIR_SCORE"
    }


def from_records(records: Iterable[Mapping[str, Any]], population_count: int = POPULATION_COUNT, threshold_percent: float = THRESHOLD_PERCENT) -> dict[str, Any]:
    cases = [
        CaseBound(
            instruction_count=int(r["instruction_count"]),
            proved_followed_count=int(r["proved_followed_count"]),
            proved_all_followed=bool(r.get("proved_all_followed", False)),
        )
        for r in records
    ]
    return aggregate_certificate(cases, population_count, threshold_percent)
