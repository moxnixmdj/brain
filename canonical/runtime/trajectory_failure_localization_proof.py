"""Verifier-side intervention/rescue oracle for trajectory failure localization.

This is a proof-surface primitive, not an implementation of failure localization.
The operative Brain route nominates a repair target from visible trajectory evidence.
The verifier owns the hidden causal fault and evaluates two counterfactuals:
repairing the nominated target, and repairing a downstream symptom only.

Terminal cases/seeds are intentionally outside this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HiddenTrajectoryCase:
    case_id: str
    step_count: int
    causal_step: int
    symptom_step: int
    terminal_failure_step: int


def make_synthetic_case(
    *,
    case_id: str,
    step_count: int,
    causal_step: int,
    symptom_step: int,
    terminal_failure_step: int,
) -> HiddenTrajectoryCase:
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id required")
    vals=(step_count,causal_step,symptom_step,terminal_failure_step)
    if any(not isinstance(v,int) or isinstance(v,bool) for v in vals):
        raise ValueError("integer fields required")
    if step_count < 3:
        raise ValueError("step_count too small")
    if not (0 <= causal_step < symptom_step < terminal_failure_step < step_count):
        raise ValueError("require causal < symptom < terminal failure < step_count")
    return HiddenTrajectoryCase(
        case_id=case_id,
        step_count=step_count,
        causal_step=causal_step,
        symptom_step=symptom_step,
        terminal_failure_step=terminal_failure_step,
    )


def public_case(case: HiddenTrajectoryCase) -> dict[str, Any]:
    """Return only information admissible to the operative route.

    Hidden causal identity is not exposed. A real terminal case may attach visible
    normalized trajectory events/invariant receipts separately.
    """
    return {
        "case_id": case.case_id,
        "step_count": case.step_count,
        "terminal_failure_step": case.terminal_failure_step,
        "required_output": "NOMINATED_CRITICAL_REPAIR_STEP",
    }


def _terminal_success(case: HiddenTrajectoryCase, repaired_step: int | None) -> bool:
    """Hidden counterfactual world used only by the verifier.

    Repairing the true causal step rescues the terminal outcome. Repairing any
    downstream symptom alone does not.
    """
    return repaired_step == case.causal_step


def verify_localization(case: HiddenTrajectoryCase, nominated_step: int) -> dict[str, Any]:
    if not isinstance(nominated_step, int) or isinstance(nominated_step, bool):
        return {"status":"FAIL_CLOSED","reason":"NOMINATION_NOT_INTEGER","pass":False}
    if nominated_step < 0 or nominated_step >= case.terminal_failure_step:
        return {"status":"FAIL_CLOSED","reason":"NOMINATION_OUTSIDE_PRIOR_TRAJECTORY","pass":False}

    nominated_rescue=_terminal_success(case,nominated_step)
    symptom_rescue=_terminal_success(case,case.symptom_step)
    exact_match=nominated_step == case.causal_step

    return {
        "status":"PASS" if (exact_match and nominated_rescue and not symptom_rescue) else "FAIL",
        "pass": bool(exact_match and nominated_rescue and not symptom_rescue),
        "exact_causal_step_match": exact_match,
        "nominated_repair_rescues_terminal_outcome": nominated_rescue,
        "symptom_only_repair_rescues_terminal_outcome": symptom_rescue,
        "oracle":"HIDDEN_INTERVENTION_RESCUE_COUNTERFACTUAL",
    }


def verify_batch(cases_and_nominations: list[tuple[HiddenTrajectoryCase,int]]) -> dict[str,Any]:
    if not isinstance(cases_and_nominations,list) or not cases_and_nominations:
        return {"status":"FAIL_CLOSED","reason":"EMPTY_OR_INVALID_BATCH","pass":False}
    seen=set()
    results=[]
    for case,nomination in cases_and_nominations:
        if not isinstance(case,HiddenTrajectoryCase) or case.case_id in seen:
            return {"status":"FAIL_CLOSED","reason":"INVALID_OR_DUPLICATE_CASE","pass":False}
        seen.add(case.case_id)
        results.append({"case_id":case.case_id, **verify_localization(case,nomination)})
    return {
        "status":"PASS" if all(r["pass"] for r in results) else "FAIL",
        "pass":all(r["pass"] for r in results),
        "results":results,
    }
