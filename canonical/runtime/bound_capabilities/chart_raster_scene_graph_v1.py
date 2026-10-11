from __future__ import annotations
import math
from collections import defaultdict, deque
from pathlib import Path
from statistics import median
from typing import Any
from PIL import Image

CAPABILITY_ID = "chart.raster.scene_graph.v1"
SCHEMA = "PROJECT_BRAIN_CHART_RASTER_SCENE_GRAPH_V1"

class ChartSceneGraphError(ValueError):
    pass

def _luma(p):
    return 0.2126*p[0] + 0.7152*p[1] + 0.0722*p[2]

def _dark(p):
    return max(p)-min(p) <= 30 and _luma(p) <= 210

def _sat(p):
    return max(p)-min(p) >= 48 and max(p) >= 85

def _longest(flags, minimum):
    best=None; start=None
    for i,v in enumerate(flags+[False]):
        if v and start is None:
            start=i
        elif not v and start is not None:
            end=i-1
            if end-start+1 >= minimum and (best is None or end-start > best[1]-best[0]):
                best=(start,end)
            start=None
    return best

def detect_plot_box(image: Image.Image) -> tuple[int,int,int,int]:
    im=image.convert("RGB"); w,h=im.size
    hs=[]
    for y in range(int(.45*h),int(.94*h)):
        run=_longest([_dark(im.getpixel((x,y))) for x in range(w)],max(20,int(.25*w)))
        if run: hs.append((run[1]-run[0],y,run))
    if not hs: raise ChartSceneGraphError("HORIZONTAL_AXIS_NOT_FOUND")
    _,bottom,(left0,right)=max(hs)
    vs=[]
    for x in range(int(.02*w),int(.45*w)):
        run=_longest([_dark(im.getpixel((x,y))) for y in range(h)],max(20,int(.25*h)))
        if run: vs.append((run[1]-run[0],x,run))
    if not vs: raise ChartSceneGraphError("VERTICAL_AXIS_NOT_FOUND")
    _,left,(top,bottom0)=max(vs)
    if abs(bottom-bottom0)>max(12,int(.04*h)):
        raise ChartSceneGraphError("AXIS_INTERSECTION_INCONSISTENT")
    if right-left<.20*w or bottom-top<.20*h:
        raise ChartSceneGraphError("PLOT_BOX_IMPLAUSIBLE")
    return left,top,right,bottom

def _least_squares(points):
    if len(points)<3: raise ChartSceneGraphError("AXIS_TICKS_INSUFFICIENT")
    mp=sum(p for p,_ in points)/len(points); mv=sum(v for _,v in points)/len(points)
    den=sum((p-mp)**2 for p,_ in points)
    if den<=0: raise ChartSceneGraphError("AXIS_FIT_DEGENERATE")
    a=sum((p-mp)*(v-mv) for p,v in points)/den; b=mv-a*mp
    rmse=math.sqrt(sum((a*p+b-v)**2 for p,v in points)/len(points))
    return a,b,rmse

def calibrate_axis(points, expected_direction):
    pts=[(float(p),float(v)) for p,v in points]
    if len(pts)<3: raise ChartSceneGraphError("AXIS_TICKS_INSUFFICIENT")
    la,lb,le=_least_squares(pts)
    lspan=max(v for _,v in pts)-min(v for _,v in pts)
    ln=le/max(abs(lspan),1e-12)
    log=None
    if all(v>0 for _,v in pts):
        t=[(p,math.log10(v)) for p,v in pts]
        try:
            a,b,e=_least_squares(t)
            span=max(v for _,v in t)-min(v for _,v in t)
            log=(a,b,e/max(abs(span),1e-12))
        except ChartSceneGraphError:
            pass
    use_log=log is not None and log[2]+1e-7 < .40*max(ln,1e-7)
    a,b,n=(log if use_log else (la,lb,ln))
    if expected_direction=="INCREASING" and a<=0: raise ChartSceneGraphError("AXIS_DIRECTION_MISMATCH")
    if expected_direction=="DECREASING" and a>=0: raise ChartSceneGraphError("AXIS_DIRECTION_MISMATCH")
    if expected_direction not in {"INCREASING","DECREASING"}: raise ChartSceneGraphError("AXIS_DIRECTION_INVALID")
    return {
      "scale":"LOG10" if use_log else "LINEAR",
      "transformed_value_from_pixel":[a,b],
      "normalized_rmse":n,
      "tick_count":len(pts),
    }

def _bucket(p):
    return tuple(min(255,(int(v)//48)*48+24) for v in p)

def saturated_components(image: Image.Image, box, min_area=4):
    im=image.convert("RGB"); left,top,right,bottom=box
    buckets=defaultdict(set)
    for y in range(max(0,top),min(im.height,bottom+1)):
        for x in range(max(0,left),min(im.width,right+1)):
            p=im.getpixel((x,y))
            if _sat(p): buckets[_bucket(p)].add((x,y))
    out=[]
    for color,pixels in buckets.items():
        rem=set(pixels)
        while rem:
            seed=rem.pop(); q=deque([seed]); pts=[seed]
            while q:
                x,y=q.popleft()
                for nx in (x-1,x,x+1):
                    for ny in (y-1,y,y+1):
                        p=(nx,ny)
                        if p in rem:
                            rem.remove(p); q.append(p); pts.append(p)
            if len(pts)<min_area: continue
            xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            out.append({"color_bucket":list(color),"area":len(pts),
                        "bbox":[min(xs),min(ys),max(xs)+1,max(ys)+1]})
    return sorted(out,key=lambda x:(-x["area"],x["bbox"]))

def color_polylines(image: Image.Image, box, min_columns=8):
    im=image.convert("RGB"); left,top,right,bottom=box
    cols=defaultdict(lambda:defaultdict(list))
    for y in range(max(0,top),min(im.height,bottom+1)):
        for x in range(max(0,left),min(im.width,right+1)):
            p=im.getpixel((x,y))
            if _sat(p): cols[_bucket(p)][x].append(y)
    out=[]
    for color,byx in cols.items():
        xs=sorted(byx); runs=[]; run=[]
        for x in xs:
            if not run or x-run[-1]<=2: run.append(x)
            else: runs.append(run); run=[x]
        if run: runs.append(run)
        for run in runs:
            if len(run)<min_columns: continue
            out.append({"color_bucket":list(color),"column_count":len(run),
                        "x_range":[run[0],run[-1]],
                        "points":[[x,float(median(byx[x]))] for x in run]})
    return sorted(out,key=lambda x:-x["column_count"])

def build_scene_graph(image_path, x_ticks=None, y_ticks=None):
    src=Path(image_path)
    if not src.is_file(): raise ChartSceneGraphError("IMAGE_NOT_FOUND")
    with Image.open(src) as raw: im=raw.convert("RGB")
    box=detect_plot_box(im)
    axes={}; errors={}
    if x_ticks:
        try: axes["x"]=calibrate_axis(x_ticks,"INCREASING")
        except ChartSceneGraphError as e: errors["x"]=str(e)
    if y_ticks:
        try: axes["y"]=calibrate_axis(y_ticks,"DECREASING")
        except ChartSceneGraphError as e: errors["y"]=str(e)
    return {
      "schema":SCHEMA,"status":"PASS__RASTER_SCENE_GRAPH","capability_id":CAPABILITY_ID,
      "image_size":[im.width,im.height],"plot_box":list(box),"axes":axes,"axis_errors":errors,
      "saturated_components":saturated_components(im,box),
      "color_polylines":color_polylines(im,box),
      "semantic_authority":False,"domain_semantic_authority":False,
      "benchmark_score_authority":False,"cognition_dependency_class":"MODEL_INDEPENDENT",
      "general_purpose_model_dependency_count":0,
      "external_general_purpose_model_runtime_dependency_count":0,
      "donor_general_purpose_model_runtime_dependency_count":0,
      "incremental_spend_usd":0,
    }

def run(args: dict[str,Any], root):
    base=Path(root).resolve(); src=(base/str(args.get("path") or "")).resolve()
    if src!=base and base not in src.parents: raise ChartSceneGraphError("PATH_OUTSIDE_REPOSITORY")
    out=build_scene_graph(src,args.get("x_ticks"),args.get("y_ticks"))
    return {**out,"pass":True}
