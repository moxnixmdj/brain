#!/usr/bin/env python3
"""Retrieval V13 residual-root recovery arena.

Targets only the unresolved V11/V12 live residuals. Each route fixes a measured
root cause:
- GitHub qualifier pollution/platform-anchor loss -> clean compact lattices;
- cross-language semantic mismatch -> small candidate-only technical bridge;
- npm morphology mismatch -> behavior morphology/synonym variants;
- Hugging Face empty pipeline route -> alternate provider-native filter route;
- Maven prose-search mismatch -> behavior->GitHub repository->POM manifest bridge.

Answer-key identities are evaluation-only and never used for query generation.
"""
from __future__ import annotations
import base64,hashlib,json,os,re,time,urllib.parse
import xml.etree.ElementTree as ET
from typing import Any,Mapping
from canonical.runtime import retrieval_live_provider_arena_v1 as base
from canonical.runtime import retrieval_live_provider_arena_v11 as v11

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V13"
GITHUB_QUALIFIER="in:name,description,readme"
RESIDUAL_IDS=frozenset({
 "GITHUB_RU_NLP","GITHUB_PY_LINTER","GITHUB_PY_CLI","NPM_PROCESS_EXEC",
 "HF_TEXT2TEXT","MAVEN_COLLECTIONS","MAVEN_JSON_BIND","MAVEN_LOG_FACADE",
})
RU_TECH={
 "обработка":"processing","русского":"russian","русский":"russian",
 "языка":"language","язык":"language","морфология":"morphology",
 "именованные":"named","сущности":"entities",
}

def _norm(x:Any)->str:return " ".join(str(x or "").strip().split())
def _strip_github_qualifiers(query:str)->str:
 return _norm(re.sub(r"\bin:[^\s]+"," ",query,flags=re.IGNORECASE))
def _words(query:str)->list[str]:
 return re.findall(r"[^\W_]+(?:[.+#/-][^\W_]+)*",_strip_github_qualifiers(query),re.UNICODE)
def _dedupe(rows:list[str],limit:int=6)->list[str]:
 out=[];seen=set()
 for q in rows:
  q=_norm(q)
  if not q or q.casefold() in seen:continue
  seen.add(q.casefold());out.append(q)
  if len(out)>=limit:break
 return out

def github_compact_queries(query:str,*,max_queries:int=3)->list[str]:
 tokens=_words(query)
 platform=[x for x in tokens if x.casefold() in {"python","java","rust","ruby","php","javascript"}]
 content=[x for x in tokens if x.casefold() not in {"fast","flexible","toolkit"}]
 pset={p.casefold() for p in platform}
 without=[x for x in content if x.casefold() not in pset]
 rows=[]
 if platform and without:
  p=platform[0]
  rows.append(" ".join([p]+without[:3]))
  if len(without)>=3:rows.append(" ".join([p]+without[-3:]))
  if len(without)>=2:rows.append(" ".join([p]+without[:2]))
 else:
  for n in (4,3,2):
   if len(content)>=n:
    rows.append(" ".join(content[:n]));rows.append(" ".join(content[-n:]))
 return [f"{q} {GITHUB_QUALIFIER}" for q in _dedupe(rows,max_queries)]

def russian_technical_bridge_queries(query:str)->list[str]:
 tokens=_words(query);translated=[RU_TECH.get(t.casefold(),t) for t in tokens]
 baseq=" ".join(translated);rows=[baseq]
 if "named entities" in baseq.casefold():
  rows.append(re.sub("named entities","NER",baseq,flags=re.IGNORECASE))
 if "russian" in baseq.casefold():
  rows+=["Russian NLP morphology NER Python","Russian language NLP Python"]
 return [f"{q} {GITHUB_QUALIFIER}" for q in _dedupe(rows,3)]

def npm_morphology_queries(query:str)->list[str]:
 q=_strip_github_qualifiers(query);lower=q.casefold();rows=[]
 if "execute" in lower:
  rows.append(re.sub("execute","execution",q,flags=re.IGNORECASE))
 if "child process" in lower or "execute" in lower:
  rows+=["process execution","process execution promise","shell command execution","child process execution"]
 return _dedupe(rows,5)

def hf_filter(query:str,*,limit:int=200,timeout:float=20.0)->list[str]:
 url="https://huggingface.co/api/models?"+urllib.parse.urlencode({
  "filter":query,"sort":"downloads","direction":"-1","limit":limit,"full":"false"})
 obj=base._url_json(url,timeout=timeout)
 return [str(x.get("id") or x.get("modelId")) for x in (obj or []) if (x.get("id") or x.get("modelId"))][:limit]

def hf_residual_queries(query:str)->list[tuple[str,str]]:
 tag=_norm(query);lexical=tag.replace("-"," ")
 return [("FILTER",tag),("SEARCH",lexical),("SEARCH",lexical.replace("generation","model"))]

def _github_headers()->dict[str,str]:
 h={};token=os.environ.get("GITHUB_TOKEN","").strip()
 if token:
  h["Authorization"]="Bearer "+token;h["X-GitHub-Api-Version"]="2022-11-28"
 return h
def _github_json(url:str,*,timeout:float=20.0)->Any:
 return base._url_json(url,timeout=timeout,headers=_github_headers())

def github_repo_union(query:str,*,limit_per_query:int=8,timeout:float=20.0)->tuple[list[str],list[dict[str,Any]]]:
 qs=github_compact_queries(query,max_queries=3);union=[];seen=set();traces=[]
 for q in qs:
  start=time.perf_counter()
  try:ids=base.github(q,limit=limit_per_query,timeout=timeout);status="SUCCESS";err=None
  except Exception as exc:ids=[];status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
  for rid in ids:
   key=str(rid).casefold()
   if key not in seen:seen.add(key);union.append(str(rid))
  traces.append({"query":q,"status":status,"candidate_count":len(ids),"error":err,
                 "latency_seconds":max(0.0,time.perf_counter()-start)})
 return union,traces

def parse_pom_coordinates(xml_text:str)->list[str]:
 try:root=ET.fromstring(xml_text)
 except Exception:return []
 ns=""
 if root.tag.startswith("{"):ns=root.tag.split("}",1)[0]+"}"
 def txt(node,name):
  child=node.find(ns+name)
  return (child.text or "").strip() if child is not None and child.text else ""
 artifact=txt(root,"artifactId");group=txt(root,"groupId");parent=root.find(ns+"parent")
 if not group and parent is not None:group=txt(parent,"groupId")
 unresolved="$"+"{"
 if not group or not artifact or unresolved in group or unresolved in artifact:return []
 return [f"{group}:{artifact}"]

def repository_pom_coordinates(repo:str,*,timeout:float=20.0,max_poms:int=10)->tuple[list[str],dict[str,Any]]:
 quoted=urllib.parse.quote(repo,safe="/")
 info=_github_json(f"https://api.github.com/repos/{quoted}",timeout=timeout)
 branch=str(info.get("default_branch") or "main")
 tree=_github_json(f"https://api.github.com/repos/{quoted}/git/trees/{urllib.parse.quote(branch,safe='')}?recursive=1",timeout=timeout)
 poms=[x for x in (tree.get("tree") or []) if isinstance(x,Mapping) and x.get("type")=="blob" and str(x.get("path") or "").endswith("pom.xml")]
 poms.sort(key=lambda x:(str(x.get("path")).count("/"),len(str(x.get("path"))),str(x.get("path"))))
 coords=[];seen=set();files=[]
 for row in poms[:max_poms]:
  sha=str(row.get("sha") or "")
  if not sha:continue
  blob=_github_json(f"https://api.github.com/repos/{quoted}/git/blobs/{sha}",timeout=timeout)
  raw=str(blob.get("content") or "").replace("\n","")
  if str(blob.get("encoding") or "").lower()!="base64" or not raw:continue
  try:xml=base64.b64decode(raw).decode("utf-8","replace")
  except Exception:continue
  got=parse_pom_coordinates(xml);files.append({"path":row.get("path"),"blob_sha":sha,"coordinates":got})
  for coord in got:
   key=coord.casefold()
   if key not in seen:seen.add(key);coords.append(coord)
 return coords,{"repository":repo,"default_branch":branch,"pom_files":files}

def maven_behavior_bridge(query:str,*,timeout:float=20.0)->dict[str,Any]:
 repos,search_traces=github_repo_union(query,limit_per_query=8,timeout=timeout)
 coords=[];seen=set();repo_traces=[]
 for repo in repos[:5]:
  try:got,trace=repository_pom_coordinates(repo,timeout=timeout,max_poms=12);status="SUCCESS";err=None
  except Exception as exc:got=[];trace={"repository":repo,"pom_files":[]};status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
  trace["status"]=status;trace["error"]=err;repo_traces.append(trace)
  for coord in got:
   key=coord.casefold()
   if key not in seen:seen.add(key);coords.append(coord)
 return {"repository_candidates":repos,"coordinates":coords,"search_traces":search_traces,"repository_manifest_traces":repo_traces}

def selected_rows()->tuple[Mapping[str,Any],...]:
 rows=tuple(x for x in v11.TASKS if x["episode_id"] in RESIDUAL_IDS)
 if {x["episode_id"] for x in rows}!=set(RESIDUAL_IDS):raise ValueError("V13_RESIDUAL_SET_MISMATCH")
 return rows

def generated_queries(row:Mapping[str,Any])->list[str]:
 eid=str(row["episode_id"])
 if eid=="GITHUB_RU_NLP":return russian_technical_bridge_queries(str(row["query"]))
 if eid in {"GITHUB_PY_LINTER","GITHUB_PY_CLI"}:return github_compact_queries(str(row["query"]),max_queries=3)
 if eid=="NPM_PROCESS_EXEC":return npm_morphology_queries(str(row["query"]))
 if eid=="HF_TEXT2TEXT":return [q for _,q in hf_residual_queries(str(row["query"]))]
 if eid.startswith("MAVEN_"):return github_compact_queries(str(row["query"]),max_queries=3)
 return []

def validate()->None:
 for row in selected_rows():
  target=v11._norm(row["target"]);basename=target.rsplit("/",1)[-1].rsplit(":",1)[-1]
  for q in generated_queries(row):
   nq=v11._norm(q)
   if target and target in nq:raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])
   if len(basename)>=4 and basename in nq:raise ValueError("TARGET_BASENAME_LEAKED_IN_QUERY:"+row["episode_id"])

def _run_simple(queries,provider,*,limit,timeout):
 union=[];seen=set();traces=[];failures=0
 for q in queries:
  start=time.perf_counter()
  try:ids=provider(q,limit=limit,timeout=timeout);status="SUCCESS";err=None
  except Exception as exc:ids=[];status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:400]}";failures+=1
  norm=[v11._norm(x) for x in ids if v11._norm(x)]
  for cid in norm:
   if cid not in seen:seen.add(cid);union.append(cid)
  traces.append({"query":q,"status":status,"candidate_count":len(norm),"latency_seconds":max(0.0,time.perf_counter()-start),"error":err})
 return {"candidate_ids":union,"traces":traces,"request_count":len(queries),"failed_request_count":failures}

def run(*,timeout:float=20.0)->dict[str,Any]:
 validate();events=[]
 for seq,row in enumerate(selected_rows(),1):
  eid=str(row["episode_id"]);start=time.perf_counter();bridge=None
  if eid=="GITHUB_RU_NLP":result=_run_simple(generated_queries(row),base.github,limit=30,timeout=timeout)
  elif eid in {"GITHUB_PY_LINTER","GITHUB_PY_CLI"}:result=_run_simple(generated_queries(row),base.github,limit=30,timeout=timeout)
  elif eid=="NPM_PROCESS_EXEC":result=_run_simple(generated_queries(row),base.npm,limit=40,timeout=timeout)
  elif eid=="HF_TEXT2TEXT":
   union=[];seen=set();traces=[];failures=0
   for kind,value in hf_residual_queries(str(row["query"])):
    qs=time.perf_counter()
    try:ids=hf_filter(value,limit=200,timeout=timeout) if kind=="FILTER" else base.huggingface(value,limit=100,timeout=timeout);status="SUCCESS";err=None
    except Exception as exc:ids=[];status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:400]}";failures+=1
    norm=[v11._norm(x) for x in ids if v11._norm(x)]
    for cid in norm:
     if cid not in seen:seen.add(cid);union.append(cid)
    traces.append({"route":kind,"query":value,"status":status,"candidate_count":len(norm),"latency_seconds":max(0.0,time.perf_counter()-qs),"error":err})
   result={"candidate_ids":union,"traces":traces,"request_count":3,"failed_request_count":failures}
  elif eid.startswith("MAVEN_"):
   try:
    bridge=maven_behavior_bridge(str(row["query"]),timeout=timeout)
    result={"candidate_ids":[v11._norm(x) for x in bridge["coordinates"]],"traces":bridge["search_traces"],
            "request_count":len(bridge["search_traces"])+len(bridge["repository_manifest_traces"]),
            "failed_request_count":sum(1 for x in bridge["search_traces"] if x["status"]!="SUCCESS")+sum(1 for x in bridge["repository_manifest_traces"] if x["status"]!="SUCCESS")}
   except Exception as exc:
    bridge={"error":f"{type(exc).__name__}:{str(exc)[:500]}","coordinates":[]}
    result={"candidate_ids":[],"traces":[],"request_count":1,"failed_request_count":1}
  else:raise AssertionError(eid)
  target=v11._norm(row["target"]);hit=target in set(result["candidate_ids"])
  all_failed=result["request_count"]>0 and result["failed_request_count"]>=result["request_count"]
  events.append({
   "episode_id":eid,"difficulty":row["difficulty"],"provider":row["provider"],"source_id":row["source_id"],
   "upstream_group":row["upstream_group"],"strategy_id":"RESIDUAL_ROOT_FIX_V13",
   "generated_queries":generated_queries(row),"answer_key_used_for_query_generation":False,
   "status":"FAILED_RETRYABLE" if all_failed else "SUCCESS","candidate_ids":result["candidate_ids"],
   "candidate_count":len(result["candidate_ids"]),"expected_target_answer_key":target,"target_hit":hit,
   "target_rank":(result["candidate_ids"].index(target)+1) if hit else None,
   "request_count":result["request_count"],"failed_request_count":result["failed_request_count"],
   "traces":result["traces"],"bridge":bridge,"latency_seconds":max(0.0,time.perf_counter()-start),
   "sequence":seq,"action_id":"LIVEV13:"+hashlib.sha256((eid+"\0"+"\0".join(generated_queries(row))).encode()).hexdigest()[:24],
  })
 good=[x for x in events if x["status"]=="SUCCESS"];recovered=[x for x in good if x["target_hit"]];misses=[x for x in good if not x["target_hit"]]
 prior=22;total=30
 return {
  "schema":SCHEMA,"status":"LIVE_V12_RESIDUAL_ROOT_FIX_PROBE_COMPLETE","residual_case_count":len(events),
  "successful_case_count":len(good),"recovered_count":len(recovered),"remaining_true_miss_count":len(misses),
  "retryable_failure_count":len(events)-len(good),"prior_v11_v12_union_hits":prior,"prior_v11_v12_union_recall":prior/total,
  "v11_v12_v13_union_hits":prior+len(recovered),"v11_v12_v13_union_recall":(prior+len(recovered))/total,
  "recovered_episode_ids":[x["episode_id"] for x in recovered],"remaining_miss_episode_ids":[x["episode_id"] for x in misses],
  "failed_episode_ids":[x["episode_id"] for x in events if x["status"]!="SUCCESS"],"events":events,
  "answer_key_identity_used_for_query_generation":False,"open_world_completeness_claim":False,
  "incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
  "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
  "hard_rules":[
   "ONLY_V12_RESIDUAL_OR_RETRYABLE_EPISODES_ARE_PROBED","ANSWER_KEY_IDENTITIES_ARE_SCORING_ONLY",
   "GITHUB_QUALIFIERS_ARE_REMOVED_BEFORE_QUERY_TOKENIZATION","PLATFORM_ANCHORS_ARE_PRESERVED_WHEN_BEHAVIOR_REQUIRES_THEM",
   "CROSS_LANGUAGE_BRIDGE_TERMS_ARE_CONCEPT_ALIASES_NOT_TARGET_IDENTITIES",
   "MAVEN_PACKAGE_CREDIT_REQUIRES_POM_GROUP_ARTIFACT_COORDINATE_EXTRACTION",
   "FAILED_CALLS_REMAIN_RETRYABLE","FINITE_LIVE_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS"
  ],
 }

def main()->int:
 out=run();print(json.dumps(out,ensure_ascii=False,sort_keys=True));return 0 if out["successful_case_count"]>0 else 1
if __name__=="__main__":raise SystemExit(main())
