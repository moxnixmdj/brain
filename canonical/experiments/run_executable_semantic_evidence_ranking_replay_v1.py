#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,sys,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

SPEC=ROOT/"canonical"/"experiments"/"PRETRUNCATION_CANDIDATE_RANK_TRACE_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"EXECUTABLE_SEMANTIC_EVIDENCE_RANKING_REPLAY_V1.json"

def fam_match(name,families):
    n=str(name or "").lower()
    return any(
        n==str(f).lower() or n.startswith(str(f).lower()+"-") or str(f).lower().startswith(n+"-")
        for f in families
    )

def main():
    spec=json.loads(SPEC.read_text())
    results=[]
    t0=time.monotonic()
    top20_hits=0
    family_hits=0
    bzip2_ok=False
    for item in spec["effects"]:
        t=time.monotonic()
        found=d.search_apt_packages(item["goal"],limit=50)
        candidates=found.get("candidates",[]) or []
        rank=None; oracle=None
        for i,c in enumerate(candidates,1):
            if fam_match(c.get("name"),item["oracle_families"]):
                rank=i; oracle=c; break
        hit=rank is not None
        family_hits+=int(hit)
        top20_hits+=int(hit and rank<=20)
        if item["effect_id"]=="TRACE-BZIP2-001":
            bzip2_ok=bool(hit and rank<=20)
        results.append({
          "effect_id":item["effect_id"],
          "goal":item["goal"],
          "oracle_families":item["oracle_families"],
          "oracle_found":hit,
          "oracle_rank":rank,
          "oracle_name":oracle.get("name") if oracle else None,
          "oracle_score":oracle.get("score") if oracle else None,
          "oracle_semantic_coverage":oracle.get("effect_semantic_coverage") if oracle else None,
          "oracle_executable_role_evidence":oracle.get("executable_role_evidence") if oracle else None,
          "top20":[
            {
              "rank":i,
              "name":c.get("name"),
              "score":c.get("score"),
              "semantic_coverage":c.get("effect_semantic_coverage"),
              "executable_role_evidence":c.get("executable_role_evidence"),
            } for i,c in enumerate(candidates[:20],1)
          ],
          "wall_s":round(time.monotonic()-t,6),
        })
    family_recall=family_hits/len(results) if results else 0
    top20_recall=top20_hits/len(results) if results else 0
    passed=(family_recall==1 and top20_recall>=0.75 and bzip2_ok)
    out={
      "schema":"PROJECT_BRAIN_EXECUTABLE_SEMANTIC_EVIDENCE_RANKING_REPLAY_V1",
      "repair_id":"EXECUTABLE-SEMANTIC-EVIDENCE-RANKING-REPAIR-V1",
      "frozen_source":"PRETRUNCATION-CANDIDATE-RANK-TRACE-001",
      "runtime_generalization_only":True,
      "package_hints_used":False,
      "task_specific_literals_added":False,
      "results":results,
      "oracle_family_recall":family_recall,
      "top20_oracle_recall":top20_recall,
      "bzip2_no_regression":bzip2_ok,
      "acceptance_gate_pass":passed,
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_SECOND_REPAIR_ON_THIS_BRANCH",
      "wall_s":round(time.monotonic()-t0,6),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if passed else 2)

if __name__=="__main__":
    main()
