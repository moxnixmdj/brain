#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,re,subprocess,sys,time,collections

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

SPEC=ROOT/"canonical"/"experiments"/"PRETRUNCATION_CANDIDATE_RANK_TRACE_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"PRETRUNCATION_CANDIDATE_RANK_TRACE_001__RESULT.json"

def fam_match(name,families):
    n=str(name or "").lower()
    for f in families:
        f=str(f).lower()
        if n==f or n.startswith(f+"-") or f.startswith(n+"-"):
            return True
    return False

def reconstruct_pool(effect):
    queries=d.effect_queries(effect)
    apt_queries=d._apt_query_variants(queries)
    effect_tokens=set(queries)
    seen={}
    per_query=[]
    for query in apt_queries:
        p=subprocess.run(["apt-cache","search",query],text=True,capture_output=True,timeout=30)
        admitted_this=0
        raw_lines=0
        if p.returncode==0:
            for line in p.stdout.splitlines():
                if " - " not in line:
                    continue
                raw_lines+=1
                name,description=line.split(" - ",1)
                name=name.strip(); description=description.strip()
                blob=(name+" "+description).lower()
                ordered_blob_tokens=re.findall(r"[a-z0-9]+",blob)
                blob_tokens=set(ordered_blob_tokens)
                compound_tokens={
                    ordered_blob_tokens[i]+ordered_blob_tokens[i+1]
                    for i in range(len(ordered_blob_tokens)-1)
                    if len(ordered_blob_tokens[i])>=2 and len(ordered_blob_tokens[i+1])>=2
                }
                lexical_tokens=blob_tokens | compound_tokens
                matched={
                    t for t in effect_tokens
                    if any(v in lexical_tokens for v in d._lexical_variants(t))
                }
                if not matched:
                    continue
                admitted_this+=1
                score=0
                ordered_name_tokens=re.findall(r"[a-z0-9]+",name.lower())
                name_tokens=set(ordered_name_tokens) | {
                    ordered_name_tokens[i]+ordered_name_tokens[i+1]
                    for i in range(len(ordered_name_tokens)-1)
                }
                for t in matched:
                    distinctive=t not in d.GENERIC_DISCOVERY_TOKENS
                    if t in name_tokens:
                        score += 24 if distinctive else 6
                    else:
                        score += 10 if distinctive else 2
                lname=name.lower()
                integration_friction=0
                if lname.startswith(("python3-","ruby-","golang-","php-","php")):
                    integration_friction=2; score-=10
                if lname.startswith(("lib","librust-","libghc-")):
                    integration_friction=3; score-=12
                if name.endswith(("-dev","-doc","-dbg","-prof")):
                    integration_friction=max(integration_friction,4); score-=8
                if integration_friction==0:
                    score+=8
                if len(matched)>1:
                    score += 20*(len(matched)-1)
                if lname in effect.lower():
                    score+=8
                cand={
                  "name":name,"description":description,"query":query,
                  "matched_terms":sorted(matched),"score":score,
                  "integration_friction":integration_friction,
                }
                prior=seen.get(name)
                if prior is None or cand["score"]>prior["score"]:
                    seen[name]=cand
        per_query.append({"query":query,"raw_lines":raw_lines,"admitted_lines":admitted_this,"returncode":p.returncode})
    ranked=sorted(seen.values(),key=lambda x:(-x["score"],x["name"]))
    return queries,apt_queries,per_query,ranked

def main():
    spec=json.loads(SPEC.read_text())
    results=[]
    losses=collections.Counter()
    t0=time.monotonic()
    for item in spec["effects"]:
        t=time.monotonic()
        queries,apt_queries,per_query,ranked=reconstruct_pool(item["goal"])
        oracle_positions=[
            (idx,c) for idx,c in enumerate(ranked,1)
            if fam_match(c["name"],item["oracle_families"])
        ]
        if oracle_positions:
            rank,oracle=oracle_positions[0]
            threshold=ranked[49]["score"] if len(ranked)>=50 else (ranked[-1]["score"] if ranked else None)
            outrankers=ranked[:max(0,rank-1)]
            reason="ADMITTED_BELOW_TOP50" if rank>50 else "ADMITTED_TOP50"
            losses[reason]+=1
            oracle_info={
              "admitted":True,
              "name":oracle["name"],
              "rank":rank,
              "score":oracle["score"],
              "matched_terms":oracle["matched_terms"],
              "query":oracle["query"],
              "integration_friction":oracle["integration_friction"],
              "count_outranking":rank-1,
              "rank50_score_threshold":threshold,
              "score_gap_to_rank50":(threshold-oracle["score"]) if threshold is not None and rank>50 else 0,
              "top_outrankers":[
                {"rank":i+1,"name":c["name"],"score":c["score"],"matched_terms":c["matched_terms"],"friction":c["integration_friction"]}
                for i,c in enumerate(outrankers[:20])
              ]
            }
        else:
            losses["NOT_ADMITTED_TO_SEEN"]+=1
            oracle_info={"admitted":False,"name":None,"rank":None,"score":None,"matched_terms":[]}
        results.append({
          "effect_id":item["effect_id"],
          "goal":item["goal"],
          "queries":queries,
          "apt_queries":apt_queries,
          "per_query":per_query,
          "candidate_pool_size":len(ranked),
          "oracle":oracle_info,
          "top50_names":[c["name"] for c in ranked[:50]],
          "wall_s":round(time.monotonic()-t,6),
        })
    out={
      "schema":"PROJECT_BRAIN_PRETRUNCATION_CANDIDATE_RANK_TRACE_RESULT_V1",
      "diagnostic_id":spec["diagnostic_id"],
      "runtime_mutated":False,
      "results":results,
      "loss_class_counts":dict(losses),
      "repeated_loss_classes":{k:v for k,v in losses.items() if v>=2 and k!="ADMITTED_TOP50"},
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_RUNTIME_REPAIR_ON_THIS_BRANCH",
      "wall_s":round(time.monotonic()-t0,6),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
