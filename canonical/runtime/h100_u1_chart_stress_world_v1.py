from __future__ import annotations
import copy,json
from canonical.runtime import h100_u1_chart_fresh_world_generator_v1 as base

def _rows(task):
    return [list(r) for r in task["public_input"]["rows"]]

def generate():
    world=base.generate()
    src=world["tasks"][0]
    gold=copy.deepcopy(src["gold"])
    atlas=copy.deepcopy(src["public_input"]["atlas"])
    out=[]

    # 1 palette permutation.
    g=_rows(src); mp={"1":"3","2":"4","3":"1","4":"2"}
    for y,row in enumerate(g):
        for x,ch in enumerate(row):
            if ch in mp: g[y][x]=mp[ch]
    out.append({"id":"PALETTE_PERMUTE","public_input":{"rows":["".join(r) for r in g],"atlas":atlas},"gold":gold})

    # 2 monochrome collapse.
    g=_rows(src)
    for y,row in enumerate(g):
        for x,ch in enumerate(row):
            if ch!="0": g[y][x]="1"
    out.append({"id":"MONOCHROME","public_input":{"rows":["".join(r) for r in g],"atlas":atlas},"gold":gold})

    # 3 move symbol-4 swatch and right-side text one row down and one column right.
    g=_rows(src); H=len(g); W=len(g[0])
    pts=[]
    for y in range(H):
        for x in range(W):
            if g[y][x]=="4" or (x>=24 and g[y][x]=="3"):
                pts.append((y,x,g[y][x])); g[y][x]="0"
    for y,x,ch in pts:
        if y+1<H and x+1<W: g[y+1][x+1]=ch
    out.append({"id":"LEGEND_SHIFT","public_input":{"rows":["".join(r) for r in g],"atlas":atlas},"gold":gold})

    # 4 erase the first foreground pixel in the left-side tick glyph.
    g=_rows(src); done=False
    for y in range(1,6):
        for x in range(0,8):
            if g[y][x]=="3":
                g[y][x]="0"; done=True; break
        if done: break
    out.append({"id":"TICK_ONE_PIXEL_ERASURE","public_input":{"rows":["".join(r) for r in g],"atlas":atlas},"gold":gold})
    return {"schema":"PROJECT_BRAIN_H100_U1_CHART_STRESS_WORLD_V1","tasks":out}

if __name__=="__main__": print(json.dumps(generate(),indent=2,sort_keys=True))
