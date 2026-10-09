"""R2 direct adequacy router V20.

V20 prepends the compositional-natural V6 field lattice before V19. V19
remains the exact fallback for all nonmatching requests.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v19 as v19
from canonical.runtime import (
    r2_cross_document_compositional_lattice_direct_adequacy_v1
    as compositional_lattice,
)

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V20"
CROSS_DOCUMENT_COMPOSITIONAL_LATTICE_ROUTE_ID=compositional_lattice.ROUTE_ID
ROUTES=dict(v19.ROUTES)
ROUTES[CROSS_DOCUMENT_COMPOSITIONAL_LATTICE_ROUTE_ID]={
    "capability_id":compositional_lattice.CAPABILITY_ID,
    "scope":"COMPOSITIONAL_BOUNDED_COMPLETE_EFFECT_SENTENCE_TO_V6_FIELD_LATTICE",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=compositional_lattice.preflight(request,repo_root=repo_root)
    if (
        candidate.get("matched") is True
        or candidate.get("direct_route_semantic_open") is True
    ):
        return candidate
    return v19.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=compositional_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return compositional_lattice.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v19.run(request,repo_root=repo_root)
