#!/usr/bin/env python3
"""Finance Agent v2 Brain model boundary V2: deterministic pre-submit repair loop.

V2 composes V1 selection with the deterministic pre-submit guard. It never
changes Vals tool execution or benchmark stopping semantics. A candidate
submit_final_result is allowed only when the public-contract guard passes.
Otherwise, only capability-neutral missing-evidence feedback is appended to
the model context and Brain selects again.

The cognition substrate remains proposal-only. Tool identity stays Brain-owned.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from canonical.runtime.finance_agent_v2_brain_model_boundary_v1 import (
    FinanceModelBoundaryError,
    Substrate,
    choose_next_tool_call as choose_v1,
)
from canonical.runtime.finance_agent_v2_presubmit_guard_v1 import evaluate as guard_submit

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_BRAIN_MODEL_BOUNDARY_V2"
MAX_REPAIR_ROUNDS = 4

_NEUTRAL_REPAIR = {
    "FINAL_RESULT_EMPTY": "a non-empty final answer",
    "FINAL_SOURCES_DICTIONARY_MISSING_OR_INVALID": "a valid final source dictionary",
    "CALCULATION_REQUEST_WITHOUT_SUCCESSFUL_CALCULATOR_RECEIPT": "verified arithmetic computation evidence",
    "HISTORICAL_PRICE_REQUEST_WITHOUT_PRICE_HISTORY_OR_RECORDED_FALLBACK": "historical price evidence under the benchmark source hierarchy",
    "FILING_REQUEST_WITHOUT_SEC_EVIDENCE_RECEIPT": "authoritative filing evidence",
}


class FinanceModelBoundaryV2Error(FinanceModelBoundaryError):
    pass


def _repair_message(errors: Sequence[str]) -> dict[str, Any]:
    missing = [
        _NEUTRAL_REPAIR.get(str(error), "unresolved required evidence")
        for error in errors
    ]
    # Deduplicate while preserving deterministic order.
    missing = list(dict.fromkeys(missing))
    return {
        "role": "system",
        "content": (
            "BRAIN_PRESUBMIT_REPAIR_REQUIRED: do not finish yet unless every "
            "listed item is resolved. Missing: " + "; ".join(missing)
        ),
        "brain_internal": True,
        "route_identity_disclosed": False,
    }


async def choose_next_tool_call(
    *,
    question: str,
    history: Sequence[Mapping[str, Any]],
    tool_definitions: Sequence[Mapping[str, Any]],
    tool_receipts: Sequence[Mapping[str, Any]],
    substrate: Substrate,
    max_repair_rounds: int = MAX_REPAIR_ROUNDS,
) -> dict[str, Any]:
    question = str(question or "").strip()
    if not question:
        raise FinanceModelBoundaryV2Error("QUESTION_REQUIRED")
    if (
        not isinstance(max_repair_rounds, int)
        or isinstance(max_repair_rounds, bool)
        or max_repair_rounds < 0
        or max_repair_rounds > 8
    ):
        raise FinanceModelBoundaryV2Error("MAX_REPAIR_ROUNDS_INVALID")

    working_history = [dict(x) for x in history]
    audits: list[dict[str, Any]] = []

    for repair_round in range(max_repair_rounds + 1):
        selected = await choose_v1(
            history=working_history,
            tool_definitions=tool_definitions,
            substrate=substrate,
        )
        if selected.get("tool_name") != "submit_final_result":
            return {
                **selected,
                "schema": SCHEMA,
                "presubmit_guard_applied": bool(audits),
                "repair_rounds": repair_round,
                "presubmit_audits": audits,
            }

        args = selected.get("arguments")
        if not isinstance(args, Mapping):
            raise FinanceModelBoundaryV2Error("SUBMIT_ARGUMENTS_NOT_OBJECT")
        final_result = args.get("final_result")
        if not isinstance(final_result, str):
            raise FinanceModelBoundaryV2Error("SUBMIT_FINAL_RESULT_ARGUMENT_MISSING")

        audit = guard_submit(
            question=question,
            final_result=final_result,
            tool_receipts=tool_receipts,
        )
        audits.append(audit)
        if audit.get("pass") is True:
            return {
                **selected,
                "schema": SCHEMA,
                "presubmit_guard_applied": True,
                "repair_rounds": repair_round,
                "presubmit_audits": audits,
            }

        if repair_round >= max_repair_rounds:
            raise FinanceModelBoundaryV2Error(
                "PRESUBMIT_REPAIR_BUDGET_EXHAUSTED:"
                + json.dumps(audit.get("errors") or [], sort_keys=True)
            )

        working_history.append(_repair_message(audit.get("errors") or []))

    raise FinanceModelBoundaryV2Error("UNREACHABLE_REPAIR_LOOP_STATE")
