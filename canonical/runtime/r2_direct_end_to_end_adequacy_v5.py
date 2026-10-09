"""R2 direct adequacy router V5.

Adds exact explicit-alias Finance UNLESS resolution before V4. Every nonmatching
request delegates to V4 unchanged.
"""
from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime import r2_direct_end_to_end_adequacy_v4 as v4
from canonical.runtime import r2_finance_explicit_alias_unless_direct_adequacy_v1 as finance_alias

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V5"
FINANCE_EXPLICIT_ALIAS_ROUTE_ID=finance_alias.ROUTE_ID
ROUTES=dict(v4.ROUTES)
ROUTES[FINANCE_EXPLICIT_ALIAS_ROUTE_ID]={
 "capability_id":finance_alias.CAPABILITY_ID,
 "scope":"EXACT_EXPLICIT_REFERS_TO_OR_IS_DEFINED_AS_ALIAS_TO_LITERAL_TYPED_UNLESS_REFERENCE",
 "preflight":"r2_finance_explicit_alias_unless_direct_adequacy_v1.preflight",
 "executor":"r2_finance_explicit_alias_unless_direct_adequacy_v1.run",
 "acceptance":"PRODUCER_INDEPENDENT_EXPLICIT_ALIAS_REFERENCE_TYPED_CONDITION_BRANCH_AND_HASH_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_alias.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return candidate
 return v4.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_alias.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return finance_alias.run(request,repo_root=repo_root)
 return v4.run(request,repo_root=repo_root)
