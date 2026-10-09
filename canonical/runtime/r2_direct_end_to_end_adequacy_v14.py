"""R2 direct adequacy router V14.

Adds independently source-proved per-dimension effect semantics before V13.
Partial semantic closure remains open and is surfaced as exact lattice TOP atoms.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v13 as v13
from canonical.runtime import r2_cross_document_effect_dimension_lattice_direct_adequacy_v1 as dims

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V14"
CROSS_DOCUMENT_EFFECT_DIMENSION_ROUTE_ID=dims.ROUTE_ID
ROUTES=dict(v13.ROUTES)
ROUTES[CROSS_DOCUMENT_EFFECT_DIMENSION_ROUTE_ID]={
    "capability_id":dims.CAPABILITY_ID,
    "scope":"QUERY_RELATIVE_MONOTONE_EFFECT_DIMENSION_LATTICE",
    "preflight":"r2_cross_document_effect_dimension_lattice_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_effect_dimension_lattice_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_V9_SOURCE_PROOF_DIMENSION_LATTICE_AND_FINITE_WORLDSET_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=dims.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v13.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=dims.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return dims.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v13.run(request,repo_root=repo_root)
