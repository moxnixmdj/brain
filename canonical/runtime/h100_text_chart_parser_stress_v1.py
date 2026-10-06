from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import h100_text_axis_legend_font_v1 as fontmod
from canonical.runtime import h100_text_axis_legend_parser_v1 as parser

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_TEXT_CHART_PARSER_STRESS_PRECOMMIT_V1.json"

def _render(spec):
    c=spec["base_chart"]; r=spec["deterministic_renderer"]
    W=int(c["canvas"]["width"]); H=int(c["canvas"]["height"])
    bg=r["background"]; axis=r["axis"]
    grid=[[bg]*W for _ in range(H)]
    xaxis=int(c["canvas"]["xaxis_y"]); yaxis=int(c["canvas"]["yaxis_x"])
    for x in range(yaxis,61): grid[xaxis][x]=axis
    for y in range(5,xaxis+1): grid[y][yaxis]=axis

    def text(txt,x,y):
        cx=x
        for ch in txt:
            glyph=fontmod.GLYPHS[ch]
            for yy,row in enumerate(glyph):
                for xx,b in enumerate(row):
                    if b=="1": grid[y+yy][cx+xx]=axis
            cx+=4

    for val in r["tick_values"]:
        y=round(xaxis-float(val)*float(c["pixels_per_unit"]))
        label=str(val); width=len(label)*4-1
        text(label,yaxis-3-width,y-2)
        grid[y][yaxis-1]=axis

    centers=list(r["category_centers"])
    for i,cat in enumerate(c["categories"]):
        center=int(centers[i])
        text(str(cat),center-1,xaxis+3)
        for j,series_name in enumerate(("R","S")):
            value=float(c["series"][series_name][i])
            ph=round(value*float(c["pixels_per_unit"]))
            x0=center-4+j*5
            pix=r["series_pixels"][series_name]
            for y in range(xaxis-ph,xaxis):
                for x in range(x0,x0+int(r["bar_width"])):
                    grid[y][x]=pix

    lx=45; ly=2
    for idx,name in enumerate(c["legend_order"]):
        y=ly+idx*7; pix=r["series_pixels"][name]
        for yy in range(y,y+2):
            for xx in range(lx,lx+4): grid[yy][xx]=pix
        text(name,lx+6,y-1)
    return ["".join(row) for row in grid]

def _transform(rows,t):
    kind=t["kind"]
    if kind=="CHAR_MAP":
        m=t["map"]
        return ["".join(m.get(ch,ch) for ch in row) for row in rows]
    if kind=="PAD":
        bg=rows[0][0]
        left=int(t["left"]); right=int(t["right"]); top=int(t["top"]); bottom=int(t["bottom"])
        W=len(rows[0])+left+right
        return [bg*W for _ in range(top)]+[bg*left+r+bg*right for r in rows]+[bg*W for _ in range(bottom)]
    if kind=="NEAREST_NEIGHBOR_INTEGER_SCALE":
        s=int(t["factor"])
        out=[]
        for row in rows:
            rr="".join(ch*s for ch in row)
            out.extend([rr]*s)
        return out
    raise ValueError("TRANSFORM_UNKNOWN")

def run():
    spec=json.loads(PRE.read_text())
    base=_render(spec)
    gold={"categories":spec["base_chart"]["categories"],"series":spec["base_chart"]["series"]}
    rows=[]
    for task in spec["tasks"]:
        image=_transform(base,task["transform"])
        error=None
        try:
            got=parser.parse(image)
        except Exception as exc:
            got=None; error=type(exc).__name__+":"+str(exc)
        rows.append({"id":task["id"],"pass":got==gold,"output":got,"error":error})
    return {
        "schema":"PROJECT_BRAIN_H100_TEXT_CHART_PARSER_STRESS_V1",
        "parser_modified":False,
        "passed":sum(r["pass"] for r in rows),
        "total":len(rows),
        "rows":rows,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
