from __future__ import annotations
import ast,hashlib,json,math,os,pathlib,subprocess,sys
from typing import Any,Mapping
import importlib.util
def _load_patch():
 p=pathlib.Path(__file__).with_name('python_test_guided_patch_search_v1.py');s=importlib.util.spec_from_file_location('_p',p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
_PATCH=_load_patch()
def _source_env(*paths):
 """Delegate to the one implementation in the shared patch-search module.

 A traced child inherits the repository root as its working directory and runpy.run_path does NOT
 put the target's own directory on sys.path the way running a script does, so a test suite that
 imports the module it tests dies on line 1 with ModuleNotFoundError. The localizer then reports
 PASS with an empty ranking - a false positive - and every consumer of its guidance downstream
 gets nothing. Adding the source directory to PYTHONPATH fixes the import without moving the
 working directory the caller chose.
 """
 return _PATCH._source_env(*paths)



SCHEMA="PROJECT_BRAIN_PYTHON_INTERPROCEDURAL_VALUE_PROVENANCE_V1"
class ProvenanceError(RuntimeError): pass

def _rel(repo,p): return str(p.relative_to(repo)).replace("\\","/")

def _safe_file(repo,raw):
 p=(repo/str(raw or "")).resolve()
 if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py":
  raise ProvenanceError("FILE_INVALID")
 return p

def _safe_dir(repo,raw):
 p=(repo/str(raw or ".")).resolve()
 if p!=repo and repo not in p.parents: raise ProvenanceError("PATH_OUTSIDE_REPOSITORY")
 if not p.is_dir() or p.is_symlink(): raise ProvenanceError("DIRECTORY_INVALID")
 return p

def _trace_one(repo,test,timeout,max_events,max_value_chars,env=None):
 code=_PATCH.SUITE_RUNNER+r'''import hashlib,json,math,pathlib,runpy,sys,traceback
repo=pathlib.Path(sys.argv[1]).resolve(); target=pathlib.Path(sys.argv[2]).resolve(); cap=int(sys.argv[3]); maxchars=int(sys.argv[4])
events=[]; seq=0
def path_of(frame):
 try:p=pathlib.Path(frame.f_code.co_filename).resolve()
 except Exception:return None
 return p if p.is_file() and repo in p.parents and p.suffix==".py" else None
def scalar(v):
 t=type(v).__name__
 if v is None or isinstance(v,(bool,int)):return {"type":t,"value":v}
 if isinstance(v,float):
  return {"type":t,"value":v if math.isfinite(v) else str(v)}
 if isinstance(v,str):
  raw=v.encode("utf-8","replace");return {"type":t,"value":v[:maxchars],"truncated":len(v)>maxchars,"sha256":hashlib.sha256(raw).hexdigest()}
 if isinstance(v,(bytes,bytearray)):
  raw=bytes(v);return {"type":t,"length":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
 try:n=len(v)
 except Exception:n=None
 return {"type":t,**({"length":n} if isinstance(n,int) and n>=0 else {})}
def tr(frame,event,arg):
 global seq
 if len(events)>=cap:return tr
 p=path_of(frame)
 if p is None:return tr
 if event=="call":
  caller=frame.f_back; cp=path_of(caller) if caller is not None else None
  argc=frame.f_code.co_argcount+frame.f_code.co_kwonlyargcount
  names=list(frame.f_code.co_varnames[:argc])
  args={name:scalar(frame.f_locals[name]) for name in names if name in frame.f_locals}
  events.append({"i":seq,"event":"call","callee":{"path":str(p.relative_to(repo)).replace("\\","/"),"function":frame.f_code.co_name,"firstlineno":frame.f_code.co_firstlineno},"caller":None if cp is None else {"path":str(cp.relative_to(repo)).replace("\\","/"),"function":caller.f_code.co_name,"line":caller.f_lineno},"args":args});seq+=1
 elif event=="return":
  events.append({"i":seq,"event":"return","callee":{"path":str(p.relative_to(repo)).replace("\\","/"),"function":frame.f_code.co_name,"firstlineno":frame.f_code.co_firstlineno},"value":scalar(arg)});seq+=1
 elif event=="exception":
  typ=arg[0].__name__ if isinstance(arg,tuple) and arg and hasattr(arg[0],"__name__") else "Exception"
  events.append({"i":seq,"event":"exception","callee":{"path":str(p.relative_to(repo)).replace("\\","/"),"function":frame.f_code.co_name,"firstlineno":frame.f_code.co_firstlineno},"exception_type":typ});seq+=1
 return tr
ok=True;tb=[]
sys.settrace(tr)
try:_brain_run_suite(target)
except SystemExit as e:
 ok=(e.code in (None,0,False))
 if not ok:tb=traceback.extract_tb(e.__traceback__)
except BaseException as e:
 ok=False;tb=traceback.extract_tb(e.__traceback__)
finally:sys.settrace(None)
frames=[]
for x in tb:
 try:p=pathlib.Path(x.filename).resolve()
 except Exception:continue
 if p.is_file() and repo in p.parents:frames.append([str(p.relative_to(repo)).replace("\\","/"),x.lineno,x.name])
print("__BRAIN_PROVENANCE__"+json.dumps({"pass":ok,"events":events,"traceback":frames,"event_count":len(events)},sort_keys=True))
'''
 try:
  r=subprocess.run([sys.executable,"-c",code,str(repo),str(test),str(max_events),str(max_value_chars)],cwd=repo,text=True,capture_output=True,timeout=timeout,env=env)
 except subprocess.TimeoutExpired:
  raise ProvenanceError("TEST_TIMEOUT")
 marker="__BRAIN_PROVENANCE__"; lines=[x for x in r.stdout.splitlines() if x.startswith(marker)]
 if not lines: raise ProvenanceError("TRACE_OUTPUT_MISSING")
 out=json.loads(lines[-1][len(marker):]);out["returncode"]=r.returncode;return out

def _static_calls(path):
 tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path));out=[]
 def names(expr):
  return sorted({n.id for n in ast.walk(expr) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)})
 def callee_name(call):
  f=call.func
  if isinstance(f,ast.Name):return f.id
  if isinstance(f,ast.Attribute):return f.attr
  return None
 for fn in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
  for stmt in ast.walk(fn):
   call=None;assigned=[]
   if isinstance(stmt,(ast.Assign,ast.AnnAssign)):
    val=stmt.value
    if isinstance(val,ast.Call):call=val
    targets=stmt.targets if isinstance(stmt,ast.Assign) else [stmt.target]
    for t in targets:
     assigned.extend(n.id for n in ast.walk(t) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store))
   elif isinstance(stmt,ast.Return) and isinstance(stmt.value,ast.Call):
    call=stmt.value;assigned=["<return>"]
   if call is None:continue
   cname=callee_name(call)
   if not cname:continue
   out.append({"caller_symbol":fn.name,"line":getattr(call,"lineno",0),"callee_surface":cname,"assigned_to":sorted(set(assigned)),"argument_loads":sorted(set(x for a in call.args for x in names(a)))})
 return out

def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"))

def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 if not isinstance(args,Mapping):raise ProvenanceError("ARGS_NOT_OBJECT")
 repo=pathlib.Path(root).resolve();src=_safe_dir(repo,args.get("source_root","."))
 tests=[_safe_file(repo,x) for x in (args.get("test_paths") or [])]
 env=_source_env(src,*tests)
 if not tests:raise ProvenanceError("TEST_PATHS_REQUIRED")
 timeout=max(1,min(int(args.get("timeout_s",20)),120))
 max_events=max(100,min(int(args.get("max_trace_events",100000)),500000))
 max_value_chars=max(16,min(int(args.get("max_value_chars",120)),1024))
 traces=[{"test_path":_rel(repo,t),**_trace_one(repo,t,timeout,max_events,max_value_chars,env)} for t in tests]
 F=sum(not x["pass"] for x in traces);P=sum(x["pass"] for x in traces)
 if F==0:raise ProvenanceError("NO_FAILING_TEST")
 edges={}
 traceback_symbols=set()
 for tr in traces:
  failing=not tr["pass"]
  for p,l,f in tr.get("traceback",[]):traceback_symbols.add((p,f))
  pending=[]
  for ev in tr["events"]:
   if ev["event"]=="call":
    pending.append(ev)
    caller=ev.get("caller"); callee=ev["callee"]
    if caller is None:continue
    key=(caller["path"],caller["function"],caller["line"],callee["path"],callee["function"],callee["firstlineno"])
    rec=edges.setdefault(key,{"fail":0,"pass":0,"fail_args":set(),"pass_args":set(),"fail_returns":set(),"pass_returns":set()})
    rec["fail" if failing else "pass"]+=1
    rec["fail_args" if failing else "pass_args"].add(_canon(ev.get("args",{})))
   elif ev["event"]=="return":
    callee=ev["callee"]
    for call in reversed(pending):
     if call["callee"]["path"]==callee["path"] and call["callee"]["function"]==callee["function"] and call["callee"]["firstlineno"]==callee["firstlineno"]:
      caller=call.get("caller")
      if caller is not None:
       key=(caller["path"],caller["function"],caller["line"],callee["path"],callee["function"],callee["firstlineno"])
       rec=edges.get(key)
       if rec is not None:rec["fail_returns" if failing else "pass_returns"].add(_canon(ev.get("value")))
      pending.remove(call);break
 rows=[]
 for key,r in edges.items():
  cp,cf,cl,dp,df,dl=key
  f=r["fail"];q=r["pass"];och=(f/math.sqrt(F*(f+q))) if f else 0.0
  reasons=[]
  if f and not q:reasons.append("FAIL_ONLY_CALL_EDGE")
  if q:reasons.append("PASSING_TEST_OVERLAP")
  args_diff=bool(r["fail_args"] and r["pass_args"] and r["fail_args"]!=r["pass_args"])
  ret_diff=bool(r["fail_returns"] and r["pass_returns"] and r["fail_returns"]!=r["pass_returns"])
  if args_diff:reasons.append("ARGUMENT_OBSERVATION_DIFFERS")
  if ret_diff:reasons.append("RETURN_OBSERVATION_DIFFERS")
  bonus=(0.5 if (dp,df) in traceback_symbols else 0.0)
  if bonus:reasons.append("CALLEE_ON_FAILING_TRACEBACK")
  rows.append({"caller":{"path":cp,"function":cf,"line":cl},"callee":{"path":dp,"function":df,"firstlineno":dl},"fail_coverage":f,"pass_coverage":q,"ochiai":round(och,12),"score":round(och+bonus,12),"argument_observation_differs":args_diff,"return_observation_differs":ret_diff,"fail_argument_fingerprints":sorted(r["fail_args"]),"pass_argument_fingerprints":sorted(r["pass_args"]),"fail_return_fingerprints":sorted(r["fail_returns"]),"pass_return_fingerprints":sorted(r["pass_returns"]),"reasons":reasons})
 rows.sort(key=lambda x:(-x["score"],-x["fail_coverage"],x["pass_coverage"],x["caller"]["path"],x["caller"]["line"],x["callee"]["path"],x["callee"]["function"]))
 static={}
 for p in sorted(src.rglob("*.py")):
  if p.is_file() and not p.is_symlink() and not p.name.startswith("test_"):
   static[_rel(repo,p)]=_static_calls(p)
 hypotheses=[]
 for row in rows:
  cp=row["caller"]["path"];line=row["caller"]["line"];df=row["callee"]["function"]
  matches=[x for x in static.get(cp,[]) if x["line"]==line and x["callee_surface"]==df]
  for m in matches:
   hypotheses.append({"caller_path":cp,"caller_symbol":m["caller_symbol"],"call_line":line,"callee_path":row["callee"]["path"],"callee_symbol":df,"assigned_to":m["assigned_to"],"argument_loads":m["argument_loads"],"dynamic_score":row["score"],"fail_coverage":row["fail_coverage"],"pass_coverage":row["pass_coverage"],"argument_observation_differs":row["argument_observation_differs"],"return_observation_differs":row["return_observation_differs"],"basis":["DYNAMIC_CALL_EDGE","STATIC_CALLSITE_BINDING"]+([ "FAIL_ONLY_CALL_EDGE" ] if "FAIL_ONLY_CALL_EDGE" in row["reasons"] else [])})
 hypotheses.sort(key=lambda x:(-x["dynamic_score"],x["caller_path"],x["call_line"],x["callee_path"],x["callee_symbol"]))
 result={"schema":SCHEMA,"status":"PASS__BOUNDED_INTERPROCEDURAL_VALUE_PROVENANCE","pass":True,"failing_test_count":F,"passing_test_count":P,"test_traces":traces,"ranked_call_edges":rows,"interprocedural_hypotheses":hypotheses,"provenance_basis":"DYNAMIC_REPO_LOCAL_CALL_RETURN_ARGUMENT_OBSERVATIONS_PLUS_STATIC_CALLSITE_ASSIGNMENT_BINDING","model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_GENERAL_SEMANTIC_CAUSALITY_PROOF","NO_COMPLETE_INTERPROCEDURAL_DEF_USE_GRAPH","NO_OBJECT_INTERNAL_STATE_PROVENANCE","NO_NON_PYTHON_SUPPORT","NO_PATCH_CORRECTNESS_OR_MERGEABILITY_CLAIM","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 out=(repo/str(args.get("output_path") or "")).resolve()
 if out==repo or repo not in out.parents:raise ProvenanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");result["output_path"]=_rel(repo,out);result["output_sha256"]=hashlib.sha256(out.read_bytes()).hexdigest();result["output_verified"]=True;return result
