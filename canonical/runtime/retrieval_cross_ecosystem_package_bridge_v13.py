#!/usr/bin/env python3
"""V13 cross-ecosystem repository -> package identity recovery.

A package target is counted recovered only when:
1) behavior-only GitHub repository search discovers the expected repository, and
2) a manifest inside that discovered repository independently yields the expected
   package identity.

Answer-key package/repository identities are never query terms.
"""
from __future__ import annotations
import base64,hashlib,json,os,re,time,urllib.parse,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor,as_completed
from typing import Any,Mapping
from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_CROSS_ECOSYSTEM_PACKAGE_BRIDGE_V13"

CASES=(
 {"episode_id":"MAVEN_COLLECTIONS","ecosystem":"maven","target_repo":"google/guava","target_package":"com.google.guava:guava","queries":["Java collections caching immutable collections library in:name,description,readme","Java core utility collections cache concurrency in:name,description,readme"]},
 {"episode_id":"MAVEN_JSON_BIND","ecosystem":"maven","target_repo":"FasterXML/jackson-databind","target_package":"com.fasterxml.jackson.core:jackson-databind","queries":["Java JSON data binding object mapper in:name,description,readme","Java POJO JSON serialization data binding in:name,description,readme"]},
 {"episode_id":"MAVEN_LOG_FACADE","ecosystem":"maven","target_repo":"qos-ch/slf4j","target_package":"org.slf4j:slf4j-api","queries":["Java logging facade abstraction API in:name,description,readme","simple logging facade Java in:name,description,readme"]},
 {"episode_id":"NUGET_JSON","ecosystem":"nuget","target_repo":"JamesNK/Newtonsoft.Json","target_package":"Newtonsoft.Json","queries":["dotnet JSON serialization framework in:name,description,readme","C sharp JSON serializer LINQ in:name,description,readme"]},
 {"episode_id":"NUGET_STRUCT_LOG","ecosystem":"nuget","target_repo":"serilog/serilog","target_package":"Serilog","queries":["dotnet structured logging message templates in:name,description,readme","C sharp structured event logging sinks in:name,description,readme"]},
 {"episode_id":"RUBY_HTTP","ecosystem":"rubygems","target_repo":"lostisland/faraday","target_package":"faraday","queries":["Ruby HTTP client middleware adapters in:name,description,readme","Ruby networking client middleware in:name,description,readme"]},
 {"episode_id":"PHP_HTTP","ecosystem":"composer","target_repo":"guzzle/guzzle","target_package":"guzzlehttp/guzzle","queries":["PHP HTTP client PSR middleware in:name,description,readme","PHP HTTP requests promises client in:name,description,readme"]},
 {"episode_id":"PHP_LOGGING","ecosystem":"composer","target_repo":"Seldaek/monolog","target_package":"monolog/monolog","queries":["PHP PSR logging handlers processors in:name,description,readme","PHP logging library handlers formatters in:name,description,readme"]},
)

def _headers():
    h={"Accept":"application/vnd.github+json"}
    token=os.environ.get("GITHUB_TOKEN","").strip()
    if token:
        h["Authorization"]="Bearer "+token
        h["X-GitHub-Api-Version"]="2022-11-28"
    return h

def _j(url,timeout=20.0):
    return base._url_json(url,timeout=timeout,headers=_headers())

def _repo_info(repo,timeout=20.0):
    return _j("https://api.github.com/repos/"+repo,timeout)

def _tree(repo,ref,timeout=20.0):
    url="https://api.github.com/repos/"+repo+"/git/trees/"+urllib.parse.quote(ref,safe="")+"?recursive=1"
    return _j(url,timeout)

def _content(repo,path,ref,timeout=20.0):
    url="https://api.github.com/repos/"+repo+"/contents/"+urllib.parse.quote(path,safe="/")+"?ref="+urllib.parse.quote(ref,safe="")
    obj=_j(url,timeout)
    if obj.get("encoding")!="base64":return ""
    return base64.b64decode(str(obj.get("content") or "")).decode("utf-8","replace")

def _local(tag):
    return tag.rsplit("}",1)[-1]

def parse_maven(text):
    try: root=ET.fromstring(text)
    except Exception:return []
    direct={_local(x.tag):str(x.text or "").strip() for x in list(root)}
    parent=next((x for x in list(root) if _local(x.tag)=="parent"),None)
    pd={_local(x.tag):str(x.text or "").strip() for x in list(parent)} if parent is not None else {}
    group=direct.get("groupId") or pd.get("groupId")
    artifact=direct.get("artifactId")
    if group and artifact and "$" not in group+artifact:return [group+":"+artifact]
    return []

def parse_nuget(text,path):
    out=[]
    try:
        root=ET.fromstring(text)
        for x in root.iter():
            name=_local(x.tag)
            val=str(x.text or "").strip()
            if name in {"PackageId","id"} and val and "$" not in val:out.append(val)
        if not out:
            for x in root.iter():
                if _local(x.tag)=="AssemblyName" and str(x.text or "").strip():out.append(str(x.text).strip())
    except Exception:
        pass
    if not out and path.casefold().endswith(".csproj"):
        out.append(path.rsplit("/",1)[-1][:-7])
    return out

def parse_rubygems(text):
    out=[]
    for m in re.finditer(r"(?:\.|\b)name\s*=\s*['\"]([^'\"]+)['\"]",text):
        out.append(m.group(1))
    return out

def parse_composer(text):
    try:
        name=json.loads(text).get("name")
        return [str(name)] if name else []
    except Exception:return []

def manifest_paths(tree,ecosystem):
    paths=[str(x.get("path")) for x in (tree.get("tree") or []) if x.get("type")=="blob" and x.get("path")]
    if ecosystem=="maven":rows=[p for p in paths if p.endswith("pom.xml")]
    elif ecosystem=="nuget":rows=[p for p in paths if p.casefold().endswith((".csproj",".nuspec"))]
    elif ecosystem=="rubygems":rows=[p for p in paths if p.casefold().endswith(".gemspec")]
    else:rows=[p for p in paths if p.casefold().endswith("composer.json")]
    return sorted(rows,key=lambda p:(p.count("/"),len(p),p))[:50]

def bridge(repo,ecosystem,timeout=20.0):
    info=_repo_info(repo,timeout);ref=str(info.get("default_branch") or "main")
    tree=_tree(repo,ref,timeout);ids=[];seen=set();rows=[]
    for path in manifest_paths(tree,ecosystem):
        try:text=_content(repo,path,ref,timeout)
        except Exception as exc:
            rows.append({"path":path,"status":"FAILED_RETRYABLE","error":f"{type(exc).__name__}:{str(exc)[:250]}"});continue
        if ecosystem=="maven":found=parse_maven(text)
        elif ecosystem=="nuget":found=parse_nuget(text,path)
        elif ecosystem=="rubygems":found=parse_rubygems(text)
        else:found=parse_composer(text)
        for x in found:
            n=str(x).strip()
            if n and n.casefold() not in seen:seen.add(n.casefold());ids.append(n)
        rows.append({"path":path,"status":"SUCCESS","identities":found})
    return {"default_branch":ref,"tree_truncated":bool(tree.get("truncated")),"manifest_count":len(rows),"manifest_rows":rows,"package_identities":ids}

def validate():
    assert len(CASES)==8
    for row in CASES:
        joined=" ".join(row["queries"]).casefold()
        if row["target_repo"].casefold() in joined or row["target_package"].casefold() in joined:
            raise ValueError("ANSWER_KEY_IDENTITY_LEAKED:"+row["episode_id"])

def _case(row:Mapping[str,Any],limit=30,timeout=20.0):
    union=[];seen=set();qrows=[];errors=[];start=time.perf_counter()
    for q in row["queries"]:
        qs=time.perf_counter()
        try:ids=base.github(q,limit=limit,timeout=timeout);st="SUCCESS";err=None
        except Exception as exc:ids=[];st="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}";errors.append(err)
        before=len(union)
        for x in ids:
            n=str(x)
            if n.casefold() not in seen:seen.add(n.casefold());union.append(n)
        qrows.append({"query":q,"status":st,"new_union_candidates":len(union)-before,"latency_seconds":time.perf_counter()-qs,"error":err})
    repo_target=row["target_repo"].casefold()
    repo_hit=repo_target in seen
    observed_bridge=None;package_hit=False;bridge_error=None
    if repo_hit:
        discovered=next(x for x in union if x.casefold()==repo_target)
        try:
            observed_bridge=bridge(discovered,row["ecosystem"],timeout)
            package_hit=row["target_package"].casefold() in {x.casefold() for x in observed_bridge["package_identities"]}
        except Exception as exc:
            bridge_error=f"{type(exc).__name__}:{str(exc)[:400]}"
    return {
      "episode_id":row["episode_id"],"ecosystem":row["ecosystem"],"strategy_id":"CROSS_ECOSYSTEM_MANIFEST_BRIDGE_V13",
      "queries":list(row["queries"]),"query_rows":qrows,"candidate_repositories":union,
      "expected_repository_answer_key":row["target_repo"],"repository_hit":repo_hit,
      "expected_package_answer_key":row["target_package"],"bridge":observed_bridge,
      "package_identity_hit":package_hit,"bridge_error":bridge_error,
      "recovered":bool(repo_hit and package_hit),"request_count":len(row["queries"])+(0 if not repo_hit else 2+(observed_bridge["manifest_count"] if observed_bridge else 0)),
      "latency_seconds":time.perf_counter()-start,"errors":errors,
    }

def run(limit=30,timeout=20.0):
    validate();events=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        fs=[pool.submit(_case,row,limit,timeout) for row in CASES]
        for f in as_completed(fs):events.append(f.result())
    order={x["episode_id"]:i for i,x in enumerate(CASES)};events.sort(key=lambda x:order[x["episode_id"]])
    repo_hits=[x for x in events if x["repository_hit"]];recovered=[x for x in events if x["recovered"]]
    return {"schema":SCHEMA,"status":"LIVE_CROSS_ECOSYSTEM_PACKAGE_BRIDGE_COMPLETE","case_count":8,"repository_hit_count":len(repo_hits),"verified_package_recovery_count":len(recovered),"verified_package_recovery_rate":len(recovered)/8,"recovered_episode_ids":[x["episode_id"] for x in recovered],"residual_episode_ids":[x["episode_id"] for x in events if not x["recovered"]],"events":events,"open_world_completeness_claim":False,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"execution_authority":False,"promotion_authority":False}

if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
