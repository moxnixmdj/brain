"""R2 direct adequacy router V12.

Adds the combined byte-coverage + source-residual cross-document frontier before
V11. Stronger combined cases are intercepted here; all existing V11 residual-TOP
behavior remains the delegated fallback.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v11 as v11
from canonical.runtime import r2_cross_document_source_residual_direct_adequacy_v1 as combined

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V12"
CROSS_DOCUMENT_SOURCE_RESIDUAL_ROUTE_ID=combined.ROUTE_ID
ROUTES=dict(v11.ROUTES)
ROUTES[CROSS_DOCUMENT_SOURCE_RESIDUAL_ROUTE_ID]={
    "capability_id":combined.CAPABILITY_ID,
    "scope":"QUERY_RELATIVE_BYTE_COVERAGE_PLUS_SOURCE_RESIDUAL_TOP_EFFECT_REASONING",
    "preflight":"r2_cross_document_source_residual_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_source_residual_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_BYTE_COVERAGE_RESIDUAL_TOP_AND_FINITE_WORLDSET_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=combined.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v11.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=combined.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return combined.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v11.run(request,repo_root=repo_root)
