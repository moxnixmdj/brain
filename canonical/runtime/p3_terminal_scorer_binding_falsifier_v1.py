"""Deterministic falsifier for the frozen Terminal-V3 P3 synthesis scorer.

This does not test model quality.  It checks whether the exact scorer bound by
TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1 enforces two predeclared P3
requirements: provenance preservation and audience sensitivity.

A successful falsification means the historical scorer can return PASS after a
load-bearing mutation that the frozen P3 binding says must be detected.
"""
from __future__ import annotations

import copy
from typing import Any

from canonical.runtime import contract_native_brain_candidate as candidate
from canonical.runtime import contract_native_proof_suites as suite

BEHAVIOR_ID = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"


def _drop_provenance(case: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(case)
    for row in mutated["task"]["evidence"]:
        row.pop("provenance", None)
    return mutated


def _swap_audience(case: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(case)
    task = mutated["task"]
    current = task.get("audience")
    choices = ("executive", "engineer", "auditor", "operator")
    task["audience"] = next(x for x in choices if x != current)
    for row in task["evidence"]:
        if "audience" in row:
            row["audience"] = task["audience"]
    return mutated


def _evaluate(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    public = suite.public_task(case)
    output = candidate.solve(public)
    verdict = suite.score_case(case, output)
    return output, verdict


def falsify(seed_count: int = 64) -> dict[str, Any]:
    rows = []
    provenance_undetected = 0
    audience_undetected = 0
    original_failures = 0

    for seed in range(seed_count):
        for difficulty in range(1, 6):
            case = suite.generate_case(BEHAVIOR_ID, seed, difficulty)
            original_output, original_verdict = _evaluate(case)
            if original_verdict.get("pass") is not True:
                original_failures += 1
                rows.append({
                    "seed": seed,
                    "difficulty": difficulty,
                    "kind": "ORIGINAL_FAIL",
                    "verdict": original_verdict,
                })
                continue

            pcase = _drop_provenance(case)
            poutput, pverdict = _evaluate(pcase)
            if pverdict.get("pass") is True:
                provenance_undetected += 1

            acase = _swap_audience(case)
            aoutput, averdict = _evaluate(acase)
            if averdict.get("pass") is True:
                audience_undetected += 1

            if len(rows) < 12 and (pverdict.get("pass") is True or averdict.get("pass") is True):
                rows.append({
                    "seed": seed,
                    "difficulty": difficulty,
                    "original_output": original_output,
                    "provenance_drop": {
                        "candidate_output_unchanged": poutput == original_output,
                        "verdict": pverdict,
                    },
                    "audience_swap": {
                        "candidate_output_unchanged": aoutput == original_output,
                        "verdict": averdict,
                    },
                })

    total = seed_count * 5
    falsified = (
        original_failures == 0
        and provenance_undetected > 0
        and audience_undetected > 0
    )
    return {
        "schema": "PROJECT_BRAIN_P3_TERMINAL_SCORER_BINDING_FALSIFIER_V1",
        "behavior_id": BEHAVIOR_ID,
        "case_count": total,
        "original_failures": original_failures,
        "provenance_drop_undetected_passes": provenance_undetected,
        "audience_swap_undetected_passes": audience_undetected,
        "falsified": falsified,
        "meaning": (
            "The bound historical scorer is insufficient for the frozen P3 "
            "terminal binding if falsified=true. This does not prove the "
            "underlying capability absent or inferior."
        ),
        "sample_rows": rows,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(falsify(), indent=2, sort_keys=True))
