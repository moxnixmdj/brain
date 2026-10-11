"""Deterministic media routing for the model-independent OSWorld subject."""
from __future__ import annotations
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_MEDIA_POLICY_OVERLAY_V1"

def _history(state:Mapping[str,Any]):
    raw=state.get("history")
    return [x for x in raw if isinstance(x,Mapping)] if isinstance(raw,list) else []

def _paths(text:str):
    hits=re.findall(r"/home/oai/[A-Za-z0-9_./-]+",text)
    media=(".mp4",".mov",".mkv",".webm",".avi",".wav",".mp3",".m4a",".png",".jpg",".jpeg",".bmp",".gif",".webp")
    out=[]
    for x in hits:
        x=x.rstrip(".,;)")
        if x.casefold().endswith(media) and x not in out: out.append(x)
    return out

def _emit(op,args,response):
    return {
      "response":response,
      "actions":[{"type":"MEDIA_OP","operation":op,"args":dict(args)}],
      "_policy_receipt":{
        "schema":SCHEMA,"route":"GENERIC_MEDIA_TRANSFORMATION","operation":op,
        "task_specific_policy_data":False,"external_model_dependency":False,
      },
    }

def _finish(state,candidate):
    action=candidate["actions"][0]
    for row in reversed(_history(state)):
        sub=row.get("submitted_media_operation"); res=row.get("media_result")
        if not isinstance(sub,Mapping) or not isinstance(res,Mapping): continue
        if res.get("ok") is True and action.get("operation")==sub.get("operation") and dict(action.get("args") or {})==dict(sub.get("args") or {}):
            return {
              "response":"media transformation postcondition verified",
              "actions":[{"type":"DONE"}],
              "_policy_receipt":{
                "schema":SCHEMA,"route":"GENERIC_MEDIA_TRANSFORMATION_VERIFIED",
                "operation":action.get("operation"),"task_specific_policy_data":False,
                "external_model_dependency":False,
              },
            }
        break
    return candidate

def route_media(state:Mapping[str,Any]):
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip(): return None
    low=instruction.casefold(); paths=_paths(instruction)
    if len(paths)==1 and any(x in low for x in ("probe","inspect","metadata","duration","resolution","codec")):
        return _finish(state,_emit("PROBE",{"input":paths[0]},"inspect media metadata"))
    if len(paths)!=2: return None
    src,dst=paths
    nums=[float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b",instruction)]

    if ("trim" in low or "cut" in low) and " from " in low and " to " in low and len(nums)>=2:
        return _finish(state,_emit("TRIM",{"input":src,"output":dst,"start_s":nums[0],"end_s":nums[1]},"trim media interval"))

    size=re.search(r"(\d{1,4})\s*[xX]\s*(\d{1,4})",instruction)
    if ("resize" in low or "scale" in low) and size:
        return _finish(state,_emit("RESIZE",{"input":src,"output":dst,"width":int(size.group(1)),"height":int(size.group(2))},"resize media"))

    if "rotate" in low:
        deg=next((x for x in (90,180,270) if str(x) in instruction),None)
        if deg is not None:
            return _finish(state,_emit("ROTATE",{"input":src,"output":dst,"degrees":deg},"rotate media"))

    if "extract" in low and "audio" in low:
        return _finish(state,_emit("EXTRACT_AUDIO",{"input":src,"output":dst},"extract audio"))

    if "volume" in low and nums:
        factor=nums[-1]/100.0 if "%" in instruction else nums[-1]
        return _finish(state,_emit("SET_VOLUME",{"input":src,"output":dst,"factor":factor},"adjust media volume"))
    return None
