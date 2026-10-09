"""R2 direct adequacy router V19.

V19 prepends the Brain-owned compositional semantic-edge V6 lattice.
V18 remains the exact fallback for all nonmatching requests.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v18 as v18
from canonical.runtime import (
    r2_cross_document_compositional_lattice_direct_adequacy_v1
    as compositional_lattice,
)

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V19"
CROSS_DOCUMENT_COMPOSITIONAL_LATTICE_ROUTE_ID=compositional_lattice.ROUTE_ID
ROUTES=dict(v18.ROUTES)
ROUTES[CROSS_DOCUMENT_COMPOSITIONAL_LATTICE_ROUTE_ID]={
    "capability_id":compositional_lattice.CAPABILITY_ID,
    "scope":"BRAIN_OWNED_COMPOSITIONAL_SEMANTIC_RELATION_REGISTRY_TO_QUERY_RELATIVE_FIELD_LATTICE",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=compositional_lattice.preflight(request,repo_root=repo_root)
    if (
        candidate.get("matched") is True
        or candidate.get("direct_route_semantic_open") is True
    ):
        return candidate
    return v18.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=compositional_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return compositional_lattice.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v18.run(request,repo_root=repo_root)
