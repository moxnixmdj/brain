"""Fail-closed scorer for the frozen Unknown-Domain direct-oracle family."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_SCORE_V1"


class DirectScoreError(ValueError):
    pass


def score_case(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping) or not isinstance(result, Mapping):
        raise DirectScoreError("CASE_OR_RESULT_INVALID")
    hidden = case.get("hidden_evaluator")
    if not isinstance(hidden, Mapping):
        raise DirectScoreError("HIDDEN_EVALUATOR_MISSING")
    mode = hidden["mode"]
    verdict = result.get("verdict")
    reasons = []

    if result.get("persistent_learned_bytes") != 0:
        reasons.append("LEARNED_BYTES_NONZERO")
    if result.get("external_frontier_model_calls") != 0:
        reasons.append("EXTERNAL_FRONTIER_MODEL_USED")
    if result.get("external_learned_capability_calls") != 0:
        reasons.append("EXTERNAL_LEARNED_CAPABILITY_USED")

    if mode == "IDENTIFIABLE_TRANSFER":
        if verdict != "ANSWER":
            reasons.append("IDENTIFIABLE_CASE_NOT_ANSWERED")
        if result.get("answer") != hidden["gold_query_output"]:
            reasons.append("ANSWER_INCORRECT")
        used = set(result.get("surviving_source_ids") or [])
        if used != {hidden["relevant_source_id"]}:
            reasons.append("RELEVANT_SOURCE_NOT_EXCLUSIVE")
        receipts = set(result.get("source_receipt_ids") or [])
        if "source-receipt-" + hidden["relevant_source_id"] not in receipts:
            reasons.append("SOURCE_PROVENANCE_NOT_PRESERVED")
        if hidden.get("target_only_baseline_ambiguous") is not True:
            reasons.append("TARGET_ONLY_BASELINE_NOT_AMBIGUOUS")
    elif mode == "NONIDENTIFIABLE_ABSTAIN":
        if verdict != "ABSTAIN":
            reasons.append("NONIDENTIFIABLE_CASE_DID_NOT_ABSTAIN")
        if result.get("answer") is not None:
            reasons.append("ABSTENTION_CARRIES_FORCED_ANSWER")
    elif mode == "UNDERSPECIFIED_REQUEST_DISCRIMINATOR":
        if verdict != "REQUEST_DISCRIMINATOR":
            reasons.append("UNDERSPECIFIED_CASE_DID_NOT_REQUEST_DISCRIMINATOR")
        if result.get("answer") is not None:
            reasons.append("PREMATURE_ANSWER_BEFORE_DISCRIMINATION")
        if result.get("probe_id") not in set(hidden.get("valid_discriminator_probe_ids") or []):
            reasons.append("REQUESTED_PROBE_NOT_VALID_DISCRIMINATOR")
    else:
        reasons.append("MODE_UNKNOWN")

    return {
        "case_id": case.get("case_id"),
        "mode": mode,
        "pass": not reasons,
        "reasons": sorted(reasons),
    }


def score_cases(cases: Sequence[Mapping[str, Any]], results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(cases) != len(results):
        raise DirectScoreError("CASE_RESULT_COUNT_MISMATCH")
    rows = [score_case(case, result) for case, result in zip(cases, results)]
    by_mode = {}
    for row in rows:
        s = by_mode.setdefault(row["mode"], {"pass": 0, "total": 0})
        s["total"] += 1
        s["pass"] += int(row["pass"])
    all_pass = all(row["pass"] for row in rows)
    return {
        "schema": SCHEMA,
        "status": "PASS" if all_pass else "FAIL",
        "pass": all_pass,
        "case_count": len(rows),
        "by_mode": by_mode,
        "rows": rows,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authority": False,
    }
