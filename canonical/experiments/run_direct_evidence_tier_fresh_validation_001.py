#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"canonical"/"runtime"))
import capability_discovery as d

SPEC=ROOT/"canonical"/"experiments"/"DIRECT_EVIDENCE_TIER_FRESH_VALIDATION_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"DIRECT_EVIDENCE_TIER_FRESH_VALIDATION_001__RESULT.json"

OLD=[
 ("OLD-PDF","Extract plain text from a PDF document.",["poppler-utils"]),
 ("OLD-SVG","Convert an SVG vector image into a PNG raster image.",["librsvg2-bin","inkscape","imagemagick"]),
 ("OLD-BZIP2","Compress a text file using bzip2 compression.",["bzip2"]),
 ("OLD-MEDIA","Inspect a multimedia file and report its technical media metadata.",["mediainfo"]),
]

def fam(name,families):
    n=str(name or "").lower()
    for f in families:
        f=str(f).lower()
        if n==f or n.startswith(f+"-") or f.startswith(n+"-"):
            return True
    return False

def eval_case(effect_id,goal,families):
    t=time.monotonic()
    out=d.search_apt_packages(goal,limit=50)
    cs=out.get("candidates",[]) or []
    rank=None; oracle=None
    for i,c in enumerate(cs,1):
        if fam(c.get("name"),families):
            rank=i; oracle=c; break
    top1=cs[0] if cs else {}
    return {
      "effect_id":effect_id,
      "goal":goal,
      "oracle_families":families,
      "oracle_found":rank is not None,
      "oracle_rank":rank,
      "oracle_name":oracle.get("name") if oracle else None,
      "oracle_evidence_tier":oracle.get("evidence_tier") if oracle else None,
      "top1_name":top1.get("name"),
      "top1_evidence_tier":top1.get("evidence_tier"),
      "top20":[
        {"rank":i,"name":c.get("name"),"tier":c.get("evidence_tier"),
         "score":c.get("score"),
         "coverage":(c.get("executable_semantic_evidence") or {}).get("semantic_coverage")}
        for i,c in enumerate(cs[:20],1)
      ],
      "wall_s":round(time.monotonic()-t,6),
    }

def main():
    spec=json.loads(SPEC.read_text())
    fresh=[eval_case(x["effect_id"],x["goal"],x["oracle_families"]) for x in spec["cases"]]
    old=[eval_case(*x) for x in OLD]
    n=len(fresh)
    recall=sum(x["oracle_found"] for x in fresh)/n
    top20=sum(bool(x["oracle_found"] and x["oracle_rank"]<=20) for x in fresh)/n
    lexical_top1=sum(1 for x in fresh if x["top1_evidence_tier"]!="DIRECT_EXECUTABLE_SEMANTIC")
    gate=spec["acceptance"]
    passed=(
      recall+1e-12>=float(gate["fresh_oracle_family_recall_min"])
      and top20+1e-12>=float(gate["fresh_top20_oracle_recall_min"])
      and lexical_top1<=int(gate["lexical_only_top1_max"])
    )
    result={
      "schema":"PROJECT_BRAIN_DIRECT_EVIDENCE_TIER_FRESH_VALIDATION_RESULT_V1",
      "validation_id":spec["validation_id"],
      "fresh_results":fresh,
      "old_four_regression_results":old,
      "fresh_oracle_family_recall":recall,
      "fresh_top20_oracle_recall":top20,
      "fresh_lexical_only_top1_count":lexical_top1,
      "acceptance_gate_pass":passed,
      "runtime_generalization_only":True,
      "package_hints_used_by_discovery":False,
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_SECOND_REPAIR_ON_THIS_BRANCH",
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(0 if passed else 2)

if __name__=="__main__":
    main()
