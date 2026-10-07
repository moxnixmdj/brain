from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_CERTIFICATE_GATED_SELECTED_ROUTE_ROUTER_V1"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA1.fullmatch(value))


def _validate_candidate(row: Mapping[str, Any]) -> str | None:
    if not isinstance(row, Mapping):
        return "CANDIDATE_NOT_MAPPING"
    if not isinstance(row.get("route_id"), str) or not row["route_id"]:
        return "ROUTE_ID_REQUIRED"
    if not _valid_sha(row.get("admission_certificate_sha")):
        return "ADMISSION_CERTIFICATE_SHA_INVALID"
    if not _valid_sha(row.get("adequacy_certificate_sha")):
        return "ADEQUACY_CERTIFICATE_SHA_INVALID"
    if type(row.get("admission_true")) is not bool:
        return "ADMISSION_TRUTH_MUST_BE_BOOLEAN"
    if type(row.get("certificate_verified")) is not bool:
        return "CERTIFICATE_VERIFIED_MUST_BE_BOOLEAN"
    return None


def select_certified_route(candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Return only a route with a true, independently verified admission certificate.

    The function is deliberately pure. It does not infer semantics, execute a route,
    create evidence, or treat fail-closed as coverage. Malformed input fails the whole
    selection rather than being silently ignored.
    """
    rows = list(candidates)
    errors: list[str] = []
    for i, row in enumerate(rows):
        err = _validate_candidate(row)
        if err:
            errors.append(f"{i}:{err}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_MALFORMED_CANDIDATE_SET",
            "pass": False,
            "dispatch_authority": False,
            "selected_route_id": None,
            "errors": errors,
            "cover_complete": False,
            "terminal_credit_delta": 0,
        }

    matches = [
        row for row in rows
        if row["admission_true"] is True and row["certificate_verified"] is True
    ]
    if not matches:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_NO_CERTIFIED_ADMISSION_MATCH",
            "pass": False,
            "dispatch_authority": False,
            "selected_route_id": None,
            "errors": [],
            "cover_complete": False,
            "terminal_credit_delta": 0,
        }

    selected = min(
        matches,
        key=lambda row: (
            row["admission_certificate_sha"],
            row["adequacy_certificate_sha"],
            row["route_id"],
        ),
    )
    return {
        "schema": SCHEMA,
        "status": "PASS_CERTIFICATE_GATED_ROUTE_SELECTED",
        "pass": True,
        "dispatch_authority": True,
        "selected_route_id": selected["route_id"],
        "admission_certificate_sha": selected["admission_certificate_sha"],
        "adequacy_certificate_sha": selected["adequacy_certificate_sha"],
        "eligible_match_count": len(matches),
        "deterministic_tie_break": "ADMISSION_SHA__ADEQUACY_SHA__ROUTE_ID",
        "cover_complete": None,
        "terminal_credit_delta": 0,
    }
