from __future__ import annotations
import json
from collections import Counter
from canonical.runtime import h100_u1_chart_stress_world_v1 as stress

def longest_run(row,fg):
    best=(0,None,None); start=None
    for i,v in enumerate(row+[False]):
        if v and start is None: start=i
        if not v and start is not None:
            length=i-start
            if length>best[0]: best=(length,start,i-1)
            start=None
    return best

def pack_box(rows,x0,y0,bg):
    v=0
    for y in range(y0,y0+5):
        for x in range(x0,x0+3):
            bit=(0<=y<len(rows) and 0<=x<len(rows[0]) and rows[y][x]!=bg)
            v=(v<<1)|int(bit)
    return v

def lookup_nearest(atlas,pattern,max_distance=2):
    scored=sorted((((int(p)^int(pattern)).bit_count(),int(d)) for p,d in atlas))
    if not scored or scored[0][0]>max_distance: return None
    if len(scored)>1 and scored[0][0]==scored[1][0]: return None
    return scored[0][1]

def parse(public_input):
    rows=[list(r) for r in public_input["rows"]]; atlas=public_input["atlas"]
    H=len(rows); W=len(rows[0])
    bg=Counter(ch for r in rows for ch in r).most_common(1)[0][0]
    fg=[[rows[y][x]!=bg for x in range(W)] for y in range(H)]

    # Longest horizontal run gives baseline; longest vertical run gives axis x.
    rr=[longest_run(fg[y],True) for y in range(H)]
    baseline=max(range(H),key=lambda y:rr[y][0])
    col_runs=[]
    for x in range(W):
        col=[fg[y][x] for y in range(H)]
        col_runs.append(longest_run(col,True))
    axis_x=max(range(W),key=lambda x:col_runs[x][0])

    # Bars: contiguous foreground height immediately above baseline.
    heights=[]
    for x in range(axis_x+1,W):
        h=0; y=baseline-1
        while y>=0 and fg[y][x]:
            h+=1; y-=1
        heights.append(h)
    bars=[]; i=0
    while i<len(heights):
        if heights[i]==0: i+=1; continue
        h=heights[i]; j=i+1
        while j<len(heights) and heights[j]==h: j+=1
        bars.append(h); i=j

    tick_pat=pack_box(rows,axis_x-4,1,bg)
    tick=lookup_nearest(atlas,tick_pat)

    # Find the leftmost solid 2x2 foreground block in the upper-right zone;
    # scope uses that as swatch. Glyph box is fixed relative to swatch.
    candidates=[]
    for y in range(0,min(8,H-1)):
        for x in range(axis_x+8,W-1):
            if all(fg[yy][xx] for yy in (y,y+1) for xx in (x,x+1)):
                candidates.append((x,y))
    if not candidates: raise ValueError("SWATCH_NOT_FOUND")
    swx,swy=min(candidates)
    legend_pat=pack_box(rows,swx+4,swy-1,bg)
    legend=lookup_nearest(atlas,legend_pat)

    return {"tick":tick,"legend":legend,"bar_count":len(bars),"values":bars}

def run():
    w=stress.generate(); out=[]
    for t in w["tasks"]:
        got=parse(t["public_input"])
        out.append({"id":t["id"],"output":got,"gold":t["gold"],"pass":got==t["gold"]})
    return {"passed":sum(x["pass"] for x in out),"total":len(out),"rows":out,"NO_CREDIT":"DEVELOPED_AFTER_STRESS_OUTCOMES"}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
