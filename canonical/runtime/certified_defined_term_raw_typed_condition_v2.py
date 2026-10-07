"""Defined-term typed condition evaluated from raw authoritative fact-source bytes.

This wrapper removes the caller-supplied typed-context digest from the controlled
denotation path. It compiles the typed context directly from raw JSON source bytes,
then invokes the explicit-definition condition evaluator with the internally
computed digest.

The remaining authority boundary is source selection: an upstream task/source
contract must establish that fact_source_id is authoritative for the task.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context
from canonical.runtime.certified_defined_term_typed_condition_v1 import (
    evaluate_defined_unless_condition,
)

SCHEMA = "BRAIN_CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION_V2"


def evaluate_defined_unless_condition_from_raw_facts(
    policy_source_text: str,
    *,
    policy_source_id: str,
    fact_source: str | bytes,
    fact_source_id: str,
) -> dict[str, Any]:
    compiled = compile_typed_context(fact_source, source_id=fact_source_id)
    if compiled.get("status") != "COMPILED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "FACT_SOURCE_TYPED_CONTEXT_COMPILE_FAILED",
            "fact_source_compilation": compiled,
            "terminal_authority": False,
        }

    evaluated = evaluate_defined_unless_condition(
        policy_source_text,
        source_id=policy_source_id,
        typed_context=compiled["typed_context"],
        expected_typed_context_sha256=compiled["typed_context_sha256"],
    )
    out = dict(evaluated)
    out["schema"] = SCHEMA
    out["fact_source_id"] = compiled["source_id"]
    out["fact_source_sha256"] = compiled["raw_source_sha256"]
    out["fact_source_byte_length"] = compiled["raw_source_byte_length"]
    out["typed_context_compilation"] = {
        "schema": compiled["schema"],
        "status": compiled["status"],
        "typed_context_sha256": compiled["typed_context_sha256"],
        "field_count": compiled["field_count"],
    }
    out["authority_boundary"] = (
        "POLICY_AND_FACT_BYTES_ARE_DETERMINISTICALLY_BOUND_AND_INTERPRETED;"
        "UPSTREAM_MUST_PROVE_THE_DECLARED_POLICY_SOURCE_AND_FACT_SOURCE_ARE_AUTHORIZED_FOR_THE_TASK"
    )
    out["terminal_authority"] = False
    return out
