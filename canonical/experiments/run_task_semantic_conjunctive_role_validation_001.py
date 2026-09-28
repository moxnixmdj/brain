#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,sys,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

MANIFEST=ROOT/"canonical"/"experiments"/"TASK_SEMANTIC_CONJUNCTIVE_ROLE_VALIDATION_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"TASK_SEMANTIC_CONJUNCTIVE_ROLE_VALIDATION_001__RESULT.json"

def rank_of(candidates,families):
    fam=[x.lower() for x in families]
    for i,c in enumerate(candidates,1):
        name=str(c.get("name") or "").lower()
        if any(name==x or name.startswith(x+"-") or x.startswith(name+"-") for x in fam):
            return i,name
    return None,None

def main():
    spec=json.loads(MANIFEST.read_text())
    results=[]
    t0=time.monotonic()
    for item in spec["effects"]:
        goal=item["goal"]
        t=time.monotonic()
        apt=d.search_apt_packages(goal,limit=50)
        candidates=apt.get("candidates",[]) or []
        rank,name=rank_of(candidates,item["oracle_families"])
        top=candidates[0] if candidates else {}
        topcompat=bool((top.get("essential_role_compatibility") or {}).get("compatible"))
        topdirect=(top.get("supplier_role") or {}).get("role")=="DIRECT_EXECUTABLE_CANDIDATE"
        roles=d.effect_semantic_roles(goal)
        queries=d.effect_queries(goal)
        results.append({
          "effect_id":item["effect_id"],
          "goal":goal,
          "roles":roles,
          "queries":queries,
          "oracle_rank":rank,
          "oracle_name":name,
          "top1_name":top.get("name"),
          "top1_score":top.get("score"),
          "top1_essential_compatible":topcompat,
          "top1_direct":topdirect,
          "top12":[
            {
              "rank":i+1,
              "name":c.get("name"),
              "score":c.get("score"),
              "compatible":bool((c.get("essential_role_compatibility") or {}).get("compatible")),
              "supplier_role":(c.get("supplier_role") or {}).get("role"),
              "alignment":c.get("semantic_alignment"),
            }
            for i,c in enumerate(candidates[:12])
          ],
          "wall_s":round(time.monotonic()-t,6),
        })

    recall=sum(1 for x in results if x["oracle_rank"] is not None and x["oracle_rank"]<=12)/len(results)
    compatible=sum(1 for x in results if x["top1_essential_compatible"])
    direct=sum(1 for x in results if x["top1_direct"])
    noise_terms={"project","brain","arbitrary","payload","alpha","beta"}
    noise_count=sum(
      1 for x in results for q in x["queries"] if q.lower() in noise_terms
    )
    acc=spec["acceptance"]
    gate=(
      recall>=float(acc["exact_oracle_top12_recall_min"])
      and compatible>=int(acc["top1_essential_compatible_count_min"])
      and (len(results)-direct)<=int(acc["top1_auxiliary_or_non_direct_count_max"])
      and noise_count<=int(acc["payload_schema_noise_query_count_max"])
    )
    out={
      "schema":"PROJECT_BRAIN_FRESH_SEMANTIC_ROLE_VALIDATION_RESULT_V1",
      "validation_id":spec["validation_id"],
      "results":results,
      "exact_oracle_top12_recall":recall,
      "top1_essential_compatible_count":compatible,
      "top1_direct_count":direct,
      "payload_schema_noise_query_count":noise_count,
      "acceptance_gate_pass":gate,
      "promotion_authorized":False,
      "required_next_action":"RECONCILE_REGARDLESS_OF_OUTCOME",
      "wall_s":round(time.monotonic()-t0,6),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if gate else 2

if __name__=="__main__":
    raise SystemExit(main())
