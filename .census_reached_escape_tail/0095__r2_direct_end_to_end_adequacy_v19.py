"""R2 direct adequacy router V19."""
from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime import r2_direct_end_to_end_adequacy_v18 as v18
from canonical.runtime import r2_source_bound_regcap_identity_direct_adequacy_v1 as local

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V19"
SOURCE_BOUND_REGCAP_IDENTITY_ROUTE_ID=local.ROUTE_ID
ROUTES=dict(v18.ROUTES)
ROUTES[SOURCE_BOUND_REGCAP_IDENTITY_ROUTE_ID]={
 "capability_id":local.CAPABILITY_ID,
 "scope":"EXACT_AUTHENTICATED_NYFED_SOURCE_CONTEXT_LOSS_ABSORBING_CUSHION_TO_CCOB",
 "acceptance":"INDEPENDENT_HTTPS_FRAGMENT_RELATION_REDERIVATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=local.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True: return candidate
 return v18.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=local.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True: return local.run(request,repo_root=repo_root)
 return v18.run(request,repo_root=repo_root)
