"""R2 direct adequacy router V14.

Adds field-wise effect semantic lattice reasoning before V13.
Existing V13 complete-relation semantics remain the delegated fallback.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v13 as v13
from canonical.runtime import r2_cross_document_effect_field_lattice_direct_adequacy_v1 as field_lattice

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V14"
CROSS_DOCUMENT_EFFECT_FIELD_LATTICE_ROUTE_ID=field_lattice.ROUTE_ID
ROUTES=dict(v13.ROUTES)
ROUTES[CROSS_DOCUMENT_EFFECT_FIELD_LATTICE_ROUTE_ID]={
    "capability_id":field_lattice.CAPABILITY_ID,
    "scope":"QUERY_RELATIVE_MONOTONE_EFFECT_FIELD_LATTICE",
    "preflight":"r2_cross_document_effect_field_lattice_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_effect_field_lattice_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_V9_SOURCE_PROOF_FIELD_ASSEMBLY_AND_FINITE_WORLDSET_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=field_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v13.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=field_lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return field_lattice.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v13.run(request,repo_root=repo_root)
