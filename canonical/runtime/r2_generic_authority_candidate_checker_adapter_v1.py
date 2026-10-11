"""Generic reuse adapter from materialized authority source to existing truth checkers.

The adapter does not invent semantics. It takes checker templates already present
under the selected predicate, substitutes only the newly materialized source
text identity, and sends the resulting candidates back through the same
downstream truth checker. Caller/discovery labels remain non-authoritative.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_GENERIC_AUTHORITY_CANDIDATE_CHECKER_ADAPTER_V1"
MATERIALIZATION_SCHEMA = "PROJECT_BRAIN_R2_AUTHORITY_CANDIDATE_MATERIALIZATION_V1"


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "provider_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _existing_payloads(
    decision_payload: Mapping[str, Any],
    predicate_id: str,
) -> list[Mapping[str, Any]]:
    loop = decision_payload.get("bound_relevance_cegar_loop")
    if not isinstance(loop, Mapping):
        raise ValueError("BOUND_RELEVANCE_CEGAR_LOOP_REQUIRED")
    by_predicate = loop.get("truth_payloads_by_predicate_id")
    if not isinstance(by_predicate, Mapping):
        raise ValueError("TRUTH_PAYLOADS_BY_PREDICATE_ID_REQUIRED")
    value = by_predicate.get(predicate_id)
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list) and all(isinstance(x, Mapping) for x in value):
        return value
    raise ValueError("EXISTING_TRUTH_PAYLOAD_INVALID")


def _eligible(payload: Mapping[str, Any]) -> bool:
    return (
        isinstance(payload.get("target_claim_id"), str)
        and bool(payload.get("target_claim_id"))
        and isinstance(payload.get("claims"), list)
        and bool(payload.get("claims"))
    )


def adapt(
    decision_payload: Mapping[str, Any],
    predicate_id: str,
    request_packet: Mapping[str, Any],
    materialization: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        if not isinstance(predicate_id, str) or not predicate_id:
            return _base("FAIL_CLOSED", reason="PREDICATE_ID_REQUIRED")
        if (
            not isinstance(materialization, Mapping)
            or materialization.get("schema") != MATERIALIZATION_SCHEMA
            or materialization.get("pass") is not True
            or materialization.get("semantic_truth_authority") is True
        ):
            return _base("FAIL_CLOSED", reason="MATERIALIZATION_INVALID")
        material = materialization.get("checker_material")
        if not isinstance(material, Mapping):
            return _base("FAIL_CLOSED", reason="CHECKER_MATERIAL_REQUIRED")
        source_text = material.get("source_text")
        source_id = material.get("source_id")
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="MATERIALIZED_SOURCE_TEXT_REQUIRED")
        if not isinstance(source_id, str) or not source_id:
            return _base("FAIL_CLOSED", reason="MATERIALIZED_SOURCE_ID_REQUIRED")

        payloads = _existing_payloads(decision_payload, predicate_id)
        eligible = [p for p in payloads if _eligible(p)]
        if not eligible:
            return _base(
                "NOT_APPLICABLE__NO_EXISTING_SELECTED_SEMANTIC_TRUTH_CHECKER_TEMPLATE"
            )

        enriched: list[dict[str, Any]] = []
        seen: set[str] = set()
        for payload in eligible:
            row = deepcopy(dict(payload))
            row["source_text"] = source_text
            row["source_id"] = source_id
            row["authority_candidate_materialization"] = {
                "raw_sha256": material.get("raw_sha256"),
                "raw_size_bytes": material.get("raw_size_bytes"),
                "final_url": material.get("final_url"),
                "authority_domains": deepcopy(material.get("authority_domains")),
            }
            signature = repr((
                row.get("target_claim_id"),
                row.get("claims"),
                row.get("typed_context"),
                row.get("expected_typed_context_sha256"),
                row.get("fact_source"),
                row.get("fact_source_id"),
                source_id,
            ))
            if signature not in seen:
                seen.add(signature)
                enriched.append(row)

        if not enriched:
            return _base("NOT_APPLICABLE__NO_DISTINCT_CHECKER_CANDIDATES")

        return _base(
            "PASS__MATERIALIZED_AUTHORITY_CANDIDATE_BOUND_TO_EXISTING_TRUTH_CHECKER_TEMPLATES",
            passed=True,
            truth_payload_candidates=enriched,
            candidate_count=len(enriched),
            original_requested_predicate_id=predicate_id,
            downstream_checker_must_recompute_predicate_identity_and_truth=True,
            source_replacement_is_proposal_only=True,
            materialized_raw_sha256=material.get("raw_sha256"),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
