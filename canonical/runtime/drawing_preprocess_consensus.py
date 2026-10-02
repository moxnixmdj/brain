"""Consensus preprocessing for degraded technical drawing rasters.

Multiple deterministic preprocessing routes independently propose an ink mask.
A result is admitted only when a unique largest pairwise-consistent cluster exists.
This extends M1A beyond pristine high-contrast images without allowing one fragile
thresholding heuristic to become semantic authority.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

import cv2
import numpy as np

from canonical.runtime.raw_drawing_primitives import normalize_ink_mask

SCHEMA="BRAIN_DRAWING_PREPROCESS_CONSENSUS_V1"

def _gray(image:np.ndarray[Any,Any])->np.ndarray[Any,Any]:
    if image.ndim==2:
        return image.astype(np.uint8,copy=False)
    if image.ndim==3 and image.shape[2] in (3,4):
        code=cv2.COLOR_BGRA2GRAY if image.shape[2]==4 else cv2.COLOR_BGR2GRAY
        return cv2.cvtColor(image,code)
    raise ValueError("unsupported image shape")

def _iou(a:np.ndarray,b:np.ndarray)->float:
    av=a.astype(bool); bv=b.astype(bool)
    inter=int(np.logical_and(av,bv).sum())
    union=int(np.logical_or(av,bv).sum())
    return 1.0 if union==0 else inter/union

def _variants(image:np.ndarray[Any,Any])->dict[str,np.ndarray]:
    gray=_gray(image)

    raw_otsu=normalize_ink_mask(gray,adaptive=False)
    raw_adaptive=normalize_ink_mask(gray,adaptive=True)

    clahe=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
    clahe_otsu=normalize_ink_mask(clahe,adaptive=False)

    den=cv2.bilateralFilter(gray,7,40,40)
    den_adaptive=normalize_ink_mask(den,adaptive=True)

    # Local illumination normalization: estimate background and divide.
    bg=cv2.GaussianBlur(gray,(0,0),sigmaX=15,sigmaY=15)
    norm=cv2.divide(gray,bg,scale=255)
    norm_otsu=normalize_ink_mask(norm,adaptive=False)

    return {
        "RAW_OTSU":raw_otsu,
        "RAW_ADAPTIVE":raw_adaptive,
        "CLAHE_OTSU":clahe_otsu,
        "DENOISED_ADAPTIVE":den_adaptive,
        "BACKGROUND_NORMALIZED_OTSU":norm_otsu,
    }

def consensus_ink_mask(
    image:np.ndarray[Any,Any],
    *,
    min_pairwise_iou:float=0.72,
    min_cluster_size:int=3,
    min_ink_fraction:float=0.0005,
    max_ink_fraction:float=0.45,
)->dict[str,Any]:
    if not (0<min_pairwise_iou<=1):
        raise ValueError("min_pairwise_iou must be in (0,1]")
    if min_cluster_size<2:
        raise ValueError("min_cluster_size must be >=2")
    if not (0<=min_ink_fraction<max_ink_fraction<1):
        raise ValueError("ink fraction bounds must satisfy 0 <= min < max < 1")

    variants=_variants(image)
    names=sorted(variants)
    if min_cluster_size>len(names):
        raise ValueError("min_cluster_size exceeds variant count")

    pair={}
    for a,b in combinations(names,2):
        pair[(a,b)]=_iou(variants[a],variants[b])

    good=[]
    for size in range(min_cluster_size,len(names)+1):
        for combo in combinations(names,size):
            vals=[pair[tuple(sorted((a,b)))] for a,b in combinations(combo,2)]
            if all(v>=min_pairwise_iou for v in vals):
                good.append((size,float(sum(vals)/len(vals)) if vals else 1.0,combo))
    if not good:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "error":"NO_CONSENSUS_CLUSTER",
            "pairwise_iou":{f"{a}|{b}":v for (a,b),v in sorted(pair.items())},
            "terminal_authority":False,
        }

    good.sort(key=lambda x:(-x[0],-x[1],x[2]))
    best=good[0]
    same_rank=[g for g in good if g[0]==best[0] and abs(g[1]-best[1])<1e-12]
    distinct={g[2] for g in same_rank}
    if len(distinct)>1:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "error":"AMBIGUOUS_CONSENSUS_CLUSTERS",
            "candidate_clusters":[list(x) for x in sorted(distinct)],
            "terminal_authority":False,
        }

    cluster=list(best[2])
    stack=np.stack([variants[n] for n in cluster],axis=0).astype(np.uint8)
    votes=stack.sum(axis=0)
    mask=(votes >= (len(cluster)//2+1)).astype(np.uint8)
    ink_fraction=float(mask.mean())
    if ink_fraction<min_ink_fraction or ink_fraction>max_ink_fraction:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "error":"INK_FRACTION_IMPLAUSIBLY_LOW" if ink_fraction<min_ink_fraction else "INK_FRACTION_IMPLAUSIBLY_HIGH",
            "ink_fraction":ink_fraction,"cluster":cluster,"terminal_authority":False
        }

    # Consensus must agree with every cluster member at or above the same floor.
    final_iou={n:_iou(mask,variants[n]) for n in cluster}
    if any(v<min_pairwise_iou for v in final_iou.values()):
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","error":"MAJORITY_MASK_NOT_STABLE",
            "cluster":cluster,"final_iou":final_iou,"terminal_authority":False
        }

    return {
        "schema":SCHEMA,"status":"CONSENSUS",
        "cluster":cluster,
        "cluster_size":len(cluster),
        "mean_pairwise_iou":best[1],
        "final_iou":final_iou,
        "ink_fraction":ink_fraction,
        "mask":mask,
        "terminal_authority":False,
        "scope":"DEGRADED_RASTER_NORMALIZATION_WHEN_AT_LEAST_THREE_INDEPENDENT_DETERMINISTIC_PREPROCESSING_ROUTES_AGREE",
    }
