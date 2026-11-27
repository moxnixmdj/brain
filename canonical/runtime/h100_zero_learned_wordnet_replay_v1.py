"""Replay frozen H100 lexical challenge against exact pinned raw WordNet bytes."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

from canonical.runtime.h100_zero_learned_wordnet_role_v1 import induce_roles_from_wordnet

COMMIT="ce91915ae38a341ae845be4d825ef6003cddf395"
BASE=f"https://raw.githubusercontent.com/nltk/wordnet/{COMMIT}/wn/data/wordnet-3.0"
SOURCES={
    "index.noun":"1a458379f794704c0e283d5204413732f1dbe65d",
    "data.noun":"4575737e5b3b832f52c18842ff5e195d83deeb54",
}
PRE=Path(__file__).resolve().parents[1]/"governance"/"H100_ZERO_LEARNED_LEXICAL_ROLE_PREEXPOSURE_V1.json"

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def fetch(name:str)->str:
    with urllib.request.urlopen(f"{BASE}/{name}",timeout=30) as response:
        data=response.read()
    actual=git_blob_sha(data)
    expected=SOURCES[name]
    if actual!=expected:
        raise RuntimeError(f"WORDNET_BLOB_MISMATCH:{name}:{actual}!={expected}")
    return data.decode("utf-8",errors="strict")

def replay()->dict:
    index_text=fetch("index.noun")
    data_text=fetch("data.noun")
    doc=json.loads(PRE.read_text())
    results=[]
    identified=0
    abstained=0
    for task in doc["tasks"]:
        out=induce_roles_from_wordnet(task["text"],noun_index=index_text,noun_data=data_text)
        ok=(out["status"]==task["expected_status"] and out["inputs"]==task["expected_inputs"] and out["target"]==task["expected_target"])
        results.append({
            "task_id":task["task_id"],
            "pass":ok,
            "status":out["status"],
            "expected_status":task["expected_status"],
            "left_cue_role":out["left_cue_role"],
            "right_cue_role":out["right_cue_role"],
        })
        if ok and out["status"]=="ROLES_IDENTIFIED":
            identified+=1
        elif ok and out["status"]=="ABSTAIN_DIRECTION_NOT_IDENTIFIED":
            abstained+=1
    return {
        "schema":"PROJECT_BRAIN_H100_ZERO_LEARNED_WORDNET_REPLAY_RESULT_V1",
        "status":"PASS" if all(r["pass"] for r in results) else "RESIDUAL_OPEN",
        "identified_correct":identified,
        "abstained_correct":abstained,
        "task_count":len(results),
        "results":results,
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "raw_external_knowledge_source":"PINNED_WORDNET_3_0",
        "hard_nonclaim":"FINITE_PINNED_WORDNET_REPLAY_IS_NOT_OPEN_WORLD_SEMANTIC_UNDERSTANDING",
    }

if __name__=="__main__":
    print(json.dumps(replay(),sort_keys=True,indent=2))
