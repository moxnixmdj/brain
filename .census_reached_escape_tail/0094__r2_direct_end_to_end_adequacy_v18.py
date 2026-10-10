"""R2 direct adequacy router V18.

V18 prepends the Brain-owned semantic-relation registry backed V5 field lattice.
V17 remains the exact fallback for all nonmatching requests.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v17 as v17
from canonical.runtime import (
    r2_cross_document_semantic_registry_lattice_direct_adequacy_v1
    as registry_lattice,
)

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V18"
CROSS_DOCUMENT_SEMANTIC_REGISTRY_LATTICE_ROUTE_ID=registry_lattice.ROUTE_ID
ROUTES=dict(v17.ROUTES)
ROUTES[CROSS_DOCUMENT_SEMANTIC_REGISTRY_LATTICE_ROUTE_ID]={
    "capability_id":registry_lattice.CAPABILITY_ID,
    "scope":"BRAIN_OWNED_MULTI_CLASS_SEMANTIC_RELATION_REGISTRY_TO_QUERY_RELATIVE_FIELD_LATTICE",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=registry_lattice.preflight(request,repo_root=repo_root)
    if (
        candidate.get("matched") is True
        or candidate.get("direct_route_semantic_open") is True
    ):
        return candidate
    return v17.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=registry_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return registry_lattice.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v17.run(request,repo_root=repo_root)
