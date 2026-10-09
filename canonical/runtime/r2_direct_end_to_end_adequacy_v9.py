"""R2 direct adequacy router V9.

Adds bounded demonstrative event-reference Finance resolution before V8.
Nonmatching requests delegate to verified V38 router unchanged.
"""
from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime import r2_direct_end_to_end_adequacy_v8 as v8
from canonical.runtime import r2_finance_event_reference_direct_adequacy_v1 as finance_event

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V9"
FINANCE_EVENT_REFERENCE_ROUTE_ID=finance_event.ROUTE_ID
ROUTES=dict(v8.ROUTES)
ROUTES[FINANCE_EVENT_REFERENCE_ROUTE_ID]={
 "capability_id":finance_event.CAPABILITY_ID,
 "scope":"FINITE_LEXICAL_DEMONSTRATIVE_EVENT_REFERENCE_VALIDATE_OPERATE_PROCESS",
 "preflight":"r2_finance_event_reference_direct_adequacy_v1.preflight",
 "executor":"r2_finance_event_reference_direct_adequacy_v1.run",
 "acceptance":"PRODUCER_INDEPENDENT_EVENT_TYPE_EVENT_SPAN_MENTION_SPAN_AND_TEXT_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_event.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return candidate
 return v8.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
 candidate=finance_event.preflight(request,repo_root=repo_root)
 if candidate.get("matched") is True:return finance_event.run(request,repo_root=repo_root)
 return v8.run(request,repo_root=repo_root)
