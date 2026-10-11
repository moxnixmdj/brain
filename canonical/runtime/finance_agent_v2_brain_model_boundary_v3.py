#!/usr/bin/env python3
"""Finance Agent v2 Brain model boundary V3: deterministic finance work contract.

V3 preserves the V2 model-boundary and pre-submit repair semantics. Before V2
selects an official Vals tool, V3 compiles only structure that is explicit in
the public/raw question into a donor-free work contract:

- named tickers and dates;
- explicitly requested quantitative operation families;
- explicit source hints;
- formula-implied dependency classes;
- semantic/custom-source obligations that remain unresolved.

The contract is appended as Brain-internal context. It is not a benchmark tool,
does not alter the official Vals tool surface, does not expose private rubric
content, and does not grant score/terminal authority.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from canonical.runtime.finance_agent_v2_brain_model_boundary_v1 import Substrate
from canonical.runtime.finance_agent_v2_brain_model_boundary_v2 import (
    FinanceModelBoundaryV2Error,
    choose_next_tool_call as choose_v2,
)
from canonical.runtime.finance_quantitative_dependency_v1 import compile_dependencies
from canonical.runtime.finance_quantitative_question_contract_v1 import compile_question

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_BRAIN_MODEL_BOUNDARY_V3"


class FinanceModelBoundaryV3Error(FinanceModelBoundaryV2Error):
    pass


def build_work_contract(question: str) -> dict[str, Any]:
    """Compile explicit question structure into a compact execution contract."""
    question = str(question or "").strip()
    if not question:
        raise FinanceModelBoundaryV3Error("QUESTION_REQUIRED")

    q = compile_question(question)
    deps = compile_dependencies(q)

    dependency_rows = [
        {
            "operation": str(row.get("operation") or ""),
            "dependency": str(row.get("dependency") or ""),
            "kind": str(row.get("kind") or ""),
        }
        for row in deps.get("dependencies", [])
        if isinstance(row, Mapping)
    ]

    metric_ids = sorted(
        {
            str(row.get("metric_id"))
            for row in q.get("metric_requests", [])
            if isinstance(row, Mapping) and row.get("metric_id")
        }
    )

    return {
        "schema": SCHEMA + "__WORK_CONTRACT",
        "status": "COMPILED_EXPLICIT_FINANCE_WORK_CONTRACT",
        "question_sha256": q.get("question_sha256"),
        "tickers": list(q.get("tickers") or []),
        "dates": list(q.get("dates") or []),
        "operations": list(q.get("operations") or []),
        "metric_ids": metric_ids,
        "source_hints": list(q.get("source_hints") or []),
        "dependencies": dependency_rows,
        "semantic_source_dependencies": list(
            deps.get("semantic_source_dependencies") or []
        ),
        "semantic_tail_required": bool(q.get("semantic_tail_required")),
        "mechanically_closed_candidate": bool(
            deps.get("mechanically_closed_candidate")
        ),
        "rules": [
            "THIS_CONTRACT_CONTAINS_NO_SOURCE_FACT_VALUES",
            "BIND_REQUIRED_FACTS_WITH_OFFICIAL_VALS_TOOLS_BEFORE_CALCULATION",
            "USE_CALCULATOR_FOR_REQUESTED_ARITHMETIC_UNLESS_ALREADY_RECEIPTED",
            "RESOLVE_EVERY_SEMANTIC_SOURCE_DEPENDENCY_FROM_EVIDENCE",
            "ANSWER_EVERY_EXPLICIT_COMPARISON_RANKING_OR_METHOD_CHOICE",
            "DO_NOT_INFER_HIDDEN_RUBRIC_OR_PRIVATE_CASE_CONTENT",
        ],
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "source_fact_binding_proved": False,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }


def _work_contract_message(question: str) -> dict[str, Any]:
    contract = build_work_contract(question)
    return {
        "role": "system",
        "content": (
            "BRAIN_FINANCE_WORK_CONTRACT_V1:"
            + json.dumps(
                contract,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            )
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
    max_repair_rounds: int = 4,
) -> dict[str, Any]:
    """Delegate to V2 after adding one deterministic finance work contract."""
    if not isinstance(history, Sequence) or isinstance(history, (str, bytes)):
        raise FinanceModelBoundaryV3Error("HISTORY_NOT_SEQUENCE")
    augmented_history = [dict(item) for item in history]
    augmented_history.append(_work_contract_message(question))

    selected = await choose_v2(
        question=question,
        history=augmented_history,
        tool_definitions=tool_definitions,
        tool_receipts=tool_receipts,
        substrate=substrate,
        max_repair_rounds=max_repair_rounds,
    )
    return {
        **selected,
        "schema": SCHEMA,
        "finance_work_contract_applied": True,
        "official_vals_tool_surface_unchanged": True,
        "benchmark_score_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


__all__ = [
    "FinanceModelBoundaryV3Error",
    "build_work_contract",
    "choose_next_tool_call",
]
