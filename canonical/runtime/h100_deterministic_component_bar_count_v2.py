from __future__ import annotations
from PIL import Image
import numpy as np

class ComponentBarError(ValueError): pass

def _components(mask):
    h,w=mask.shape
    seen=np.zeros_like(mask,dtype=bool); out=[]
    for y in range(h):
        for x in range(w):
            if not mask[y,x] or seen[y,x]: continue
            stack=[(y,x)]; seen[y,x]=1
            minx=maxx=x; miny=maxy=y; n=0
            while stack:
                yy,xx=stack.pop(); n+=1
                minx=min(minx,xx); maxx=max(maxx,xx); miny=min(miny,yy); maxy=max(maxy,yy)
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<h and 0<=nx<w and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=1; stack.append((ny,nx))
            out.append((n,minx,miny,maxx,maxy))
    return out

def _rects_from_mask(mask,h,w,channel):
    rects_h=[]; rects_v=[]
    min_area=max(45,int(0.00010*h*w))
    for n,x0,y0,x1,y1 in _components(mask):
        bw=x1-x0+1; bh=y1-y0+1; box=bw*bh
        if n<min_area or bw<4 or bh<4: continue
        fill=n/box
        if fill<0.34: continue
        r={"x0":x0,"y0":y0,"x1":x1,"y1":y1,"area":n,"bbox_area":box,"fill":fill,"channel":channel}
        if bw>=1.25*bh and bw>=12: rects_h.append(r)
        if bh>=1.25*bw and bh>=12: rects_v.append(r)
    return rects_h,rects_v

def _dedupe(rects):
    rects=sorted(rects,key=lambda r:r["area"],reverse=True)
    kept=[]
    for r in rects:
        dup=False
        for k in kept:
            ix=max(0,min(r["x1"],k["x1"])-max(r["x0"],k["x0"])+1)
            iy=max(0,min(r["y1"],k["y1"])-max(r["y0"],k["y0"])+1)
            inter=ix*iy
            if inter/min(r["bbox_area"],k["bbox_area"])>=0.65:
                dup=True;break
        if not dup: kept.append(r)
    return kept

def _best_aligned(rects,ori,w,h):
    if len(rects)<2:return []
    tol=max(5,int(0.035*(w if ori=="h" else h)))
    sides=("x0","x1") if ori=="h" else ("y0","y1")
    best=[]
    for side in sides:
        vals=rects
        for r in vals:
            g=[z for z in vals if abs(z[side]-r[side])<=tol]
            # prefer larger groups, then larger total bar area
            if (len(g),sum(z["area"] for z in g))>(len(best),sum(z["area"] for z in best) if best else 0):
                best=g
    return best

def count_bars(path):
    a=np.array(Image.open(path).convert("RGB")).astype(np.int16)
    h,w=a.shape[:2]
    mx=a.max(2);mn=a.min(2);chroma=mx-mn;mean=a.mean(2)

    chrom=(chroma>=24)&(mean<=242)
    # Gray/black filled bars: exclude near-white and near-black text-heavy pixels.
    ach=(chroma<24)&(mean>=45)&(mean<=225)

    h1,v1=_rects_from_mask(chrom,h,w,"chromatic")
    h2,v2=_rects_from_mask(ach,h,w,"achromatic")
    hs=_dedupe(h1+h2); vs=_dedupe(v1+v2)

    hg=_best_aligned(hs,"h",w,h); vg=_best_aligned(vs,"v",w,h)
    def score(g): return (len(g),sum(r["area"] for r in g))
    best=hg if score(hg)>=score(vg) else vg
    ori="horizontal" if best is hg else "vertical"
    if len(best)<2: raise ComponentBarError("NO_ALIGNED_BAR_FAMILY")
    return {"prediction":len(best),"orientation":ori,"bars":best,"horizontal_candidates":len(hs),"vertical_candidates":len(vs)}
