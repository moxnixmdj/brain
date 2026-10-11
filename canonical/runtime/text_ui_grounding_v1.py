from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_TEXT_UI_GROUNDING_V1"

class TextGroundingError(ValueError):
    pass

def _norm(value:Any)->str:
    if not isinstance(value,str):
        raise TextGroundingError("TEXT_NOT_STRING")
    s=unicodedata.normalize("NFKC",value).casefold()
    s=" ".join(s.split())
    return s

def _box(raw:Any,width:int,height:int)->dict[str,int]:
    if not isinstance(raw,Mapping):
        raise TextGroundingError("BOX_NOT_OBJECT")
    vals=[]
    for k in ("x0","y0","x1_exclusive","y1_exclusive"):
        v=raw.get(k)
        if isinstance(v,bool) or not isinstance(v,int):
            raise TextGroundingError("BOX_COORD_INVALID:"+k)
        vals.append(v)
    x0,y0,x1,y1=vals
    if x0<0 or y0<0 or x1<=x0 or y1<=y0 or x1>width or y1>height:
        raise TextGroundingError("BOX_OUT_OF_BOUNDS")
    return {"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1}

def _sha(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def compile_candidates(positioned:Mapping[str,Any],target:Any,*,match_mode:str="exact")->dict[str,Any]:
    if not isinstance(positioned,Mapping):
        raise TextGroundingError("POSITIONED_OCR_REQUIRED")
    w=positioned.get("page_width")
    h=positioned.get("page_height")
    if not isinstance(w,int) or isinstance(w,bool) or w<=0 or not isinstance(h,int) or isinstance(h,bool) or h<=0:
        extent=positioned.get("page_extent")
        if isinstance(extent,Mapping):
            w,h=extent.get("width"),extent.get("height")
    if not isinstance(w,int) or isinstance(w,bool) or w<=0 or not isinstance(h,int) or isinstance(h,bool) or h<=0:
        raise TextGroundingError("PAGE_EXTENT_INVALID")
    rows=positioned.get("text_items")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        raise TextGroundingError("TEXT_ITEMS_INVALID")
    q=_norm(target)
    if not q:
        raise TextGroundingError("TARGET_EMPTY")
    if match_mode not in {"exact","token"}:
        raise TextGroundingError("MATCH_MODE_INVALID")

    candidates=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise TextGroundingError("TEXT_ITEM_NOT_OBJECT")
        text=row.get("text")
        if not isinstance(text,str):
            raise TextGroundingError("TEXT_ITEM_TEXT_INVALID")
        n=_norm(text)
        matched = n==q
        if match_mode=="token":
            matched = q in re.findall(r"[\w.+:/-]+",n)
        if not matched:
            continue
        b=_box(row.get("box"),w,h)
        candidates.append({
            "candidate_id":str(row.get("source_id") or f"text_item:{i}"),
            "observed_text":text,
            "normalized_text":n,
            "box":b,
            "confidence":row.get("confidence",row.get("confidence_mean")),
            "center":{"x":(b["x0"]+b["x1_exclusive"]-1)//2,"y":(b["y0"]+b["y1_exclusive"]-1)//2},
        })
    material={"target":q,"match_mode":match_mode,"page_width":w,"page_height":h,"candidates":candidates}
    return {
        "schema":SCHEMA,
        "status":"COMPILED",
        "target_normalized":q,
        "match_mode":match_mode,
        "page_width":w,
        "page_height":h,
        "candidate_count":len(candidates),
        "candidates":candidates,
        "candidate_set_sha256":_sha(material),
        "semantic_truth_authority":False,
        "execution_authority":False,
        "terminal_authority":False,
    }

def resolve_unique_text_target(positioned:Mapping[str,Any],target:Any,*,match_mode:str="exact")->dict[str,Any]:
    compiled=compile_candidates(positioned,target,match_mode=match_mode)
    rows=compiled["candidates"]
    if not rows:
        return {**compiled,
            "status":"OPEN__TEXT_TARGET_NOT_OBSERVED",
            "pass":False,
            "action":"ACQUIRE_STRONGER_VISUAL_OBSERVATION_OR_DIFFERENT_GROUNDING_ROUTE",
            "additional_information_required":True,
        }
    if len(rows)>1:
        return {**compiled,
            "status":"OPEN__TEXT_TARGET_AMBIGUOUS",
            "pass":False,
            "action":"ACQUIRE_MINIMUM_SPATIAL_OR_CONTEXTUAL_DISCRIMINATOR",
            "additional_information_required":True,
            "unresolved_candidate_ids":[r["candidate_id"] for r in rows],
        }
    row=rows[0]
    return {**compiled,
        "status":"PASS__UNIQUE_TEXT_TARGET_GROUNDED",
        "pass":True,
        "selected_candidate_id":row["candidate_id"],
        "selected_box":row["box"],
        "click_point":row["center"],
        "grounding_scope":"UNIQUE_POSITIONED_OCR_TEXT_MATCH_ONLY",
        "semantic_truth_authority":False,
        "execution_authority":False,
        "terminal_authority":False,
    }

def compile_click_action(positioned:Mapping[str,Any],target:Any,*,match_mode:str="exact",button:str="left")->dict[str,Any]:
    if button not in {"left","right"}:
        raise TextGroundingError("BUTTON_INVALID")
    result=resolve_unique_text_target(positioned,target,match_mode=match_mode)
    if result.get("pass") is not True:
        return {**result,"typed_action":None}
    point=result["click_point"]
    return {**result,
        "typed_action":{"type":"click","x":point["x"],"y":point["y"],"button":button},
        "execution_authority":False,
    }
