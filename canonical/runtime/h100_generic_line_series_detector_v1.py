from __future__ import annotations
import math
from collections import Counter
from canonical.runtime.h100_generic_repeated_mark_detector_purepy_v1 import read_png_rgb

def _unit_white_vector(color):
    v=[255.0-c for c in color]
    n=math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n else [0.0,0.0,0.0]

def _cos(a,b):
    return sum(x*y for x,y in zip(a,b))

def detect_line_series(path):
    w,h,rows=read_png_rgb(path)
    q=[[(r//32*32,g//32*32,b//32*32) for r,g,b in row] for row in rows]
    counts=Counter(px for row in q for px in row)
    colors=[]
    for color,count in counts.items():
        if max(color)-min(color)<32 or sum(color)/3>240 or count<30:continue
        xs=[];ys=[]
        for y,row in enumerate(q):
            for x,px in enumerate(row):
                if px==color:xs.append(x);ys.append(y)
        if not xs:continue
        spanx=(max(xs)-min(xs)+1)/w
        if spanx<0.70:continue
        colors.append((count,color,_unit_white_vector(color)))
    colors.sort(reverse=True)
    clusters=[]
    for count,color,v in colors:
        best=-1;bi=None
        for i,c in enumerate(clusters):
            sim=_cos(v,c["v"])
            if sim>best:best=sim;bi=i
        if bi is not None and best>=0.995:
            c=clusters[bi];tot=c["weight"]+count
            nv=[(c["v"][j]*c["weight"]+v[j]*count)/tot for j in range(3)]
            n=math.sqrt(sum(x*x for x in nv));c["v"]=[x/n for x in nv];c["weight"]=tot;c["colors"].append((count,color))
        else:
            clusters.append({"v":v,"weight":count,"colors":[(count,color)]})
    clusters.sort(key=lambda c:c["weight"],reverse=True)
    if not clusters:return {"series_count":0,"clusters":[]}
    floor=0.5*clusters[0]["weight"]
    strong=[c for c in clusters if c["weight"]>=floor]
    return {"series_count":len(strong),"strong_weights":[c["weight"] for c in strong],"all_weights":[c["weight"] for c in clusters]}
