"""Deterministic raw-pixel bar geometry solver.

Frozen after training-only development and before any final-holdout image is
downloaded or evaluated. Uses no OCR, learned vision model, chart annotation,
or external visual capability provider.

Two complementary generic geometry routes are combined:
- projection geometry (V5-style)
- connected-component geometry (V6-style)
The hybrid selector uses only parser outputs/orientations:
  * if the component route abstains, abstain;
  * if orientations disagree, use projection route;
  * if same orientation and component prediction == projection prediction + 1,
    use component route;
  * otherwise use projection route.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
import math

import numpy as np
from PIL import Image

SCHEMA="PROJECT_BRAIN_H100_DETERMINISTIC_BAR_GEOMETRY_SOLVER_V1"

def _intervals(v,thr):
    on=v>=thr; out=[]; s=None
    for i,b in enumerate(on):
        if b and s is None: s=i
        if s is not None and ((not b) or i==len(on)-1):
            e=i if b and i==len(on)-1 else i-1; out.append((s,e)); s=None
    return out

def _cluster_intervals(items,tol=.42):
    groups=[]
    for lo,hi in sorted(items,key=lambda x:(x[0]+x[1])/2):
        c=(lo+hi)/2; th=hi-lo+1; hit=None
        for g in groups:
            gc=np.mean([(a+b)/2 for a,b in g]); gt=np.median([b-a+1 for a,b in g])
            if abs(c-gc)<=tol*max(th,gt,3): hit=g; break
        if hit is None: groups.append([(lo,hi)])
        else: hit.append((lo,hi))
    return groups

def _thickness_families(cands,rel=.28):
    gs=[]
    for x in sorted(cands,key=lambda z:z["thick"]):
        hit=None
        for g in gs:
            med=float(np.median([z["thick"] for z in g]))
            if abs(x["thick"]-med)<=max(2,rel*med): hit=g; break
        if hit is None: gs.append([x])
        else: hit.append(x)
    return gs

def _best_family(cands):
    gs=_thickness_families(cands)
    if not gs: return [],0.0
    def score(g):
        return sum(x["area"] for x in g)*(1+.025*max(0,len(g)-1))
    g=max(gs,key=score)
    return g,score(g)

def _projection_extract(path,qstep=16,min_thick=3,max_thick_ratio=.35,min_long_ratio=.005,fill_thr=.65,min_frac=.000025):
    a=np.array(Image.open(path).convert("RGB")); h,w=a.shape[:2]
    q=(a//qstep)*qstep
    codes=(q[:,:,0].astype(np.uint32)<<16)|(q[:,:,1].astype(np.uint32)<<8)|q[:,:,2].astype(np.uint32)
    vals,counts=np.unique(codes,return_counts=True)
    out={"h":[],"v":[]}; total=h*w
    for code,count in zip(vals,counts):
        if count<min_frac*total: continue
        color=np.array([(code>>16)&255,(code>>8)&255,code&255],dtype=np.uint8)
        if float(color.mean())>248: continue
        mask=(codes==code); rs=mask.sum(1); cs=mask.sum(0)
        for axis,vec,dim_long,dim_cross in [("h",rs,w,h),("v",cs,h,w)]:
            for lo,hi in _intervals(vec,max(2,int(min_long_ratio*dim_long))):
                thick=hi-lo+1
                if not(min_thick<=thick<=max_thick_ratio*dim_cross): continue
                if axis=="h":
                    sub=mask[lo:hi+1,:]; pos=np.where(sub.any(0))[0]
                else:
                    sub=mask[:,lo:hi+1]; pos=np.where(sub.any(1))[0]
                if not len(pos): continue
                long=int(pos[-1]-pos[0]+1); area=int(sub.sum()); fill=area/max(thick*long,1)
                if long/dim_long>=.965: continue
                if long>=max(2,int(min_long_ratio*dim_long)) and fill>=fill_thr:
                    out[axis].append({"lo":lo,"hi":hi,"thick":thick,"long":long,"fill":fill,"area":area,"color":tuple(map(int,color))})
    return out,(h,w)

def _projection_solve(path,intent):
    feats,(h,w)=_projection_extract(path)
    gh,sh=_best_family(feats["h"]); gv,sv=_best_family(feats["v"])
    axis="h" if sh>=sv else "v"; fam=gh if axis=="h" else gv
    positions=_cluster_intervals([(x["lo"],x["hi"]) for x in fam])
    area=sum(x["area"] for x in fam); ar=area/(h*w)
    if not fam or not positions or ar<.003:
        return None,{"axis":axis,"area_ratio":ar}
    if intent=="BAR_INSTANCE_COUNT":
        pred=len(positions)
    else:
        counts=defaultdict(int)
        for x in fam: counts[x["color"]]+=1
        recurrent={c:n for c,n in counts.items() if n>=2}
        recurrent_mass=sum(recurrent.values())
        pred=len(recurrent) if recurrent and recurrent_mass/len(fam)>=.60 else len(positions)
    return pred,{"axis":axis,"area_ratio":ar}

def _components(path,qstep=16,min_area=18):
    a=np.array(Image.open(path).convert("RGB")); h,w=a.shape[:2]
    q=(a//qstep)*qstep
    code=(q[:,:,0].astype(np.uint32)<<16)|(q[:,:,1].astype(np.uint32)<<8)|q[:,:,2].astype(np.uint32)
    valid=q.mean(2)<248
    seen=np.zeros((h,w),dtype=np.uint8); out=[]
    for y in range(h):
        for x in range(w):
            if seen[y,x] or not valid[y,x]: continue
            c=code[y,x]; stack=[(y,x)]; seen[y,x]=1
            minx=maxx=x; miny=maxy=y; n=0
            while stack:
                yy,xx=stack.pop(); n+=1
                minx=min(minx,xx); maxx=max(maxx,xx); miny=min(miny,yy); maxy=max(maxy,yy)
                if xx and not seen[yy,xx-1] and valid[yy,xx-1] and code[yy,xx-1]==c:
                    seen[yy,xx-1]=1; stack.append((yy,xx-1))
                if xx+1<w and not seen[yy,xx+1] and valid[yy,xx+1] and code[yy,xx+1]==c:
                    seen[yy,xx+1]=1; stack.append((yy,xx+1))
                if yy and not seen[yy-1,xx] and valid[yy-1,xx] and code[yy-1,xx]==c:
                    seen[yy-1,xx]=1; stack.append((yy-1,xx))
                if yy+1<h and not seen[yy+1,xx] and valid[yy+1,xx] and code[yy+1,xx]==c:
                    seen[yy+1,xx]=1; stack.append((yy+1,xx))
            if n<min_area: continue
            bw=maxx-minx+1; bh=maxy-miny+1
            out.append({"x0":minx,"x1":maxx,"y0":miny,"y1":maxy,"bw":bw,"bh":bh,"area":n,"fill":n/(bw*bh),"color":(int((c>>16)&255),int((c>>8)&255),int(c&255))})
    return out,(h,w)

def _merge_collinear(comps,axis):
    groups=[]
    for z in sorted(comps,key=lambda z:(z["color"],z["y0"] if axis=="h" else z["x0"],z["x0"] if axis=="h" else z["y0"])):
        cross=(z["y0"],z["y1"]) if axis=="h" else (z["x0"],z["x1"])
        long=(z["x0"],z["x1"]) if axis=="h" else (z["y0"],z["y1"])
        hit=None
        for g in groups:
            if g["color"]!=z["color"]: continue
            gc=g["cross"]; inter=max(0,min(cross[1],gc[1])-max(cross[0],gc[0])+1)
            small=min(cross[1]-cross[0]+1,gc[1]-gc[0]+1)
            if small and inter/small>=.75:
                gl=g["long"]; gap=max(0,max(long[0],gl[0])-min(long[1],gl[1])-1)
                if gap<=max(14,.12*max(long[1]-long[0]+1,gl[1]-gl[0]+1)): hit=g; break
        if hit is None:
            groups.append({"color":z["color"],"cross":cross,"long":long,"area":z["area"]})
        else:
            hit["cross"]=(min(hit["cross"][0],cross[0]),max(hit["cross"][1],cross[1]))
            hit["long"]=(min(hit["long"][0],long[0]),max(hit["long"][1],long[1]))
            hit["area"]+=z["area"]
    out=[]
    for g in groups:
        th=g["cross"][1]-g["cross"][0]+1; ln=g["long"][1]-g["long"][0]+1
        out.append({**g,"thick":th,"length":ln,"fill":g["area"]/max(th*ln,1)})
    return out

def _component_candidates(path):
    cs,(h,w)=_components(path)
    out={}
    for axis in ("h","v"):
        arr=[]
        for z in _merge_collinear(cs,axis):
            th=z["thick"]; ln=z["length"]; dimcross=h if axis=="h" else w; dimlong=w if axis=="h" else h
            if th<3 or th>.38*dimcross or ln<3 or ln>.965*dimlong or z["fill"]<.48 or z["area"]<20: continue
            arr.append(z)
        out[axis]=arr
    return out,(h,w)

def _component_positions(fam,tol=.42):
    groups=[]
    for z in sorted(fam,key=lambda z:sum(z["cross"])/2):
        c=sum(z["cross"])/2; th=z["thick"]; hit=None
        for g in groups:
            gc=np.mean([sum(x["cross"])/2 for x in g]); gt=np.median([x["thick"] for x in g])
            if abs(c-gc)<=tol*max(th,gt,3): hit=g; break
        if hit is None: groups.append([z])
        else: hit.append(z)
    return groups

def _component_solve(path,intent):
    feats,(h,w)=_component_candidates(path)
    gh,sh=_best_family(feats["h"]); gv,sv=_best_family(feats["v"])
    axis="h" if sh>=sv else "v"; fam=gh if axis=="h" else gv
    pos=_component_positions(fam); ar=sum(x["area"] for x in fam)/(h*w)
    if not fam or not pos or ar<.02:
        return None,{"axis":axis,"area_ratio":ar}
    if intent=="BAR_INSTANCE_COUNT":
        pred=len(pos)
    else:
        by=defaultdict(int)
        for z in fam: by[z["color"]]+=z["area"]
        total=sum(by.values()); mx=max(by.values())
        pred=sum(1 for a in by.values() if a/total>=.004 and a/mx>=.012)
    return pred,{"axis":axis,"area_ratio":ar}

def solve(path,intent):
    p5,m5=_projection_solve(path,intent)
    p6,m6=_component_solve(path,intent)
    if p6 is None:
        pred=None; route="ABSTAIN_COMPONENT_NOT_APPLICABLE"
    elif p5 is None:
        pred=p6; route="COMPONENT_ONLY"
    elif m5["axis"]!=m6["axis"]:
        pred=p5; route="PROJECTION_AXIS_DISAGREEMENT"
    elif p6==p5+1:
        pred=p6; route="COMPONENT_PLUS_ONE"
    else:
        pred=p5; route="PROJECTION_DEFAULT"
    return {
        "schema":SCHEMA,
        "prediction":pred,
        "route":route,
        "projection_prediction":p5,
        "component_prediction":p6,
        "projection_axis":m5["axis"],
        "component_axis":m6["axis"],
        "persistent_learned_bytes":0,
        "external_visual_capability_calls":0,
    }
