"""R2 direct adequacy router V6.

Adds state-keyed independently refetched external JSON finance policy before the
current V5 router. Every nonmatching request delegates to V5 unchanged, preserving
the explicit-alias Finance slice and every earlier route.
"""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import r2_direct_end_to_end_adequacy_v5 as v5
from canonical.runtime import r2_finance_external_json_policy_direct_adequacy_v1 as finance_external

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V6"
FINANCE_EXTERNAL_JSON_POLICY_ROUTE_ID=finance_external.ROUTE_ID
ROUTES=dict(v5.ROUTES)
ROUTES[FINANCE_EXTERNAL_JSON_POLICY_ROUTE_ID]={
    "capability_id":finance_external.CAPABILITY_ID,
    "scope":"STATE_KEYED_INDEPENDENTLY_REFETCHED_HTTPS_JSON_VALUE_TO_EXACT_BOOLEAN_OR_DECIMAL_FINANCE_POLICY",
    "preflight":"r2_finance_external_json_policy_direct_adequacy_v1.preflight",
    "executor":"r2_finance_external_json_policy_direct_adequacy_v1.run",
    "acceptance":"INHERITED_INDEPENDENT_HTTP_SEMANTIC_REFETCH_PLUS_PRODUCER_INDEPENDENT_EXACT_JSON_PATH_PREDICATE_AND_ACTION_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=finance_external.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v5.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=finance_external.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_external.run(request,repo_root=repo_root)
    return v5.run(request,repo_root=repo_root)
