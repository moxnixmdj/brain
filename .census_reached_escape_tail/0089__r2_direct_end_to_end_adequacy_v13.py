"""R2 direct adequacy router V13.

Adds query-relative effect semantic lattice reasoning before V12.
A lattice route matches only after source-aligned proof has refined every
query-relevant semantic TOP dimension to finite exact effect semantics.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v12 as v12
from canonical.runtime import r2_cross_document_effect_semantic_lattice_direct_adequacy_v1 as lattice

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V13"
CROSS_DOCUMENT_EFFECT_LATTICE_ROUTE_ID=lattice.ROUTE_ID
ROUTES=dict(v12.ROUTES)
ROUTES[CROSS_DOCUMENT_EFFECT_LATTICE_ROUTE_ID]={
    "capability_id":lattice.CAPABILITY_ID,
    "scope":"QUERY_RELATIVE_MONOTONE_EFFECT_SEMANTIC_LATTICE",
    "preflight":"r2_cross_document_effect_semantic_lattice_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_effect_semantic_lattice_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_SOURCE_PROOF_LATTICE_AND_FINITE_WORLDSET_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v12.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=lattice.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return lattice.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v12.run(request,repo_root=repo_root)
