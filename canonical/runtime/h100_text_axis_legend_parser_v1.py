from __future__ import annotations
from collections import Counter, defaultdict

from canonical.runtime import h100_text_axis_legend_font_v1 as fontmod

class TextChartParserError(ValueError):
    pass

GLYPHS=fontmod.GLYPHS

def _axis(rows):
    if not isinstance(rows,list) or not rows or any(not isinstance(r,str) for r in rows):
        raise TextChartParserError("ROWS_INVALID")
    if len({len(r) for r in rows})!=1:
        raise TextChartParserError("ROW_WIDTH_MISMATCH")
    cnt=Counter("".join(rows))
    bg=cnt.most_common(1)[0][0]
    chars=[c for c in cnt if c!=bg]
    if not chars:
        raise TextChartParserError("NO_FOREGROUND")
    H=len(rows); W=len(rows[0])
    def runs(ch):
        mh=mv=0
        for row in rows:
            cur=0
            for c in row:
                cur=cur+1 if c==ch else 0
                mh=max(mh,cur)
        for x in range(W):
            cur=0
            for y in range(H):
                cur=cur+1 if rows[y][x]==ch else 0
                mv=max(mv,cur)
        return mh,mv
    score={c:runs(c) for c in chars}
    axis=max(chars,key=lambda c:(min(score[c]),sum(score[c])))
    rc=[sum(c==axis for c in row) for row in rows]
    cc=[sum(rows[y][x]==axis for y in range(H)) for x in range(W)]
    xaxis=max(range(H),key=rc.__getitem__)
    yaxis=max(range(W),key=cc.__getitem__)
    return bg,axis,xaxis,yaxis

def _scan_glyphs(rows,axis,x0,x1,y0,y1,allowed):
    H=len(rows); W=len(rows[0])
    x0=max(0,x0); x1=min(W,x1); y0=max(0,y0); y1=min(H,y1)
    found=[]
    for y in range(y0,max(y0,y1-4)):
        for x in range(x0,max(x0,x1-2)):
            pat=["".join("1" if rows[y+dy][x+dx]==axis else "0" for dx in range(3)) for dy in range(5)]
            for ch,glyph in GLYPHS.items():
                if ch in allowed and pat==glyph:
                    found.append({"text":ch,"x0":x,"x1":x+2,"y0":y,"y1":y+4,"cx":x+1.0,"cy":y+2.0})
    chosen=[]
    for c in sorted(found,key=lambda z:(z["y0"],z["x0"],z["text"])):
        overlap=any(not(c["x1"]<d["x0"] or c["x0"]>d["x1"] or c["y1"]<d["y0"] or c["y0"]>d["y1"]) for d in chosen)
        if not overlap:
            chosen.append(c)
    return chosen

def _tokens(glyphs):
    by_y=defaultdict(list)
    for g in glyphs:
        by_y[g["y0"]].append(g)
    groups=[]
    for y in sorted(by_y):
        cur=[]
        for g in sorted(by_y[y],key=lambda z:z["x0"]):
            if cur and g["x0"]-cur[-1]["x1"]>2:
                groups.append(cur); cur=[]
            cur.append(g)
        if cur:
            groups.append(cur)
    out=[]
    for grp in groups:
        out.append({
            "text":"".join(g["text"] for g in grp),
            "x0":grp[0]["x0"],"x1":grp[-1]["x1"],
            "y0":grp[0]["y0"],"y1":grp[0]["y1"],
            "cx":(grp[0]["x0"]+grp[-1]["x1"])/2.0,
            "cy":grp[0]["y0"]+2.0,
        })
    return out

def _components(rows,ch):
    H=len(rows); W=len(rows[0]); seen=set(); out=[]
    for y in range(H):
        for x in range(W):
            if rows[y][x]!=ch or (y,x) in seen:
                continue
            stack=[(y,x)]; seen.add((y,x)); pts=[]
            while stack:
                yy,xx=stack.pop(); pts.append((yy,xx))
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<H and 0<=nx<W and rows[ny][nx]==ch and (ny,nx) not in seen:
                        seen.add((ny,nx)); stack.append((ny,nx))
            ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
            out.append({
                "char":ch,"x0":min(xs),"x1":max(xs),"y0":min(ys),"y1":max(ys),
                "w":max(xs)-min(xs)+1,"h":max(ys)-min(ys)+1,
                "cx":(min(xs)+max(xs))/2.0,"cy":(min(ys)+max(ys))/2.0
            })
    return out

def parse(rows):
    bg,axis,xaxis,yaxis=_axis(rows)
    digits=set("0123456789")
    letters=set(ch for ch in GLYPHS if ch not in digits)

    y_ticks=_tokens(_scan_glyphs(rows,axis,0,yaxis-1,0,len(rows),digits))
    x_labels=_tokens(_scan_glyphs(rows,axis,yaxis+2,len(rows[0]),xaxis+2,len(rows),letters))
    legend_labels=_tokens(_scan_glyphs(rows,axis,yaxis+5,len(rows[0]),0,max(0,xaxis-7),letters))

    y_ticks=[t for t in y_ticks if t["text"].isdigit()]
    x_labels=[t for t in x_labels if len(t["text"])==1]
    legend_labels=[t for t in legend_labels if len(t["text"])==1]
    if len(y_ticks)<2 or not x_labels or not legend_labels:
        raise TextChartParserError("INSUFFICIENT_TEXT_STRUCTURE")

    pairs=sorted({(t["cy"],int(t["text"])) for t in y_ticks})
    mean_y=sum(y for y,_ in pairs)/len(pairs)
    mean_v=sum(v for _,v in pairs)/len(pairs)
    den=sum((y-mean_y)**2 for y,_ in pairs)
    if den==0:
        raise TextChartParserError("TICK_SCALE_DEGENERATE")
    slope=sum((y-mean_y)*(v-mean_v) for y,v in pairs)/den
    intercept=mean_v-slope*mean_y

    colored=set("".join(rows))-{bg,axis}
    comps=[]
    for ch in colored:
        comps.extend(_components(rows,ch))
    legend_swatches=[c for c in comps if c["y1"]<xaxis-7]
    bars=[c for c in comps if c["y1"]==xaxis-1 and c["w"]>=2]
    if not legend_swatches or not bars:
        raise TextChartParserError("NO_LEGEND_OR_BARS")

    color_to_series={}
    for c in legend_swatches:
        nearest=min(legend_labels,key=lambda t:(t["cy"]-c["cy"])**2+(t["cx"]-c["cx"])**2)
        color_to_series[c["char"]]=nearest["text"]
    if len(set(color_to_series.values()))!=len(color_to_series):
        raise TextChartParserError("LEGEND_MAPPING_AMBIGUOUS")

    categories=sorted(x_labels,key=lambda t:t["cx"])
    groups={i:[] for i in range(len(categories))}
    for c in bars:
        i=min(range(len(categories)),key=lambda j:abs(categories[j]["cx"]-c["cx"]))
        groups[i].append(c)

    series_names=sorted(color_to_series.values())
    series={name:[] for name in series_names}
    for i,cat in enumerate(categories):
        values={}
        for c in groups[i]:
            if c["char"] not in color_to_series:
                continue
            value=int(round(slope*c["y0"]+intercept))
            values[color_to_series[c["char"]]]=value
        if set(values)!=set(series_names):
            raise TextChartParserError("CATEGORY_SERIES_INCOMPLETE")
        for name in series_names:
            series[name].append(values[name])

    return {
        "categories":[t["text"] for t in categories],
        "series":series,
    }
