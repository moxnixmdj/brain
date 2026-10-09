"""R2 direct adequacy router V8.

Adds explicit ordered-pair former/latter Finance resolution before V7.
Nonmatching requests delegate to verified V37 router unchanged.
"""
from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime import r2_direct_end_to_end_adequacy_v7 as v7
from canonical.runtime import r2_finance_former_latter_direct_adequacy_v1 as finance_pair

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V8"
FINANCE_FORMER_LATTER_ROUTE_ID=finance_pair.ROUTE_ID
ROUTES=dict(v7.ROUTES)
ROUTES[FINANCE_FORMER_LATTER_ROUTE_ID]={
 "capability_id":finance_pair.CAPABILITY_ID,
 "scope":"EXPLICIT_ORDERED_PAIR_FORMER_TO_FIRST_LATTER_TO_SECOND_ONLY",
 "preflight":"r2_finance_former_latter_direct_adequacy_v1.preflight",
 "executor":"r2_finance_former_latter_direct_adequacy_v1.run",
 "acceptance":"PRODUCER_INDEPENDENT_ORDERED_PAIR_AND_REFERENCE_SPAN_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_pair.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return candidate
 return v7.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_pair.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return finance_pair.run(request,repo_root=repo_root)
 return v7.run(request,repo_root=repo_root)
