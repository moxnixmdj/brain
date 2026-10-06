from __future__ import annotations
import numpy as np
from PIL import Image

def intervals(v,thr):
    on=v>=thr;out=[];start=None
    for i,b in enumerate(on):
        if b and start is None:start=i
        if start is not None and (not b or i==len(on)-1):
            end=i if b and i==len(on)-1 else i-1
            out.append((start,end));start=None
    return out

def detect_repeated_marks(path):
    a=np.array(Image.open(path).convert("RGB"));h,w=a.shape[:2]
    q=(a//16)*16
    colors,counts=np.unique(q.reshape(-1,3),axis=0,return_counts=True)
    candidates=[]
    for color,count in zip(colors,counts):
        ci=color.astype(int);chroma=int(ci.max()-ci.min());bright=int(ci.mean())
        if chroma<32 or bright>235 or count<0.001*h*w:continue
        mask=np.all(q==color.astype(np.uint8),axis=2)
        rs=mask.sum(1);cs=mask.sum(0)
        rints=[z for z in intervals(rs,max(8,int(0.02*w))) if 2<=z[1]-z[0]+1<=max(80,int(.2*h))]
        cints=[z for z in intervals(cs,max(8,int(0.02*h))) if 2<=z[1]-z[0]+1<=max(80,int(.2*w))]
        def score(ints,axis):
            if len(ints)<2 or len(ints)>50:return 0.0
            widths=np.array([b-a+1 for a,b in ints],float)
            cv=float(widths.std()/max(widths.mean(),1e-9))
            vec=rs if axis=="r" else cs
            occ=sum(int(vec[lo:hi+1].sum()) for lo,hi in ints)
            return len(ints)*(1/(1+cv))*occ/max(int(mask.sum()),1)
        sr,sc=score(rints,"r"),score(cints,"c")
        if max(sr,sc)>0:
            axis="rows" if sr>=sc else "cols";ints2=rints if sr>=sc else cints
            candidates.append({"score":max(sr,sc),"axis":axis,"count":len(ints2),"intervals":ints2,"color":ci.tolist()})
    candidates.sort(key=lambda x:(x["score"],x["count"]),reverse=True)
    return {"status":"DETECTED" if candidates else "NO_REPEAT_MARKS","best":candidates[0] if candidates else None,"candidate_count":len(candidates)}
