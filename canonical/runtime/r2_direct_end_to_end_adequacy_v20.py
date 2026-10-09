"""R2 direct adequacy router V20.

Prepends decision-relative effect behavioral abstraction before V19.
Existing V19 source-bound RegCap identity and all prior routes remain exact
fallbacks for nonmatching requests.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v19 as v19
from canonical.runtime import (
    r2_cross_document_effect_behavioral_direct_adequacy_v1 as behavioral
)

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V20"
CROSS_DOCUMENT_EFFECT_BEHAVIORAL_ROUTE_ID=behavioral.ROUTE_ID
ROUTES=dict(v19.ROUTES)
ROUTES[CROSS_DOCUMENT_EFFECT_BEHAVIORAL_ROUTE_ID]={
    "capability_id":behavioral.CAPABILITY_ID,
    "scope":"COMPLETE_FINITE_BEHAVIORAL_OVERAPPROXIMATION_OF_V5_PARTIAL_EFFECT_SEMANTICS",
    "preflight":"r2_cross_document_effect_behavioral_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_effect_behavioral_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_BEHAVIORAL_WORLD_RECOMPUTATION_AND_OUTPUT_READBACK",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=behavioral.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v19.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=behavioral.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return behavioral.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v19.run(request,repo_root=repo_root)
