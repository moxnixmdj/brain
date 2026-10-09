"""R2 direct adequacy router V11.

Adds exact source-coverage-gated cross-document effect reasoning before V10.
Closed source capsules may terminate. Any OPEN_UNKNOWN_EFFECT region remains
unmatched and is surfaced as a semantic-open hint for the adaptive resolver.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v10 as v10
from canonical.runtime import r2_cross_document_source_coverage_direct_adequacy_v1 as sourcecov

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V11"
CROSS_DOCUMENT_SOURCE_COVERAGE_ROUTE_ID=sourcecov.ROUTE_ID
ROUTES=dict(v10.ROUTES)
ROUTES[CROSS_DOCUMENT_SOURCE_COVERAGE_ROUTE_ID]={
    "capability_id":sourcecov.CAPABILITY_ID,
    "scope":"EXACT_SOURCE_BYTE_COVERAGE_PLUS_CLOSED_EFFECT_WORLDSET_COMMON_VALUE_ONLY",
    "preflight":"r2_cross_document_source_coverage_direct_adequacy_v1.preflight",
    "executor":"r2_cross_document_source_coverage_direct_adequacy_v1.run",
    "acceptance":"INDEPENDENT_SOURCE_COVERAGE_AND_WORLDSET_RECOMPUTATION_WITH_OUTPUT_READBACK",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=sourcecov.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v10.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=sourcecov.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return sourcecov.run(request,repo_root=repo_root)
    if candidate.get("direct_route_semantic_open") is True:
        return candidate
    return v10.run(request,repo_root=repo_root)
