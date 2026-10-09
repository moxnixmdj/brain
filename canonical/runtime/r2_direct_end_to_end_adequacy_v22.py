"""R2 direct adequacy router V22.

V22 prepends the already-verified bounded regulatory-capital contextual-fact
extraction route before V21. V21 remains the exact fallback for every request
outside that route's narrow grammar and authority boundary.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v21 as v21
from canonical.runtime import r2_regcap_contextual_fact_direct_adequacy_v1 as local

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V22"
REGCAP_CONTEXTUAL_FACT_ROUTE_ID = local.ROUTE_ID
ROUTES = dict(v21.ROUTES)
ROUTES[REGCAP_CONTEXTUAL_FACT_ROUTE_ID] = {
    "capability_id": local.CAPABILITY_ID,
    "scope": (
        "BOUNDED_REPOSITORY_LOCAL_REGCAP_CONTEXTUAL_FACT_EXTRACTION__"
        "NO_PROPERTY_TO_CONCEPT_REVERSE_CLASSIFICATION"
    ),
    "acceptance": "PRODUCER_INDEPENDENT_CONTEXT_FACT_REDERIVATION",
}


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = local.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v21.preflight(request, repo_root=repo_root)


def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = local.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return local.run(request, repo_root=repo_root)
    return v21.run(request, repo_root=repo_root)
