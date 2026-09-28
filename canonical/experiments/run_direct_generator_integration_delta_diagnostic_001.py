#!/usr/bin/env python3
from __future__ import annotations
import collections,json,pathlib,re,subprocess,sys,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

SPEC=ROOT/"canonical"/"experiments"/"DIRECT_GENERATOR_INTEGRATION_DELTA_DIAGNOSTIC_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"DIRECT_GENERATOR_INTEGRATION_DELTA_DIAGNOSTIC_001__RESULT.json"

PR70_GENERIC=set(d.GENERIC_DISCOVERY_TOKENS)|{
    "plain","document","file","using","report","technical","vector","raster",
    "inspect","compress","compression"
}
PR72_LOW={
    "those","these","exact","records","record","fields","field",
    "values","value","same","identical","order","count","save",
    "plain","document","file","using","report"
}

def fam_match(name,families):
    n=str(name or "").lower()
    for f in families:
        f=str(f).lower()
        if n==f or n.startswith(f+"-") or f.startswith(n+"-"):
            return True
    return False

def pr70_terms(goal):
    out=[]
    for token in d.effect_queries(goal):
        t=re.sub(r"[^a-z0-9]+","",str(token).lower())
        if len(t)<3 or t in PR70_GENERIC:
            continue
        if t not in out:
            out.append(t)
    return out[:6]

def pr72_terms(goal):
    semantic=d._semanticize_paths(goal)
    out=[]
    for token in re.split(r"[^A-Za-z0-9]+",semantic):
        t=token.lower()
        if len(t)<3 or t in d.STOPWORDS or t in PR72_LOW or t.isdigit():
            continue
        if t not in out:
            out.append(t)
    return out[:8]

def query_terms(terms):
    evidence=collections.defaultdict(lambda:{"paths":set(),"terms":set()})
    per_term={}
    for term in terms:
        pattern=rf"/usr/bin/[^/]*{re.escape(term)}[^/]*$"
        p=subprocess.run(["apt-file","search","-x",pattern],text=True,capture_output=True,timeout=60)
        rows=0
        if p.returncode in (0,1):
            for line in p.stdout.splitlines():
                if ": " not in line: continue
                package,path=line.split(": ",1)
                package=package.strip(); path=path.strip()
                if not package or not path.startswith("/usr/bin/"): continue
                rows+=1
                ev=evidence[package]
                ev["paths"].add(path); ev["terms"].add(term)
        per_term[term]={"returncode":p.returncode,"row_count":rows}
    ranked=[]
    for package,ev in evidence.items():
        paths=sorted(ev["paths"]); hits=sorted(ev["terms"])
        score=100*len(hits)+20*len(paths)
        for path in paths:
            cmd=path.rsplit("/",1)[-1].lower()
            for term in hits:
                if cmd==term: score+=80
                elif cmd.startswith(term) or cmd.endswith(term): score+=30
        ranked.append({"package":package,"paths":paths,"matched_terms":hits,"score":score})
    ranked.sort(key=lambda x:(-x["score"],x["package"]))
    return ranked,per_term

def oracle_info(ranked,families):
    rows=[(i,c) for i,c in enumerate(ranked,1) if fam_match(c["package"],families)]
    if not rows: return {"found":False,"rank":None,"package":None}
    rank,c=rows[0]
    return {"found":True,"rank":rank,"package":c["package"],"score":c["score"],"matched_terms":c["matched_terms"],"paths":c["paths"]}

def main():
    spec=json.loads(SPEC.read_text())
    results=[]
    losses=collections.Counter()
    t0=time.monotonic()
    for case in spec["cases"]:
        t=time.monotonic()
        bterms=pr70_terms(case["goal"])
        iterms=pr72_terms(case["goal"])
        baseline,bdiag=query_terms(bterms)
        integrated,idiag=query_terms(iterms)
        b=oracle_info(baseline,case["oracle_families"])
        i=oracle_info(integrated,case["oracle_families"])
        survives=bool(i["found"] and i["rank"]<=100)
        if not b["found"]:
            loss="BASELINE_GENERATOR_MISS"
        elif not i["found"]:
            loss="INTEGRATED_TERM_GENERATOR_REMOVES_ORACLE"
        elif i["rank"]>100:
            loss="INTEGRATED_BROAD_TERMS_PUSH_ORACLE_BELOW_PRELIM_TOP100"
        else:
            loss="ORACLE_SURVIVES_GENERATOR_AND_TOP100"
        losses[loss]+=1
        added=[x for x in iterms if x not in bterms]
        removed=[x for x in bterms if x not in iterms]
        results.append({
          "effect_id":case["effect_id"],
          "goal":case["goal"],
          "baseline_command_terms":bterms,
          "integrated_semantic_terms":iterms,
          "added_integrated_terms":added,
          "removed_baseline_terms":removed,
          "baseline_candidate_count":len(baseline),
          "integrated_candidate_count":len(integrated),
          "baseline_term_rows":bdiag,
          "integrated_term_rows":idiag,
          "baseline_oracle":b,
          "integrated_oracle_before_top100":i,
          "integrated_oracle_survives_top100":survives,
          "first_loss_stage":loss,
          "wall_s":round(time.monotonic()-t,6)
        })
    out={
      "schema":"PROJECT_BRAIN_DIRECT_GENERATOR_INTEGRATION_DELTA_DIAGNOSTIC_RESULT_V1",
      "diagnostic_id":spec["diagnostic_id"],
      "runtime_mutated":False,
      "candidate_packages_installed":False,
      "candidate_binaries_executed":False,
      "results":results,
      "loss_stage_counts":dict(losses),
      "repeated_loss_stages":{k:v for k,v in losses.items() if v>=2 and k!="ORACLE_SURVIVES_GENERATOR_AND_TOP100"},
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_RUNTIME_REPAIR_ON_THIS_BRANCH",
      "wall_s":round(time.monotonic()-t0,6)
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
