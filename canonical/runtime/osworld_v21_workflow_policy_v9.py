"""Workflow policy V9: verified V13 stack plus task-independent semantic normalization."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_semantic_normalizer_v1 import normalize_instruction
from canonical.runtime.osworld_v21_workflow_policy_v8 import decide as base_decide

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_WORKFLOW_POLICY_V9"

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    if not isinstance(state,Mapping):
        raise ValueError("STATE_NOT_OBJECT")
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip():
        return base_decide(state)

    norm=normalize_instruction(instruction)
    local=dict(state)
    local["instruction"]=norm["normalized"]
    out=base_decide(local)
    if not isinstance(out,Mapping):
        raise ValueError("BASE_POLICY_OUTPUT_NOT_OBJECT")
    result=dict(out)
    if norm["changed"]:
        receipt=result.get("_policy_receipt")
        if isinstance(receipt,Mapping):
            receipt=dict(receipt)
            receipt["semantic_normalization"]={
                "schema":SCHEMA,
                "applied_rules":list(norm["applied_rules"]),
                "task_specific_policy_data":False,
                "external_model_dependency":False,
            }
            result["_policy_receipt"]=receipt
        else:
            result["_semantic_normalization"]={
                "schema":SCHEMA,
                "applied_rules":list(norm["applied_rules"]),
                "task_specific_policy_data":False,
                "external_model_dependency":False,
            }
    return result
