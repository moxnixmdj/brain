#!/usr/bin/env python3
"""Zero-cost live multi-provider calibration epoch for retrieval V10."""
from __future__ import annotations
import hashlib,json,time,urllib.parse,urllib.request,urllib.error
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_EPOCH_V1"
RECEIPT="canonical/verification/RETRIEVAL_V10_LIVE_PROVIDER_EPOCH_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
UA="Project-Brain-Retrieval-Calibration/1.0"

EPISODES=[
 {"episode_id":"V10_FASTAPI","task_class":"CODE_REPOSITORY","query":"fastapi python async web framework","sources":["GITHUB","GITLAB","CODEBERG"],"targets":{"GITHUB":{"github:fastapi/fastapi"}}},
 {"episode_id":"V10_TESSERACT","task_class":"CODE_REPOSITORY","query":"tesseract ocr engine","sources":["GITLAB","GITHUB","CODEBERG"],"targets":{"GITHUB":{"github:tesseract-ocr/tesseract"}}},
 {"episode_id":"V10_REACT","task_class":"JAVASCRIPT_PACKAGE","query":"react javascript ui library","sources":["NPM","GITHUB","GITLAB"],"targets":{"NPM":{"npm:react"},"GITHUB":{"github:facebook/react"}}},
 {"episode_id":"V10_REACT_ROTATE","task_class":"JAVASCRIPT_PACKAGE","query":"react component library javascript","sources":["GITHUB","NPM","GITLAB"],"targets":{"NPM":{"npm:react"},"GITHUB":{"github:facebook/react"}}},
 {"episode_id":"V10_SERDE","task_class":"RUST_PACKAGE","query":"serde rust serialization","sources":["CRATES","GITHUB","GITLAB"],"targets":{"CRATES":{"crates:serde"},"GITHUB":{"github:serde-rs/serde"}}},
 {"episode_id":"V10_SERDE_ROTATE","task_class":"RUST_PACKAGE","query":"rust serialize deserialize serde","sources":["GITHUB","CRATES","GITLAB"],"targets":{"CRATES":{"crates:serde"},"GITHUB":{"github:serde-rs/serde"}}},
 {"episode_id":"V10_BERT","task_class":"MODEL_HUB","query":"bert base uncased","sources":["HUGGINGFACE","GITHUB"],"targets":{"HUGGINGFACE":{"hf:google-bert/bert-base-uncased"}}},
 {"episode_id":"V10_CLIP","task_class":"MODEL_HUB","query":"openai clip vision text","sources":["GITHUB","HUGGINGFACE"],"targets":{"GITHUB":{"github:openai/clip"},"HUGGINGFACE":{"hf:openai/clip-vit-base-patch32"}}},
 {"episode_id":"V10_ATTENTION","task_class":"SCHOLARLY_WORK","query":"Attention Is All You Need","sources":["CROSSREF","OPENALEX"],"target_title":"attention is all you need"},
 {"episode_id":"V10_RESNET","task_class":"SCHOLARLY_WORK","query":"Deep Residual Learning for Image Recognition","sources":["OPENALEX","CROSSREF"],"target_title":"deep residual learning for image recognition"},
 {"episode_id":"V10_LISTCOMP","task_class":"TECHNICAL_DISCUSSION","query":"python list comprehension","sources":["STACKOVERFLOW","GITHUB"],"targets":{}},
 {"episode_id":"V10_RUSTLIFETIME","task_class":"TECHNICAL_DISCUSSION","query":"rust lifetime error","sources":["GITHUB","STACKOVERFLOW"],"targets":{}},
]

def _canon(x:Any)->str:return " ".join(str(x or "").casefold().strip().split())
def _get(url:str,timeout:int=20)->Any:
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:
  return json.loads(r.read().decode("utf-8","replace"))
def _qid(s:str)->str:return urllib.parse.quote_plus(s)

def provider(source:str,query:str)->list[dict[str,str]]:
 q=_qid(query)
 if source=="GITHUB":
  obj=_get("https://api.github.com/search/repositories?q="+q+"&per_page=10")
  return [{"id":"github:"+_canon(x.get("full_name")),"title":str(x.get("full_name") or "")} for x in obj.get("items",[]) if x.get("full_name")]
 if source=="GITLAB":
  obj=_get("https://gitlab.com/api/v4/projects?simple=true&per_page=10&search="+q)
  return [{"id":"gitlab:"+_canon(x.get("path_with_namespace")),"title":str(x.get("path_with_namespace") or "")} for x in obj if x.get("path_with_namespace")]
 if source=="CODEBERG":
  obj=_get("https://codeberg.org/api/v1/repos/search?q="+q+"&limit=10")
  rows=obj.get("data",[]) if isinstance(obj,dict) else []
  return [{"id":"codeberg:"+_canon(x.get("full_name")),"title":str(x.get("full_name") or "")} for x in rows if x.get("full_name")]
 if source=="NPM":
  obj=_get("https://registry.npmjs.org/-/v1/search?size=10&text="+q)
  return [{"id":"npm:"+_canon((x.get("package") or {}).get("name")),"title":str((x.get("package") or {}).get("name") or "")} for x in obj.get("objects",[]) if (x.get("package") or {}).get("name")]
 if source=="CRATES":
  obj=_get("https://crates.io/api/v1/crates?per_page=10&q="+q)
  return [{"id":"crates:"+_canon(x.get("id")),"title":str(x.get("id") or "")} for x in obj.get("crates",[]) if x.get("id")]
 if source=="HUGGINGFACE":
  obj=_get("https://huggingface.co/api/models?limit=10&search="+q)
  return [{"id":"hf:"+_canon(x.get("id")),"title":str(x.get("id") or "")} for x in obj if x.get("id")]
 if source=="CROSSREF":
  obj=_get("https://api.crossref.org/works?rows=10&query.title="+q)
  out=[]
  for x in (obj.get("message") or {}).get("items",[]):
   title=((x.get("title") or [""])[0] if isinstance(x.get("title"),list) else x.get("title") or "")
   doi=str(x.get("DOI") or "")
   cid="doi:"+_canon(doi) if doi else "crossref-title:"+hashlib.sha256(_canon(title).encode()).hexdigest()[:20]
   out.append({"id":cid,"title":title})
  return out
 if source=="OPENALEX":
  obj=_get("https://api.openalex.org/works?per-page=10&search="+q)
  return [{"id":"openalex:"+_canon(str(x.get("id") or "").rsplit("/",1)[-1]),"title":str(x.get("display_name") or "")} for x in obj.get("results",[]) if x.get("id")]
 if source=="STACKOVERFLOW":
  obj=_get("https://api.stackexchange.com/2.3/search/advanced?site=stackoverflow&pagesize=10&q="+q)
  return [{"id":"stackoverflow:"+str(x.get("question_id")),"title":str(x.get("title") or "")} for x in obj.get("items",[]) if x.get("question_id")]
 raise ValueError("UNKNOWN_SOURCE:"+source)

def run()->dict[str,Any]:
 events=[];raw=[]
 for ep in EPISODES:
  for seq,source in enumerate(ep["sources"],1):
   start=time.perf_counter();rows=[];status="SUCCESS";err=None
   try:rows=provider(source,ep["query"])
   except urllib.error.HTTPError as exc:
    status="FAILED_RETRYABLE" if exc.code in {403,408,409,425,429,500,502,503,504} else "FAILED_PERMANENT";err=f"HTTPError:{exc.code}"
   except Exception as exc:
    status="FAILED_RETRYABLE";err=type(exc).__name__+":"+str(exc)[:240]
   latency=time.perf_counter()-start
   ids=[x["id"] for x in rows if x.get("id")]
   sufficient=[]
   expected=(ep.get("targets") or {}).get(source,set())
   if expected:sufficient=sorted(set(ids)&set(expected))
   target_title=_canon(ep.get("target_title"))
   if target_title:
    for x in rows:
     if _canon(x.get("title"))==target_title:sufficient.append(x["id"])
   sufficient=sorted(set(sufficient))
   event={"episode_id":ep["episode_id"],"task_class":ep["task_class"],"source_id":source,
    "upstream_group":source+"_PUBLIC_API","action_id":ep["episode_id"]+":"+source,"sequence":seq,"status":status,
    "candidate_ids":ids,"verified_sufficient_candidate_ids":sufficient,
    "independent_receipt":RECEIPT if sufficient else None,"latency_seconds":round(latency,6),"request_count":1}
   events.append(event);raw.append({"episode_id":ep["episode_id"],"source_id":source,"query":ep["query"],"status":status,"error":err,"rows":rows})
 return {"schema":SCHEMA,"status":"LIVE_EPOCH_COMPLETED","episode_count":len(EPISODES),"event_count":len(events),
  "source_count":len({x["source_id"] for x in events}),"task_class_count":len({x["task_class"] for x in events}),
  "events":events,"raw_results":raw,"incremental_spend_usd":0,
  "hard_rules":["PUBLIC_ZERO_COST_APIS_ONLY","FAILED_PROVIDER_CALLS_REMAIN_FAILURE_EVENTS","SUFFICIENT_LABELS_ONLY_MATCH_FROZEN_EXPECTED_IDENTITIES_OR_EXACT_FROZEN_TITLES","LIVE_RESULTS_ARE_NOT_COMPLETENESS_PROOFS"]}
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
