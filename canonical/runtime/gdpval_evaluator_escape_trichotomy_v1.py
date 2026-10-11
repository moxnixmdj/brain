from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_GDPVAL_EVALUATOR_ESCAPE_TRICHOTOMY_V1"
EXPECTED_TASK_COUNT = 220


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _receipts(value: Any, count: int | None = None) -> bool:
    ok = (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and all(_nonempty(x) for x in value)
    )
    if not ok:
        return False
    return len(value) == count if count is not None else len(value) > 0


def route(payload: Mapping[str, Any]) -> dict[str, Any]:
    base = {
        "schema": SCHEMA,
        "pass": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if not isinstance(payload, Mapping):
        return {**base, "status": "INVALID", "reason": "PAYLOAD_INVALID"}

    owner = payload.get("owner_contract")
    if (
        not isinstance(owner, Mapping)
        or owner.get("public_contract_bound") is not True
        or owner.get("task_count") != EXPECTED_TASK_COUNT
    ):
        return {**base, "status": "BLOCKED", "reason": "OWNER_PUBLIC_CONTRACT_NOT_BOUND"}

    explicit = payload.get("explicit_relation")
    if isinstance(explicit, Mapping) and explicit.get("status") == "PROVED_EXTENSIONALLY_EQUIVALENT":
        if not _receipts(explicit.get("proof_receipts")):
            return {**base, "status": "BLOCKED", "reason": "E_PROOF_RECEIPTS_MISSING"}
        if not _receipts(explicit.get("task_outcome_receipts"), EXPECTED_TASK_COUNT):
            return {**base, "status": "BLOCKED", "reason": "E_TASK_OUTCOME_RECEIPTS_NOT_220"}
        if explicit.get("any_opus_preferred_task") is True:
            return {**base, "status": "FAIL", "reason": "E_OPUS_PREFERRED_COUNTEREXAMPLE"}
        if explicit.get("all_tasks_brain_win_or_tie") is not True:
            return {**base, "status": "BLOCKED", "reason": "E_SCOPE_COMPLETE_NONINFERIORITY_NOT_PROVED"}
        return {
            **base,
            "pass": True,
            "status": "CONDITIONAL_ESCAPE_CERTIFIED",
            "selected_route": "E_EXPLICIT_OWNER_RELATION",
            "hidden_owner_prompt_needed": False,
            "semantic_premise_verified_by_runtime": False,
        }

    monotone = payload.get("monotone_hidden_class")
    if isinstance(monotone, Mapping) and monotone.get("status") == "PROVED_OWNER_RELATION_IN_MONOTONE_CLASS":
        if not _receipts(monotone.get("semantic_proof_receipts")):
            return {**base, "status": "BLOCKED", "reason": "M_MONOTONICITY_PROOF_RECEIPTS_MISSING"}
        if not _receipts(monotone.get("task_dominance_receipts"), EXPECTED_TASK_COUNT):
            return {**base, "status": "BLOCKED", "reason": "M_TASK_DOMINANCE_RECEIPTS_NOT_220"}
        if monotone.get("owner_compatible_counterexample_exists") is True:
            return {**base, "status": "FAIL", "reason": "M_OWNER_COMPATIBLE_COUNTEREXAMPLE"}
        if monotone.get("all_tasks_universal_monotone_noninferiority") is not True:
            return {
                **base,
                "status": "BLOCKED",
                "reason": "M_UNIVERSAL_MONOTONE_NONINFERIORITY_NOT_PROVED",
            }
        return {
            **base,
            "pass": True,
            "status": "CONDITIONAL_ESCAPE_CERTIFIED",
            "selected_route": "M_PROVED_MONOTONE_HIDDEN_CLASS",
            "hidden_owner_prompt_needed": False,
            "semantic_premise_verified_by_runtime": False,
        }

    equality = payload.get("arbitrary_hidden_equality")
    if (
        isinstance(equality, Mapping)
        and equality.get("status") == "PROVED_EXACT_OWNER_VISIBLE_INPUT_LAW_EQUALITY"
    ):
        if not _receipts(equality.get("equality_proof_receipts")):
            return {**base, "status": "BLOCKED", "reason": "U_EQUALITY_PROOF_RECEIPTS_MISSING"}
        if not _receipts(equality.get("task_equality_receipts"), EXPECTED_TASK_COUNT):
            return {**base, "status": "BLOCKED", "reason": "U_TASK_EQUALITY_RECEIPTS_NOT_220"}
        required = (
            "same_task_and_references",
            "same_owner_parser_transform",
            "same_anonymization_law",
            "same_judge_sampling_law",
            "brain_opus_owner_visible_submission_law_equal",
        )
        missing = [key for key in required if equality.get(key) is not True]
        if missing:
            return {
                **base,
                "status": "BLOCKED",
                "reason": "U_FULL_INPUT_LAW_EQUALITY_INCOMPLETE",
                "missing": missing,
            }
        return {
            **base,
            "pass": True,
            "status": "CONDITIONAL_ESCAPE_CERTIFIED",
            "selected_route": "U_ARBITRARY_HIDDEN_EXACT_INPUT_LAW_EQUALITY",
            "hidden_owner_prompt_needed": False,
            "semantic_premise_verified_by_runtime": False,
        }

    return {
        **base,
        "status": "UNRESOLVED__NO_SOUND_EVALUATOR_ESCAPE_INSTANTIATED",
        "selected_route": None,
        "residuals": {
            "E": "EXACT_OWNER_RELATION_OR_EXTENSIONALLY_EQUIVALENT_ACCEPTANCE_PROGRAM_NOT_PROVED",
            "M": "OWNER_RELATION_MEMBERSHIP_IN_A_SOUND_MONOTONE_TASK_RESPONSE_CLASS_NOT_PROVED",
            "U": "EXACT_OWNER_VISIBLE_BRAIN_OPUS_INPUT_LAW_EQUALITY_NOT_PROVED",
        },
        "scheduler_rule": (
            "DO_NOT_INFER_M_FROM_BETTER_RESPONDS_WORDING;"
            "DO_NOT_INFER_U_FROM_AGGREGATE_ELO;"
            "DO_NOT_TREAT_RUBRIC_COMPLETENESS_AS_E"
        ),
    }
