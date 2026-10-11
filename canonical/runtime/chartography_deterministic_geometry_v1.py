from __future__ import annotations

import struct
from collections import deque
from pathlib import Path

WHITE=(255,255,255)
BLACK=(0,0,0)

def read_bmp_rgb(path: str | Path):
    data=Path(path).read_bytes()
    if data[:2]!=b"BM":
        raise ValueError("not BMP")
    off=struct.unpack_from("<I",data,10)[0]
    dib=struct.unpack_from("<I",data,14)[0]
    if dib<40:
        raise ValueError("unsupported DIB")
    w,h,planes,bpp=struct.unpack_from("<iiHH",data,18)
    if planes!=1 or bpp!=24 or w<=0 or h==0:
        raise ValueError("only 24-bit BMP")
    top_down=h<0
    H=abs(h)
    stride=((w*3+3)//4)*4
    out=[]
    for yy in range(H):
        src_y=yy if top_down else H-1-yy
        row=[]
        base=off+src_y*stride
        for x in range(w):
            b,g,r=data[base+3*x:base+3*x+3]
            row.append((r,g,b))
        out.append(row)
    return out

def pixels_of_color(im,color):
    return {(x,y) for y,row in enumerate(im) for x,c in enumerate(row) if c==color}

def connected_components(points):
    points=set(points)
    out=[]
    while points:
        seed=points.pop()
        q=[seed]; comp={seed}
        while q:
            x,y=q.pop()
            for nb in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if nb in points:
                    points.remove(nb); comp.add(nb); q.append(nb)
        out.append(comp)
    return out

def bbox(comp):
    xs=[p[0] for p in comp]; ys=[p[1] for p in comp]
    return min(xs),min(ys),max(xs),max(ys)

def solid_rect_components(im,color,min_pixels=30):
    comps=[]
    for c in connected_components(pixels_of_color(im,color)):
        if len(c)<min_pixels: continue
        x0,y0,x1,y1=bbox(c)
        area=(x1-x0+1)*(y1-y0+1)
        fill=len(c)/area
        if fill>=0.9:
            comps.append({"bbox":(x0,y0,x1,y1),"pixels":len(c),"height":y1-y0+1,"width":x1-x0+1,"cx":(x0+x1)/2})
    return comps

def tallest_bar_color(im,colors):
    best=None
    for name,color in colors.items():
        rects=solid_rect_components(im,color)
        if not rects: continue
        h=max(r["height"] for r in rects)
        if best is None or h>best[1]:
            best=(name,h)
    if best is None: raise ValueError("no bars")
    return best[0]

def bar_height_ratio(im,color_a,color_b):
    a=max((r["height"] for r in solid_rect_components(im,color_a)),default=None)
    b=max((r["height"] for r in solid_rect_components(im,color_b)),default=None)
    if a is None or b is None or b==0: raise ValueError("bars missing")
    return a/b

def line_right_higher_color(im,colors,right_fraction=0.2):
    W=len(im[0])
    xcut=int(W*(1-right_fraction))
    scores={}
    for name,color in colors.items():
        pts=[(x,y) for x,y in pixels_of_color(im,color) if x>=xcut]
        if not pts: continue
        # Plot coordinates rise upward, while raster y grows downward.
        scores[name]=sum(y for _,y in pts)/len(pts)
    if not scores: raise ValueError("no line pixels on right")
    return min(scores,key=scores.get)

def line_left_to_right_trend(im,color):
    pts=pixels_of_color(im,color)
    if not pts: raise ValueError("line missing")
    xs=[x for x,_ in pts]
    lo=min(xs); hi=max(xs); span=max(1,hi-lo)
    left=[y for x,y in pts if x<=lo+0.15*span]
    right=[y for x,y in pts if x>=hi-0.15*span]
    if not left or not right: raise ValueError("insufficient endpoints")
    # smaller raster y => higher plotted value
    return "INCREASE" if sum(right)/len(right)<sum(left)/len(left) else "DECREASE"

def count_components_left_of_x(im,color,x_div,min_pixels=20):
    n=0
    for c in connected_components(pixels_of_color(im,color)):
        if len(c)<min_pixels: continue
        x0,_,x1,_=bbox(c)
        if (x0+x1)/2<x_div: n+=1
    return n

def vertical_divider_x(im):
    pts=pixels_of_color(im,BLACK)
    byx={}
    for x,y in pts: byx.setdefault(x,[]).append(y)
    # Ignore y-axis near far left by preferring central long vertical line.
    W=len(im[0])
    candidates=[(len(ys),x) for x,ys in byx.items() if 0.3*W<x<0.7*W and max(ys)-min(ys)>0.4*len(im)]
    if not candidates: raise ValueError("divider missing")
    return max(candidates)[1]

def grouped_bar_winner_group(im,color_a,color_b):
    bars=[]
    for label,color in (("A",color_a),("B",color_b)):
        for r in solid_rect_components(im,color):
            bars.append((r["cx"],label,r["height"]))
    if len(bars)<4: raise ValueError("expected grouped bars")
    bars.sort()
    # Split by largest x gap.
    gaps=[bars[i+1][0]-bars[i][0] for i in range(len(bars)-1)]
    split=max(range(len(gaps)),key=gaps.__getitem__)+1
    groups=[bars[:split],bars[split:]]
    if any({x[1] for x in g}!={"A","B"} for g in groups):
        raise ValueError("ambiguous groups")
    winners=[]
    for idx,g in enumerate(groups):
        d={label:h for _,label,h in g}
        if d["A"]>d["B"]: winners.append(idx)
    if len(winners)!=1: raise ValueError("no unique winning group")
    return "LEFT" if winners[0]==0 else "RIGHT"
