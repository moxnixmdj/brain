from __future__ import annotations
from PIL import Image
import numpy as np

class BarGeometryError(ValueError): pass

def intervals(v,thr):
    on=v>=thr
    out=[]; start=None
    for i,b in enumerate(on):
        if b and start is None: start=i
        if start is not None and (not b or i==len(on)-1):
            end=i if b and i==len(on)-1 else i-1
            out.append((start,end))
            start=None
    return out

def count_bars(path):
    a=np.array(Image.open(path).convert("RGB"))
    h,w=a.shape[:2]
    q=(a//16)*16
    colors,counts=np.unique(q.reshape(-1,3),axis=0,return_counts=True)
    candidates=[]
    for color,count in zip(colors,counts):
        ci=color.astype(int)
        if int(ci.max()-ci.min())<32 or int(ci.mean())>235 or count<0.001*h*w:
            continue
        mask=np.all(q==color.astype(np.uint8),axis=2)
        rs=mask.sum(1); cs=mask.sum(0)
        rints=[z for z in intervals(rs,max(8,int(0.02*w))) if 2<=z[1]-z[0]+1<=max(80,int(.2*h))]
        cints=[z for z in intervals(cs,max(8,int(0.02*h))) if 2<=z[1]-z[0]+1<=max(80,int(.2*w))]
        for axis,ints,vec in (("rows",rints,rs),("cols",cints,cs)):
            if not (2<=len(ints)<=50): continue
            widths=np.array([b-a+1 for a,b in ints],float)
            cv=float(widths.std()/max(widths.mean(),1e-9))
            occ=sum(int(vec[lo:hi+1].sum()) for lo,hi in ints)
            score=len(ints)*(1/(1+cv))*occ/max(int(mask.sum()),1)
            candidates.append({"score":score,"count":len(ints),"axis":axis,"color":tuple(int(x) for x in ci),"intervals":ints})
    if not candidates: raise BarGeometryError("NO_BAR_CANDIDATE")
    candidates.sort(key=lambda x:(x["score"],x["count"]),reverse=True)
    return {"prediction":candidates[0]["count"],"winner":candidates[0],"candidate_count":len(candidates)}
