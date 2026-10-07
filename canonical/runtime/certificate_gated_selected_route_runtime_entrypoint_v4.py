"""Certificate-gated selected-route runtime V4.

V4 repairs the load-bearing context/payload seam in V3. A symbolic predicate
selects a route from the authenticated context, but the route executes a
separate payload object. For every creditable row, V4 therefore restores V2's
mandatory content-addressed payload-membership validator before route import or
execution. Non-creditable deployment canaries remain compatible.

Global selected-cover completeness is still derived only from the exact
creditable predicate set plus an independent complement proof.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2 import (
    RuntimeBindingFailClosed,
    _canonical_path,
    _load_callable,
    _load_json,
    _validate_creditable_payload,
    context_digest,
    git_blob_sha,
)
from canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v3 import (
    _selected_cover_state,
    _verified_rows as _verified_rows_v3,
    load_registry,
)

SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_ENTRYPOINT_V4"


def _verified_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Reuse V3 symbolic-route validation and restore V2 payload binding."""
    rows = _verified_rows_v3(registry)
    for index, row in enumerate(rows):
        if row.get("creditable") is not True:
            continue

        required = (
            "payload_validator_path",
            "payload_validator_blob_sha",
            "payload_validator_callable",
        )
        if any(not row.get(key) for key in required):
            raise RuntimeBindingFailClosed(
                f"CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING:{index}"
            )

        validator_path = _canonical_path(
            row.get("payload_validator_path"),
            prefixes=("canonical/runtime/",),
        )
        if row.get("payload_validator_blob_sha") != git_blob_sha(validator_path):
            raise RuntimeBindingFailClosed(
                f"PAYLOAD_VALIDATOR_BLOB_DRIFT:{index}"
            )

        admission_path = _canonical_path(
            row.get("admission_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        admission = _load_json(admission_path)
        for key in required:
            if admission.get(key) != row.get(key):
                raise RuntimeBindingFailClosed(
                    f"ADMISSION_PAYLOAD_VALIDATOR_BINDING_MISMATCH:{index}:{key}"
                )
    return rows


def preflight() -> dict[str, Any]:
    try:
        registry = load_registry()
        rows = _verified_rows(registry)
        cover = _selected_cover_state(registry, rows)
        return {
            "schema": SCHEMA,
            "status": "PASS__SYMBOLIC_ROUTE_RUNTIME_WITH_CREDITABLE_PAYLOAD_BINDING_VALID",
            "pass": True,
            "route_count": len(rows),
            "symbolic_route_count": sum(
                row.get("match_mode") == "SYMBOLIC_PREDICATE" for row in rows
            ),
            "creditable_route_count": sum(
                row.get("creditable") is True for row in rows
            ),
            "selected_cover_complete": cover["authorized"],
            "selected_cover_gate_status": cover["gate_status"],
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "selected_cover_complete": False,
            "terminal_credit_delta": 0,
        }


def dispatch(context: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        raise RuntimeBindingFailClosed("CONTEXT_MAPPING_REQUIRED")
    if not isinstance(payload, Mapping):
        raise RuntimeBindingFailClosed("PAYLOAD_MAPPING_REQUIRED")

    registry = load_registry()
    rows = _verified_rows(registry)
    actual_context_digest = context_digest(context)
    matches: list[dict[str, Any]] = []

    for row in rows:
        if row.get("admitted") is not True:
            continue
        mode = row.get("match_mode")
        matched = False
        if mode == "EXACT_DIGEST":
            matched = row.get("context_digest") == actual_context_digest
        else:
            fn = _load_callable(
                row["_predicate_path"],
                str(row.get("admission_predicate_callable") or ""),
                module_prefix="project_brain_admission_predicate_v4_",
            )
            result = fn(dict(context))
            if type(result) is not bool:
                raise RuntimeBindingFailClosed(
                    "ADMISSION_PREDICATE_MUST_RETURN_LITERAL_BOOL"
                )
            matched = result
        if matched:
            matches.append(row)

    if not matches:
        raise RuntimeBindingFailClosed("NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT")

    matches.sort(
        key=lambda row: (
            str(row.get("admission_certificate_blob_sha") or ""),
            str(row.get("adequacy_certificate_blob_sha") or ""),
            str(row.get("route_blob_sha") or ""),
            str(row.get("cell_id") or ""),
            str(row.get("route_id") or ""),
        )
    )
    selected = matches[0]

    bound_payload_digest = None
    if selected.get("creditable") is True:
        bound_payload_digest = _validate_creditable_payload(
            selected,
            cell_id=str(selected["cell_id"]),
            context=context,
            payload=payload,
            actual_context_digest=actual_context_digest,
        )

    route_fn = _load_callable(
        selected["_route_path"],
        str(selected.get("callable") or ""),
        module_prefix="project_brain_selected_route_v4_",
    )
    result = route_fn(dict(payload))
    if not isinstance(result, Mapping):
        raise RuntimeBindingFailClosed("ROUTE_RESULT_NOT_MAPPING")

    cover = _selected_cover_state(registry, rows)
    return {
        "schema": SCHEMA,
        "status": "PASS__CERTIFICATE_GATED_SYMBOLIC_ROUTE_EXECUTED_WITH_PAYLOAD_BINDING",
        "actual_context_digest": actual_context_digest,
        "payload_sha256": bound_payload_digest,
        "selected_cell_id": selected["cell_id"],
        "selected_route_id": selected["route_id"],
        "match_mode": selected["match_mode"],
        "admission_predicate_id": selected.get("admission_predicate_id"),
        "route_blob_sha": selected["route_blob_sha"],
        "adequacy_certificate_blob_sha": selected["adequacy_certificate_blob_sha"],
        "admission_certificate_blob_sha": selected["admission_certificate_blob_sha"],
        "creditable": selected.get("creditable") is True,
        "result": dict(result),
        "selected_cover_complete": cover["authorized"],
        "selected_cover_gate_status": cover["gate_status"],
        "terminal_credit_delta": 0,
        "rule": (
            "CREDITABLE_SYMBOLIC_ROUTE_EXECUTES_ONLY_AFTER_CONTENT_ADDRESSED_"
            "PREDICATE_ROUTE_CERTIFICATE_AND_CONTEXT_PAYLOAD_MEMBERSHIP_BINDING"
        ),
    }
