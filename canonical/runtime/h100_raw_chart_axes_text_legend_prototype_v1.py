from __future__ import annotations
import json
from collections import deque
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_RAW_CHART_AXES_TEXT_LEGEND_HOLDOUT_PRECOMMIT_V1.json"

class ChartParserError(ValueError): pass

def _pack_glyph(rows,x0,y0):
    v=0
    for y in range(y0,y0+5):
        for x in range(x0,x0+3):
            v=(v<<1) | (1 if rows[y][x]=="3" else 0)
    return v

def _lookup(atlas,pattern):
    hits=[int(d) for p,d in atlas if int(p)==int(pattern)]
    if len(hits)!=1: raise ChartParserError("GLYPH_LOOKUP_NOT_UNIQUE")
    return hits[0]

def _components(rows,symbol):
    h=len(rows); w=len(rows[0]); seen=set(); out=[]
    for y in range(h):
        for x in range(w):
            if rows[y][x]!=symbol or (y,x) in seen: continue
            q=deque([(y,x)]); seen.add((y,x)); pts=[]
            while q:
                yy,xx=q.popleft(); pts.append((yy,xx))
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<h and 0<=nx<w and rows[ny][nx]==symbol and (ny,nx) not in seen:
                        seen.add((ny,nx)); q.append((ny,nx))
            ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
            out.append({"x0":min(xs),"x1":max(xs),"y0":min(ys),"y1":max(ys),"area":len(pts)})
    return out

def parse(public_input):
    rows=public_input["rows"]; atlas=public_input["atlas"]
    if not rows or len({len(r) for r in rows})!=1: raise ChartParserError("RASTER_SHAPE")
    h=len(rows); w=len(rows[0])

    # Axis inference from longest row/column of symbol 1.
    row_counts=[sum(c=="1" for c in row) for row in rows]
    col_counts=[sum(rows[y][x]=="1" for y in range(h)) for x in range(w)]
    baseline=max(range(h),key=lambda y:row_counts[y])
    axis_x=max(range(w),key=lambda x:col_counts[x])
    if row_counts[baseline]<3 or col_counts[axis_x]<3: raise ChartParserError("AXES_NOT_FOUND")

    bars=[]
    for c in _components(rows,"2"):
        # Bars must sit immediately above the inferred baseline and be rectangular.
        if c["y1"]!=baseline-1: continue
        height=baseline-c["y0"]
        width=c["x1"]-c["x0"]+1
        if c["area"]!=height*width: continue
        bars.append((c["x0"],height))
    bars.sort()
    if not bars: raise ChartParserError("NO_BARS")

    swatches=_components(rows,"4")
    if len(swatches)!=1: raise ChartParserError("SWATCH_NOT_UNIQUE")
    sw=swatches[0]

    # Scope-frozen layout relation: 3x5 tick glyph immediately left of y-axis
    # with one blank column; legend glyph starts two blank columns after swatch.
    tick_x=axis_x-4; tick_y=1
    legend_x=sw["x1"]+3; legend_y=1
    if min(tick_x,legend_x)<0 or tick_x+2>=w or legend_x+2>=w or max(tick_y,legend_y)+4>=h:
        raise ChartParserError("GLYPH_BOX_OUT_OF_RANGE")

    tick=_lookup(atlas,_pack_glyph(rows,tick_x,tick_y))
    legend=_lookup(atlas,_pack_glyph(rows,legend_x,legend_y))
    return {"tick":tick,"legend":legend,"bar_count":len(bars),"values":[v for _,v in bars]}

def run():
    spec=json.loads(PRE.read_text()); out=[]
    for t in spec["tasks"]:
        got=parse(t["public_input"])
        out.append({"id":t["id"],"output":got,"pass":got==t["gold"]})
    return {
      "schema":"PROJECT_BRAIN_H100_RAW_CHART_AXES_TEXT_LEGEND_PROTOTYPE_V1",
      "passed":sum(x["pass"] for x in out),
      "total":len(out),
      "rows":out,
      "learned_bits":0,
      "hard_nonclaim":"DISCOVERY_PROTOTYPE_EXECUTED_ON_THE_SAME_FROZEN_HOLDOUT_USED_TO_DEVELOP_IT__NO_GENERALIZATION_OR_U1_COMPLEXITY_CREDIT"
    }
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
