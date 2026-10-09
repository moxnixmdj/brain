"""R2 direct adequacy router V17."""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import r2_direct_end_to_end_adequacy_v16 as v16
from canonical.runtime import r2_cross_document_semantic_edge_lattice_direct_adequacy_v1 as edge_lattice

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V17"
CROSS_DOCUMENT_SEMANTIC_EDGE_LATTICE_ROUTE_ID=edge_lattice.ROUTE_ID
ROUTES=dict(v16.ROUTES)
ROUTES[CROSS_DOCUMENT_SEMANTIC_EDGE_LATTICE_ROUTE_ID]={
    "capability_id":edge_lattice.CAPABILITY_ID,
    "scope":"BRAIN_OWNED_SUPPORTED_SEMANTIC_EDGE_TO_QUERY_RELATIVE_FIELD_LATTICE",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=edge_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True or candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v16.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=edge_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return edge_lattice.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v16.run(request,repo_root=repo_root)
