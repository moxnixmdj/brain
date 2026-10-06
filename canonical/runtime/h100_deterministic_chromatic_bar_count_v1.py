from __future__ import annotations
from PIL import Image
import numpy as np

class ChromaticBarError(ValueError): pass

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

def _group(rects,ori,w,h):
    if len(rects)<2:return []
    tol=max(4,int(0.03*(w if ori=="h" else h)))
    best=[]
    fields=("x0","x1") if ori=="h" else ("y0","y1")
    for side in fields:
        for r in rects:
            g=[z for z in rects if abs(z[side]-r[side])<=tol]
            if len(g)>len(best):best=g
    return best

def count_bars(path):
    a=np.array(Image.open(path).convert("RGB")).astype(np.int16)
    h,w=a.shape[:2]
    mx=a.max(2); mn=a.min(2); chroma=mx-mn; mean=a.mean(2)
    mask=(chroma>=28)&(mean<=240)
    comps=_components(mask)
    horizontal=[]; vertical=[]
    min_area=max(60,int(0.00015*h*w))
    for n,x0,y0,x1,y1 in comps:
        bw=x1-x0+1; bh=y1-y0+1; box=bw*bh
        if n<min_area or bw<5 or bh<5: continue
        fill=n/box
        if fill<0.45: continue
        r={"x0":x0,"y0":y0,"x1":x1,"y1":y1,"area":n,"bbox_area":box,"fill":fill}
        if bw>=1.5*bh and bw>=15: horizontal.append(r)
        if bh>=1.5*bw and bh>=15: vertical.append(r)
    hg=_group(horizontal,"h",w,h); vg=_group(vertical,"v",w,h)
    best=hg if len(hg)>=len(vg) else vg
    ori="horizontal" if best is hg else "vertical"
    if len(best)<2: raise ChromaticBarError("NO_ALIGNED_CHROMATIC_BAR_FAMILY")
    return {"prediction":len(best),"orientation":ori,"bars":best,"horizontal_candidates":len(horizontal),"vertical_candidates":len(vertical)}
