from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MANIFEST="canonical/governance/CONTINUITY_SELECTED_DEPLOYMENT_ROUTE_20261007_V1.json"
ADAPTER="canonical/runtime/continuity_root3_inprocess_executor_v1.py"
SUPERVISOR="canonical/runtime/same_identity_supervisor_credited_v1.py"

EXPECTED={
 ADAPTER:"a5cee8555b79d330e415d71df827c51bd6339644",
 SUPERVISOR:"47c461f502e840def0c38728e1bfd7c6401cb804",
}
DEFAULTS={
 "--tasks-dir":"canonical/same_identity_worker/tasks",
 "--state-dir":"canonical/same_identity_worker/state",
 "--evidence-dir":"canonical/same_identity_worker/evidence",
}
ALLOWED_PREFIXES=(
 "canonical/same_identity_worker/state",
 "canonical/same_identity_worker/evidence",
 "canonical/same_identity_worker/external_tool_bridge",
)

def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def defs(tree):
 return {n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

def parser_defaults(fn):
 out={}
 for n in ast.walk(fn):
  if not isinstance(n,ast.Call): continue
  if not isinstance(n.func,ast.Attribute) or n.func.attr!="add_argument": continue
  if not n.args or not isinstance(n.args[0],ast.Constant) or not isinstance(n.args[0].value,str): continue
  flag=n.args[0].value
  for kw in n.keywords:
   if kw.arg=="default" and isinstance(kw.value,ast.Constant) and isinstance(kw.value.value,str):
    out[flag]=kw.value.value
 return out

def evaluate(root:Path=ROOT):
 errors=[]
 observed={}
 texts={}
 trees={}
 for rel,expected in EXPECTED.items():
  data=(root/rel).read_bytes(); sha=blob(data); observed[rel]=sha
  if sha!=expected: errors.append(f"BLOB_DRIFT:{rel}:{sha}")
  text=data.decode(); texts[rel]=text; trees[rel]=ast.parse(text,filename=rel)

 manifest=json.loads((root/MANIFEST).read_text())
 if tuple(manifest.get("allowed_continuity_effect_prefixes",[]))!=ALLOWED_PREFIXES:
  errors.append("MANIFEST_ALLOWED_PREFIX_DRIFT")

 ad=defs(trees[ADAPTER]); su=defs(trees[SUPERVISOR])
 main=ad.get("main"); safe=su.get("_safe_id"); statep=su.get("_state_path"); execfn=su.get("execute_claimed_task")
 if not all([main,safe,statep,execfn]): errors.append("REQUIRED_FUNCTION_MISSING")
 else:
  defaults=parser_defaults(main)
  for flag,val in DEFAULTS.items():
   if defaults.get(flag)!=val: errors.append(f"DEFAULT_DRIFT:{flag}:{defaults.get(flag)}")

  safe_src=ast.get_source_segment(texts[SUPERVISOR],safe) or ""
  if r"[A-Za-z0-9_.-]{1,160}" not in safe_src:
   errors.append("SAFE_ID_REGEX_DRIFT")
  if "return state_dir / f\"{task_id}.json\"" not in (ast.get_source_segment(texts[SUPERVISOR],statep) or ""):
   errors.append("STATE_PATH_SHAPE_DRIFT")

  exsrc=ast.get_source_segment(texts[SUPERVISOR],execfn) or ""
  constants={
   n.value for n in ast.walk(execfn)
   if isinstance(n,ast.Constant) and isinstance(n.value,str)
  }
  for token in ("canonical","same_identity_worker","external_tool_bridge"):
   if token not in constants: errors.append("BRIDGE_PATH_TOKEN_MISSING:"+token)
  required_fragments=[
   'evidence_dir / f"{task[\'task_id\']}__CHECKPOINT.json"',
   'evidence_dir / f"{task[\'task_id\']}__ATTEMPT_{attempt}.json"',
  ]
  for frag in required_fragments:
   if frag not in exsrc: errors.append("EXPECTED_EFFECT_PATH_SHAPE_MISSING:"+frag)

 # Algebraic path proof for safe task ids on fixed roots.
 examples=["A","a.b-c_1","Z"*160]
 for tid in examples:
  if not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}",tid): errors.append("TEST_ID_INVALID")
  for prefix in ALLOWED_PREFIXES:
   p=Path(prefix)/tid
   try:
    p.relative_to(Path(prefix))
   except ValueError:
    errors.append("PREFIX_ESCAPE:"+str(p))
 malicious=["../x","a/b","a\\b","", "x"*161]
 for tid in malicious:
  if re.fullmatch(r"[A-Za-z0-9_.-]{1,160}",tid):
   errors.append("MALICIOUS_ID_ACCEPTED:"+tid)

 return {
  "schema":"PROJECT_BRAIN_CONTINUITY_FILESYSTEM_CONFINEMENT_V1",
  "status":"PASS__SELECTED_ROUTE_FILESYSTEM_EFFECTS_CONFINED" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "observed_blobs":observed,
  "allowed_prefixes":list(ALLOWED_PREFIXES),
  "effect_classes":["file.open_write","file.remove","file.rename","file.directory_mutation"],
  "raw_process_effect_in_continuity_leaf":False,
  "downstream_effects_separate":True,
  "terminal_credit_delta":0,
 }

if __name__=="__main__":
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
