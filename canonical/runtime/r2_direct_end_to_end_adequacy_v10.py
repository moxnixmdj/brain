"""R2 direct adequacy router V10.

Adds decision-invariant cross-document effect hypothesis worlds before V9.
The route matches only when every declared complete effect world yields one
common effective value. Outcome-changing ambiguity remains unmatched.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v9 as v9
from canonical.runtime import r2_cross_document_effect_worldset_direct_adequacy_v1 as worldset

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V10"
CROSS_DOCUMENT_WORLDSET_ROUTE_ID=worldset.ROUTE_ID
ROUTES=dict(v9.ROUTES)
ROUTES[CROSS_DOCUMENT_WORLDSET_ROUTE_ID]={
    "capability_id":worldset.CAPABILITY_ID,
    "scope":"DECLARED_COMPLETE_FINITE_TYPED_EFFECT_HYPOTHESIS_UNIVERSE__COMMON_EFFECTIVE_VALUE_ONLY",
    "preflight":"r2_cross_document_effect_worldset_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_effect_worldset_direct_adequacy_v1.run",
    "acceptance":"PRODUCER_INDEPENDENT_WORLDSET_RECOMPUTATION_AND_OUTPUT_READBACK",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=worldset.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v9.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=worldset.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return worldset.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v9.run(request,repo_root=repo_root)
