"""Fail-closed implementation-target admission from canonical behavioral contracts.

A mechanism-search target is admissible only when the target itself is a registered
BEHAVIOR with every canonical contract field present and non-empty. Accounting labels,
undefined names, missing targets, and incomplete contracts cannot drive implementation.
"""
from __future__ import annotations
from typing import Mapping,Any

REQUIRED=(
 "behavior_id","inputs","environment_state","allowed_information",
 "required_output_or_action","success_condition","failure_condition",
 "terminal_consequence","verification_route","dependency_boundary","scope",
)

def admit_mechanism_target(target_id:str,registry:Mapping[str,Any])->dict:
    if not isinstance(target_id,str) or not target_id.strip():
        return {"status":"FAIL_CLOSED","reason":"TARGET_ID_INVALID","admitted":False}
    rows=registry.get("active_contracted_residuals") if isinstance(registry,Mapping) else None
    if not isinstance(rows,list):
        return {"status":"FAIL_CLOSED","reason":"REGISTRY_INVALID","admitted":False}
    matches=[r for r in rows if isinstance(r,Mapping) and r.get("behavior_id")==target_id]
    if len(matches)!=1:
        return {
          "status":"SPECIFICATION_REQUIRED","reason":"TARGET_NOT_UNIQUELY_REGISTERED_BEHAVIOR",
          "admitted":False,"target_id":target_id,
        }
    row=matches[0]
    missing=[k for k in REQUIRED if k not in row or row[k] in (None,"",[],{})]
    if missing:
        return {
          "status":"SPECIFICATION_REQUIRED","reason":"BEHAVIORAL_CONTRACT_INCOMPLETE",
          "admitted":False,"target_id":target_id,"missing_fields":missing,
        }
    return {
      "status":"ADMIT_MECHANISM_SEARCH","reason":"COMPLETE_REGISTERED_BEHAVIORAL_CONTRACT",
      "admitted":True,"target_id":target_id,
    }
