#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,sys,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

CASES=[
  ("PDF_TEXT","Extract plain text from a PDF document.",["poppler-utils"]),
  ("SVG_RASTER","Convert an SVG vector image into a PNG raster image.",["librsvg2-bin","inkscape","imagemagick"]),
  ("BZIP2","Compress a text file using bzip2 compression.",["bzip2"]),
  ("MEDIA_METADATA","Inspect a multimedia file and report its technical media metadata.",["mediainfo"]),
]
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"EXECUTABLE_SEMANTIC_EVIDENCE_REPAIR_V1__REPLAY.json"

def fam(name,families):
    n=str(name or "").lower()
    return any(n==f or n.startswith(f+"-") or f.startswith(n+"-") for f in [x.lower() for x in families])

def main():
    results=[]
    t0=time.monotonic()
    hits=0; top20=0
    for effect_id,goal,families in CASES:
        t=time.monotonic()
        out=d.search_apt_packages(goal,limit=50)
        ranked=out.get("candidates") or []
        rows=[(i,c) for i,c in enumerate(ranked,1) if fam(c.get("name"),families)]
        if rows:
            hits+=1
            rank,c=rows[0]
            if rank<=20: top20+=1
            oracle={
              "surfaced":True,"rank":rank,"name":c.get("name"),
              "score":c.get("score"),
              "evidence":c.get("executable_semantic_evidence")
            }
        else:
            oracle={"surfaced":False,"rank":None,"name":None}
        results.append({
          "effect_id":effect_id,"goal":goal,"oracle":oracle,
          "top20_names":[c.get("name") for c in ranked[:20]],
          "wall_s":round(time.monotonic()-t,6)
        })
    recall=hits/len(CASES)
    recall20=top20/len(CASES)
    bzip=next(x for x in results if x["effect_id"]=="BZIP2")["oracle"]["surfaced"]
    passed=(recall==1.0 and recall20>=0.75 and bzip)
    result={
      "schema":"PROJECT_BRAIN_EXECUTABLE_SEMANTIC_EVIDENCE_REPAIR_REPLAY_V1",
      "runtime_patch":"EXECUTABLE_SEMANTIC_EVIDENCE_V1",
      "oracle_family_recall":recall,
      "top20_oracle_recall":recall20,
      "bzip2_no_regression":bool(bzip),
      "acceptance_gate_pass":passed,
      "results":results,
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_SECOND_REPAIR_ON_THIS_BRANCH",
      "wall_s":round(time.monotonic()-t0,6)
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
    if not passed:
        raise SystemExit(1)

if __name__=="__main__":
    main()
