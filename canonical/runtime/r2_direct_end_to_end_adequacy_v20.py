"""R2 direct adequacy router V20.

Prepends registry-V2 semantic-edge lattice reasoning, including genuinely
nonexplicit source implication-closure entailment. All unrelated requests
delegate to V19 unchanged.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v19 as v19
from canonical.runtime import r2_cross_document_semantic_registry_v2_lattice_direct_adequacy_v1 as local

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V20"
SEMANTIC_REGISTRY_V2_ROUTE_ID=local.ROUTE_ID
ROUTES=dict(v19.ROUTES)
ROUTES[SEMANTIC_REGISTRY_V2_ROUTE_ID]={
    "capability_id":local.CAPABILITY_ID,
    "scope":"QUERY_RELATIVE_EFFECT_FIELD_LATTICE_WITH_SOURCE_IMPLICATION_CLOSURE",
    "acceptance":"INDEPENDENT_V5_RECOMPUTATION_USING_BRAIN_OWNED_RELATION_REGISTRY_V2",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=local.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v19.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=local.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return local.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v19.run(request,repo_root=repo_root)
