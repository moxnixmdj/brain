"""Zero-learned deterministic chart-bar counter V1.

The detector intentionally uses only pixel color geometry:
- quantize RGB colors,
- discover sufficiently saturated non-background color clusters,
- project each cluster onto rows/columns,
- identify repeated thick occupancy bands,
- choose the strongest bar orientation,
- aggregate compatible colors,
- merge duplicate overlapping bands,
- fail closed when geometry is weak.

No OCR, pretrained vision model, learned embeddings, or fitted image classifier
is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_BAR_COUNT_V1"


class BarCountError(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    orientation:str
    color:tuple[int,int,int]
    bands:tuple[tuple[int,int],...]
    score:float
    pixel_count:int


def _intervals(values:np.ndarray, threshold:int)->list[tuple[int,int]]:
    on=np.asarray(values)>=int(threshold)
    out=[]
    start=None
    for i,flag in enumerate(on.tolist()):
        if flag and start is None:
            start=i
        if start is not None and ((not flag) or i==len(on)-1):
            end=i if flag and i==len(on)-1 else i-1
            out.append((int(start),int(end)))
            start=None
    return out


def _score_bands(values:np.ndarray,bands:list[tuple[int,int]],mask_pixels:int)->float:
    if not 2<=len(bands)<=50:
        return 0.0
    widths=np.asarray([hi-lo+1 for lo,hi in bands],dtype=float)
    mean=float(widths.mean())
    cv=float(widths.std()/max(mean,1e-12))
    occupied=sum(int(values[lo:hi+1].sum()) for lo,hi in bands)
    coverage=occupied/max(int(mask_pixels),1)
    return float(len(bands)*(1.0/(1.0+cv))*coverage)


def _merge_bands(bands:list[tuple[int,int]])->list[tuple[int,int]]:
    if not bands:
        return []
    remaining=sorted((int(a),int(b)) for a,b in bands)
    merged=[]
    while remaining:
        a,b=remaining.pop(0)
        changed=True
        while changed:
            changed=False
            ca=(a+b)/2.0
            ta=b-a+1
            keep=[]
            for x,y in remaining:
                cb=(x+y)/2.0
                tb=y-x+1
                overlap=max(0,min(b,y)-max(a,x)+1)
                overlap_frac=overlap/max(1,min(ta,tb))
                center_close=abs(ca-cb)<=0.5*min(ta,tb)
                if overlap_frac>=0.5 or center_close:
                    a=min(a,x); b=max(b,y)
                    ca=(a+b)/2.0; ta=b-a+1
                    changed=True
                else:
                    keep.append((x,y))
            remaining=keep
        merged.append((a,b))
    return sorted(merged)


def discover_candidates(rgb:np.ndarray)->list[Candidate]:
    if not isinstance(rgb,np.ndarray) or rgb.ndim!=3 or rgb.shape[2]!=3:
        raise BarCountError("RGB_INVALID")
    h,w=rgb.shape[:2]
    if h<20 or w<20:
        raise BarCountError("IMAGE_TOO_SMALL")

    q=(rgb.astype(np.uint16)//16*16).astype(np.uint8)
    colors,counts=np.unique(q.reshape(-1,3),axis=0,return_counts=True)
    min_pixels=max(1,int(np.ceil(0.001*h*w)))
    candidates=[]

    for raw,count in zip(colors,counts):
        color=tuple(int(x) for x in raw)
        chroma=max(color)-min(color)
        brightness=sum(color)/3.0
        if chroma<32 or brightness>235 or int(count)<min_pixels:
            continue

        mask=np.all(q==raw,axis=2)
        rows=mask.sum(axis=1)
        cols=mask.sum(axis=0)
        row_threshold=max(8,int(np.ceil(0.02*w)))
        col_threshold=max(8,int(np.ceil(0.02*h)))
        row_max=max(2,int(np.floor(0.20*h)))
        col_max=max(2,int(np.floor(0.20*w)))

        rb=[
            z for z in _intervals(rows,row_threshold)
            if 2<=z[1]-z[0]+1<=row_max
        ]
        cb=[
            z for z in _intervals(cols,col_threshold)
            if 2<=z[1]-z[0]+1<=col_max
        ]
        rscore=_score_bands(rows,rb,int(mask.sum()))
        cscore=_score_bands(cols,cb,int(mask.sum()))
        if rscore>0:
            candidates.append(Candidate("HORIZONTAL",color,tuple(rb),rscore,int(count)))
        if cscore>0:
            candidates.append(Candidate("VERTICAL",color,tuple(cb),cscore,int(count)))

    candidates.sort(key=lambda c:(-c.score,c.orientation,c.color))
    return candidates


def count_bars_from_rgb(rgb:np.ndarray)->dict[str,Any]:
    candidates=discover_candidates(rgb)
    if not candidates or candidates[0].score<1.5:
        return {
            "schema":SCHEMA,
            "status":"ABSTAIN_BAR_GEOMETRY_WEAK",
            "count":None,
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
        }

    best=candidates[0]
    orientation=best.orientation
    threshold=max(1.5,0.30*best.score)
    selected=[
        c for c in candidates
        if c.orientation==orientation and c.score>=threshold
    ]
    bands=_merge_bands([band for c in selected for band in c.bands])
    if not 2<=len(bands)<=50:
        return {
            "schema":SCHEMA,
            "status":"ABSTAIN_BAR_COUNT_IMPLAUSIBLE",
            "count":None,
            "orientation":orientation,
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
        }
    return {
        "schema":SCHEMA,
        "status":"BAR_COUNT_IDENTIFIED",
        "count":len(bands),
        "orientation":orientation,
        "bands":[list(x) for x in bands],
        "selected_colors":[list(c.color) for c in selected],
        "selected_candidate_scores":[float(c.score) for c in selected],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "pretrained_vision_models":0,
        "ocr_models":0,
    }


def count_bars(path:str)->dict[str,Any]:
    try:
        rgb=np.asarray(Image.open(path).convert("RGB"))
    except Exception as exc:
        raise BarCountError("IMAGE_LOAD_FAILED") from exc
    return count_bars_from_rgb(rgb)
