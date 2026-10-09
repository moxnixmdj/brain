"""R2 direct adequacy router V9.

Adds generic typed cross-document effect composition before V8.
Only cases with a verifier-confirmed common effective value match this route;
semantic conflicts remain unmatched so R2 can pursue a discriminator.
"""
from __future__ import annotations
from typing import Any,Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v8 as v8
from canonical.runtime import r2_cross_document_effect_direct_adequacy_v1 as crossdoc_effect

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V9"
CROSS_DOCUMENT_EFFECT_ROUTE_ID=crossdoc_effect.ROUTE_ID
ROUTES=dict(v8.ROUTES)
ROUTES[CROSS_DOCUMENT_EFFECT_ROUTE_ID]={
 "capability_id":crossdoc_effect.CAPABILITY_ID,
 "scope":"TYPED_CONTENT_ADDRESSED_CROSS_DOCUMENT_EFFECTS__COMMON_EFFECTIVE_VALUE_ONLY",
 "preflight":"r2_cross_document_effect_direct_adequacy_v1.preflight",
 "executor":"r2_cross_document_effect_direct_adequacy_v1.run",
 "acceptance":"PRODUCER_INDEPENDENT_EFFECT_APPLICABILITY_SUPERSESSION_AND_COMMON_VALUE_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=crossdoc_effect.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v8.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=crossdoc_effect.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return crossdoc_effect.run(request,repo_root=repo_root)
    return v8.run(request,repo_root=repo_root)
