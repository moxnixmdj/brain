#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,json,os,pathlib,re
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_SOFTWARE_REQUEST_ACCEPTANCE_COMPILE_V1"
class RequestCompileError(RuntimeError):pass
RET=re.compile(r"`(?P<call>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?\s*\([^\x60]*\))`\s+(?:must|should)\s+return\s+`(?P<expected>[^\x60]+)`",re.I)
RAISE=re.compile(r"`(?P<call>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?\s*\([^\x60]*\))`\s+(?:must|should)\s+raise\s+`(?P<exc>[A-Za-z_]\w*)`",re.I)
FNEG=re.compile(r"`(?P<path>[^\x60]+)`\s+(?:must|should)\s+not\s+exist\b",re.I)
FPOS=re.compile(r"`(?P<path>[^\x60]+)`\s+(?:must|should)\s+exist\b",re.I)
NORM=re.compile(r"\b(must|should|required|returns?|raises?|exists?|creates?|deletes?|never|always)\b",re.I)
def _sha(x):return hashlib.sha256(x.encode()).hexdigest()
def _rel(r,p):return str(p.relative_to(r)).replace("\\","/")
def _root(repo,raw):
 p=(repo/str(raw or ".")).resolve()
 if p!=repo and repo not in p.parents:raise RequestCompileError("PATH_OUTSIDE_REPOSITORY")
 if not p.is_dir() or p.is_symlink():raise RequestCompileError("SOURCE_ROOT_INVALID")
 return p
def _jsonable(v):
 if v is None or isinstance(v,(bool,int,float,str)):return v
 if isinstance(v,list):return [_jsonable(x) for x in v]
 if isinstance(v,dict) and all(isinstance(k,str) for k in v):return {k:_jsonable(x) for k,x in v.items()}
 raise RequestCompileError("NON_JSON_LITERAL")
def _lit(x):return _jsonable(ast.literal_eval(x.strip()))
def _call(x):
 n=ast.parse(x.strip(),mode="eval").body
 if not isinstance(n,ast.Call):raise RequestCompileError("CALL_REQUIRED")
 if isinstance(n.func,ast.Name):hint=None;fn=n.func.id
 elif isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name):hint=n.func.value.id;fn=n.func.attr
 else:raise RequestCompileError("CALL_TARGET_UNSUPPORTED")
 args=[_jsonable(ast.literal_eval(a)) for a in n.args];kw={}
 for k in n.keywords:
  if k.arg is None:raise RequestCompileError("KW_SPLAT_UNSUPPORTED")
  kw[k.arg]=_jsonable(ast.literal_eval(k.value))
 return hint,fn,args,kw
def _defs(root):
 out=[]
 for p in sorted(root.rglob("*.py")):
  if not p.is_file() or p.is_symlink() or p.name.startswith("test_"):continue
  try:t=ast.parse(p.read_text(encoding="utf-8"))
  except Exception:continue
  for n in t.body:
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):out.append((p,p.stem,n.name,n.lineno))
 return out
def _norm_count(x):
 mod=len(re.findall(r"\b(?:must|should|required)\b",x,re.I))
 act=len(re.findall(r"\b(?:returns?|raises?|exists?|creates?|deletes?)\b",x,re.I))
 return max(1,mod,act) if NORM.search(x) else 0
def compile_request(request_text:str,root,source_root="."):
 if not request_text.strip():raise RequestCompileError("REQUEST_REQUIRED")
 repo=pathlib.Path(root).resolve();src=_root(repo,source_root);defs=_defs(src)
 req=[];holes=[];cursor=0
 lines=request_text.splitlines(keepends=True) or [request_text]
 for li,line in enumerate(lines):
  start=cursor;cursor+=len(line);matches=[]
  for kind,pat in [("PYTHON_CALL_RETURNS",RET),("PYTHON_CALL_RAISES",RAISE),("FILE_MUST_NOT_EXIST",FNEG),("FILE_MUST_EXIST",FPOS)]:
   for m in pat.finditer(line):matches.append((m.start(),m.end(),kind,m))
  matches.sort(key=lambda z:(z[0],-(z[1]-z[0])));accepted=[];spans=[]
  for row in matches:
   if any(not(row[1]<=a or row[0]>=b) for a,b in spans):continue
   accepted.append(row);spans.append((row[0],row[1]))
  for i,(_,_,kind,m) in enumerate(accepted):
   rid="REQ-"+_sha(f"{li}:{kind}:{i}:{m.group(0)}")[:20];pred={"type":kind};bound=True;reason=None
   if kind.startswith("PYTHON_"):
    try:hint,fn,args,kw=_call(m.group("call"));rows=[d for d in defs if d[2]==fn and (hint is None or d[1]==hint)]
    except Exception as e:rows=[];reason=type(e).__name__+":"+str(e)
    if len(rows)!=1:bound=False;reason=reason or "CALL_TARGET_BINDING_CARDINALITY:"+str(len(rows))
    else:pred.update({"source_path":_rel(repo,rows[0][0]),"function":fn,"args":args,"kwargs":kw})
    if kind=="PYTHON_CALL_RETURNS":
     try:pred["expected"]=_lit(m.group("expected"))
     except Exception as e:bound=False;reason=type(e).__name__+":"+str(e)
    else:pred["exception_type"]=m.group("exc")
   else:
    p=(repo/m.group("path")).resolve()
    if p==repo or repo not in p.parents:bound=False;reason="TARGET_PATH_OUTSIDE_REPOSITORY"
    else:pred["path"]=_rel(repo,p)
   req.append({"id":rid,"critical":True,"source_range":[start+m.start(),start+m.end()],"source_text":m.group(0),"predicate":pred,"verifier_binding_status":"BOUND" if bound else "UNBOUND","unbound_reason":reason})
  lower=_norm_count(line)
  if lower and len(accepted)<lower:holes.append({"line":li+1,"reason":"NORMATIVE_OBLIGATION_UNDERSEGMENTED","recognized":len(accepted),"lower_bound":lower,"text":line.rstrip()})
  if any(x["verifier_binding_status"]!="BOUND" and start<=x["source_range"][0]<cursor for x in req):holes.append({"line":li+1,"reason":"OPERATIVE_REQUIREMENT_UNBOUND","text":line.rstrip()})
 ready=bool(req) and not holes and all(x["verifier_binding_status"]=="BOUND" for x in req)
 return {"schema":SCHEMA,"status":"COMPILED_ADMISSION_READY" if ready else "OPEN_SPECIFICATION_OR_BINDING_HOLE","request_sha256":_sha(request_text),"source_root":_rel(repo,src) if src!=repo else ".","requirements":req,"requirement_count":len(req),"bound_requirement_count":sum(x["verifier_binding_status"]=="BOUND" for x in req),"specification_holes":holes,"admission_ready":ready,"existing_test_evidence_authority":False,"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS","NO_UNSUPPORTED_CLAUSE_INFERENCE","NO_EXISTING_TEST_SUITE_COMPLETENESS_INFERENCE","NO_PATCH_CORRECTNESS_FROM_COMPILATION_ALONE","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
def run(args:Mapping[str,Any],root):
 out=compile_request(str(args.get("request_text") or ""),root,str(args.get("source_root") or "."))
 repo=pathlib.Path(root).resolve();p=(repo/str(args.get("output_path") or "")).resolve()
 if p==repo or repo not in p.parents:raise RequestCompileError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");out["output_path"]=_rel(repo,p);out["output_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest();out["output_verified"]=True;return out
