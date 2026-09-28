#!/usr/bin/env python3
from __future__ import annotations
import collections,json,pathlib,re,subprocess,sys,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

SPEC=ROOT/"canonical"/"experiments"/"RAW_TO_RANKED_CANDIDATE_TRACE_001.json"
REG=RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"RAW_TO_RANKED_CANDIDATE_TRACE_001__RESULT.json"

def fam_match(name,families):
    n=str(name or "").lower()
    for f in families:
        f=str(f).lower()
        if n==f or n.startswith(f+"-") or f.startswith(n+"-"):
            return True
    return False

def inherited_candidates(goal):
    queries=d.effect_queries(goal)
    reg=json.loads(REG.read_text())
    out=[]
    for cid,entry in (reg.get("capabilities") or {}).items():
        if entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        words=set()
        for v in [cid,*entry.get("keywords",[]),*entry.get("provides",[])]:
            words.update(re.findall(r"[a-z0-9]+",str(v).lower()))
        overlap=[q for q in queries if q in words]
        if overlap:
            out.append({
              "capability_id":cid,
              "overlap":overlap,
              "overlap_count":len(overlap),
              "adapter_module":entry.get("adapter_module"),
              "source_type":(entry.get("source") or {}).get("type"),
            })
    out.sort(key=lambda x:(-x["overlap_count"],x["capability_id"]))
    return out[:10]

def raw_apt_trace(queries,families):
    rows=[]
    any_oracle=False
    for query in queries:
        p=subprocess.run(["apt-cache","search",query],text=True,capture_output=True,timeout=30)
        names=[]
        first=None
        oracle_names=[]
        if p.returncode==0:
            for idx,line in enumerate(p.stdout.splitlines(),1):
                if " - " not in line:
                    continue
                name=line.split(" - ",1)[0].strip()
                names.append(name)
                if fam_match(name,families):
                    any_oracle=True
                    oracle_names.append(name)
                    if first is None:
                        first=idx
        rows.append({
          "query":query,
          "returncode":p.returncode,
          "result_count":len(names),
          "oracle_present":bool(oracle_names),
          "oracle_names":oracle_names[:10],
          "oracle_first_line":first,
          "stderr_tail":p.stderr[-500:],
        })
    return rows,any_oracle

def main():
    spec=json.loads(SPEC.read_text())
    results=[]
    counts=collections.Counter()
    t0=time.monotonic()
    for item in spec["effects"]:
        goal=item["goal"]
        families=item["oracle_families"]
        queries=d.effect_queries(goal)
        inherited=inherited_candidates(goal)
        raw,raw_present=raw_apt_trace(queries,families)
        t=time.monotonic()
        admitted=d.search_apt_packages(goal,limit=50)
        candidates=admitted.get("candidates",[]) or []
        oracle_rank=None; oracle_name=None
        for idx,c in enumerate(candidates,1):
            if fam_match(c.get("name"),families):
                oracle_rank=idx; oracle_name=c.get("name"); break
        if not raw_present:
            loss="RAW_SEARCH_COVERAGE"
        elif oracle_rank is None:
            loss="RAW_PRESENT_BUT_NOT_ADMITTED_OR_RETAINED"
        elif oracle_rank>12:
            loss="ADMITTED_BUT_BELOW_TOP12"
        else:
            loss="PRESENT_TOP12"
        counts[loss]+=1
        results.append({
          "effect_id":item["effect_id"],
          "goal":goal,
          "queries":queries,
          "inherited_verified_candidates":inherited,
          "raw_apt_trace":raw,
          "raw_oracle_present":raw_present,
          "admitted_candidate_count":len(candidates),
          "oracle_admitted_rank":oracle_rank,
          "oracle_admitted_name":oracle_name,
          "top12_names":[c.get("name") for c in candidates[:12]],
          "loss_stage":loss,
          "search_apt_wall_s":round(time.monotonic()-t,6),
        })
    top12=sum(1 for r in results if r["oracle_admitted_rank"] is not None and r["oracle_admitted_rank"]<=12)/len(results)
    raw_recall=sum(1 for r in results if r["raw_oracle_present"])/len(results)
    admitted_recall=sum(1 for r in results if r["oracle_admitted_rank"] is not None)/len(results)
    out={
      "schema":"PROJECT_BRAIN_RAW_TO_RANKED_CANDIDATE_TRACE_RESULT_V1",
      "diagnostic_id":spec["diagnostic_id"],
      "runtime_mutated":False,
      "results":results,
      "raw_catalog_oracle_recall":raw_recall,
      "admitted_oracle_recall":admitted_recall,
      "top12_oracle_recall":top12,
      "loss_stage_counts":dict(counts),
      "repeated_loss_stages":{k:v for k,v in counts.items() if v>=2 and k!="PRESENT_TOP12"},
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_RUNTIME_REPAIR_ON_THIS_BRANCH",
      "wall_s":round(time.monotonic()-t0,6),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
