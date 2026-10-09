"""R2 direct adequacy router V7.

Adds bounded structural contextual-reference Finance resolution before V6.
Every nonmatching request delegates to the verified V36 router unchanged.
"""
from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime import r2_direct_end_to_end_adequacy_v6 as v6
from canonical.runtime import r2_finance_contextual_reference_direct_adequacy_v1 as finance_context

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V7"
FINANCE_CONTEXTUAL_REFERENCE_ROUTE_ID=finance_context.ROUTE_ID
ROUTES=dict(v6.ROUTES)
ROUTES[FINANCE_CONTEXTUAL_REFERENCE_ROUTE_ID]={
 "capability_id":finance_context.CAPABILITY_ID,
 "scope":"FOUR_STRUCTURAL_CONTEXTUAL_REFERENCE_FORMS_WITH_NO_UNRESOLVED_AMBIGUITY",
 "preflight":"r2_finance_contextual_reference_direct_adequacy_v1.preflight",
 "executor":"r2_finance_contextual_reference_direct_adequacy_v1.run",
 "acceptance":"PRODUCER_INDEPENDENT_FULL_SPAN_BINDING_RELATION_AND_OBLIGATION_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_context.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return candidate
 return v6.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_context.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return finance_context.run(request,repo_root=repo_root)
 return v6.run(request,repo_root=repo_root)
