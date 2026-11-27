from __future__ import annotations
import ast, hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
OWNERSHIP="canonical/verification/ACCEPTED_THREE_OWNERSHIP_PROMOTION_PROOF_20261003_V1.json"
EXPECTED_OWNERSHIP="4711fb5eed330990edea369725de6eaedfd3bc70"

ROUTES={
 "DELEGATION_SELECTED_LEAF_V1":{
   "family":"SUBAGENT_DELEGATION_AND_COORDINATION",
   "path":"canonical/runtime/delegation_whole_scope_candidate_v2.py",
   "git_blob_sha":"f1a93ee66d90093de61dc17c6ebf2e24073df522",
   "entries":("solve_initial","solve_after_receipt"),
   "imports":("__future__","collections","heapq","itertools","math","typing"),
 },
 "RECOVERY_SELECTED_LEAF_V1":{
   "family":"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
   "path":"canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
   "git_blob_sha":"28940387bd6c11671035ad9201e37bba13fd9bc9",
   "entries":("solve",),
   "imports":("__future__","typing"),
 },
 "TOOL_DISCOVERY_SELECTED_LEAF_V1":{
   "family":"TOOL_DISCOVERY_SELECTION_AND_LEARNING",
   "path":"canonical/runtime/tool_discovery_information_safe_candidate.py",
   "git_blob_sha":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
   "entries":("next_action",),
   "imports":("__future__","typing"),
 },
}

FORBIDDEN_CALLS={
 "open","eval","exec","compile","__import__",
 "os.system","os.remove","os.unlink","os.rename","os.replace","os.mkdir","os.rmdir",
 "os.chmod","os.chown","os.truncate","os.utime","os.symlink","os.link",
 "subprocess.run","subprocess.Popen","subprocess.call","subprocess.check_call","subprocess.check_output",
 "socket.socket","socket.create_connection","requests.get","requests.post",
 "urllib.request.urlopen","http.client.HTTPConnection","http.client.HTTPSConnection",
 "ctypes.CDLL","ctypes.PyDLL","ctypes.cdll.LoadLibrary",
 "Path.write_text","Path.write_bytes","Path.unlink","Path.rename","Path.replace","Path.mkdir","Path.rmdir",
}
FORBIDDEN_IMPORT_PREFIXES=("os","subprocess","socket","requests","urllib","http","ctypes","pathlib","shutil","tempfile")

def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _import_roots(tree:ast.AST)->tuple[str,...]:
 out=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):
   out.extend(x.name.split(".")[0] for x in n.names)
  elif isinstance(n,ast.ImportFrom):
   out.append((n.module or "").split(".")[0])
 return tuple(sorted(set(out)))

def _defs(tree:ast.AST)->dict[str,ast.AST]:
 out={}
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
   out.setdefault(n.name,n)
 return out

def _call_name(call:ast.Call)->str|None:
 cur=call.func
 if isinstance(cur,ast.Name): return cur.id
 if isinstance(cur,ast.Attribute):
  parts=[]
  while isinstance(cur,ast.Attribute):
   parts.append(cur.attr);cur=cur.value
  if isinstance(cur,ast.Name):
   parts.append(cur.id);return ".".join(reversed(parts))
 return None

def _reachable(defs:dict[str,ast.AST],roots:tuple[str,...])->set[str]:
 missing=[x for x in roots if x not in defs]
 if missing: raise ValueError("ENTRY_MISSING:"+",".join(missing))
 seen=set();stack=list(roots)
 while stack:
  name=stack.pop()
  if name in seen: continue
  seen.add(name)
  fn=defs[name]
  for n in ast.walk(fn):
   if isinstance(n,ast.Call):
    cn=_call_name(n)
    if cn in defs and cn not in seen: stack.append(cn)
 return seen

def _effect_hits(defs:dict[str,ast.AST],reachable:set[str])->list[str]:
 hits=[]
 for name in sorted(reachable):
  for n in ast.walk(defs[name]):
   if not isinstance(n,ast.Call): continue
   cn=_call_name(n)
   if cn in FORBIDDEN_CALLS:
    hits.append(name+"::"+str(cn))
   if cn and (
      cn.startswith("os.") or cn.startswith("subprocess.") or cn.startswith("socket.")
      or cn.startswith("requests.") or cn.startswith("urllib.") or cn.startswith("ctypes.")
      or cn.startswith("shutil.")
   ):
    hits.append(name+"::"+cn)
 return sorted(set(hits))

def evaluate(root:Path=ROOT)->dict[str,Any]:
 errors=[];rows=[]
 own_path=root/OWNERSHIP
 if blob(own_path.read_bytes())!=EXPECTED_OWNERSHIP:
  errors.append("OWNERSHIP_RECEIPT_DRIFT")
 own=json.loads(own_path.read_text(encoding="utf-8"))
 promoted={
   x["family"]:x for x in own.get("families",[])
   if isinstance(x,dict) and x.get("promotion")=="VERIFIED_OWNED_EQUAL_OR_BETTER"
 }
 for rid,spec in ROUTES.items():
  p=root/spec["path"]; data=p.read_bytes();sha=blob(data)
  row={"route_id":rid,"family":spec["family"],"path":spec["path"],"git_blob_sha":sha}
  if sha!=spec["git_blob_sha"]: errors.append("BLOB_DRIFT:"+rid+":"+sha)
  tree=ast.parse(data.decode("utf-8"),filename=spec["path"])
  imports=_import_roots(tree)
  expected=tuple(sorted(set(spec["imports"])))
  if imports!=expected: errors.append("IMPORT_SET_DRIFT:"+rid+":"+repr(imports))
  if any(any(x==p or x.startswith(p+".") for p in FORBIDDEN_IMPORT_PREFIXES) for x in imports):
   errors.append("FORBIDDEN_IMPORT:"+rid)
  defs=_defs(tree)
  try: reachable=_reachable(defs,spec["entries"])
  except Exception as exc:
   errors.append(rid+":"+str(exc));reachable=set()
  hits=_effect_hits(defs,reachable)
  if hits: errors.extend("MATERIAL_EFFECT_CALL:"+rid+":"+x for x in hits)
  fam=promoted.get(spec["family"])
  if not fam: errors.append("OWNERSHIP_PROMOTION_MISSING:"+rid)
  else:
   art=fam.get("operative_artifact") or {}
   if art.get("path")!=spec["path"] or art.get("git_blob_sha")!=spec["git_blob_sha"]:
    errors.append("OWNERSHIP_ARTIFACT_BINDING_MISMATCH:"+rid)
   if fam.get("external_target_capability_provider") is not False:
    errors.append("OWNERSHIP_PROVIDER_CLOSURE_MISSING:"+rid)
  row.update({
    "selected_entries":list(spec["entries"]),
    "reachable_local_functions":sorted(reachable),
    "imports":list(imports),
    "material_external_effect_classes":[],
    "effect_call_hits":hits,
    "ownership_exact_binding":not any(e.endswith(":"+rid) or (":"+rid+":") in e for e in errors),
  })
  rows.append(row)
 ok=not errors
 return {
  "schema":"PROJECT_BRAIN_ACCEPTED_THREE_SELECTED_LEAF_EFFECT_AUDIT_V1",
  "status":"PASS__THREE_ACCEPTED_SELECTED_LEAVES_EFFECT_FREE__ZERO_CREDIT" if ok else "FAIL_CLOSED",
  "pass":ok,
  "errors":errors,
  "route_count":3,
  "routes":rows,
  "union_material_external_effect_classes":[],
  "terminal_credit_delta":0,
  "ownership_credit_delta":0,
 }

if __name__=="__main__":
 out=evaluate();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
