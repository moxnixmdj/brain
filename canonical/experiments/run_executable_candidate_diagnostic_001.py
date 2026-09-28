#!/usr/bin/env python3
"""Metadata-only diagnosis of inherited-route reuse and executable supplier ranking."""
from __future__ import annotations
import json, pathlib, re, sys, time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0,str(RUNTIME))

import capability_discovery
import goal_compiler

MANIFEST=ROOT/"canonical"/"experiments"/"EXECUTABLE_CANDIDATE_DIAGNOSTIC_001.json"
REGISTRY=ROOT/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"EXECUTABLE_CANDIDATE_DIAGNOSTIC_001__RESULT.json"
KS=(1,3,5,10,20)

def norm(x):
    return re.sub(r"[-_.]+","",str(x or "").lower())

def role_class(candidate):
    kind=str(candidate.get("binding_kind") or "").lower()
    source=str(candidate.get("discovery_source") or "").upper()
    name=str(candidate.get("name") or "").lower()
    friction=int(candidate.get("integration_friction") or 0)
    if kind=="apt" or source=="APT_CATALOG":
        obvious_noise=(
            name.startswith(("lib","python3-","ruby-","golang-","php"))
            or name.endswith(("-dev","-doc","-dbg","-prof"))
        )
        if obvious_noise or friction>=2:
            return "LIBRARY_DOC_BINDING_NOISE"
        return "EXECUTABLE_ROLE_LIKELY"
    if source=="OFFICIAL_MCP_REGISTRY":
        secrets=int(candidate.get("required_secret_count") or 0)
        if secrets==0 and (candidate.get("remotes") or candidate.get("packages")):
            return "EXECUTABLE_ROLE_LIKELY"
        return "REMOTE_OR_SECRET_DEPENDENT"
    if kind=="pypi" or source=="PYPI":
        return "LIBRARY_SUPPLIER"
    return "UNKNOWN_ROLE"

def inherited_rank(goal, registry, oracle_ids):
    admissible=goal_compiler._platform_admissible_registry(registry)
    scored=[]
    for cid,entry in admissible.items():
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        try:
            score,specificity,evidence=goal_compiler._score(goal,cid,entry)
        except Exception as exc:
            continue
        if score>0:
            scored.append({
              "capability_id":cid,
              "score":score,
              "specificity":specificity,
              "evidence":evidence,
              "source":entry.get("source"),
            })
    scored.sort(key=lambda x:(-x["score"],-x["specificity"],x["capability_id"]))
    rank=None
    found=None
    wanted=set(oracle_ids)
    for i,item in enumerate(scored,1):
        if item["capability_id"] in wanted:
            rank=i; found=item["capability_id"]; break
    compile_result=None
    compile_error=None
    try:
        compiled=goal_compiler.compile_goal(goal,admissible,ROOT)
        compile_result={
          "status":"COMPILED",
          "compiler_mode":compiled.get("compiler_mode"),
          "capability_id":compiled.get("capability_id"),
          "compiled":compiled,
        }
    except Exception as exc:
        compile_error=type(exc).__name__+":"+str(exc)
    return {
      "oracle_rank":rank,
      "oracle_capability":found,
      "top_matches":scored[:10],
      "compile_result":compile_result,
      "compile_error":compile_error,
    }

def external_metrics(candidates, oracle_names):
    wanted={norm(x) for x in oracle_names}
    first_rank=None
    first_name=None
    roles=[]
    for i,c in enumerate(candidates,1):
        n=norm(c.get("name"))
        if first_rank is None and n in wanted:
            first_rank=i; first_name=c.get("name")
        roles.append(role_class(c))
    recalls={}
    precisions={}
    noise={}
    for k in KS:
        subset=candidates[:k]
        names={norm(x.get("name")) for x in subset}
        recalls[str(k)]=bool(wanted & names) if wanted else None
        r=[role_class(x) for x in subset]
        precisions[str(k)]=(sum(1 for x in r if x=="EXECUTABLE_ROLE_LIKELY")/len(r)) if r else None
        noise[str(k)]=(sum(1 for x in r if x in {"LIBRARY_DOC_BINDING_NOISE","LIBRARY_SUPPLIER"})/len(r)) if r else None
    return {
      "oracle_names":oracle_names,
      "first_oracle_rank":first_rank,
      "first_oracle_name":first_name,
      "recall_at_k":recalls,
      "executable_role_precision_at_k":precisions,
      "library_doc_binding_noise_rate_at_k":noise,
      "top_candidates":[
        {
          "rank":i,
          "name":c.get("name"),
          "source":c.get("discovery_source"),
          "binding_kind":c.get("binding_kind"),
          "score":c.get("score"),
          "integration_friction":c.get("integration_friction"),
          "role_class":role_class(c),
          "description":c.get("description"),
        }
        for i,c in enumerate(candidates[:20],1)
      ],
    }

def main():
    manifest=json.loads(MANIFEST.read_text())
    registry=json.loads(REGISTRY.read_text())["capabilities"]
    results=[]
    t0=time.monotonic()
    for probe in manifest["probes"]:
        goal=probe["goal"]
        inherited=inherited_rank(goal,registry,probe.get("inherited_oracle_capabilities") or [])
        t=time.monotonic()
        discovery=capability_discovery.search_all(goal,limit_per_source=40)
        elapsed=time.monotonic()-t
        candidates=discovery.get("candidates") or []
        external=external_metrics(candidates,probe.get("external_oracle_names") or [])
        results.append({
          "probe_id":probe["id"],
          "domain":probe["domain"],
          "goal":goal,
          "inherited":inherited,
          "discovery_wall_s":round(elapsed,6),
          "discovery_queries":{
            str(x.get("source")):x.get("queries")
            for x in (discovery.get("results") or [])
          },
          "candidate_count":len(candidates),
          "source_distribution":{
            source:sum(1 for x in candidates if x.get("discovery_source")==source)
            for source in sorted({x.get("discovery_source") for x in candidates})
          },
          "external":external,
        })
    oracle_ranks=[x["external"]["first_oracle_rank"] for x in results if x["external"]["oracle_names"]]
    found=[x for x in oracle_ranks if x is not None]
    sqlite=next(x for x in results if x["probe_id"]=="DISCOVERY-SQLITE-001")
    diagnosis=[]
    if sqlite["inherited"]["oracle_rank"] is not None and sqlite["inherited"]["compile_error"]:
        diagnosis.append("INHERITED_ROUTE_VISIBLE_BUT_NOT_DIRECTLY_COMPILABLE")
    if len(found)<len(oracle_ranks):
        diagnosis.append("KNOWN_VIABLE_EXTERNAL_SUPPLIER_RECALL_FAILURE")
    if found and max(found)>10:
        diagnosis.append("KNOWN_VIABLE_SUPPLIER_RANKING_FAILURE")
    p5=[
      x["external"]["executable_role_precision_at_k"]["5"]
      for x in results
      if x["external"]["executable_role_precision_at_k"]["5"] is not None
    ]
    if p5 and sum(p5)/len(p5)<0.5:
        diagnosis.append("TOP5_EXECUTABLE_ROLE_PRECISION_LOW")
    out={
      "schema":"PROJECT_BRAIN_EXECUTABLE_CANDIDATE_DIAGNOSTIC_RESULT_V1",
      "diagnostic_id":"EXECUTABLE-CANDIDATE-DIAGNOSTIC-001",
      "runtime_mutation_performed":False,
      "package_installation_performed":False,
      "candidate_execution_performed":False,
      "oracle_used_for_search":False,
      "probe_results":results,
      "aggregate":{
        "known_external_oracle_count":len(oracle_ranks),
        "known_external_oracles_found":len(found),
        "known_external_recall":(len(found)/len(oracle_ranks)) if oracle_ranks else None,
        "median_first_oracle_rank":sorted(found)[len(found)//2] if found else None,
        "mean_top5_executable_role_precision":(sum(p5)/len(p5)) if p5 else None,
        "diagnosis_candidates":diagnosis,
      },
      "promotion_authorized":False,
      "required_next_action":"RECONCILE_FRONTIER_ONLY",
      "wall_s":round(time.monotonic()-t0,6),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    raise SystemExit(main())
