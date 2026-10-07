from __future__ import annotations
import ast, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUNNER="canonical/obsolescence/run_exact_symbolic_v1.py"
EXPECTED="8f6f04fee00664b26ddf1a45a65698399c7ca6c3"

def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def defs(tree):
 return {n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

def calls(fn):
 out=[]
 for n in ast.walk(fn):
  if isinstance(n,ast.Call):
   if isinstance(n.func,ast.Name): out.append(n.func.id)
   elif isinstance(n.func,ast.Attribute):
    parts=[]; cur=n.func
    while isinstance(cur,ast.Attribute):
     parts.append(cur.attr); cur=cur.value
    if isinstance(cur,ast.Name):
     parts.append(cur.id); out.append(".".join(reversed(parts)))
 return out

def evaluate(root:Path=ROOT):
 errors=[]
 data=(root/RUNNER).read_bytes(); sha=blob(data)
 if sha!=EXPECTED: errors.append("RUNNER_BLOB_DRIFT:"+sha)
 text=data.decode(); tree=ast.parse(text,filename=RUNNER); ds=defs(tree)
 rt=ds.get("run_task"); main=ds.get("main")
 if rt is None or main is None: errors.append("REQUIRED_FUNCTION_MISSING")
 else:
  main_calls=calls(main)
  if "run_task" not in main_calls: errors.append("MAIN_DOES_NOT_USE_SELECTED_LEAF")
  rtcalls=set(calls(rt))
  forbidden={
   "open","Path.write_text","Path.write_bytes","os.remove","os.unlink","os.rename","os.replace",
   "subprocess.run","subprocess.Popen","os.system","socket.socket","requests.get","requests.post"
  }
  bad=sorted(rtcalls & forbidden)
  if bad: errors.append("SELECTED_LEAF_MATERIAL_EFFECT_CALL:"+",".join(bad))
  main_src=ast.get_source_segment(text,main) or ""
  rt_src=ast.get_source_segment(text,rt) or ""
  if "write_text" not in main_src: errors.append("EXPECTED_REPORT_WRITE_NOT_FOUND_IN_MAIN")
  if "write_text" in rt_src: errors.append("REPORT_WRITE_LEAKED_INTO_SELECTED_LEAF")
  # All accepted task dispatch happens through run_task before report construction.
  if 'output,ok=run_task(task)' not in main_src.replace(" ",""):
   errors.append("ACCEPTED_LOOP_NOT_DIRECT_RUN_TASK_DISPATCH")

 return {
  "schema":"PROJECT_BRAIN_EXACT_SYMBOLIC_SELECTED_LEAF_VERIFICATION_V1",
  "status":"PASS__ACCEPTED_COMPUTE_LEAF_EXTRACTED_EFFECT_FREE" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "runner_blob":sha,
  "selected_entry":"run_task",
  "material_external_effect_classes":[],
  "report_write_outside_selected_leaf":not errors,
  "terminal_credit_delta":0
 }

if __name__=="__main__":
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
