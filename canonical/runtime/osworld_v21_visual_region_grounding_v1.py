"""Deterministic visual-region grounding for explicit color/geometry targets."""
from __future__ import annotations

from collections import deque
import hashlib
import io
import math
from typing import Any, Mapping

from PIL import Image

MAX_PIXELS=2_500_000
GRID_MAX_W=480
GRID_MAX_H=270
MIN_COMPONENT_PIXELS=8

COLORS={
    "red":(220,45,45),
    "green":(45,170,75),
    "blue":(50,100,220),
    "yellow":(225,200,45),
    "orange":(230,130,40),
    "purple":(145,75,190),
    "pink":(225,105,160),
    "black":(25,25,25),
    "white":(235,235,235),
    "gray":(130,130,130),
    "grey":(130,130,130),
}

class VisualGroundingError(ValueError):
    pass

def _distance(p,anchor):
    return math.sqrt(sum((int(p[i])-anchor[i])**2 for i in range(3)))

def _matches(pixel,color):
    r,g,b=pixel
    if color=="black": return max(r,g,b)<=70
    if color=="white": return min(r,g,b)>=205
    if color in {"gray","grey"}:
        return max(r,g,b)-min(r,g,b)<=28 and 65<=sum((r,g,b))/3<=195
    return _distance(pixel,COLORS[color])<=105 and max(r,g,b)-min(r,g,b)>=55

def _components(mask,w,h):
    seen=bytearray(w*h); out=[]
    for idx,val in enumerate(mask):
        if not val or seen[idx]: continue
        q=deque([idx]); seen[idx]=1; pts=[]
        while q:
            n=q.popleft(); pts.append(n); x=n%w; y=n//w
            for nn in (n-1,n+1,n-w,n+w):
                if nn<0 or nn>=w*h or seen[nn] or not mask[nn]: continue
                nx=nn%w; ny=nn//w
                if abs(nx-x)+abs(ny-y)!=1: continue
                seen[nn]=1; q.append(nn)
        if len(pts)<MIN_COMPONENT_PIXELS: continue
        xs=[p%w for p in pts]; ys=[p//w for p in pts]
        x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
        bw=x1-x0; bh=y1-y0
        fill=len(pts)/(bw*bh)
        out.append({"area":len(pts),"x0":x0,"y0":y0,"x1":x1,"y1":y1,"fill":fill})
    return out

def _shape_ok(c,shape):
    if not shape: return True
    w=c["x1"]-c["x0"]; h=c["y1"]-c["y0"]
    ratio=w/h if h else 99
    fill=c["fill"]
    if shape=="circle": return 0.72<=ratio<=1.38 and 0.48<=fill<=0.92
    if shape=="square": return 0.78<=ratio<=1.28 and fill>=0.68
    if shape=="rectangle": return fill>=0.60
    return True

def _spatial_ok(cx,cy,w,h,spatial):
    if not spatial: return True
    if spatial=="left": return cx<w*0.5
    if spatial=="right": return cx>w*0.5
    if spatial=="top": return cy<h*0.5
    if spatial=="bottom": return cy>h*0.5
    if spatial=="top-left": return cx<w*0.5 and cy<h*0.5
    if spatial=="top-right": return cx>w*0.5 and cy<h*0.5
    if spatial=="bottom-left": return cx<w*0.5 and cy>h*0.5
    if spatial=="bottom-right": return cx>w*0.5 and cy>h*0.5
    if spatial=="center": return w*0.25<=cx<=w*0.75 and h*0.25<=cy<=h*0.75
    raise VisualGroundingError("SPATIAL_INVALID")

def ground_visual_region(
    screenshot:bytes,*,color:str,shape:str|None=None,spatial:str|None=None
)->dict[str,Any]:
    if not isinstance(screenshot,(bytes,bytearray)) or not screenshot:
        raise VisualGroundingError("SCREENSHOT_REQUIRED")
    data=bytes(screenshot)
    if color not in COLORS: raise VisualGroundingError("COLOR_UNSUPPORTED")
    if shape not in {None,"circle","square","rectangle"}:
        raise VisualGroundingError("SHAPE_UNSUPPORTED")
    try:
        im=Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise VisualGroundingError("SCREENSHOT_DECODE_FAILED") from exc
    ow,oh=im.size
    if ow<=0 or oh<=0 or ow*oh>MAX_PIXELS:
        raise VisualGroundingError("SCREENSHOT_EXTENT_UNSUPPORTED")
    scale=min(1.0,GRID_MAX_W/ow,GRID_MAX_H/oh)
    if scale<1:
        w=max(1,int(round(ow*scale))); h=max(1,int(round(oh*scale)))
        im=im.resize((w,h),Image.Resampling.BILINEAR)
    else:
        w,h=ow,oh
    pixels=list(im.getdata())
    mask=bytearray(1 if _matches(p,color) else 0 for p in pixels)
    rows=[]
    for c in _components(mask,w,h):
        cx=(c["x0"]+c["x1"]-1)/2; cy=(c["y0"]+c["y1"]-1)/2
        if not _shape_ok(c,shape) or not _spatial_ok(cx,cy,w,h,spatial): continue
        sx=ow/w; sy=oh/h
        rows.append({
            "box":{
                "x0":int(c["x0"]*sx),"y0":int(c["y0"]*sy),
                "x1_exclusive":min(ow,int(math.ceil(c["x1"]*sx))),
                "y1_exclusive":min(oh,int(math.ceil(c["y1"]*sy))),
            },
            "fill_ratio":round(c["fill"],4),
            "grid_area":c["area"],
            "center":{"x":min(ow-1,int(round(cx*sx))),"y":min(oh-1,int(round(cy*sy)))},
        })
    base={
        "schema":"PROJECT_BRAIN_OSWORLD_V21_VISUAL_REGION_GROUNDING_V1",
        "source_sha256":hashlib.sha256(data).hexdigest(),
        "target":{"color":color,"shape":shape,"spatial":spatial},
        "candidate_count":len(rows),
        "candidates":rows,
        "semantic_authority":False,
        "task_specific_policy_data":False,
    }
    if len(rows)!=1:
        return {**base,"pass":False,"reason":"NO_MATCH" if not rows else "AMBIGUOUS_MATCH"}
    return {**base,"pass":True,"reason":"UNIQUE_EXPLICIT_VISUAL_REGION","selected":rows[0],"click_point":rows[0]["center"]}
