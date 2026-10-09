"""Sound decision-relative irrelevance test for partial effect semantics."""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PARTIAL_EFFECT_QUERY_IRRELEVANCE_V1"

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _exact(component:Mapping[str,Any]|None)->tuple[bool,Any]:
    if not isinstance(component,Mapping):
        return False,None
    if str(component.get("kind") or "").startswith("EXACT"):
        return True,deepcopy(component.get("value"))
    return False,None

def prove_inapplicable(
    effect_state:Mapping[str,Any],
    query:Mapping[str,Any],
)->dict[str,Any]:
    try:
        if not isinstance(effect_state,Mapping):
            raise ValueError("EFFECT_STATE_NOT_OBJECT")
        if not isinstance(query,Mapping) or set(query)!={"target_id","as_of","context"}:
            raise ValueError("QUERY_INVALID")
        components=effect_state.get("components")
        if not isinstance(components,Mapping):
            raise ValueError("COMPONENTS_MISSING")
        as_of=date.fromisoformat(str(query["as_of"]))
        context=query["context"]
        if not isinstance(context,Mapping):
            raise ValueError("QUERY_CONTEXT_INVALID")

        ok,start=_exact(components.get("valid_from"))
        if ok and start is not None and as_of < date.fromisoformat(str(start)):
            return {
                "schema":SCHEMA,"pass":True,
                "status":"PASS__PROVED_INAPPLICABLE_VALID_FROM",
                "reason":{"kind":"VALID_FROM_AFTER_QUERY","valid_from":start,"as_of":query["as_of"]},
                "semantic_truth_authority":False,"terminal_authority":False,
            }

        ok,end=_exact(components.get("valid_until"))
        if ok and end is not None and as_of >= date.fromisoformat(str(end)):
            return {
                "schema":SCHEMA,"pass":True,
                "status":"PASS__PROVED_INAPPLICABLE_VALID_UNTIL",
                "reason":{"kind":"VALID_UNTIL_NOT_AFTER_QUERY","valid_until":end,"as_of":query["as_of"]},
                "semantic_truth_authority":False,"terminal_authority":False,
            }

        ok,conditions=_exact(components.get("conditions"))
        if ok:
            if not isinstance(conditions,Mapping):
                raise ValueError("EXACT_CONDITIONS_NOT_OBJECT")
            for key,expected in conditions.items():
                if key not in context or _canon(context[key])!=_canon(expected):
                    return {
                        "schema":SCHEMA,"pass":True,
                        "status":"PASS__PROVED_INAPPLICABLE_CONDITION",
                        "reason":{
                            "kind":"CONDITION_MISMATCH",
                            "condition_key":key,
                            "expected":deepcopy(expected),
                            "observed":deepcopy(context.get(key)),
                            "context_key_present":key in context,
                        },
                        "semantic_truth_authority":False,"terminal_authority":False,
                    }

        return {
            "schema":SCHEMA,"pass":False,
            "status":"OPEN__PARTIAL_EFFECT_MAY_APPLY",
            "reason":None,
            "semantic_truth_authority":False,"terminal_authority":False,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,"terminal_authority":False,
        }
