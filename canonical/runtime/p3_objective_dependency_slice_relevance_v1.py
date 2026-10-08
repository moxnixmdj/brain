"""Bounded objective dependency-slice relevance cell v1.

For already verified generic evidence extraction, bind an explicit objective to
the exact evidence units/literals that can determine the bounded relation.
Everything outside that dependency slice is irrelevant to the relation
evaluator for this exact extraction and objective.

This is deliberately narrower than semantic relevance. It supports only the
already-verified objective binder grammar: exact quoted support or explicit
binary numeric relations. Ambiguity, paraphrase, causal inference, unit
conversion, source authority, and general salience fail closed.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.bound_capabilities import objective_claim_operand_binding as binder

SCHEMA = "PROJECT_BRAIN_P3_OBJECTIVE_DEPENDENCY_SLICE_RELEVANCE_V1"
_FORBIDDEN_EVIDENCE_LABELS = {
    "role", "support", "relevance", "audience", "required", "include",
    "salience", "salience_weight", "objective_weight",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "decision_relevance_complete_for_bounded_objective": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    if set(payload) != {"objective", "extraction"}:
        return _fail("PAYLOAD_FIELDS_INVALID")

    objective = payload.get("objective")
    extraction = payload.get("extraction")
    if not isinstance(objective, str) or not objective.strip():
        return _fail("OBJECTIVE_REQUIRED")
    if not isinstance(extraction, Mapping):
        return _fail("EXTRACTION_REQUIRED")

    rows = extraction.get("evidence_units")
    if not isinstance(rows, list) or not rows:
        return _fail("EVIDENCE_UNITS_REQUIRED")
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return _fail("EVIDENCE_UNIT_INVALID", index=i)
        leaked = sorted(_FORBIDDEN_EVIDENCE_LABELS & set(row))
        if leaked:
            return _fail("UNVERIFIED_RELEVANCE_LABEL_FORBIDDEN", index=i, fields=leaked)

    try:
        bound = binder.bind(objective, dict(extraction), evaluate_relation=True)
    except Exception as exc:
        return _fail(
            "OBJECTIVE_BINDING_OR_RELATION_EVALUATION_FAILED",
            exception_type=type(exc).__name__,
            detail_text=str(exc)[:200],
        )

    status = bound.get("status")
    if status not in {"CLAIM_SPEC_AND_OPERANDS_BOUND", "CLAIM_SPEC_BOUND"}:
        return _fail(
            "OBJECTIVE_NOT_SOUNDLY_BOUND",
            binding_status=status,
            binding_reason=bound.get("reason"),
        )

    relation = bound.get("relation_result")
    if not isinstance(relation, Mapping):
        return _fail("RELATION_RESULT_REQUIRED")

    selected: list[str] = []
    mode = (bound.get("relation_spec") or {}).get("mode")
    if mode == "NUMERIC_RELATION":
        if relation.get("status") != "NUMERIC_RELATION_VERIFIED":
            return _fail("NUMERIC_RELATION_NOT_VERIFIED", relation_status=relation.get("status"))
        spec = bound.get("relation_spec") or {}
        for key in ("left", "right"):
            ref = spec.get(key)
            if not isinstance(ref, Mapping) or not isinstance(ref.get("evidence_unit_id"), str):
                return _fail("NUMERIC_OPERAND_REFERENCE_INVALID", operand=key)
            selected.append(ref["evidence_unit_id"])
        threshold = spec.get("threshold")
        if isinstance(threshold, Mapping):
            tid = threshold.get("evidence_unit_id")
            if not isinstance(tid, str):
                return _fail("THRESHOLD_REFERENCE_INVALID")
            selected.append(tid)
    elif mode == "VERBATIM_SUPPORT":
        if relation.get("status") != "EXACT_TEXT_SUPPORT_VERIFIED":
            return _fail("EXACT_TEXT_SUPPORT_NOT_VERIFIED")
        spec = bound.get("relation_spec") or {}
        eid = spec.get("evidence_unit_id")
        if not isinstance(eid, str):
            return _fail("VERBATIM_EVIDENCE_REFERENCE_INVALID")
        selected.append(eid)
    else:
        return _fail("BOUND_MODE_UNSUPPORTED", mode=mode)

    selected = list(dict.fromkeys(selected))
    all_ids = [str(row.get("evidence_unit_id") or "") for row in rows]
    if any(not x for x in all_ids) or not set(selected).issubset(set(all_ids)):
        return _fail("SELECTED_EVIDENCE_NOT_IN_EXTRACTION")

    irrelevant = [eid for eid in all_ids if eid not in set(selected)]

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__BOUNDED_OBJECTIVE_DEPENDENCY_SLICE_RELEVANCE",
        "route": "EXACT_OBJECTIVE_OPERAND_DEPENDENCY_SLICE",
        "objective": objective,
        "binding_mode": mode,
        "selected_evidence_unit_ids": selected,
        "irrelevant_to_bounded_relation_evaluator_evidence_unit_ids": irrelevant,
        "relation_result": dict(relation),
        "decision_relevance_complete_for_bounded_objective": True,
        "completeness_basis": (
            "THE VERIFIED BOUNDED RELATION EVALUATOR DEREFERENCES ONLY THE "
            "BOUND OPERAND/THRESHOLD EVIDENCE REFERENCES; OTHER EVIDENCE UNITS "
            "CANNOT CHANGE THE EVALUATED RELATION FOR THIS EXACT EXTRACTION"
        ),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "EXACT_QUOTED_SUPPORT_OR_EXPLICIT_NUMERIC_RELATION_OVER_VERIFIED "
            "GENERIC_EXTRACTION_ONLY; NO GENERAL SEMANTIC_RELEVANCE"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
