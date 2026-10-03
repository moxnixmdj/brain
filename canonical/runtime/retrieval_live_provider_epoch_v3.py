#!/usr/bin/env python3
"""Corrected concurrent live provider calibration epoch V3.

V3 removes title-only scholarly sufficiency and emits explicit frozen
cross-source entity equivalence only for known target identities.
"""
from __future__ import annotations
import concurrent.futures,json,time,urllib.error
from typing import Any
from canonical.runtime import retrieval_live_provider_epoch_v1 as base
SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_EPOCH_V3"
RECEIPT="canonical/verification/RETRIEVAL_V10_CONTEXTUAL_LIVE_PROVIDER_EPOCH_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
EPISODES=[
 {"episode_id":"V10_FASTAPI","task_class":"CODE_REPOSITORY","query":"fastapi python async web framework","sources":["GITHUB","GITLAB","CODEBERG"],"targets":{"GITHUB":{"github:fastapi/fastapi"}},"entities":{"github:fastapi/fastapi":"entity:fastapi"}},
 {"episode_id":"V10_TESSERACT","task_class":"CODE_REPOSITORY","query":"tesseract ocr engine","sources":["GITLAB","GITHUB","CODEBERG"],"targets":{"GITHUB":{"github:tesseract-ocr/tesseract"}},"entities":{"github:tesseract-ocr/tesseract":"entity:tesseract"}},
 {"episode_id":"V10_REACT","task_class":"JAVASCRIPT_PACKAGE","query":"react javascript ui library","sources":["NPM","GITHUB","GITLAB"],"targets":{"NPM":{"npm:react"},"GITHUB":{"github:facebook/react"}},"entities":{"npm:react":"entity:react","github:facebook/react":"entity:react"}},
 {"episode_id":"V10_REACT_ROTATE","task_class":"JAVASCRIPT_PACKAGE","query":"react component library javascript","sources":["GITHUB","NPM","GITLAB"],"targets":{"NPM":{"npm:react"},"GITHUB":{"github:facebook/react"}},"entities":{"npm:react":"entity:react","github:facebook/react":"entity:react"}},
 {"episode_id":"V10_SERDE","task_class":"RUST_PACKAGE","query":"serde rust serialization","sources":["CRATES","GITHUB","GITLAB"],"targets":{"CRATES":{"crates:serde"},"GITHUB":{"github:serde-rs/serde"}},"entities":{"crates:serde":"entity:serde","github:serde-rs/serde":"entity:serde"}},
 {"episode_id":"V10_SERDE_ROTATE","task_class":"RUST_PACKAGE","query":"rust serialize deserialize serde","sources":["GITHUB","CRATES","GITLAB"],"targets":{"CRATES":{"crates:serde"},"GITHUB":{"github:serde-rs/serde"}},"entities":{"crates:serde":"entity:serde","github:serde-rs/serde":"entity:serde"}},
 {"episode_id":"V10_BERT","task_class":"MODEL_HUB","query":"bert base uncased","sources":["HUGGINGFACE","GITHUB"],"targets":{"HUGGINGFACE":{"hf:google-bert/bert-base-uncased"}},"entities":{"hf:google-bert/bert-base-uncased":"entity:bert-base-uncased"}},
 {"episode_id":"V10_CLIP","task_class":"MODEL_HUB","query":"openai clip vision text","sources":["GITHUB","HUGGINGFACE"],"targets":{"GITHUB":{"github:openai/clip"},"HUGGINGFACE":{"hf:openai/clip-vit-base-patch32"}},"entities":{"github:openai/clip":"entity:openai-clip","hf:openai/clip-vit-base-patch32":"entity:openai-clip"}},
 {"episode_id":"V10_ATTENTION","task_class":"SCHOLARLY_WORK","query":"Attention Is All You Need","sources":["CROSSREF","OPENALEX"],"targets":{"OPENALEX":{"openalex:w2626778328"}},"entities":{"openalex:w2626778328":"entity:attention-is-all-you-need"}},
 {"episode_id":"V10_RESNET","task_class":"SCHOLARLY_WORK","query":"Deep Residual Learning for Image Recognition","sources":["OPENALEX","CROSSREF"],"targets":{"OPENALEX":{"openalex:w2194775991"},"CROSSREF":{"doi:10.1109/cvpr.2016.90"}},"entities":{"openalex:w2194775991":"entity:deep-residual-learning","doi:10.1109/cvpr.2016.90":"entity:deep-residual-learning"}},
 {"episode_id":"V10_LISTCOMP","task_class":"TECHNICAL_DISCUSSION","query":"python list comprehension","sources":["STACKOVERFLOW","GITHUB"],"targets":{},"entities":{}},
 {"episode_id":"V10_RUSTLIFETIME","task_class":"TECHNICAL_DISCUSSION","query":"rust lifetime error","sources":["GITHUB","STACKOVERFLOW"],"targets":{},"entities":{}},
]
def _call(ep:dict[str,Any],seq:int,source:str):
 start=time.perf_counter();rows=[];status="SUCCESS";err=None
 try:rows=base.provider(source,ep["query"])
 except urllib.error.HTTPError as exc:
  status="FAILED_RETRYABLE" if exc.code in {403,408,409,425,429,500,502,503,504} else "FAILED_PERMANENT";err=f"HTTPError:{exc.code}"
 except Exception as exc:
  status="FAILED_RETRYABLE";err=type(exc).__name__+":"+str(exc)[:240]
 latency=time.perf_counter()-start;ids=[x["id"] for x in rows if x.get("id")]
 expected=(ep.get("targets") or {}).get(source,set());sufficient=sorted(set(ids)&set(expected))
 entity_map={cid:ep["entities"][cid] for cid in ids if cid in ep.get("entities",{})}
 event={"episode_id":ep["episode_id"],"task_class":ep["task_class"],"source_id":source,"upstream_group":source+"_PUBLIC_API",
  "action_id":ep["episode_id"]+":"+source,"sequence":seq,"status":status,"candidate_ids":ids,"candidate_entities":entity_map,
  "verified_sufficient_candidate_ids":sufficient,"independent_receipt":RECEIPT if sufficient else None,
  "latency_seconds":round(latency,6),"request_count":1}
 raw={"episode_id":ep["episode_id"],"source_id":source,"query":ep["query"],"status":status,"error":err,"rows":rows}
 return seq,event,raw
def run(max_workers:int=12):
 jobs=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(max_workers),24))) as ex:
  futs={}
  for epi,ep in enumerate(EPISODES):
   for seq,source in enumerate(ep["sources"],1):futs[ex.submit(_call,ep,seq,source)]=(epi,seq)
  for fut,order in futs.items():
   seq,event,raw=fut.result();jobs.append((order,event,raw))
 jobs.sort(key=lambda x:x[0]);events=[x[1] for x in jobs];raw=[x[2] for x in jobs]
 return {"schema":SCHEMA,"status":"LIVE_CONCURRENT_ENTITY_RESOLVED_EPOCH_COMPLETED","episode_count":len(EPISODES),"event_count":len(events),
  "source_count":len({x["source_id"] for x in events}),"task_class_count":len({x["task_class"] for x in events}),"events":events,"raw_results":raw,
  "parallel_execution":True,"incremental_spend_usd":0,
  "hard_rules":["PUBLIC_ZERO_COST_APIS_ONLY","SUFFICIENCY_MATCHES_ONLY_FROZEN_EXACT_TARGET_IDS","TITLE_ONLY_SUFFICIENCY_IS_FORBIDDEN",
   "CROSS_SOURCE_ENTITY_EQUIVALENCE_IS_EXPLICIT_AND_FROZEN_NOT_HEURISTIC","UNMAPPED_CANDIDATES_REMAIN_SOURCE_SCOPED",
   "FAILED_PROVIDER_CALLS_REMAIN_FAILURE_EVENTS","LIVE_RESULTS_ARE_NOT_COMPLETENESS_PROOFS"]}
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
