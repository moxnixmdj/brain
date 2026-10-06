from __future__ import annotations
from collections import Counter, deque
from pathlib import Path
import json, math

SCHEMA="PROJECT_BRAIN_H100_VISION_ORIENTATION_INVARIANT_PARSER_V1"
ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_VISION_ORIENTATION_INVARIANT_FRESH_HOLDOUT_PRECOMMIT_V1.json"

class VisionParserError(ValueError): pass

def _rect_components(rows):
    if not isinstance(rows,list) or not rows or any(not isinstance(r,str) for r in rows):
        raise VisionParserError("ROWS_INVALID")
    widths={len(r) for r in rows}
    if len(widths)!=1 or next(iter(widths))<2:
        raise VisionParserError("ROW_WIDTH_INVALID")
    h=len(rows); w=len(rows[0])
    chars=Counter(ch for r in rows for ch in r)
    bg=chars.most_common(1)[0][0]
    mask=[[rows[y][x]!=bg for x in range(w)] for y in range(h)]
    seen=[[False]*w for _ in range(h)]
    comps=[]
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]: continue
            q=deque([(y,x)]); seen[y][x]=True
            pts=[]
            while q:
                yy,xx=q.popleft(); pts.append((yy,xx))
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<h and 0<=nx<w and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx]=True; q.append((ny,nx))
            ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
            y0,y1=min(ys),max(ys); x0,x1=min(xs),max(xs)
            bh=y1-y0+1; bw=x1-x0+1; area=len(pts)
            fill=area/(bh*bw)
            if area>=4 and fill>=0.95:
                comps.append({"x0":x0,"x1":x1,"y0":y0,"y1":y1,"w":bw,"h":bh,"area":area})
    if len(comps)<2:
        raise VisionParserError("TOO_FEW_RECT_COMPONENTS")
    return comps

def _variance(values):
    m=sum(values)/len(values)
    return sum((x-m)**2 for x in values)/len(values)

def parse(rows):
    comps=_rect_components(rows)
    bottoms=[c["y1"] for c in comps]
    lefts=[c["x0"] for c in comps]
    # Vertical bars share a baseline (bottoms align). Horizontal bars share a left edge.
    vscore=_variance(bottoms)
    hscore=_variance(lefts)
    if abs(vscore-hscore)<1e-12:
        # Tie-break by aggregate aspect ratio.
        tall=sum(c["h"] for c in comps)
        wide=sum(c["w"] for c in comps)
        orientation="vertical" if tall>=wide else "horizontal"
    else:
        orientation="vertical" if vscore<hscore else "horizontal"
    if orientation=="vertical":
        comps=sorted(comps,key=lambda c:(c["x0"],c["y0"]))
        values=[c["h"] for c in comps]
    else:
        comps=sorted(comps,key=lambda c:(c["y0"],c["x0"]))
        values=[c["w"] for c in comps]
    return {"orientation":orientation,"bar_count":len(comps),"values":values}

def run():
    spec=json.loads(PRE.read_text())
    rows=[]
    for task in spec["tasks"]:
        got=parse(task["public_input"]["rows"])
        rows.append({"id":task["id"],"pass":got==task["gold"],"output":got})
    return {
      "schema":SCHEMA,
      "status":"PASS__4_OF_4_FRESH_RASTER_HOLDOUT__ZERO_TARGET_BITS" if all(r["pass"] for r in rows) and len(rows)==4 else "FAIL__VISION_RESIDUAL",
      "passed":sum(r["pass"] for r in rows),
      "total":len(rows),
      "rows":rows,
      "target_adapted_persistent_bits":0,
      "generic_parser_code_bytes":len(Path(__file__).read_bytes()),
      "hard_nonclaims":["SYNTHETIC_RECTANGULAR_BAR_RASTERS_ONLY","NO_OCR_OR_FREEFORM_CHART_UNDERSTANDING"]
    }

if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
