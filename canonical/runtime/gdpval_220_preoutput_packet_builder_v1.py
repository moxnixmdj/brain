#!/usr/bin/env python3
"""Build a fail-closed, field-firewalled GDPval-AA v2.1 220-task packet manifest.

No gold deliverable, rubric, model-submission, or judge-feedback fields are
emitted. The manifest is a pre-output execution commitment, not a score.
"""
from __future__ import annotations
import hashlib, json, re, sys, urllib.request

SCHEMA="PROJECT_BRAIN_GDPVAL_220_PREOUTPUT_PACKET_MANIFEST_V1"
PACKET_SCHEMA="PROJECT_BRAIN_GDPVAL_PREOUTPUT_PACKET_V1"
DATASET="openai/gdpval"
EXPECTED_REVISION="11e7900cdcac61bc4daf59e65feb238acda98fbf"
POPULATION=220
ALLOWED=(
    "task_id","sector","occupation","prompt",
    "reference_files","reference_file_urls","reference_file_hf_uris",
)
FORBIDDEN=(
    "deliverable_files","deliverable_file_urls","deliverable_file_hf_uris",
    "rubric_pretty","rubric_json","model_submissions","judge_feedback",
)

def canon(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def sha_obj(v):
    return sha_bytes(canon(v).encode("utf-8"))

def segments(text):
    out=[]
    def emit(start,end):
        while start<end and text[start].isspace(): start+=1
        while end>start and text[end-1].isspace(): end-=1
        if start<end and text[start:end].strip():
            s=text[start:end]
            out.append([start,end,sha_bytes(s.encode("utf-8"))])
    cursor=0; i=0; n=len(text)
    while i<n:
        ch=text[i]
        if ch=="\n":
            emit(cursor,i+1); cursor=i+1; i+=1; continue
        if ch in ".!?":
            j=i+1
            while j<n and text[j] in ".!?": j+=1
            emit(cursor,j); cursor=j; i=j; continue
        i+=1
    emit(cursor,n)
    return out

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Project-Brain-GDPval-Packet-Builder/1"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.load(r)

def dataset_revision():
    info=get_json("https://huggingface.co/api/datasets/openai/gdpval")
    return str(info.get("sha") or "")

def fetch_rows(offset,length):
    url=(
      "https://datasets-server.huggingface.co/rows?"
      "dataset=openai%2Fgdpval&config=default&split=train"
      f"&offset={offset}&length={length}"
    )
    return get_json(url).get("rows") or []

def build(output_path):
    revision=dataset_revision()
    if revision!=EXPECTED_REVISION:
        raise RuntimeError("DATASET_REVISION_DRIFT:"+revision)
    packets=[]
    seen=set()
    for offset in range(0,POPULATION,50):
        rows=fetch_rows(offset,min(50,POPULATION-offset))
        for item in rows:
            idx=item.get("row_idx")
            raw=item.get("row") or {}
            if not isinstance(idx,int) or idx<0 or idx>=POPULATION:
                raise RuntimeError("ROW_INDEX_INVALID:"+repr(idx))
            if idx in seen:
                raise RuntimeError("ROW_INDEX_DUPLICATE:"+str(idx))
            seen.add(idx)
            allowed={k:raw.get(k) for k in ALLOWED}
            if any(k in allowed for k in FORBIDDEN):
                raise RuntimeError("FIELD_FIREWALL_BREACH")
            task_id=allowed.get("task_id")
            prompt=allowed.get("prompt")
            if not isinstance(task_id,str) or not task_id:
                raise RuntimeError("TASK_ID_MISSING:"+str(idx))
            if not isinstance(prompt,str) or not prompt.strip():
                raise RuntimeError("PROMPT_MISSING:"+str(idx))
            segs=segments(prompt)
            if not segs:
                raise RuntimeError("RAW_OBLIGATIONS_EMPTY:"+str(idx))
            refs={
              "reference_files":allowed.get("reference_files") or [],
              "reference_file_urls":allowed.get("reference_file_urls") or [],
              "reference_file_hf_uris":allowed.get("reference_file_hf_uris") or [],
            }
            packet_core={
              "row_idx":idx,
              "task_id":task_id,
              "sector":allowed.get("sector"),
              "occupation":allowed.get("occupation"),
              "prompt_sha256":sha_bytes(prompt.encode("utf-8")),
              "prompt_bytes":len(prompt.encode("utf-8")),
              "allowed_projection_sha256":sha_obj(allowed),
              "raw_obligation_count":len(segs),
              "raw_obligation_root_sha256":sha_obj(segs),
              "reference_count":len(refs["reference_files"]),
              "reference_manifest_sha256":sha_obj(refs),
            }
            packets.append({
              "schema":PACKET_SCHEMA,
              **packet_core,
              "packet_sha256":sha_obj(packet_core),
              "status":"PREOUTPUT_BOUND__NO_SUBMISSION_OR_SCORE_CREDIT",
            })
    if seen!=set(range(POPULATION)):
        raise RuntimeError("POPULATION_INCOMPLETE")
    packets.sort(key=lambda x:x["row_idx"])
    root=sha_obj([x["packet_sha256"] for x in packets])
    manifest={
      "schema":SCHEMA,
      "status":"PASS__220_OF_220_FIELD_FIREWALLED_PREOUTPUT_PACKETS_BOUND__ZERO_SCORE_CREDIT",
      "dataset":DATASET,
      "dataset_revision":revision,
      "population_count":POPULATION,
      "field_firewall":{
        "allowed":list(ALLOWED),
        "forbidden_before_submission":list(FORBIDDEN),
      },
      "packets":packets,
      "manifest_root_sha256":root,
      "hard_nonclaims":[
        "NO_BRAIN_220_SUBMISSIONS",
        "NO_ARTIFICIAL_ANALYSIS_OWNER_SCORE",
        "NO_GDPVAL_ELO",
        "NO_1846_THRESHOLD_CLOSURE",
        "NO_TERMINAL_CREDIT",
      ],
    }
    raw=(json.dumps(manifest,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    with open(output_path,"wb") as f: f.write(raw)
    return manifest, sha_bytes(raw), len(raw)

if __name__=="__main__":
    out=sys.argv[1] if len(sys.argv)>1 else "GDPVAL_220_PREOUTPUT_PACKET_MANIFEST_20261011_V1.json"
    m,h,n=build(out)
    checkpoints={i:m["packets"][i] for i in (0,5,6,8,9,10,11,219)}
    print(canon({
      "status":m["status"],
      "dataset_revision":m["dataset_revision"],
      "population_count":m["population_count"],
      "manifest_root_sha256":m["manifest_root_sha256"],
      "file_sha256":h,
      "file_bytes":n,
      "checkpoints":checkpoints,
    }))
