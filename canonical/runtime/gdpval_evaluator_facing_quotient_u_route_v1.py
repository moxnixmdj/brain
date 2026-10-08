from __future__ import annotations

import re
from fractions import Fraction
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_GDPVAL_EVALUATOR_FACING_QUOTIENT_U_ROUTE_V1"
_SHA = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
EXPECTED_TASKS = 220


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__FAIL_CLOSED",
        "reason": reason,
        "gdpval_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    out.update(extra)
    return out


def _law(raw: Any) -> dict[str, Fraction] | None:
    if not isinstance(raw, Mapping) or not raw:
        return None
    out: dict[str, Fraction] = {}
    try:
        for state, probability in raw.items():
            key = str(state)
            if not key or key in out:
                return None
            p = Fraction(probability)
            if p < 0:
                return None
            out[key] = p
    except (ValueError, TypeError, ZeroDivisionError):
        return None
    if sum(out.values(), Fraction(0)) != 1:
        return None
    return out


def verify(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_INVALID")

    quotient = manifest.get("evaluator_facing_quotient")
    if not isinstance(quotient, Mapping):
        return _fail("EVALUATOR_FACING_QUOTIENT_MISSING")

    required = {
        "all_load_bearing_owner_evaluator_inputs_factor_through_quotient": True,
        "model_identity_not_available_outside_bound_quotient": True,
        "owner_randomization_and_judge_randomness_in_state_boundary": True,
        "random_ab_assignment_symmetric": True,
        "task_reference_context_bound": True,
        "owner_parsing_and_presentation_transform_bound": True,
    }
    missing = [k for k, v in required.items() if quotient.get(k) is not v]
    if missing:
        return _fail(
            "EVALUATOR_FACING_QUOTIENT_NOT_PROVED_COMPLETE",
            missing_or_false=missing,
        )

    for field in (
        "quotient_completeness_evidence_sha",
        "anonymization_symmetry_evidence_sha",
        "presentation_transform_evidence_sha",
    ):
        if not _sha(quotient.get(field)):
            return _fail(
                "EVALUATOR_FACING_QUOTIENT_EVIDENCE_MISSING",
                field=field,
            )

    if manifest.get("task_count") != EXPECTED_TASKS:
        return _fail("TASK_COUNT_NOT_220", observed=manifest.get("task_count"))

    tasks = manifest.get("tasks")
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)):
        return _fail("TASKS_INVALID")
    if len(tasks) != EXPECTED_TASKS:
        return _fail("TASK_LIST_NOT_220", observed=len(tasks))

    seen: set[str] = set()
    unequal: list[dict[str, Any]] = []
    for idx, row in enumerate(tasks):
        if not isinstance(row, Mapping):
            return _fail("TASK_ENTRY_INVALID", task_index=idx)
        task_id = row.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip() or task_id in seen:
            return _fail("TASK_ID_INVALID_OR_DUPLICATE", task_index=idx, task_id=task_id)
        seen.add(task_id)

        brain = _law(row.get("brain_quotient_law_exact"))
        target = _law(row.get("opus55_quotient_law_exact"))
        if brain is None:
            return _fail("BRAIN_QUOTIENT_LAW_INVALID_OR_UNBOUND", task_id=task_id)
        if target is None:
            return _fail("OPUS55_QUOTIENT_LAW_INVALID_OR_UNBOUND", task_id=task_id)

        if brain != target:
            states = sorted(set(brain) | set(target))
            unequal.append(
                {
                    "task_id": task_id,
                    "differences": [
                        {
                            "state": state,
                            "brain": str(brain.get(state, Fraction(0))),
                            "opus55": str(target.get(state, Fraction(0))),
                        }
                        for state in states
                        if brain.get(state, Fraction(0)) != target.get(state, Fraction(0))
                    ],
                }
            )

    if unequal:
        return _fail(
            "EVALUATOR_FACING_QUOTIENT_LAWS_NOT_EQUAL",
            unequal_task_count=len(unequal),
            first_unequal=unequal[0],
            next_action=(
                "DO_NOT_REOPEN_HIDDEN_GRADER_ENUMERATION__EITHER_PROVE_A_STRONGER_"
                "E_OR_M_ROUTE_OR_BIND_ONLY_THE_TARGET_QUOTIENT_INFORMATION_NEEDED_"
                "TO_CLOSE_THE_REPORTED_DIFFERENCE"
            ),
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__ARBITRARY_HIDDEN_EVALUATOR_QUOTIENT_LAW_PARITY",
        "task_count": EXPECTED_TASKS,
        "theorem": (
            "IF_EVERY_LOAD_BEARING_OWNER_PAIRWISE_EVALUATOR_FACTORS_THROUGH_THE_"
            "BOUND_EVALUATOR_FACING_QUOTIENT_AND_BRAIN_AND_OPUS55_HAVE_EQUAL_"
            "CONDITIONAL_QUOTIENT_LAWS_FOR_EVERY_TASK__THEN_EVERY_DOWNSTREAM_"
            "OWNER_EVALUATOR_KERNEL_HAS_EQUAL_PUSHFORWARD_OUTCOME_LAWS_FOR_BRAIN_"
            "AND_OPUS55_UNDER_MATCHED_CONTEXT_AND_RANDOMIZATION"
        ),
        "full_private_trajectory_law_equality_required": False,
        "exact_hidden_grading_prompt_required_for_u_route": False,
        "exact_opus55_evaluator_facing_quotient_law_required": True,
        "gdpval_credit_delta": 0,
        "terminal_credit_delta": 0,
        "promotion_boundary": (
            "CONDITIONAL_U_ROUTE_CERTIFICATE_ONLY__GDPVAL_CREDIT_REQUIRES_"
            "INDEPENDENT_SEMANTIC_VERIFICATION_OF_QUOTIENT_COMPLETENESS_AND_"
            "AUTHENTIC_EXACT_OPUS55_QUOTIENT_LAWS_OR_A_STRONGER_ROUTE"
        ),
    }
