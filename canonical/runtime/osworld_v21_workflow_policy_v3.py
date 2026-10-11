"""Capability-grounded semantic workflow policy V3.

V3 may split an otherwise unordered conjunction only when every resulting
clause begins with a known action verb and the existing model-independent base
policy can independently produce a nonterminal action for every clause.
Unsupported or ambiguous partitions remain unsplit.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_web_app_policy_overlay_v1 import decide as base_decide
from canonical.runtime.osworld_v21_workflow_policy_v1 import split_explicit_subgoals
from canonical.runtime.osworld_v21_workflow_policy_v2 import decide as workflow_v2_decide

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_WORKFLOW_POLICY_V3"
MAX_SEMANTIC_CLAUSES=6
_ACTION_START=re.compile(
    r"^\s*(?:please\s+)?(?:check|review|read|inspect|look\s+up|lookup|find|identify|"
    r"retrieve|list|show|open|navigate|go|click|press|select|choose|fill|enter|type|"
    r"set|change|update|edit|create|delete|remove|submit|send|reply|add|save|export|"
    r"move|rename|install|uninstall|disable|enable|write|replace|sort|merge|duplicate|"
    r"pause|play|switch|insert|format|freeze|copy|autofit|align|position)\b",
    re.I,
)

def _mask_quoted(text:str)->str:
    out=list(text); closing=None; escape=False
    pairs={'"':'"',"'":"'","“":"”"}
    for i,ch in enumerate(text):
        if escape:
            out[i]=" "; escape=False; continue
        if closing is None:
            if ch in pairs:
                closing=pairs[ch]; out[i]=" "
        else:
            out[i]=" "
            if ch=="\\":
                escape=True
            elif ch==closing:
                closing=None
    return "".join(out)

def _actionable(out:Any)->bool:
    if not isinstance(out,Mapping):
        return False
    receipt=out.get("_policy_receipt")
    if isinstance(receipt,Mapping):
        if receipt.get("external_model_dependency") is True or receipt.get("task_specific_policy_data") is True:
            return False
    actions=out.get("actions")
    if not isinstance(actions,list) or len(actions)!=1 or not isinstance(actions[0],Mapping):
        return False
    t=str(actions[0].get("type") or "").strip().upper()
    return t not in {"","WAIT","DONE","FAIL"}

def split_capability_supported_subgoals(state:Mapping[str,Any],instruction:str)->list[str]:
    explicit=split_explicit_subgoals(instruction)
    if len(explicit)>1:
        return explicit
    masked=_mask_quoted(instruction)
    spans=[m.span() for m in re.finditer(r"\b(?:and|also|as\s+well\s+as)\b",masked,re.I)]
    if not spans:
        return [instruction]
    parts=[]; start=0
    for a,b in spans:
        piece=instruction[start:a].strip(" ,;")
        if piece: parts.append(piece)
        start=b
    tail=instruction[start:].strip(" ,;")
    if tail: parts.append(tail)
    if not 2<=len(parts)<=MAX_SEMANTIC_CLAUSES:
        return [instruction]
    if any(_ACTION_START.match(p) is None for p in parts):
        return [instruction]

    probe_base=dict(state)
    probe_base["history"]=[]
    for part in parts:
        probe=dict(probe_base); probe["instruction"]=part
        try:
            out=base_decide(probe)
        except Exception:
            return [instruction]
        if not _actionable(out):
            return [instruction]
    return parts

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    if not isinstance(state,Mapping):
        raise ValueError("STATE_NOT_OBJECT")
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip():
        return workflow_v2_decide(state)
    parts=split_capability_supported_subgoals(state,instruction)
    if len(parts)<=1:
        return workflow_v2_decide(state)

    transformed="; ".join(parts)
    local=dict(state); local["instruction"]=transformed
    out=workflow_v2_decide(local)
    if not isinstance(out,Mapping):
        raise ValueError("WORKFLOW_V2_OUTPUT_NOT_OBJECT")
    result=dict(out)
    receipt=result.get("_policy_receipt")
    if isinstance(receipt,Mapping):
        r=dict(receipt)
        r["semantic_decomposition"]={
            "schema":SCHEMA,
            "mode":"CAPABILITY_GROUNDED_ALL_CLAUSES_EXECUTABLE",
            "original_sha256":hashlib.sha256(instruction.encode()).hexdigest(),
            "transformed_sha256":hashlib.sha256(transformed.encode()).hexdigest(),
            "clause_count":len(parts),
            "clauses":[hashlib.sha256(p.encode()).hexdigest() for p in parts],
            "task_specific_policy_data":False,
            "external_model_dependency":False,
        }
        result["_policy_receipt"]=r
    return result
