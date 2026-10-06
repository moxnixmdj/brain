from __future__ import annotations
from PIL import Image
import numpy as np

class RectangleBarError(ValueError): pass

def _components(mask):
    h,w=mask.shape
    seen=np.zeros_like(mask,dtype=bool)
    out=[]
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

def _overlap_1d(a0,a1,b0,b1):
    lo=max(a0,b0); hi=min(a1,b1)
    return max(0,hi-lo+1)

def _dedupe(rects,orientation):
    # Merge nearly identical rectangles from adjacent quantized shades.
    rects=sorted(rects,key=lambda r:r["area"],reverse=True)
    kept=[]
    for r in rects:
        dup=False
        for k in kept:
            ix=_overlap_1d(r["x0"],r["x1"],k["x0"],k["x1"])
            iy=_overlap_1d(r["y0"],r["y1"],k["y0"],k["y1"])
            inter=ix*iy
            if inter/min(r["bbox_area"],k["bbox_area"])>=0.70:
                dup=True; break
        if not dup: kept.append(r)
    return kept

def count_bars(path):
    a=np.array(Image.open(path).convert("RGB"))
    h,w=a.shape[:2]
    # Slightly finer than the interval parser; color is only a segmentation cue.
    q=(a//8)*8
    colors,counts=np.unique(q.reshape(-1,3),axis=0,return_counts=True)
    horizontal=[]; vertical=[]
    min_area=max(40,int(0.00012*h*w))
    for color,count in zip(colors,counts):
        ci=color.astype(int)
        # Exclude near-white backgrounds, but allow gray bars.
        if int(ci.mean())>245: continue
        mask=np.all(q==color.astype(np.uint8),axis=2)
        for n,x0,y0,x1,y1 in _components(mask):
            bw=x1-x0+1; bh=y1-y0+1; box=bw*bh
            if n<min_area or bw<4 or bh<4 or box<=0: continue
            fill=n/box
            if fill<0.55: continue
            # Text glyphs tend to be small/irregular; bars are filled elongated rectangles.
            if bw>=1.6*bh and bw>=12:
                horizontal.append({"x0":x0,"y0":y0,"x1":x1,"y1":y1,"area":n,"bbox_area":box,"fill":fill})
            if bh>=1.6*bw and bh>=12:
                vertical.append({"x0":x0,"y0":y0,"x1":x1,"y1":y1,"area":n,"bbox_area":box,"fill":fill})
    horizontal=_dedupe(horizontal,"horizontal")
    vertical=_dedupe(vertical,"vertical")
    # Reject isolated decorative rectangles. Bars should form a repeated aligned family.
    def aligned(rects,ori):
        if len(rects)<2: return []
        if ori=="horizontal":
            # horizontal bars share a similar left or right baseline
            vals=[r["x0"] for r in rects]+[r["x1"] for r in rects]
            tol=max(3,int(0.02*w))
            best=[]
            for side in ("x0","x1"):
                for r in rects:
                    grp=[z for z in rects if abs(z[side]-r[side])<=tol]
                    if len(grp)>len(best): best=grp
            return best
        else:
            tol=max(3,int(0.02*h))
            best=[]
            for side in ("y0","y1"):
                for r in rects:
                    grp=[z for z in rects if abs(z[side]-r[side])<=tol]
                    if len(grp)>len(best): best=grp
            return best
    hg=aligned(horizontal,"horizontal")
    vg=aligned(vertical,"vertical")
    best=hg if len(hg)>=len(vg) else vg
    ori="horizontal" if best is hg else "vertical"
    if len(best)<2: raise RectangleBarError("NO_ALIGNED_BAR_FAMILY")
    return {"prediction":len(best),"orientation":ori,"bars":best,"horizontal_candidates":len(horizontal),"vertical_candidates":len(vertical)}
