from __future__ import annotations
import cv2, math, numpy as np

class CVBarFamilyError(ValueError): pass

def _rect_candidates(path):
    im=cv2.imread(path)
    if im is None: raise CVBarFamilyError("IMAGE_READ_FAILED")
    h,w=im.shape[:2]
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    S=hsv[:,:,1]; V=hsv[:,:,2]
    masks=[
        ((S>=30)&(V<=245)).astype(np.uint8)*255,
        ((S<30)&(V>=70)&(V<=205)).astype(np.uint8)*255,
    ]
    out={"h":[],"v":[]}
    for mi,mask in enumerate(masks):
        mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area=cv2.contourArea(c)
            if area<max(35,0.00008*h*w): continue
            x,y,bw,bh=cv2.boundingRect(c)
            fill=area/max(bw*bh,1)
            if fill<0.35 or bw<4 or bh<4: continue
            r={"x0":x,"x1":x+bw-1,"y0":y,"y1":y+bh-1,"bw":bw,"bh":bh,"area":float(area),"fill":float(fill),"mask":mi}
            if bw>=1.15*bh and bw>=10: out["h"].append(r)
            if bh>=1.15*bw and bh>=10: out["v"].append(r)
    return out,w,h

def _family_score(group,ori,w,h):
    if len(group)<2: return -1e9
    if ori=="h":
        thickness=np.array([r["bh"] for r in group],float)
        centers=np.array(sorted((r["y0"]+r["y1"])/2 for r in group))
        b0=np.array([r["x0"] for r in group],float)
        b1=np.array([r["x1"] for r in group],float)
        base=min(np.std(b0)/max(w,1),np.std(b1)/max(w,1))
    else:
        thickness=np.array([r["bw"] for r in group],float)
        centers=np.array(sorted((r["x0"]+r["x1"])/2 for r in group))
        b0=np.array([r["y0"] for r in group],float)
        b1=np.array([r["y1"] for r in group],float)
        base=min(np.std(b0)/max(h,1),np.std(b1)/max(h,1))
    tcv=np.std(thickness)/max(np.mean(thickness),1)
    gaps=np.diff(centers)
    scv=np.std(gaps)/max(np.mean(gaps),1) if len(gaps)>1 else 0
    return len(group)-2.0*tcv-1.5*scv-8.0*base+0.1*math.log1p(sum(r["area"] for r in group))

def _best_family(rects,ori,w,h):
    dim=w if ori=="h" else h
    sides=("x0","x1") if ori=="h" else ("y0","y1")
    best=(None,-1e9)
    for side in sides:
        for anchor in rects:
            for frac in (0.015,0.03,0.06,0.12):
                tol=max(4,frac*dim)
                g=[r for r in rects if abs(r[side]-anchor[side])<=tol]
                if len(g)<2: continue
                th=np.array([r["bh"] if ori=="h" else r["bw"] for r in g],float)
                med=np.median(th)
                for ratio in (0.25,0.45,0.75):
                    gg=[r for r in g if abs((r["bh"] if ori=="h" else r["bw"])-med)<=max(2,ratio*med)]
                    s=_family_score(gg,ori,w,h)
                    if s>best[1]: best=(gg,s)
    return best

def count_bars(path):
    rs,w,h=_rect_candidates(path)
    hg,hs=_best_family(rs["h"],"h",w,h)
    vg,vs=_best_family(rs["v"],"v",w,h)
    group,ori,score=(hg,"horizontal",hs) if hs>=vs else (vg,"vertical",vs)
    if not group or len(group)<2: raise CVBarFamilyError("NO_BAR_FAMILY")
    return {
        "prediction":len(group),
        "orientation":ori,
        "score":float(score),
        "horizontal_candidates":len(rs["h"]),
        "vertical_candidates":len(rs["v"]),
    }
