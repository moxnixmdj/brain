"""Zero-learned deterministic chart-bar counter V4.

V3 counts repeated filled rectangular bars using only classical pixel geometry:
quantized colors, dense rectangle cores, duplicate-band merging, and consistent
bar-thickness series detection. It intentionally uses no OCR or learned vision.
"""
from __future__ import annotations
from typing import Any
import numpy as np
from PIL import Image

SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_BAR_COUNT_V4"

class BarCountV4Error(ValueError):
    pass

def _intervals(values:np.ndarray,threshold:int)->list[tuple[int,int]]:
    on=np.asarray(values)>=int(threshold)
    out=[]; start=None
    for i,flag in enumerate(on.tolist()):
        if flag and start is None:
            start=i
        if start is not None and ((not flag) or i==len(on)-1):
            end=i if flag and i==len(on)-1 else i-1
            out.append((int(start),int(end))); start=None
    return out

def _close_small_gaps(bits:np.ndarray,max_gap:int=3)->np.ndarray:
    b=np.asarray(bits,dtype=bool).copy()
    i=0
    while i<len(b):
        if b[i]:
            i+=1; continue
        j=i
        while j<len(b) and not b[j]:
            j+=1
        if i>0 and j<len(b) and j-i<=max_gap:
            b[i:j]=True
        i=j
    return b

def _longest_run(bits:np.ndarray)->tuple[int,int]|None:
    b=np.asarray(bits,dtype=bool)
    best=None; start=None
    for i,flag in enumerate(b.tolist()):
        if flag and start is None:
            start=i
        if start is not None and ((not flag) or i==len(b)-1):
            end=i if flag and i==len(b)-1 else i-1
            if best is None or end-start>best[1]-best[0]:
                best=(int(start),int(end))
            start=None
    return best

def _raw_rectangles(rgb:np.ndarray)->dict[str,list[dict[str,Any]]]:
    if not isinstance(rgb,np.ndarray) or rgb.ndim!=3 or rgb.shape[2]!=3:
        raise BarCountV4Error("RGB_INVALID")
    h,w=rgb.shape[:2]
    if h<20 or w<20:
        raise BarCountV4Error("IMAGE_TOO_SMALL")
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
        for orientation,values,axis_dim,orth_dim in (
            ("HORIZONTAL",mask.sum(axis=1),h,w),
            ("VERTICAL",mask.sum(axis=0),w,h),
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
                    dense=_close_small_gaps(sub.sum(axis=0)>=max(1,int(np.ceil(0.55*thickness))),3)
                else:
                    sub=mask[:,lo:hi+1]
                    dense=_close_small_gaps(sub.sum(axis=1)>=max(1,int(np.ceil(0.55*thickness))),3)
                run=_longest_run(dense)
                if run is None:
                    continue
                orth_lo,orth_hi=run
                span=orth_hi-orth_lo+1
                span_fraction=span/orth_dim
                if span_fraction<0.03 or span_fraction>0.95:
                    continue
                core=(mask[lo:hi+1,orth_lo:orth_hi+1]
                      if orientation=="HORIZONTAL"
                      else mask[orth_lo:orth_hi+1,lo:hi+1])
                density=float(core.mean())
                if density<0.45:
                    continue
                out[orientation].append({
                    "orientation":orientation,"color":color,
                    "band_lo":int(lo),"band_hi":int(hi),
                    "orth_lo":int(orth_lo),"orth_hi":int(orth_hi),
                    "density":density,"area":int(core.sum())
                })
    return out

def _merge_duplicates(rects:list[dict[str,Any]])->list[dict[str,Any]]:
    merged=[]
    for raw in sorted(rects,key=lambda r:(r["band_lo"],r["band_hi"],-r["area"])):
        r=dict(raw); hit=None
        for i,m in enumerate(merged):
            overlap=max(0,min(r["band_hi"],m["band_hi"])-max(r["band_lo"],m["band_lo"])+1)
            smaller=max(1,min(r["band_hi"]-r["band_lo"]+1,m["band_hi"]-m["band_lo"]+1))
            if overlap/smaller>=0.55:
                hit=i; break
        if hit is None:
            merged.append(r)
        elif r["area"]>merged[hit]["area"]:
            keep=dict(r)
            keep["band_lo"]=min(merged[hit]["band_lo"],r["band_lo"])
            keep["band_hi"]=max(merged[hit]["band_hi"],r["band_hi"])
            merged[hit]=keep
        else:
            merged[hit]["band_lo"]=min(merged[hit]["band_lo"],r["band_lo"])
            merged[hit]["band_hi"]=max(merged[hit]["band_hi"],r["band_hi"])
    return merged

def _best_thickness_series(rects:list[dict[str,Any]],orientation:str,*,h:int,w:int)->tuple[list[dict[str,Any]],float]:
    if not rects:
        return [],0.0
    orth_dim=w if orientation=="HORIZONTAL" else h
    best=[]; best_score=0.0
    for anchor in rects:
        anchor_th=anchor["band_hi"]-anchor["band_lo"]+1
        tolerance=max(2.0,0.25*anchor_th)
        group=[r for r in rects if abs((r["band_hi"]-r["band_lo"]+1)-anchor_th)<=tolerance]
        if len(group)<2:
            continue
        thickness=np.asarray([r["band_hi"]-r["band_lo"]+1 for r in group],dtype=float)
        cv=float(thickness.std()/max(float(thickness.mean()),1e-12))
        spans=[(r["orth_hi"]-r["orth_lo"]+1)/orth_dim for r in group]
        densities=[float(r["density"]) for r in group]
        score=len(group)*float(np.median(spans))*float(np.median(densities))/(1.0+cv)
        if score>best_score:
            best_score=float(score); best=group
    return sorted(best,key=lambda r:(r["band_lo"],r["band_hi"])),best_score

def count_bars_from_rgb(rgb:np.ndarray)->dict[str,Any]:
    h,w=rgb.shape[:2]
    raw=_raw_rectangles(rgb)
    horizontal=_merge_duplicates(raw["HORIZONTAL"])
    vertical=_merge_duplicates(raw["VERTICAL"])
    hg,hs=_best_thickness_series(horizontal,"HORIZONTAL",h=h,w=w)
    vg,vs=_best_thickness_series(vertical,"VERTICAL",h=h,w=w)

    if max(hs,vs)<0.12:
        return {
            "schema":SCHEMA,"status":"ABSTAIN_BAR_GEOMETRY_WEAK","count":None,
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,
            "pretrained_vision_models":0,"ocr_models":0
        }
    orientation="HORIZONTAL" if hs>=vs else "VERTICAL"
    group=hg if hs>=vs else vg
    score=hs if hs>=vs else vs
    if not 2<=len(group)<=50:
        return {
            "schema":SCHEMA,"status":"ABSTAIN_BAR_COUNT_IMPLAUSIBLE","count":None,
            "orientation":orientation,"persistent_learned_bytes":0,
            "external_learned_capability_calls":0,"pretrained_vision_models":0,"ocr_models":0
        }
    return {
        "schema":SCHEMA,"status":"BAR_COUNT_IDENTIFIED","count":len(group),
        "orientation":orientation,"score":float(score),
        "rectangles":[dict(r) for r in group],
        "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        "pretrained_vision_models":0,"ocr_models":0
    }

def count_bars(path:str)->dict[str,Any]:
    try:
        rgb=np.asarray(Image.open(path).convert("RGB"))
    except Exception as exc:
        raise BarCountV4Error("IMAGE_LOAD_FAILED") from exc
    return count_bars_from_rgb(rgb)
