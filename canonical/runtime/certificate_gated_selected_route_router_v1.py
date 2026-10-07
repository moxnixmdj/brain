"""Brain-owned fail-closed certificate-gated selected-route router.

This module implements only the mechanical selection consequence of the
certificate-gated router theorem. It does NOT infer whether an admission
predicate is semantically true for a context. Upstream admission predicates
must already be independently bound to sound adequacy certificates.

Invariant:
    the router either selects one explicitly certified positive match or
    returns a fail-closed result with no selected route.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_GIT_SHA1 = re.compile(r"^[0-9a-f]{40}$")


def _fail(reason: str, *, index: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "selected_route": None,
        "selected_admission_predicate_id": None,
        "certified_match_count": 0,
    }
    if index is not None:
        out["invalid_index"] = index
    return out


def _identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value else None


def _sha1(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if _GIT_SHA1.fullmatch(value) else None


def select_certified_route(matches: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Select one certified route or fail closed.

    Each positive match must contain:
      * admitted: literal bool True
      * admission_predicate_id: non-empty stable identifier
      * admission_certificate_sha: exact 40-hex Git blob/commit identity
      * route_id: non-empty stable route identifier
      * route_certificate_sha: exact 40-hex Git blob/commit identity

    False matches are ignored. Any non-boolean admission value, malformed
    positive identity, or conflicting binding for the same admission
    predicate causes the whole decision to fail closed.

    If multiple independent positive matches survive, selection is
    deterministic by content-addressed lexical order. This is sound only
    under the upstream theorem premise that every admitted match is itself
    independently certified adequate for the actual context.
    """
    if isinstance(matches, (str, bytes, bytearray)) or not isinstance(matches, Sequence):
        return _fail("MATCHES_MUST_BE_SEQUENCE")

    positives: list[dict[str, str]] = []
    predicate_bindings: dict[str, tuple[str, str, str]] = {}

    for index, raw in enumerate(matches):
        if not isinstance(raw, Mapping):
            return _fail("MATCH_NOT_MAPPING", index=index)

        admitted = raw.get("admitted")
        if type(admitted) is not bool:
            return _fail("ADMISSION_MUST_BE_LITERAL_BOOL", index=index)
        if admitted is False:
            continue

        predicate_id = _identifier(raw.get("admission_predicate_id"))
        admission_sha = _sha1(raw.get("admission_certificate_sha"))
        route_id = _identifier(raw.get("route_id"))
        route_sha = _sha1(raw.get("route_certificate_sha"))

        if predicate_id is None:
            return _fail("ADMISSION_PREDICATE_ID_INVALID", index=index)
        if admission_sha is None:
            return _fail("ADMISSION_CERTIFICATE_SHA_INVALID", index=index)
        if route_id is None:
            return _fail("ROUTE_ID_INVALID", index=index)
        if route_sha is None:
            return _fail("ROUTE_CERTIFICATE_SHA_INVALID", index=index)

        binding = (route_id, route_sha, admission_sha)
        prior = predicate_bindings.get(predicate_id)
        if prior is not None and prior != binding:
            return _fail("CONFLICTING_ADMISSION_PREDICATE_BINDING", index=index)
        predicate_bindings[predicate_id] = binding

        positives.append(
            {
                "admission_predicate_id": predicate_id,
                "admission_certificate_sha": admission_sha,
                "route_id": route_id,
                "route_certificate_sha": route_sha,
            }
        )

    if not positives:
        return _fail("NO_CERTIFIED_POSITIVE_MATCH")

    unique = {
        (
            item["admission_predicate_id"],
            item["admission_certificate_sha"],
            item["route_id"],
            item["route_certificate_sha"],
        ): item
        for item in positives
    }
    ordered = sorted(
        unique.values(),
        key=lambda item: (
            item["admission_predicate_id"],
            item["route_id"],
            item["route_certificate_sha"],
            item["admission_certificate_sha"],
        ),
    )
    selected = ordered[0]

    return {
        "pass": True,
        "status": "SELECTED_CERTIFIED_ROUTE",
        "reason": "CERTIFIED_POSITIVE_MATCH",
        "selected_route": selected["route_id"],
        "selected_admission_predicate_id": selected["admission_predicate_id"],
        "selected_admission_certificate_sha": selected["admission_certificate_sha"],
        "selected_route_certificate_sha": selected["route_certificate_sha"],
        "certified_match_count": len(ordered),
        "tie_break": "LEXICAL_CONTENT_ADDRESSED",
    }
