from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import h100_text_axis_legend_font_v1 as fontmod
from canonical.runtime import h100_text_axis_legend_parser_v2 as parser

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_TEXT_CHART_SCALE_REPAIR_FRESH_HOLDOUT_PRECOMMIT_V1.json"

def _render(chart):
    W=72; H=34; bg="."; axis="k"
    grid=[[bg]*W for _ in range(H)]
    xaxis=25; yaxis=12
    for x in range(yaxis,61): grid[xaxis][x]=axis
    for y in range(5,xaxis+1): grid[y][yaxis]=axis
    def text(txt,x,y):
        cx=x
        for ch in txt:
            for yy,row in enumerate(fontmod.GLYPHS[ch]):
                for xx,b in enumerate(row):
                    if b=="1": grid[y+yy][cx+xx]=axis
            cx+=4
    ticks=[0,5,10,15] if float(chart["pixels_per_unit"])==1.0 else [0,10,20,30]
    for val in ticks:
        y=round(xaxis-float(val)*float(chart["pixels_per_unit"]))
        lab=str(val); width=len(lab)*4-1
        text(lab,yaxis-3-width,y-2); grid[y][yaxis-1]=axis
    centers=[24,38,52]
    pix={"R":"r","S":"s"}
    for i,cat in enumerate(chart["categories"]):
        center=centers[i]; text(cat,center-1,xaxis+3)
        for j,name in enumerate(("R","S")):
            h=round(float(chart["series"][name][i])*float(chart["pixels_per_unit"]))
            x0=center-4+j*5
            for y in range(xaxis-h,xaxis):
                for x in range(x0,x0+3): grid[y][x]=pix[name]
    lx=45; ly=2
    for idx,name in enumerate(chart["legend_order"]):
        y=ly+idx*7; ch=pix[name]
        for yy in range(y,y+2):
            for xx in range(lx,lx+4): grid[yy][xx]=ch
        text(name,lx+6,y-1)
    return ["".join(r) for r in grid]

def _transform(rows,t):
    cmap=t.get("char_map")
    if cmap:
        rows=["".join(cmap.get(ch,ch) for ch in row) for row in rows]
    s=int(t["scale"])
    out=[]
    for row in rows:
        rr="".join(ch*s for ch in row)
        out.extend([rr]*s)
    pad=t.get("pad") or {}
    top=int(pad.get("top",0)); left=int(pad.get("left",0))
    if top or left:
        bg=out[0][0]
        out=[bg*(len(out[0])+left) for _ in range(top)]+[bg*left+r for r in out]
    return out

def run():
    spec=json.loads(PRE.read_text())
    rows=[]
    for chart in spec["base_charts"]:
        image=_transform(_render(chart),chart["transform"])
        gold={"categories":chart["categories"],"series":chart["series"]}
        err=None
        try: got=parser.parse(image)
        except Exception as exc:
            got=None; err=type(exc).__name__+":"+str(exc)
        rows.append({"id":chart["id"],"pass":got==gold,"output":got,"error":err})
    return {"schema":"PROJECT_BRAIN_H100_TEXT_CHART_SCALE_REPAIR_V1","passed":sum(r["pass"] for r in rows),"total":len(rows),"rows":rows}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
