"""R2 direct adequacy router V16.

Adds bounded-natural cross-document effect lattice reasoning before V15.
Existing V15 coreference and V14/V13 cross-document routes remain delegated fallbacks.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v15 as v15
from canonical.runtime import r2_cross_document_natural_effect_lattice_direct_adequacy_v1 as natural_lattice

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V16"
CROSS_DOCUMENT_NATURAL_EFFECT_LATTICE_ROUTE_ID=natural_lattice.ROUTE_ID
ROUTES=dict(v15.ROUTES)
ROUTES[CROSS_DOCUMENT_NATURAL_EFFECT_LATTICE_ROUTE_ID]={
    "capability_id":natural_lattice.CAPABILITY_ID,
    "scope":"BOUNDED_NATURAL_EFFECT_CLAUSE_TO_QUERY_RELATIVE_FIELD_LATTICE",
    "preflight":"r2_cross_document_natural_effect_lattice_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_natural_effect_lattice_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_V10_SOURCE_PROOF_V3_LATTICE_AND_FINITE_WORLDSET_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=natural_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v15.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=natural_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return natural_lattice.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v15.run(request,repo_root=repo_root)
