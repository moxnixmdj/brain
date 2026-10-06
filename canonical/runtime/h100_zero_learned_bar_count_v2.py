"""Zero-learned deterministic chart-bar counter V2.

V2 repairs two observed V1 failures without introducing learned state:
- ultra-thin color stripes (e.g. gridline overlays) are rejected by a dynamic
  minimum thickness;
- single bars from different colors are allowed and aggregated if they share a
  common chart baseline.

The detector still uses only pixel geometry. No OCR, pretrained vision model,
embedding, learned classifier, or external learned capability is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_BAR_COUNT_V2"


class BarCountV2Error(ValueError):
    pass


@dataclass(frozen=True)
class Rectangle:
    orientation:str
    color:tuple[int,int,int]
    band_lo:int
    band_hi:int
    orth_lo:int
    orth_hi:int
    density:float
    area:int


def _intervals(values:np.ndarray,threshold:int)->list[tuple[int,int]]:
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


def _raw_rectangles(rgb:np.ndarray)->dict[str,list[dict[str,Any]]]:
    if not isinstance(rgb,np.ndarray) or rgb.ndim!=3 or rgb.shape[2]!=3:
        raise BarCountV2Error("RGB_INVALID")
    h,w=rgb.shape[:2]
    if h<20 or w<20:
        raise BarCountV2Error("IMAGE_TOO_SMALL")

    q=(rgb.astype(np.uint16)//16*16).astype(np.uint8)
    colors,counts=np.unique(q.reshape(-1,3),axis=0,return_counts=True)
    min_pixels=max(1,int(np.ceil(0.0005*h*w)))
    out={"HORIZONTAL":[],"VERTICAL":[]}

    for raw,count in zip(colors,counts):
        color=tuple(int(x) for x in raw)
        chroma=max(color)-min(color)
        brightness=sum(color)/3.0
        if chroma<20 or brightness>240 or int(count)<min_pixels:
            continue

        mask=np.all(q==raw,axis=2)
        rows=mask.sum(axis=1)
        cols=mask.sum(axis=0)

        for orientation,values,axis_dim,orth_dim in (
            ("HORIZONTAL",rows,h,w),
            ("VERTICAL",cols,w,h),
        ):
            threshold=max(8,int(np.ceil(0.02*orth_dim)))
            min_th=max(4,int(np.ceil(0.008*axis_dim)))
            max_th=max(min_th,int(np.floor(0.40*axis_dim)))

            for lo,hi in _intervals(values,threshold):
                thickness=hi-lo+1
                if not min_th<=thickness<=max_th:
                    continue

                if orientation=="HORIZONTAL":
                    sub=mask[lo:hi+1,:]
                    yy,xx=np.where(sub)
                    if xx.size==0:
                        continue
                    orth_lo,orth_hi=int(xx.min()),int(xx.max())
                else:
                    sub=mask[:,lo:hi+1]
                    yy,xx=np.where(sub)
                    if yy.size==0:
                        continue
                    orth_lo,orth_hi=int(yy.min()),int(yy.max())

                span=orth_hi-orth_lo+1
                if span<0.08*orth_dim:
                    continue
                area=int(sub.sum())
                density=area/max(1,thickness*span)
                if density<0.50:
                    continue
                out[orientation].append({
                    "orientation":orientation,
                    "color":color,
                    "band_lo":int(lo),
                    "band_hi":int(hi),
                    "orth_lo":orth_lo,
                    "orth_hi":orth_hi,
                    "density":float(density),
                    "area":area,
                })
    return out


def _merge_band_duplicates(rects:list[dict[str,Any]])->list[dict[str,Any]]:
    merged=[]
    for raw in sorted(rects,key=lambda r:(r["band_lo"],r["band_hi"],-r["area"])):
        r=dict(raw)
        hit=None
        for i,m in enumerate(merged):
            overlap=max(0,min(r["band_hi"],m["band_hi"])-max(r["band_lo"],m["band_lo"])+1)
            smaller=max(1,min(
                r["band_hi"]-r["band_lo"]+1,
                m["band_hi"]-m["band_lo"]+1,
            ))
            if overlap/smaller>=0.55:
                hit=i
                break
        if hit is None:
            merged.append(r)
        else:
            m=merged[hit]
            m["band_lo"]=min(m["band_lo"],r["band_lo"])
            m["band_hi"]=max(m["band_hi"],r["band_hi"])
            m["orth_lo"]=min(m["orth_lo"],r["orth_lo"])
            m["orth_hi"]=max(m["orth_hi"],r["orth_hi"])
            m["density"]=max(float(m["density"]),float(r["density"]))
            m["area"]=max(int(m["area"]),int(r["area"]))
    return merged


def _best_baseline_group(
    rects:list[dict[str,Any]],
    orientation:str,
    *,
    h:int,
    w:int,
)->tuple[list[dict[str,Any]],float]:
    if not rects:
        return [],0.0

    orth_dim=w if orientation=="HORIZONTAL" else h
    tolerance=0.035*orth_dim
    endpoints=[
        r["orth_lo"] if orientation=="HORIZONTAL" else r["orth_hi"]
        for r in rects
    ]

    best=[]
    for anchor in endpoints:
        group=[
            r for r,e in zip(rects,endpoints)
            if abs(float(e)-float(anchor))<=tolerance
        ]
        if len(group)>len(best):
            best=group
        elif len(group)==len(best) and sum(int(r["area"]) for r in group)>sum(int(r["area"]) for r in best):
            best=group

    if not best:
        return [],0.0
    spans=[
        (r["orth_hi"]-r["orth_lo"]+1)/orth_dim
        for r in best
    ]
    densities=[float(r["density"]) for r in best]
    score=len(best)*float(np.median(spans))*float(np.median(densities))
    return sorted(best,key=lambda r:(r["band_lo"],r["band_hi"])),float(score)


def count_bars_from_rgb(rgb:np.ndarray)->dict[str,Any]:
    h,w=rgb.shape[:2]
    raw=_raw_rectangles(rgb)
    horizontal=_merge_band_duplicates(raw["HORIZONTAL"])
    vertical=_merge_band_duplicates(raw["VERTICAL"])
    hg,hs=_best_baseline_group(horizontal,"HORIZONTAL",h=h,w=w)
    vg,vs=_best_baseline_group(vertical,"VERTICAL",h=h,w=w)

    if max(hs,vs)<0.15:
        return {
            "schema":SCHEMA,
            "status":"ABSTAIN_BAR_GEOMETRY_WEAK",
            "count":None,
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
            "pretrained_vision_models":0,
            "ocr_models":0,
        }

    orientation="HORIZONTAL" if hs>=vs else "VERTICAL"
    group=hg if hs>=vs else vg
    score=hs if hs>=vs else vs
    if not 2<=len(group)<=50:
        return {
            "schema":SCHEMA,
            "status":"ABSTAIN_BAR_COUNT_IMPLAUSIBLE",
            "count":None,
            "orientation":orientation,
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
            "pretrained_vision_models":0,
            "ocr_models":0,
        }

    return {
        "schema":SCHEMA,
        "status":"BAR_COUNT_IDENTIFIED",
        "count":len(group),
        "orientation":orientation,
        "score":float(score),
        "rectangles":[dict(r) for r in group],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "pretrained_vision_models":0,
        "ocr_models":0,
    }


def count_bars(path:str)->dict[str,Any]:
    try:
        rgb=np.asarray(Image.open(path).convert("RGB"))
    except Exception as exc:
        raise BarCountV2Error("IMAGE_LOAD_FAILED") from exc
    return count_bars_from_rgb(rgb)
