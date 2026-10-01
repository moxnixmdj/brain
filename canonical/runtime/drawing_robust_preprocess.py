"""Bounded degraded-raster preprocessing for technical drawings.

Deterministic normalization for uneven illumination, mild blur/noise, and low contrast.
No semantic authority; fail closed on unreadable/blank surfaces.
"""
from __future__ import annotations
from typing import Any
import cv2
import numpy as np

SCHEMA="BRAIN_DRAWING_ROBUST_PREPROCESS_V1"

def robust_ink_mask(image: np.ndarray, *, clahe_clip:float=2.0, tile:int=8) -> dict[str,Any]:
    if not isinstance(image,np.ndarray) or image.ndim not in (2,3):
        raise ValueError("image must be 2D/3D numpy array")
    if clahe_clip<=0 or tile<2: raise ValueError("invalid CLAHE parameters")
    gray=image if image.ndim==2 else cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    gray=gray.astype(np.uint8,copy=False)
    if float(gray.std()) < 1.0:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NEAR_UNIFORM_IMAGE","terminal_authority":False}
    den=cv2.fastNlMeansDenoising(gray,None,7,7,21)
    clahe=cv2.createCLAHE(clipLimit=clahe_clip,tileGridSize=(tile,tile))
    eq=clahe.apply(den)
    bg=cv2.morphologyEx(eq,cv2.MORPH_CLOSE,np.ones((31,31),np.uint8))
    norm=cv2.divide(eq,bg,scale=255)
    mask=cv2.adaptiveThreshold(norm,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,11)
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
    ink_fraction=float((mask>0).mean())
    if ink_fraction < 0.0005 or ink_fraction > 0.60:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"INK_FRACTION_OUT_OF_SCOPE","ink_fraction":ink_fraction,"terminal_authority":False}
    return {"schema":SCHEMA,"status":"NORMALIZED","normalized_gray":norm,"normalized_mask":(mask>0).astype(np.uint8),
            "ink_fraction":ink_fraction,"terminal_authority":False,
            "scope":"UNEVEN_ILLUMINATION_MILD_NOISE_LOW_CONTRAST_RASTER_NORMALIZATION"}
