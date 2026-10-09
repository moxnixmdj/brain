"""R2 direct adequacy router V13.

Adds raw cross-document effect bundle compilation before V12. Raw bundles are
compiled fail-closed into V12 cases. Unrecognized non-whitespace source remains
semantic-open and is surfaced to the adaptive resolver.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v12 as v12
from canonical.runtime import r2_raw_cross_document_effect_bundle_direct_adequacy_v1 as rawbundle

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V13"
RAW_CROSS_DOCUMENT_BUNDLE_ROUTE_ID=rawbundle.ROUTE_ID
ROUTES=dict(v12.ROUTES)
ROUTES[RAW_CROSS_DOCUMENT_BUNDLE_ROUTE_ID]={
    "capability_id":rawbundle.CAPABILITY_ID,
    "scope":"RAW_DOCUMENT_BUNDLES_WITH_EXACT_CERTIFIED_EFFECT_SENTENCES",
    "preflight":"r2_raw_cross_document_effect_bundle_direct_adequacy_v1.preflight",
    "executor":"r2_raw_cross_document_effect_bundle_direct_adequacy_v1.run",
    "acceptance":"RAW_BYTES_RECOMPILED_THROUGH_V12_COMBINED_SOURCE_RESIDUAL_VERIFICATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=rawbundle.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v12.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=rawbundle.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return rawbundle.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v12.run(request,repo_root=repo_root)
