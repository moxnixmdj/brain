"""Capability-first workflow coordinator V8 with deterministic visual fallback.

Preserves V9 relational dataflow and safe semantic decomposition while swapping
only the base policy for the V10 unified code-aware policy.
"""
from __future__ import annotations
import hashlib
import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_receipt_dataflow_v3 import materialize_explicit_references
from canonical.runtime.osworld_v21_workflow_policy_v1 import split_explicit_subgoals
from canonical.runtime.osworld_v21_unified_policy_v13 import decide as base_decide

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_WORKFLOW_POLICY_V8"
MAX_SEMANTIC_CLAUSES=6
_OBSERVE=re.compile(r"\b(check|review|read|inspect|look up|lookup|find|identify|retrieve|list|show|see|examine)\b",re.I)
_MUTATE=re.compile(r"\b(send|reply|update|change|edit|create|delete|remove|submit|post|like|add|schedule|book|purchase|buy|pay|attach|upload|download|fill|set|write|replace|install|uninstall|disable|enable|export|save|move|rename|run|execute|compile)\b",re.I)
_ACTION_START=re.compile(
 r"^\s*(?:please\s+)?(?:check|review|read|inspect|look\s+up|lookup|find|identify|retrieve|list|show|open|navigate|go|click|press|select|choose|fill|enter|type|set|change|update|edit|create|delete|remove|submit|send|reply|add|save|export|move|rename|install|uninstall|disable|enable|write|replace|sort|merge|duplicate|pause|play|switch|insert|format|freeze|copy|autofit|align|position|run|execute|compile)\b",
 re.I,
)

def _sha(text:str)->str:
    return hashlib.sha256(text.encode()).hexdigest()

def _history(state:Mapping[str,Any]):
    raw=state.get("history")
    return [x for x in raw if isinstance(x,Mapping)] if isinstance(raw,list) else []

def _receipt(row:Mapping[str,Any]):
    r=row.get("policy_receipt")
    return r if isinstance(r,Mapping) and r.get("schema")==SCHEMA and isinstance(r.get("clause_index"),int) else None

def _current_index(state:Mapping[str,Any],workflow_sha:str,count:int)->int:
    for row in reversed(_history(state)):
        r=_receipt(row)
        if r is None or r.get("workflow_sha256")!=workflow_sha: continue
        i=r.get("clause_index")
        if isinstance(i,int) and not isinstance(i,bool) and 0<=i<count: return i
    return 0

def _rows(state:Mapping[str,Any],workflow_sha:str,*,clause_index=None,before=None):
    out=[]
    for row in _history(state):
        r=_receipt(row)
        if r is None or r.get("workflow_sha256")!=workflow_sha: continue
        i=r.get("clause_index")
        if clause_index is not None and i!=clause_index: continue
        if before is not None and (not isinstance(i,int) or i>=before): continue
        out.append(row)
    return out

def _observation_complete(instruction:str,rows:list[Mapping[str,Any]])->bool:
    if not _OBSERVE.search(instruction) or _MUTATE.search(instruction): return False
    for row in rows:
        for key in ("web_app_result","browser_result","app_result","guest_result","code_result"):
            result=row.get(key)
            if isinstance(result,Mapping) and result.get("ok") is True: return True
    return False

def _done(out:Mapping[str,Any])->bool:
    a=out.get("actions")
    return isinstance(a,list) and len(a)==1 and isinstance(a[0],Mapping) and str(a[0].get("type") or "").upper()=="DONE"

def _actionable(out:Any)->bool:
    if not isinstance(out,Mapping): return False
    receipt=out.get("_policy_receipt")
    if isinstance(receipt,Mapping) and (receipt.get("external_model_dependency") is True or receipt.get("task_specific_policy_data") is True):
        return False
    a=out.get("actions")
    if not isinstance(a,list) or len(a)!=1 or not isinstance(a[0],Mapping): return False
    return str(a[0].get("type") or "").upper() not in {"","WAIT","DONE","FAIL"}

def _mask_quoted(text:str)->str:
    out=list(text); closing=None; escape=False
    pairs={'"':'"',"'":"'","“":"”"}
    for i,ch in enumerate(text):
        if escape: out[i]=" "; escape=False; continue
        if closing is None:
            if ch in pairs: closing=pairs[ch]; out[i]=" "
        else:
            out[i]=" "
            if ch=="\\": escape=True
            elif ch==closing: closing=None
    return "".join(out)

def _split(state:Mapping[str,Any],instruction:str)->list[str]:
    explicit=split_explicit_subgoals(instruction)
    if len(explicit)>1: return explicit
    masked=_mask_quoted(instruction)
    spans=[m.span() for m in re.finditer(r"\b(?:and|also|as\s+well\s+as)\b",masked,re.I)]
    if not spans: return [instruction]
    parts=[]; start=0
    for a,b in spans:
        piece=instruction[start:a].strip(" ,;")
        if piece: parts.append(piece)
        start=b
    tail=instruction[start:].strip(" ,;")
    if tail: parts.append(tail)
    if not 2<=len(parts)<=MAX_SEMANTIC_CLAUSES or any(_ACTION_START.match(x) is None for x in parts):
        return [instruction]
    probe_base=dict(state); probe_base["history"]=[]
    for part in parts:
        probe=dict(probe_base); probe["instruction"]=part
        try: out=base_decide(probe)
        except Exception: return [instruction]
        if not _actionable(out): return [instruction]
    return parts

def _wrap(out:Mapping[str,Any],*,workflow_sha:str,clauses:list[str],clause_index:int,dataflow=None):
    result=dict(out)
    base=result.get("_policy_receipt")
    receipt={
      "schema":SCHEMA,"route":"V13_VISUAL_FALLBACK_ORDERED_WORKFLOW_WITH_RELATIONAL_DATAFLOW",
      "workflow_sha256":workflow_sha,"clause_index":clause_index,"clause_count":len(clauses),
      "clause_sha256":_sha(clauses[clause_index]),"task_specific_policy_data":False,
      "external_model_dependency":False,
    }
    if isinstance(base,Mapping): receipt["base_policy_receipt"]=dict(base)
    if isinstance(dataflow,Mapping): receipt["dataflow"]=dict(dataflow)
    result["_policy_receipt"]=receipt
    return result

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    if not isinstance(state,Mapping): raise ValueError("STATE_NOT_OBJECT")
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip(): return base_decide(state)
    clauses=_split(state,instruction)
    if len(clauses)<=1: return base_decide(state)

    workflow_sha=_sha("\n".join(clauses))
    index=_current_index(state,workflow_sha,len(clauses))
    for _ in range(len(clauses)):
        local_rows=_rows(state,workflow_sha,clause_index=index)
        if index<len(clauses)-1 and _observation_complete(clauses[index],local_rows):
            index+=1; continue
        prior=_rows(state,workflow_sha,before=index)
        flow=materialize_explicit_references(clauses[index],prior)
        if flow.get("pass") is not True:
            return _wrap({"response":"cross-clause reference unresolved","actions":[{"type":"WAIT"}]},workflow_sha=workflow_sha,clauses=clauses,clause_index=index,dataflow=flow)
        local=dict(state); local["instruction"]=str(flow.get("text") or clauses[index]); local["history"]=local_rows
        out=base_decide(local)
        if not isinstance(out,Mapping): raise ValueError("BASE_POLICY_OUTPUT_NOT_OBJECT")
        if _done(out) and index<len(clauses)-1:
            index+=1; continue
        return _wrap(out,workflow_sha=workflow_sha,clauses=clauses,clause_index=index,dataflow=flow)
    raise RuntimeError("WORKFLOW_ADVANCE_LOOP_EXHAUSTED")
