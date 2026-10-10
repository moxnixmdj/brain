"""Ambiguity-safe binary symbol template matcher.

Reference templates are external/JIT knowledge. Matching capability is local and generic.
"""
from __future__ import annotations
from typing import Any, Mapping
import cv2, numpy as np

SCHEMA="BRAIN_VISUAL_SYMBOL_TEMPLATE_MATCHER_V1"

def match_symbol(image:np.ndarray,templates:Mapping[str,np.ndarray],*,min_score:float=0.72,min_margin:float=0.08)->dict[str,Any]:
    if not isinstance(image,np.ndarray) or image.ndim!=2:
        raise ValueError("image must be grayscale 2D")
    if not templates:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_TEMPLATES"}
    scores=[]
    src=cv2.threshold(image,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)[1]
    for sid,t in templates.items():
        if not isinstance(sid,str) or not sid or not isinstance(t,np.ndarray) or t.ndim!=2:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"INVALID_TEMPLATE"}
        th,tw=t.shape; ih,iw=src.shape
        if th>ih or tw>iw: continue
        ref=cv2.threshold(t,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)[1]
        res=cv2.matchTemplate(src,ref,cv2.TM_CCOEFF_NORMED)
        score=float(np.max(res)); scores.append((score,sid))
    if not scores:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_SIZE_COMPATIBLE_TEMPLATES"}
    scores.sort(reverse=True)
    best_score,best=scores[0]; second=scores[1][0] if len(scores)>1 else -1.0
    if best_score<min_score:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"LOW_MATCH_SCORE","best_score":best_score}
    if best_score-second<min_margin:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_MATCH","best_score":best_score,"second_score":second}
    return {"schema":SCHEMA,"status":"MATCHED","symbol_id":best,"score":best_score,
            "margin":best_score-second,"terminal_authority":False,
            "scope":"JIT_TEMPLATE_MATCHING_WITH_SCORE_AND_AMBIGUITY_GATES"}
