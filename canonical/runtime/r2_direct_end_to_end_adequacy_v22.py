"""R2 direct adequacy router V22.

V22 prepends the explicit three-rival regulatory-capital contextual selection
family. V21 remains the exact fallback for every nonmatching request.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v21 as v21
from canonical.runtime import r2_regcap_context_selection_direct_adequacy_v1 as local

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V22"
REGCAP_CONTEXT_SELECTION_ROUTE_ID = local.ROUTE_ID

ROUTES = dict(v21.ROUTES)
ROUTES[REGCAP_CONTEXT_SELECTION_ROUTE_ID] = {
    "capability_id": local.CAPABILITY_ID,
    "scope": (
        "EXPLICIT_TASK_UNIVERSE_CCOB_CCYB_TLAC__"
        "BOUNDED_loss-absorbing_cushion_CONTEXT_SIGNATURE_SELECTION"
    ),
    "acceptance": (
        "INDEPENDENT_SOURCE_ALIGNED_CONTEXT_REPARSE_PLUS_AUTHENTICATED_MATRIX"
    ),
}


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = local.preflight(request, repo_root=repo_root)
    if (
        candidate.get("matched") is True
        or candidate.get("direct_route_semantic_open") is True
    ):
        return candidate
    return v21.preflight(request, repo_root=repo_root)


def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = local.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return local.run(request, repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v21.run(request, repo_root=repo_root)
