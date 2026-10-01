"""Bounded perspective rectification for photographed/scanned technical drawings.

Owns only a four-corner planar page/document homography. It does not claim arbitrary
local dewarping, folded paper correction, or semantic view registration.
"""
from __future__ import annotations
from typing import Any, Sequence
import cv2
import numpy as np

SCHEMA="BRAIN_DRAWING_PERSPECTIVE_RECTIFICATION_V1"

def _order_quad(points: np.ndarray) -> np.ndarray:
    pts=np.asarray(points,dtype=np.float32).reshape(4,2)
    s=pts.sum(axis=1); d=np.diff(pts,axis=1).reshape(-1)
    return np.array([pts[np.argmin(s)],pts[np.argmin(d)],pts[np.argmax(s)],pts[np.argmax(d)]],dtype=np.float32)

def rectify_from_quad(image: np.ndarray, quad: Sequence[Sequence[float]], *, max_output_side:int=4096) -> dict[str,Any]:
    if not isinstance(image,np.ndarray) or image.ndim not in (2,3):
        raise ValueError("image must be 2D/3D numpy array")
    if max_output_side<=0: raise ValueError("max_output_side must be positive")
    try: src=_order_quad(np.asarray(quad,dtype=np.float32))
    except Exception:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"INVALID_QUAD","terminal_authority":False}
    area=abs(float(cv2.contourArea(src.reshape(-1,1,2))))
    h,w=image.shape[:2]
    if area < max(100.0,0.05*h*w):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"QUAD_TOO_SMALL_OR_DEGENERATE","terminal_authority":False}
    tl,tr,br,bl=src
    out_w=int(round(max(np.linalg.norm(tr-tl),np.linalg.norm(br-bl))))
    out_h=int(round(max(np.linalg.norm(bl-tl),np.linalg.norm(br-tr))))
    if min(out_w,out_h)<16 or max(out_w,out_h)>max_output_side:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"OUTPUT_GEOMETRY_OUT_OF_SCOPE","terminal_authority":False}
    dst=np.array([[0,0],[out_w-1,0],[out_w-1,out_h-1],[0,out_h-1]],dtype=np.float32)
    H=cv2.getPerspectiveTransform(src,dst)
    if not np.isfinite(H).all():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"HOMOGRAPHY_NONFINITE","terminal_authority":False}
    border=255 if image.ndim==2 else tuple([255]*image.shape[2])
    warped=cv2.warpPerspective(image,H,(out_w,out_h),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=border)
    return {"schema":SCHEMA,"status":"RECTIFIED","homography":H.tolist(),"ordered_quad":src.tolist(),
            "shape":[out_h,out_w],"rectified_image":warped,"terminal_authority":False,
            "scope":"SINGLE_PLANAR_FOUR_CORNER_PROJECTIVE_RECTIFICATION"}

def detect_page_quad(image: np.ndarray, *, min_area_fraction:float=0.25) -> dict[str,Any]:
    if not isinstance(image,np.ndarray) or image.ndim not in (2,3):
        raise ValueError("image must be 2D/3D numpy array")
    if not (0<min_area_fraction<1): raise ValueError("min_area_fraction must be in (0,1)")
    gray=image if image.ndim==2 else cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    blur=cv2.GaussianBlur(gray,(5,5),0)
    edges=cv2.Canny(blur,50,150)
    cnts,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    h,w=gray.shape[:2]; min_area=min_area_fraction*h*w
    candidates=[]
    for c in cnts:
        area=cv2.contourArea(c)
        if area<min_area: continue
        peri=cv2.arcLength(c,True)
        approx=cv2.approxPolyDP(c,0.02*peri,True)
        if len(approx)==4 and cv2.isContourConvex(approx):
            candidates.append((area,approx.reshape(4,2).astype(np.float32)))
    if not candidates:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_UNIQUE_PAGE_QUAD","terminal_authority":False}
    candidates.sort(key=lambda x:x[0],reverse=True)
    if len(candidates)>1 and candidates[1][0] >= 0.9*candidates[0][0]:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_PAGE_QUAD","terminal_authority":False}
    return {"schema":SCHEMA,"status":"DETECTED","quad":_order_quad(candidates[0][1]).tolist(),
            "area":float(candidates[0][0]),"terminal_authority":False}
