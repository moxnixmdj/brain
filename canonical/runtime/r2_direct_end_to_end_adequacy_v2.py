"""R2 direct adequacy router V2.

Adds the authoritative-normalized Finance decision family before delegating every
other request to V1 unchanged.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as v1
from canonical.runtime import r2_finance_normalized_direct_adequacy_v1 as finance

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V2"
FINANCE_ROUTE_ID = finance.ROUTE_ID
ROUTES = dict(v1.ROUTES)
ROUTES[FINANCE_ROUTE_ID] = {
    "capability_id": "decision.synthesis.typed.stdlib",
    "scope": (
        "AUTHORITATIVE_NORMALIZED_FINANCE_SOURCE_UNIVERSE_TO_"
        "INDEPENDENTLY_VERIFIED_TYPED_DECISION"
    ),
    "preflight": "r2_finance_normalized_direct_adequacy_v1.preflight",
    "executor": "r2_finance_normalized_direct_adequacy_v1.run",
    "acceptance": "finance_normalized_direct_acceptance_v1.verify",
}


def preflight(request: Mapping[str, Any]) -> dict[str, Any]:
    candidate = finance.preflight(request)
    if candidate.get("matched") is True:
        return candidate
    return v1.preflight(request)


def run(request: Mapping[str, Any]) -> dict[str, Any]:
    candidate = finance.preflight(request)
    if candidate.get("matched") is True:
        return finance.run(request)
    return v1.run(request)
