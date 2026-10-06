"""Generic deterministic bar-geometry primitive for the A/P=0 substrate.

Frozen before the cross-capability fresh suite is generated. It uses no learned
model, no OCR model, no chart-specific exact RGB value, and no task labels.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
from PIL import Image

SCHEMA="PROJECT_BRAIN_H100_GENERIC_BAR_GEOMETRY_V0"

class BarGeometryError(ValueError):
    pass

def _intervals(v:np.ndarray, threshold:int)->list[tuple[int,int]]:
    on=v>=threshold
    out=[]; start=None
    for i,b in enumerate(on):
        if bool(b) and start is None:
            start=i
        if start is not None and ((not bool(b)) or i==len(on)-1):
            end=i if bool(b) and i==len(on)-1 else i-1
            out.append((start,end))
            start=None
    return out

def detect_bar_geometry(image_path:str|Path)->dict[str,Any]:
    p=Path(image_path)
    if not p.exists():
        raise BarGeometryError("IMAGE_NOT_FOUND")
    a=np.array(Image.open(p).convert("RGB"))
    if a.ndim!=3 or a.shape[2]!=3:
        raise BarGeometryError("RGB_IMAGE_REQUIRED")
    h,w=a.shape[:2]
    q=(a//16)*16
    colors,counts=np.unique(q.reshape(-1,3),axis=0,return_counts=True)
    candidates=[]
    for color,count in zip(colors,counts):
        ci=color.astype(int)
        chroma=int(ci.max()-ci.min())
        bright=float(ci.mean())
        if chroma<32 or bright>235 or int(count)<max(1,int(0.001*h*w)):
            continue
        mask=np.all(q==color.astype(np.uint8),axis=2)
        rs=mask.sum(1); cs=mask.sum(0)
        rints=[
            z for z in _intervals(rs,max(8,int(0.02*w)))
            if 2<=z[1]-z[0]+1<=max(80,int(0.2*h))
        ]
        cints=[
            z for z in _intervals(cs,max(8,int(0.02*h)))
            if 2<=z[1]-z[0]+1<=max(80,int(0.2*w))
        ]
        def score(ints,axis):
            if len(ints)<2 or len(ints)>50:
                return 0.0
            widths=np.array([b-a+1 for a,b in ints],dtype=float)
            cv=float(widths.std()/max(widths.mean(),1e-12))
            vec=rs if axis=="r" else cs
            occ=sum(int(vec[lo:hi+1].sum()) for lo,hi in ints)
            return float(len(ints)*(1/(1+cv))*occ/max(int(mask.sum()),1))
        candidates.append({
            "color_quantized_rgb":[int(x) for x in color],
            "pixel_count":int(count),
            "row_intervals":[list(z) for z in rints],
            "column_intervals":[list(z) for z in cints],
            "row_score":score(rints,"r"),
            "column_score":score(cints,"c"),
        })
    candidates.sort(
        key=lambda x:(max(x["row_score"],x["column_score"]),x["pixel_count"]),
        reverse=True,
    )
    if not candidates:
        return {
            "schema":SCHEMA,
            "status":"NO_BARLIKE_COLOR_FAMILY",
            "orientation":None,
            "bar_intervals":[],
            "candidate":None,
            "persistent_learned_bytes":0,
        }
    top=candidates[0]
    if top["column_score"]>=top["row_score"]:
        orientation="VERTICAL"
        intervals=top["column_intervals"]
    else:
        orientation="HORIZONTAL"
        intervals=top["row_intervals"]
    return {
        "schema":SCHEMA,
        "status":"BARLIKE_GEOMETRY_IDENTIFIED" if intervals else "NO_BARLIKE_INTERVALS",
        "orientation":orientation if intervals else None,
        "bar_intervals":intervals,
        "candidate":top,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
    }
