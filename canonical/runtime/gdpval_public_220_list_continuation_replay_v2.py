from __future__ import annotations
import hashlib,json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from canonical.runtime.bounded_task_list_continuation_v1 import bind_continuations

ROOT=Path(__file__).resolve().parents[2]
BASE="https://datasets-server.huggingface.co/rows"
OLD=ROOT/"canonical/evidence/GDPVAL_PUBLIC_220_EXPLICIT_OBLIGATION_LOCALIZATION_20261007_V1.json"
EXPECTED_BLOBS={
 "canonical/runtime/bounded_task_list_continuation_v1.py":"ec3682aa4115063c937c36dd04bc73b0897d93f6",
 "canonical/runtime/bounded_task_directive_semantics_v1.py":"e3a4c01cc08e7a569692a5d6f03a6feec69934bf",
 "canonical/evidence/GDPVAL_PUBLIC_220_EXPLICIT_OBLIGATION_LOCALIZATION_20261007_V1.json":"7a2d726adb155bee0f1e6f4af71ee90cc547bbbc",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def rows():
 out=[]
 for offset,length in ((0,100),(100,100),(200,20)):
  q=urlencode({"dataset":"openai/gdpval","config":"default","split":"train","offset":offset,"length":length})
  req=Request(BASE+"?"+q,headers={"User-Agent":"project-brain-gdpval-list-v2/1.0"})
  with urlopen(req,timeout=60) as r: page=json.load(r)
  out.extend({"row_idx":x["row_idx"],**x["row"]} for x in page["rows"])
 return sorted(out,key=lambda x:x["row_idx"])
def evaluate():
 errors=[]; observed={}
 for rel,want in EXPECTED_BLOBS.items():
  p=ROOT/rel
  if not p.is_file(): errors.append("SOURCE_MISSING:"+rel); continue
  got=blob(p.read_bytes()); observed[rel]=got
  if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)
 prior_doc=json.loads(OLD.read_text()); prior={int(x["row_idx"]):x for x in prior_doc["tasks"]}
 rs=rows()
 if len(rs)!=220: errors.append("ROW_COUNT:"+str(len(rs)))
 blocks=children=tasks=0
 for row in rs:
  i=int(row["row_idx"]); p=prior.get(i)
  if p is None: errors.append("PRIOR_ROW_MISSING:"+str(i)); continue
  if row.get("task_id")!=p.get("task_id"): errors.append("TASK_ID_DRIFT:"+str(i))
  h=hashlib.sha256(str(row.get("prompt") or "").encode()).hexdigest()
  if h!=p.get("prompt_sha256"): errors.append("PROMPT_SHA_DRIFT:"+str(i))
  out=bind_continuations(str(row.get("prompt") or ""))
  blocks+=int(out.get("block_count") or 0)
  children+=int(out.get("child_item_count") or 0)
  tasks+=int(int(out.get("block_count") or 0)>0)
 expected={"bound_block_count":41,"bound_child_item_count":173,"tasks_with_bound_list_structure":33}
 actual={"bound_block_count":blocks,"bound_child_item_count":children,"tasks_with_bound_list_structure":tasks}
 if actual!=expected: errors.append("AGGREGATE_DRIFT:"+json.dumps(actual,sort_keys=True))
 return {
  "schema":"PROJECT_BRAIN_GDPVAL_PUBLIC_220_LIST_CONTINUATION_REPLAY_VERIFIER_V2",
  "status":"PASS__EXACT_SOURCE_AND_PROMPT_IDENTITY__41_BLOCKS__173_CHILDREN__33_TASKS" if not errors else "FAIL_CLOSED",
  "pass":not errors,"errors":errors,"source_blobs":observed,"row_count":len(rs),
  "observed":actual,"expected":expected,"terminal_credit_delta":0,
 }
if __name__=="__main__":
 x=evaluate(); print(json.dumps(x,indent=2,sort_keys=True)); raise SystemExit(0 if x["pass"] else 1)
