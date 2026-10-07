from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class RouterFailClosed(RuntimeError):
    pass


@dataclass(frozen=True)
class AdmissionReceipt:
    context_digest: str
    cell_id: str
    route_id: str
    route_blob_sha: str
    adequacy_certificate_blob_sha: str
    admission_certificate_blob_sha: str
    admitted: bool


def _require_hex40(name: str, value: str) -> None:
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise RouterFailClosed(f"{name}_INVALID")


def select_certified_route(
    *,
    actual_context_digest: str,
    receipts: Iterable[AdmissionReceipt],
) -> AdmissionReceipt:
    """Select only an already-certified positive route; otherwise fail closed."""
    if not actual_context_digest:
        raise RouterFailClosed("ACTUAL_CONTEXT_DIGEST_MISSING")

    matches = []
    seen = set()
    for r in receipts:
        if type(r.admitted) is not bool:
            raise RouterFailClosed("ADMISSION_MUST_BE_LITERAL_BOOL")
        if not all((r.context_digest, r.cell_id, r.route_id, r.route_blob_sha,
                    r.adequacy_certificate_blob_sha, r.admission_certificate_blob_sha)):
            raise RouterFailClosed("RECEIPT_FIELD_MISSING")
        _require_hex40("ROUTE_BLOB_SHA", r.route_blob_sha)
        _require_hex40("ADEQUACY_CERTIFICATE_BLOB_SHA", r.adequacy_certificate_blob_sha)
        _require_hex40("ADMISSION_CERTIFICATE_BLOB_SHA", r.admission_certificate_blob_sha)

        identity = (
            r.context_digest, r.cell_id, r.route_id, r.route_blob_sha,
            r.adequacy_certificate_blob_sha, r.admission_certificate_blob_sha,
        )
        if identity in seen:
            raise RouterFailClosed("DUPLICATE_RECEIPT")
        seen.add(identity)

        if r.admitted and r.context_digest == actual_context_digest:
            matches.append(r)

    if not matches:
        raise RouterFailClosed("NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT")

    matches.sort(key=lambda r: (
        r.admission_certificate_blob_sha,
        r.adequacy_certificate_blob_sha,
        r.route_blob_sha,
        r.cell_id,
        r.route_id,
    ))
    return matches[0]
