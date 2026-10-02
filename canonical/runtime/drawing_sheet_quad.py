"""Bounded deterministic planar drawing-sheet quadrilateral detection.

This component detects a single dominant convex four-corner sheet boundary from
clean high-contrast imagery. It is not a general document detector and has no
semantic authority.
"""
from __future__ import annotations

from typing import Any
import cv2
import numpy as np

SCHEMA = "BRAIN_DRAWING_SHEET_QUAD_V1"


def _order_quad_tl_tr_br_bl(points: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    pts=np.asarray(points,dtype=np.float32).reshape(4,2)
    sums=pts.sum(axis=1)
    diffs=np.diff(pts,axis=1).reshape(-1)
    ordered=np.asarray([
        pts[int(np.argmin(sums))],
        pts[int(np.argmin(diffs))],
        pts[int(np.argmax(sums))],
        pts[int(np.argmax(diffs))],
    ],dtype=np.float32)
    if len({(float(x),float(y)) for x,y in ordered}) != 4:
        raise ValueError("ambiguous quadrilateral ordering")
    return ordered


def detect_planar_sheet_quad(
    image: np.ndarray[Any, Any],
    *,
    min_area_fraction: float = 0.20,
    approx_epsilon_fraction: float = 0.02,
) -> dict[str, Any]:
    if not isinstance(image,np.ndarray) or image.ndim not in (2,3):
        raise ValueError("image must be a 2D or 3D numpy array")
    if not (0.01 <= min_area_fraction < 1.0):
        raise ValueError("min_area_fraction must be in [0.01,1)")
    if not (0.001 <= approx_epsilon_fraction <= 0.10):
        raise ValueError("approx_epsilon_fraction must be in [0.001,0.10]")

    gray=image if image.ndim==2 else cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    if gray.dtype != np.uint8:
        gray=cv2.normalize(gray,None,0,255,cv2.NORM_MINMAX).astype(np.uint8)

    # Canny is polarity-agnostic and avoids assuming the sheet is lighter or
    # darker than its surroundings.
    blurred=cv2.GaussianBlur(gray,(5,5),0)
    edges=cv2.Canny(blurred,50,150)
    edges=cv2.dilate(edges,np.ones((3,3),np.uint8),iterations=1)
    contours,_=cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    image_area=float(gray.shape[0]*gray.shape[1])
    candidates=[]
    for contour in contours:
        area=abs(float(cv2.contourArea(contour)))
        if area/image_area < min_area_fraction:
            continue
        perimeter=float(cv2.arcLength(contour,True))
        if perimeter <= 0:
            continue
        approx=cv2.approxPolyDP(contour,approx_epsilon_fraction*perimeter,True)
        if len(approx)!=4 or not cv2.isContourConvex(approx):
            continue
        candidates.append((area,approx.reshape(4,2)))

    if not candidates:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "error":"NO_DOMINANT_CONVEX_QUAD",
            "terminal_authority":False,
        }

    candidates.sort(key=lambda x:x[0],reverse=True)
    # Two similarly large sheet-like quads are ambiguous. Do not guess.
    if len(candidates)>1 and candidates[1][0] >= candidates[0][0]*0.85:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "error":"AMBIGUOUS_MULTIPLE_QUADS",
            "terminal_authority":False,
        }

    area,pts=candidates[0]
    try:
        ordered=_order_quad_tl_tr_br_bl(pts)
    except ValueError:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "error":"AMBIGUOUS_QUAD_ORDER",
            "terminal_authority":False,
        }

    return {
        "schema":SCHEMA,
        "status":"DETECTED",
        "quad":ordered,
        "area_fraction":area/image_area,
        "candidate_count":len(candidates),
        "terminal_authority":False,
        "scope":"SINGLE_DOMINANT_CLEAN_HIGH_CONTRAST_CONVEX_PLANAR_SHEET_BOUNDARY",
    }
