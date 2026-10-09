"""R2 direct adequacy router V21.

V21 prepends bounded regulatory-capital contextual-property extraction before
V20. V20 remains the exact fallback for every nonmatching request.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v20 as v20
from canonical.runtime import r2_regcap_contextual_fact_direct_adequacy_v1 as regcap_context

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V21"
REGCAP_CONTEXTUAL_FACT_ROUTE_ID = regcap_context.ROUTE_ID

ROUTES = dict(v20.ROUTES)
ROUTES[REGCAP_CONTEXTUAL_FACT_ROUTE_ID] = {
    "capability_id": regcap_context.CAPABILITY_ID,
    "scope": (
        "BOUNDED_SOURCE_ALIGNED_REGCAP_CONTEXTUAL_PROPERTY_EXTRACTION__"
        "NO_CONCEPT_IDENTITY"
    ),
    "acceptance": (
        "PRODUCER_INDEPENDENT_CONTEXT_FACT_REDERIVATION_PLUS_"
        "LOSSLESS_RAW_GOAL_OBLIGATION_RECOMPUTATION"
    ),
}

def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = regcap_context.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v20.preflight(request, repo_root=repo_root)

def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = regcap_context.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return regcap_context.run(request, repo_root=repo_root)
    return v20.run(request, repo_root=repo_root)
