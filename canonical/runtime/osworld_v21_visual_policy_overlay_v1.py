"""Fail-closed policy overlay for explicit non-text visual targets."""
from __future__ import annotations
import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_visual_region_grounding_v1 import ground_visual_region

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_VISUAL_POLICY_OVERLAY_V1"
_COLORS=("red","green","blue","yellow","orange","purple","pink","black","white","gray","grey")
_SHAPES=("circle","square","rectangle")
_SPATIAL=("top-left","top-right","bottom-left","bottom-right","left","right","top","bottom","center")

def _target(instruction:str):
    if re.search(r"\b(click|press|select|choose)\b",instruction,re.I) is None: return None
    low=instruction.casefold()
    color=next((x for x in _COLORS if re.search(r"\b"+re.escape(x)+r"\b",low)),None)
    if color is None: return None
    shape=next((x for x in _SHAPES if re.search(r"\b"+x+r"\b",low)),None)
    spatial=None
    normalized=low.replace("upper left","top-left").replace("upper right","top-right").replace("lower left","bottom-left").replace("lower right","bottom-right")
    for value in _SPATIAL:
        if value in normalized:
            spatial=value; break
    return {"color":color,"shape":shape,"spatial":spatial}

def _visual_receipt(value:Any):
    if not isinstance(value,Mapping): return None
    if value.get("schema")==SCHEMA: return value
    for key in ("base_policy_receipt","base_receipt"):
        nested=_visual_receipt(value.get(key))
        if nested is not None: return nested
    return None

def _latest(state:Mapping[str,Any],target:Mapping[str,Any]):
    hist=state.get("history")
    if not isinstance(hist,list): return None,None
    for row in reversed(hist):
        if not isinstance(row,Mapping): continue
        rec=_visual_receipt(row.get("policy_receipt"))
        if isinstance(rec,Mapping) and rec.get("target")==dict(target):
            return row,rec
    return None,None

def route_visual(state:Mapping[str,Any]):
    instruction=state.get("instruction")
    screenshot=state.get("screenshot_bytes")
    if not isinstance(instruction,str) or not isinstance(screenshot,(bytes,bytearray)): return None
    target=_target(instruction)
    if target is None: return None

    prior,prior_receipt=_latest(state,target)
    current_sha=str(state.get("screenshot_sha256") or "")
    if isinstance(prior,Mapping):
        prior_sha=str(prior.get("screenshot_sha256") or "")
        if prior_sha and prior_sha==current_sha:
            return {
              "response":"visual action produced no observable transition",
              "actions":[{"type":"WAIT"}],
              "_policy_receipt":{
                "schema":SCHEMA,"route":"VISUAL_NO_PROGRESS_FAIL_CLOSED",
                "target":dict(target),"external_model_dependency":False,
                "task_specific_policy_data":False,
              },
            }
        if prior_sha and current_sha and prior_sha!=current_sha:
            return {
              "response":"explicit visual click transition observed",
              "actions":[{"type":"DONE"}],
              "_policy_receipt":{
                "schema":SCHEMA,"route":"VISUAL_CLICK_TRANSITION_VERIFIED",
                "target":dict(target),"external_model_dependency":False,
                "task_specific_policy_data":False,
              },
            }

    out=ground_visual_region(bytes(screenshot),**target)
    if out.get("pass") is not True:
        return {
          "response":"visual target not uniquely grounded",
          "actions":[{"type":"WAIT"}],
          "_policy_receipt":{
            "schema":SCHEMA,"route":"VISUAL_GROUNDING_UNRESOLVED",
            "target":dict(target),"reason":out.get("reason"),
            "candidate_count":out.get("candidate_count"),
            "external_model_dependency":False,"task_specific_policy_data":False,
          },
        }
    point=out["click_point"]
    return {
      "response":"click unique explicit visual region",
      "actions":[{"type":"CLICK","x":point["x"],"y":point["y"]}],
      "_policy_receipt":{
        "schema":SCHEMA,"route":"EXPLICIT_VISUAL_REGION_CLICK",
        "target":dict(target),"source_sha256":out.get("source_sha256"),
        "selected":out.get("selected"),"external_model_dependency":False,
        "task_specific_policy_data":False,
      },
    }
