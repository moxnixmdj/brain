from __future__ import annotations
import json,tempfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from canonical.runtime import h100_generic_bar_geometry_v0 as g

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_A_VISION_ADVERSARIAL_DEV_SUITE_V1.json"

def render(case,path):
    cid,kind,orientation,color,data,question,answer=case
    h,w=280,360
    im=Image.new("RGB",(w,h),"white")
    d=ImageDraw.Draw(im)
    bar,gap=18,24
    if kind=="BAR_SIMPLE":
        sizes=data; n=len(sizes); c=tuple(color)
        if orientation=="VERTICAL":
            x0=(w-(n*bar+(n-1)*gap))//2; base=h-15
            for i,s in enumerate(sizes):
                x=x0+i*(bar+gap); d.rectangle([x,base-s,x+bar-1,base-1],fill=c)
        else:
            y0=(h-(n*bar+(n-1)*gap))//2; left=15
            for i,s in enumerate(sizes):
                y=y0+i*(bar+gap); d.rectangle([left,y,left+s-1,y+bar-1],fill=c)
    elif kind=="BAR_GROUPED":
        colors=color; series=data; groups=len(series[0]); each=14; inner=5; groupgap=24
        total=groups*(2*each+inner)+(groups-1)*groupgap; x0=(w-total)//2; base=h-15
        for j in range(groups):
            x=x0+j*(2*each+inner+groupgap)
            for k in range(2):
                s=series[k][j]; d.rectangle([x+k*(each+inner),base-s,x+k*(each+inner)+each-1,base-1],fill=tuple(colors[k]))
    elif kind=="BAR_SIGNED":
        sizes=data; n=len(sizes); c=tuple(color); x0=(w-(n*bar+(n-1)*gap))//2; base=h//2
        for i,s in enumerate(sizes):
            x=x0+i*(bar+gap)
            if s>=0: box=[x,base-s,x+bar-1,base-1]
            else: box=[x,base,x+bar-1,base+abs(s)-1]
            d.rectangle(box,fill=c)
        d.line([10,base,w-10,base],fill=(0,0,0),width=2)
    elif kind=="BAR_STACKED":
        colors=color; series=data; n=len(series[0]); x0=(w-(n*bar+(n-1)*gap))//2; base=h-15
        for i in range(n):
            y=base
            for k in range(2):
                s=series[k][i]
                d.rectangle([x0+i*(bar+gap),y-s,x0+i*(bar+gap)+bar-1,y-1],fill=tuple(colors[k]))
                y-=s
    elif kind=="LINE":
        pts=data; c=tuple(color)
        xy=[(35+int(x)*55,240-int(y)) for x,y in pts]
        d.line(xy,fill=c,width=4)
        for x,y in xy:d.ellipse([x-4,y-4,x+4,y+4],fill=c)
    elif kind=="SCATTER":
        c=tuple(color)
        for x,y in data:d.ellipse([x-5,y-5,x+5,y+5],fill=c)
    else: raise ValueError(kind)
    im.save(path)

def adapt(out,question):
    if question=="CHART_TYPE": return "BAR" if out.get("status")=="BARLIKE_GEOMETRY_IDENTIFIED" else "UNKNOWN"
    if question=="COUNT": return len(out.get("bar_intervals",[]))
    if question in {"ARGMAX_INDEX","ARGMIN_INDEX","DESCENDING_ORDER"}: return "UNAVAILABLE"
    return None

def run():
    pre=json.loads(PRE.read_text()); rows=[]
    with tempfile.TemporaryDirectory(prefix="h100-vis-dev-") as td:
        for case in pre["cases"]:
            p=Path(td)/(case[0]+".png"); render(case,p)
            out=g.detect_bar_geometry(p)
            got=adapt(out,case[5]); want=case[6]; ok=got==want
            klass=None
            if not ok:
                klass="ALGORITHM_GAP" if case[5] in {"ARGMAX_INDEX","ARGMIN_INDEX","DESCENDING_ORDER"} else "REPRESENTATION_GAP"
            rows.append({"id":case[0],"kind":case[1],"question":case[5],"expected":want,"observed":got,"g0_status":out.get("status"),"g0_orientation":out.get("orientation"),"g0_interval_count":len(out.get("bar_intervals",[])),"pass":ok,"failure_class":klass})
    return {
      "schema":"PROJECT_BRAIN_H100_A_VISION_ADVERSARIAL_DEV_RESULT_V1",
      "status":"G0_VISION_DEV_DIAGNOSTIC_COMPLETE",
      "passed":sum(r["pass"] for r in rows),"total":len(rows),
      "failure_classes":sorted({r["failure_class"] for r in rows if r["failure_class"]}),
      "rows":rows,
      "information_gap_failures":0,
      "target_adapted_persistent_bits":0,
      "hard_nonclaims":["DEV_SUITE_BURNED_AFTER_THIS_RUN","FAILURES_DO_NOT_PROVE_POSITIVE_PERSISTENT_BITS","NO_FRESH_REPAIR_CREDIT_ON_THIS_SUITE"]
    }

if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
