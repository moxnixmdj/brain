#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, re, shutil, subprocess, sys, time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery

MANIFEST=ROOT/"canonical"/"experiments"/"SEMANTIC_ROLE_DIAGNOSTIC_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"SEMANTIC_ROLE_DIAGNOSTIC_001__RESULT.json"

NEGATIVE_ROLE_PATTERNS={
  "library_binding":[r"^lib",r"python",r"ruby",r"perl",r"php",r"bindings?",r"library",r"module"],
  "dev_doc":[r"-dev$",r"-doc$",r"documentation",r"header files?",r"development files?"],
  "editor_mode":[r"emacs",r"vim",r"mode"],
  "data_asset":[r"fonts?",r"icons?",r"flags?",r"dictionary",r"hunspell",r"data files?",r"examples?"],
  "backend_plugin":[r"backend",r"plugin",r"modules?"],
}
POSITIVE_ROLE_PATTERNS=[
  r"command[- ]line",r"cli\b",r"utility",r"tool\b",r"program\b",r"application",r"converter",
  r"compress",r"render",r"resize",r"database",r"sqlite",r"graphviz",r"gzip"
]

def norm(x):
    return re.sub(r"[^a-z0-9]+","",str(x or "").lower())

def role_terms(expected):
    out={}
    for role,values in expected.items():
        out[role]=[norm(v) for v in values if norm(v)]
    return out

def query_role_coverage(queries,expected):
    qs=[norm(x) for x in queries]
    roles=role_terms(expected)
    coverage={}
    for role,terms in roles.items():
        hits=[t for t in terms if any(t in q or q in t for q in qs if q)]
        coverage[role]={"terms":terms,"hits":hits,"covered":bool(hits) if terms else True}
    return coverage

def classify_candidate(c):
    name=str(c.get("name") or "")
    desc=str(c.get("description") or "")
    blob=(name+" "+desc).lower()
    negative=[]
    for role,patterns in NEGATIVE_ROLE_PATTERNS.items():
        if any(re.search(p,blob) for p in patterns):
            negative.append(role)
    positive=sum(1 for p in POSITIVE_ROLE_PATTERNS if re.search(p,blob))
    if negative and positive==0:
        tool_role="NON_EXECUTABLE_OR_AUXILIARY_LIKELY"
    elif negative and positive>0:
        tool_role="AMBIGUOUS_TOOL_ROLE"
    elif positive>0:
        tool_role="EXECUTABLE_TOOL_LIKELY"
    else:
        tool_role="ROLE_UNKNOWN"
    return {"tool_role":tool_role,"negative_role_evidence":negative,"positive_role_signal_count":positive}

def candidate_semantic_alignment(c,expected):
    blob=norm(str(c.get("name") or "")+" "+str(c.get("description") or ""))
    roles=role_terms(expected)
    out={}
    for role,terms in roles.items():
        hits=[t for t in terms if t and t in blob]
        out[role]={"hits":hits,"covered":bool(hits) if terms else True}
    return out

def raw_apt_search(queries):
    seen={}
    if not shutil.which("apt-cache"):
        return seen
    for query in queries:
        try:
            p=subprocess.run(["apt-cache","search",query],text=True,capture_output=True,timeout=25)
        except Exception:
            continue
        if p.returncode!=0:
            continue
        for line in p.stdout.splitlines():
            if " - " not in line:
                continue
            name,desc=line.split(" - ",1)
            seen.setdefault(name.strip(),desc.strip())
    return seen

def oracle_match(name,oracles):
    n=norm(name)
    return any(norm(o) in n or n in norm(o) for o in oracles if norm(o))

def main():
    m=json.loads(MANIFEST.read_text())
    results=[]
    t0=time.monotonic()
    for effect in m["effects"]:
        goal=effect["goal"]
        expected=effect["expected_roles"]
        queries=capability_discovery.effect_queries(goal)
        raw=raw_apt_search(queries)
        ranked=capability_discovery.search_apt_packages(goal,limit=50)
        candidates=ranked.get("candidates",[]) or []
        oracles=effect["oracle_families"]

        raw_oracles=[name for name in raw if oracle_match(name,oracles)]
        ranked_oracle_rank=None
        ranked_oracle_name=None
        for i,c in enumerate(candidates,1):
            if oracle_match(c.get("name"),oracles):
                ranked_oracle_rank=i
                ranked_oracle_name=c.get("name")
                break

        top=[]
        for i,c in enumerate(candidates[:12],1):
            top.append({
              "rank":i,
              "name":c.get("name"),
              "description":c.get("description"),
              "score":c.get("score"),
              "matched_terms":c.get("matched_terms"),
              "role_classification":classify_candidate(c),
              "semantic_alignment":candidate_semantic_alignment(c,expected),
            })

        query_cov=query_role_coverage(queries,expected)
        missing_query_roles=[
          role for role,v in query_cov.items()
          if not v["covered"] and v["terms"]
        ]

        if not raw_oracles:
            failure_stage="QUERY_RETRIEVAL"
        elif ranked_oracle_rank is None:
            failure_stage="RANKING_OR_TOPK_TRUNCATION"
        else:
            failure_stage="ORACLE_RETRIEVED_AND_RANKED"

        top1=top[0] if top else None
        top1_role=(top1 or {}).get("role_classification",{}).get("tool_role")
        top1_operation=((top1 or {}).get("semantic_alignment",{}).get("operation") or {}).get("covered")
        oracle_beaten_by_wrong_role=bool(
          ranked_oracle_rank and ranked_oracle_rank>1 and top1_role in {"NON_EXECUTABLE_OR_AUXILIARY_LIKELY","AMBIGUOUS_TOOL_ROLE"}
        )
        format_without_operation=bool(
          top1
          and ((top1.get("semantic_alignment",{}).get("format") or {}).get("covered"))
          and not top1_operation
        )

        results.append({
          "id":effect["id"],
          "goal":goal,
          "queries":queries,
          "expected_roles":expected,
          "query_role_coverage":query_cov,
          "missing_query_roles":missing_query_roles,
          "raw_apt_result_count":len(raw),
          "oracle_families":oracles,
          "oracle_present_in_raw_search":bool(raw_oracles),
          "raw_oracle_matches":raw_oracles[:20],
          "oracle_rank_top50":ranked_oracle_rank,
          "oracle_ranked_name":ranked_oracle_name,
          "failure_stage":failure_stage,
          "top12":top,
          "top1_auxiliary_or_ambiguous":top1_role in {"NON_EXECUTABLE_OR_AUXILIARY_LIKELY","AMBIGUOUS_TOOL_ROLE"},
          "top1_format_without_operation":format_without_operation,
          "oracle_beaten_by_wrong_role_candidate":oracle_beaten_by_wrong_role,
        })

    counts={}
    for r in results:
        counts[r["failure_stage"]]=counts.get(r["failure_stage"],0)+1
        for role in r["missing_query_roles"]:
            counts["MISSING_QUERY_ROLE:"+role]=counts.get("MISSING_QUERY_ROLE:"+role,0)+1
        if r["top1_auxiliary_or_ambiguous"]:
            counts["TOP1_AUXILIARY_OR_AMBIGUOUS_ROLE"]=counts.get("TOP1_AUXILIARY_OR_AMBIGUOUS_ROLE",0)+1
        if r["top1_format_without_operation"]:
            counts["TOP1_FORMAT_MATCH_WITHOUT_OPERATION_MATCH"]=counts.get("TOP1_FORMAT_MATCH_WITHOUT_OPERATION_MATCH",0)+1

    dominant=[{"class":k,"count":v} for k,v in sorted(counts.items(),key=lambda kv:(-kv[1],kv[0])) if v>=2]
    result={
      "schema":"PROJECT_BRAIN_SEMANTIC_ROLE_DIAGNOSTIC_RESULT_V1",
      "diagnostic_id":m["diagnostic_id"],
      "runtime_mutation_performed":False,
      "package_installation_performed":False,
      "candidate_execution_performed":False,
      "oracle_used_for_query_construction":False,
      "effect_count":len(results),
      "effects":results,
      "aggregate_counts":counts,
      "repeated_role_mismatches":dominant,
      "diagnostic_wall_s":round(time.monotonic()-t0,6),
      "promotion_authorized":False,
      "required_next_action":"RECONCILE_SEMANTIC_ROLE_DIAGNOSTIC__NO_RUNTIME_REPAIR_ON_THIS_BRANCH"
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
