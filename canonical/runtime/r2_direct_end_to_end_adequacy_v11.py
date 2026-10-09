"""R2 direct adequacy router V11.

Adds source-backed residual-TOP cross-document reasoning before V10.

A source-backed request is intercepted here:
- closed residual frontier -> execute the verified source-backed route;
- open residual frontier -> preserve its semantic-open proof obligations;
- unrelated request -> delegate to V10.

This prevents raw-source finite hypotheses from bypassing residual completeness.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v10 as v10
from canonical.runtime import r2_cross_document_residual_effect_direct_adequacy_v1 as residual

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V11"
CROSS_DOCUMENT_RESIDUAL_ROUTE_ID=residual.ROUTE_ID
ROUTES=dict(v10.ROUTES)
ROUTES[CROSS_DOCUMENT_RESIDUAL_ROUTE_ID]={
    "capability_id":residual.CAPABILITY_ID,
    "scope":"SOURCE_BACKED_RESIDUAL_TOP_CROSS_DOCUMENT_EFFECT_REASONING",
    "preflight":"r2_cross_document_residual_effect_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_residual_effect_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_RESIDUAL_FRONTIER_AND_FINITE_WORLDSET_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=residual.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v10.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=residual.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return residual.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v10.run(request,repo_root=repo_root)
