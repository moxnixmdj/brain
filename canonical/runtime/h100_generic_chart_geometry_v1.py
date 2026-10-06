"""Generic deterministic chart-geometry parser V1.

Developed only after the frozen V0 adversarial development suite was scored.
Contains no case IDs, expected answers, suite RGB literals, bar counts, or
learned-model calls. Future capability claims require a new frozen holdout.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
from PIL import Image

SCHEMA="PROJECT_BRAIN_H100_GENERIC_CHART_GEOMETRY_V1"

class ChartGeometryError(ValueError):
    pass

def _components(mask:np.ndarray)->list[dict[str,Any]]:
    h,w=mask.shape
    seen=np.zeros_like(mask,dtype=bool)
    out=[]
    for y in range(h):
        for x in range(w):
            if not bool(mask[y,x]) or bool(seen[y,x]):
                continue
            stack=[(y,x)]; seen[y,x]=True
            n=0; minx=maxx=x; miny=maxy=y
            while stack:
                yy,xx=stack.pop(); n+=1
                minx=min(minx,xx); maxx=max(maxx,xx)
                miny=min(miny,yy); maxy=max(maxy,yy)
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if dx==0 and dy==0: continue
                        ny,nx=yy+dy,xx+dx
                        if 0<=ny<h and 0<=nx<w and bool(mask[ny,nx]) and not bool(seen[ny,nx]):
                            seen[ny,nx]=True; stack.append((ny,nx))
            bw=maxx-minx+1; bh=maxy-miny+1
            out.append({
                "pixels":n,"minx":minx,"miny":miny,"maxx":maxx,"maxy":maxy,
                "width":bw,"height":bh,"fill":n/(bw*bh),
                "aspect":max(bw,bh)/max(1,min(bw,bh)),
            })
    return out

def _overlap_fraction(a:tuple[int,int],b:tuple[int,int])->float:
    lo=max(a[0],b[0]); hi=min(a[1],b[1])
    if hi<lo: return 0.0
    inter=hi-lo+1
    return inter/min(a[1]-a[0]+1,b[1]-b[0]+1)

def parse_chart_geometry(image_path:str|Path)->dict[str,Any]:
    p=Path(image_path)
    if not p.is_file(): raise ChartGeometryError("IMAGE_NOT_FOUND")
    a=np.array(Image.open(p).convert("RGB"))
    if a.ndim!=3 or a.shape[2]!=3: raise ChartGeometryError("RGB_REQUIRED")
    h,w=a.shape[:2]
    q=(a//16)*16
    colors,counts=np.unique(q.reshape(-1,3),axis=0,return_counts=True)
    bg=tuple(int(x) for x in colors[int(np.argmax(counts))])
    rects=[]; all_components=[]
    for color,count in zip(colors,counts):
        ct=tuple(int(x) for x in color)
        if ct==bg or int(count)<20:
            continue
        mask=np.all(q==color.astype(np.uint8),axis=2)
        for row in _components(mask):
            r=dict(row); r["color_quantized_rgb"]=list(ct)
            all_components.append(r)
            if (
                int(r["pixels"])>=40 and float(r["fill"])>=0.72
                and min(int(r["width"]),int(r["height"]))>=5
                and float(r["aspect"])>=1.25
            ):
                rects.append(r)

    vertical=[r for r in rects if r["height"]>=1.25*r["width"]]
    horizontal=[r for r in rects if r["width"]>=1.25*r["height"]]
    bars=vertical if len(vertical)>=len(horizontal) else horizontal
    orientation="VERTICAL" if bars is vertical else "HORIZONTAL"

    if len(bars)>=2:
        def pos(r):
            return (r["minx"]+r["maxx"])/2 if orientation=="VERTICAL" else (r["miny"]+r["maxy"])/2
        bars=sorted(bars,key=lambda r:(pos(r),r["miny"],r["minx"]))
        groups=[]
        for r in bars:
            interval=(r["minx"],r["maxx"]) if orientation=="VERTICAL" else (r["miny"],r["maxy"])
            placed=False
            for g in groups:
                if any(_overlap_fraction(interval,old)>=0.5 for old in g["intervals"]):
                    g["rows"].append(r); g["intervals"].append(interval); placed=True; break
            if not placed:
                groups.append({"rows":[r],"intervals":[interval]})
        groups.sort(key=lambda g:sum((a+b)/2 for a,b in g["intervals"])/len(g["intervals"]))
        lengths=[]
        intervals=[]
        for g in groups:
            lo=min(x[0] for x in g["intervals"]); hi=max(x[1] for x in g["intervals"])
            intervals.append([lo,hi])
            lengths.append(sum(int(r["height"] if orientation=="VERTICAL" else r["width"]) for r in g["rows"]))
        return {
            "schema":SCHEMA,"status":"CHART_GEOMETRY_IDENTIFIED","chart_type":"BAR",
            "orientation":orientation,"segment_count":len(bars),"category_count":len(groups),
            "category_intervals":intervals,"lengths_by_position":lengths,
            "background_quantized_rgb":list(bg),
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        }

    compact=[
        r for r in all_components
        if r["pixels"]>=20 and r["fill"]>=0.45
        and 0.7<=r["width"]/max(r["height"],1)<=1.43
        and max(r["width"],r["height"])<=30
    ]
    elongated=[
        r for r in all_components
        if r["pixels"]>=50 and r["fill"]<0.5
        and max(r["width"],r["height"])>=0.30*max(w,h)
    ]
    if len(compact)>=3 and not elongated:
        chart_type="SCATTER"
    elif elongated:
        chart_type="LINE"
    else:
        chart_type="UNKNOWN"
    return {
        "schema":SCHEMA,
        "status":"CHART_GEOMETRY_IDENTIFIED" if chart_type!="UNKNOWN" else "CHART_GEOMETRY_UNRESOLVED",
        "chart_type":chart_type,"orientation":None,"segment_count":0,"category_count":0,
        "category_intervals":[],"lengths_by_position":[],
        "background_quantized_rgb":list(bg),
        "persistent_learned_bytes":0,"external_learned_capability_calls":0,
    }

def answer_geometry(parsed:dict[str,Any],question:str,*,count_mode:str="CATEGORY")->Any:
    q=str(question)
    if q=="CHART_TYPE": return parsed.get("chart_type")
    if q=="ORIENTATION": return parsed.get("orientation")
    if q=="COUNT":
        return parsed.get("segment_count") if count_mode=="SEGMENT" else parsed.get("category_count")
    lengths=list(parsed.get("lengths_by_position") or [])
    if q=="ARGMAX_INDEX":
        return None if not lengths else max(range(len(lengths)),key=lambda i:lengths[i])
    if q=="ARGMIN_INDEX":
        return None if not lengths else min(range(len(lengths)),key=lambda i:lengths[i])
    if q=="DESCENDING_ORDER":
        return None if not lengths else sorted(range(len(lengths)),key=lambda i:(-lengths[i],i))
    raise ChartGeometryError("QUESTION_UNSUPPORTED")
