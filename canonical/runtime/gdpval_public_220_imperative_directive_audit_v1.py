"""Fail-closed replay of the public GDPval 220-task imperative-directive audit."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from canonical.runtime.bounded_imperative_directive_semantics_v2 import parse_directive,segment_task_text

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/"canonical/evidence/GDPVAL_PUBLIC_220_EXPLICIT_OBLIGATION_LOCALIZATION_20261007_V1.json"
BASE="https://datasets-server.huggingface.co/rows"
EXPECTED=(220,421,173,194)

def _rows():
    out=[]
    for offset,length in ((0,100),(100,100),(200,20)):
        q=urlencode({"dataset":"openai/gdpval","config":"default","split":"train","offset":offset,"length":length})
        with urlopen(BASE+"?"+q,timeout=60) as r: page=json.load(r)
        out.extend({"row_idx":x["row_idx"],**x["row"]} for x in page["rows"])
    return sorted(out,key=lambda x:x["row_idx"])

def evaluate():
    old=json.loads(OLD.read_text(encoding="utf-8")); prior={x["row_idx"]:x for x in old["tasks"]}
    rows=_rows(); errors=[]; directives=tasks_with=tasks_any=0; by_verb={}
    for row in rows:
        p=prior.get(row["row_idx"])
        if not p: errors.append(f"MISSING_PRIOR:{row['row_idx']}"); continue
        if row["task_id"]!=p["task_id"]: errors.append(f"TASK_ID_DRIFT:{row['row_idx']}")
        h=hashlib.sha256(row["prompt"].encode("utf-8")).hexdigest()
        if h!=p["prompt_sha256"]: errors.append(f"PROMPT_SHA_DRIFT:{row['row_idx']}")
        n=0
        for seg in segment_task_text(row["prompt"]):
            x=parse_directive(seg)
            if x.get("status")=="RESOLVED_DIRECTIVE":
                n+=1; v=x["directive"]["predicate"]; by_verb[v]=by_verb.get(v,0)+1
        directives+=n
        if n: tasks_with+=1
        if n+int(p.get("obligation_count",0)): tasks_any+=1
    observed=(len(rows),directives,tasks_with,tasks_any)
    if observed!=EXPECTED: errors.append(f"AGGREGATE_DRIFT:{observed!r}")
    return {
      "schema":"PROJECT_BRAIN_GDPVAL_PUBLIC_220_IMPERATIVE_DIRECTIVE_AUDIT_REPLAY_V1",
      "status":"PASS" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,
      "row_count":len(rows),"resolved_imperative_directive_count":directives,
      "tasks_with_imperative_directives":tasks_with,
      "tasks_with_any_prior_modal_or_new_imperative_positive_semantics":tasks_any,
      "whole_task_semantic_membership_proved_count":0,
      "by_verb":dict(sorted(by_verb.items())),"terminal_credit_delta":0,
    }

if __name__=="__main__":
    x=evaluate(); print(json.dumps(x,indent=2,sort_keys=True)); raise SystemExit(0 if x["pass"] else 1)
