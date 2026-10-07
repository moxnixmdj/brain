from __future__ import annotations
import ast, hashlib, json
from pathlib import Path
from canonical.runtime import exact_symbolic_selected_leaf_verifier_v1 as exact_symbolic

ROOT=Path(__file__).resolve().parents[2]
PURE_ROUTES={
 "accepted.delegation":{
   "path":"canonical/runtime/delegation_whole_scope_candidate_v2.py",
   "sha":"f1a93ee66d90093de61dc17c6ebf2e24073df522",
   "allowed_import_roots":{"__future__","collections","heapq","itertools","math","typing"},
 },
 "accepted.recovery":{
   "path":"canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
   "sha":"28940387bd6c11671035ad9201e37bba13fd9bc9",
   "allowed_import_roots":{"__future__","typing"},
 },
 "accepted.tool_discovery":{
   "path":"canonical/runtime/tool_discovery_information_safe_candidate.py",
   "sha":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
   "allowed_import_roots":{"__future__","typing"},
 },
}
FORBIDDEN_CALL_ROOTS={
 "open","print","exec","eval","compile","input","breakpoint",
 "os","subprocess","socket","requests","urllib","http","shutil","tempfile",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def import_roots(tree:ast.AST)->set[str]:
 out=set()
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):
   out.update(a.name.split(".")[0] for a in n.names)
  elif isinstance(n,ast.ImportFrom):
   out.add((n.module or "").split(".")[0])
 return out
def call_root(n:ast.Call)->str|None:
 cur=n.func
 while isinstance(cur,ast.Attribute):
  cur=cur.value
 return cur.id if isinstance(cur,ast.Name) else None
def module_level_calls(tree:ast.Module)->list[str]:
 out=[]
 for stmt in tree.body:
  if isinstance(stmt,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Import,ast.ImportFrom)):
   continue
  for n in ast.walk(stmt):
   if isinstance(n,ast.Call):
    out.append(call_root(n) or "<dynamic>")
 return out
def audit(root:Path=ROOT)->dict:
 errors=[]; routes={}
 for rid,spec in PURE_ROUTES.items():
  data=(root/spec["path"]).read_bytes(); sha=blob(data)
  local=[]
  if sha!=spec["sha"]: local.append("BLOB_DRIFT:"+sha)
  tree=ast.parse(data.decode("utf-8"),filename=spec["path"])
  imports=import_roots(tree)
  bad_imports=sorted(imports-set(spec["allowed_import_roots"]))
  if bad_imports: local.append("UNAPPROVED_IMPORT:"+",".join(bad_imports))
  top=module_level_calls(tree)
  if top: local.append("MODULE_LEVEL_CALL:"+",".join(top))
  bad_calls=sorted({call_root(n) for n in ast.walk(tree) if isinstance(n,ast.Call) and call_root(n) in FORBIDDEN_CALL_ROOTS})
  if bad_calls: local.append("MATERIAL_EFFECT_CALL_ROOT:"+",".join(bad_calls))
  routes[rid]={"path":spec["path"],"git_blob_sha":sha,"imports":sorted(imports),"material_effect_ids":[],"pass":not local,"errors":local}
  errors.extend(rid+":"+x for x in local)
 exact=exact_symbolic.evaluate(root)
 routes["accepted.exact_symbolic"]={
  "path":"canonical/obsolescence/run_exact_symbolic_v1.py",
  "git_blob_sha":exact.get("runner_blob"),
  "selected_entry":exact.get("selected_entry"),
  "material_effect_ids":[],
  "pass":bool(exact.get("pass")),
  "errors":list(exact.get("errors") or []),
 }
 errors.extend("accepted.exact_symbolic:"+x for x in routes["accepted.exact_symbolic"]["errors"])
 return {
  "schema":"PROJECT_BRAIN_D_CREDITED_PURE_ROUTE_EFFECT_AUDIT_V1",
  "status":"PASS__FOUR_SELECTED_CREDITED_ROUTES_EFFECT_FREE" if not errors else "FAIL_CLOSED",
  "pass":not errors,"errors":errors,"routes":routes,
  "material_effect_ids":[] if not errors else None,
  "proof_obligation_id":"D_CREDITED_ROUTE_EFFECT_TOTALITY",
  "terminal_credit_delta":0,
 }
if __name__=="__main__":
 out=audit();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
