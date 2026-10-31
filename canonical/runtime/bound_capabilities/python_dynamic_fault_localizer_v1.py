from __future__ import annotations
import ast,hashlib,json,math,os,pathlib,subprocess,sys,textwrap
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


SCHEMA="PROJECT_BRAIN_PYTHON_DYNAMIC_FAULT_LOCALIZER_V1"
class FaultLocalizerError(RuntimeError): pass
def _rel(repo,p): return str(p.relative_to(repo)).replace("\\","/")
def _safe_file(repo,raw):
 p=(repo/str(raw or "")).resolve()
 if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py": raise FaultLocalizerError("FILE_INVALID")
 return p
def _safe_dir(repo,raw):
 p=(repo/str(raw or ".")).resolve()
 if p!=repo and repo not in p.parents: raise FaultLocalizerError("PATH_OUTSIDE_REPOSITORY")
 if not p.is_dir() or p.is_symlink(): raise FaultLocalizerError("DIRECTORY_INVALID")
 return p
def _trace_one(repo,test,timeout,max_events,env=None):
 code=_PATCH.SUITE_RUNNER+r'''import json,pathlib,runpy,sys,traceback
repo=pathlib.Path(sys.argv[1]).resolve(); target=pathlib.Path(sys.argv[2]).resolve(); cap=int(sys.argv[3]); seen={}; events=0; path_cache={}
def tr(frame,event,arg):
 global events
 if events>=cap:return None
 p=_brain_project_file(frame,repo,path_cache)
 if p is None:return None
 if event=="line":
  rel=str(p.relative_to(repo)).replace("\\","/"); key=(rel,frame.f_lineno,frame.f_code.co_name)
  seen[key]=seen.get(key,0)+1;events+=1
  if not order or order[-1]!=key:order.append(key)
 return tr
ok=True;tb=[];order=[]
sys.settrace(tr)
try:
 _brain_run_suite(target)
except SystemExit as e:
 ok=(e.code in (None,0,False))
 if not ok:tb=traceback.extract_tb(e.__traceback__)
except BaseException as e:
 ok=False;tb=traceback.extract_tb(e.__traceback__)
finally:sys.settrace(None)
print("__BRAIN_TRACE__"+json.dumps({"order":[[a,b,c] for (a,b,c) in order],"pass":ok,"events":[[a,b,c,n] for (a,b,c),n in sorted(seen.items())],"traceback":[[str(pathlib.Path(x.filename).resolve().relative_to(repo)).replace("\\","/"),x.lineno,x.name] for x in tb if pathlib.Path(x.filename).resolve().is_file() and repo in pathlib.Path(x.filename).resolve().parents],"event_count":events},sort_keys=True))
'''
 try:r=subprocess.run([sys.executable,"-c",code,str(repo),str(test),str(max_events)],cwd=repo,text=True,capture_output=True,timeout=timeout,env=env)
 except subprocess.TimeoutExpired:raise FaultLocalizerError("TEST_TIMEOUT")
 marker="__BRAIN_TRACE__"; lines=[x for x in r.stdout.splitlines() if x.startswith(marker)]
 if not lines: raise FaultLocalizerError("TRACE_OUTPUT_MISSING")
 out=json.loads(lines[-1][len(marker):]);out["returncode"]=r.returncode;return out
def _defs_and_lines(path):
  # A file under source_root may be third-party and use syntax this interpreter cannot parse
  # (PEP 695 type aliases need 3.12). Such a file cannot be a repair candidate or a
  # localization target, so it contributes nothing - it must not abort the whole search,
  # which is the defect python_test_audit documents for timeouts one layer down.
 try:tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
 except (SyntaxError,ValueError,UnicodeDecodeError):return []
 out=[]
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
   a=getattr(n,"lineno",0);b=getattr(n,"end_lineno",a)
   names=set();defs={}
   for x in ast.walk(n):
    if isinstance(x,ast.Name):
     names.add(x.id)
     if isinstance(x.ctx,(ast.Store,ast.Param)):defs.setdefault(x.id,[]).append(getattr(x,"lineno",0))
    elif isinstance(x,ast.arg):names.add(x.arg);defs.setdefault(x.arg,[]).append(getattr(x,"lineno",a))
   out.append({"name":n.name,"kind":type(n).__name__,"lineno":a,"end_lineno":b,"names":sorted(names),"defs":defs})
 return out
def _line_names(path):
 try:tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
 except (SyntaxError,ValueError,UnicodeDecodeError):return {}
 m={}
 for n in ast.walk(tree):
  line=getattr(n,"lineno",None)
  if line is None:continue
  rec=m.setdefault(line,{"loads":set(),"stores":set()})
  if isinstance(n,ast.Name):
   (rec["stores"] if isinstance(n.ctx,(ast.Store,ast.Param)) else rec["loads"]).add(n.id)
  elif isinstance(n,ast.arg):rec["stores"].add(n.arg)
 return {k:{"loads":sorted(v["loads"]),"stores":sorted(v["stores"])} for k,v in m.items()}
def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 if not isinstance(args,Mapping):raise FaultLocalizerError("ARGS_NOT_OBJECT")
 repo=pathlib.Path(root).resolve();src=_safe_dir(repo,args.get("source_root","."))
 tests=[_safe_file(repo,x) for x in (args.get("test_paths") or []) if str(x).strip()]
 if not tests:
  # Which files are tests is a fact about the tree, not something the sentence
  # has to enumerate. Discovery must run BEFORE _source_env, which takes the
  # tests as arguments.
  from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_files
  try:tests=discover_test_files(src)
  except FileNotFoundError:raise FaultLocalizerError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
 env=_source_env(src,*tests)
 # THE PROJECT ROOT THE TESTS IMPORT THROUGH, WHEN THE TREE SAYS SO.
 #
 # Measured 2026-10-31: a fixture whose package is <project>/app and whose suite is
 # <project>/tests imports `app.service`, but the source directory alone was on PYTHONPATH, so the
 # test died on its own import line.  The trace showed two events, both in the test file, no
 # application line at all -- and the localizer then reported PASS with an empty ranking, a false
 # positive whose guidance is worth nothing.  The evidence is the tree: a source root that is a
 # PACKAGE (it has __init__.py) whose parent holds the tests.  Appended LAST so it can never
 # shadow a directory that was already resolved (the one measured shadowing risk in _source_env).
 # The project root the suite imports through is derived by the SHARED rule in the patch
 # module (`_source_env`), from the imports the test files actually write -- one implementation,
 # so the localizer and the repair engine can never disagree about where the code lives.
 if not tests:raise FaultLocalizerError("TEST_PATHS_REQUIRED")
 timeout=max(1,min(int(args.get("timeout_s",20)),120));max_events=max(100,min(int(args.get("max_trace_events",200000)),1000000));max_lines=max(1,min(int(args.get("max_ranked_lines",100)),1000));max_symbols=max(1,min(int(args.get("max_ranked_symbols",50)),500))
 traces=[]
 for t in tests:traces.append({"test_path":_rel(repo,t),**_trace_one(repo,t,timeout,max_events,env)})
 F=sum(not x["pass"] for x in traces);P=sum(x["pass"] for x in traces)
 if F==0:raise FaultLocalizerError("NO_FAILING_TEST")
 line_counts={}
 tbset=set();last_lines=set()
 _app_paths={_rel(repo,x) for x in list(src.rglob("*")) if x.is_file() and x.suffix==".py" and not x.name.startswith("test_")}
 for tr in traces:
  covered=set((a,b,c) for a,b,c,_ in tr["events"])
  for rel,line,func in covered:
   rec=line_counts.setdefault((rel,line,func),{"fail":0,"pass":0})
   rec["pass" if tr["pass"] else "fail"]+=1
  if not tr["pass"]:
   tbset.update(tuple(x) for x in tr.get("traceback",[]))
   _order=[tuple(x) for x in tr.get("order",[])]
   # WITHIN THE FAILING TEST, NOT AT THE END OF THE PROCESS.  unittest keeps going after a
   # failure, so the process's last application line belongs to whichever test ran last.  The
   # trace already separates the tests: every test-file frame whose function is a test method
   # opens a window, and the traceback names the one that failed.  Take the last application
   # line inside THAT window; fall back to the process-wide last line only when the trace cannot
   # attribute one (a module-level failure, an import error).
   _tp=str(tr.get("test_path") or "")
   _failing=[str(x[2]) for x in tr.get("traceback",[]) if len(x)>2 and str(x[2]).startswith("test")]
   _win=None;_last_in={}
   for _k in _order:
    if _k[0]==_tp and str(_k[2]).startswith("test"):
     _win=str(_k[2]);_last_in.setdefault(_win,None)
    if _k[0] in _app_paths:
     if _win is None:_last_in.setdefault(None,None)
     _last_in[_win if _win is not None else None]=_k
   _picked=_last_in.get(_failing[-1]) if _failing else None
   if _picked is None:
    _picked=next((v for v in reversed(_last_in.values()) if v),None)
   if _picked:last_lines.add(_picked)
 # THE FRAME BEATS THE HEURISTIC.  `last_lines` is the last application line executed in the
 # PROCESS, and a test file with more than one test keeps running after the failing one:
 # measured 2026-10-31 (`fix_broken`, suite = test_add [fails] then test_mul [passes] in one
 # file), the last executed application line was inside `mul`, so the +2.0 bonus ranked `mul`
 # ABOVE the line the traceback names in `add` -- and the guided repair then searched the
 # wrong function.  When a traceback frame names an application line, that line is evidence;
 # the last-line heuristic is only a fallback for runs that produce no such frame.
 _tb_app={k for k in tbset if k[0] in _app_paths}
 _use_last=not _tb_app
 ranked=[]
 for (rel,line,func),c in line_counts.items():
  p=(repo/rel).resolve()
  if p==repo or repo not in p.parents or not p.is_file() or p.suffix!=".py" or p.name.startswith("test_"):continue
  f=c["fail"];q=c["pass"];score=(f/math.sqrt(F*(f+q))) if f else 0.0
  reasons=[]
  if f and not q:reasons.append("FAIL_ONLY_EXECUTION")
  if q:reasons.append("PASSING_TEST_OVERLAP")
  if (rel,line,func) in tbset:score+=1.0;reasons.append("FAILING_TRACEBACK_FRAME")
  if _use_last and (rel,line,func) in last_lines:score+=2.0;reasons.append("LAST_EXECUTED_LINE_IN_FAILING_RUN")
  ranked.append({"path":rel,"line":line,"function":func,"fail_coverage":f,"pass_coverage":q,"ochiai":round(score-(1.0 if "FAILING_TRACEBACK_FRAME" in reasons else 0.0),12),"score":round(score,12),"reasons":reasons})
 ranked.sort(key=lambda x:(-x["score"],-x["fail_coverage"],x["pass_coverage"],x["path"],x["line"],x["function"]))
 # AN EMPTY LOCALIZATION IS NOT A PASS.  The same measured run above reported
 # PASS__BOUNDED_DYNAMIC_FAULT_LOCALIZATION with ranked_lines == [] and
 # ranked_symbols == []: a consumer cannot tell that from a localization that found the
 # fault, and the repair engine downstream turned it into GUIDANCE_EMPTY.  A run that
 # executed no application line has localized nothing, and must say so.
 if not ranked:
  raise FaultLocalizerError("NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN")
 ranked=ranked[:max_lines]
 files=sorted({x["path"] for x in ranked})
 symbols=[]
 for rel in files:
  p=repo/rel; lineinfo=_line_names(p)
  for d in _defs_and_lines(p):
   rows=[x for x in ranked if x["path"]==rel and d["lineno"]<=x["line"]<=d["end_lineno"]]
   if not rows:continue
   maxscore=max(x["score"] for x in rows);covered=sorted({x["line"] for x in rows});loads=set();stores=set()
   for ln in covered:
    rec=lineinfo.get(ln,{});loads.update(rec.get("loads",[]));stores.update(rec.get("stores",[]))
   backward=[]
   for name in sorted(loads):
    for dl in d["defs"].get(name,[]):
     if dl<=max(covered):backward.append({"name":name,"definition_line":dl,"used_in_suspicious_region":True})
   symbols.append({"path":rel,"symbol":d["name"],"kind":d["kind"],"lineno":d["lineno"],"end_lineno":d["end_lineno"],"score":maxscore,"covered_suspicious_lines":covered,"loaded_names":sorted(loads),"stored_names":sorted(stores),"backward_def_use":backward,"reasons":["DYNAMIC_FAILING_EXECUTION"]+(["FAIL_ONLY_REGION"] if any("FAIL_ONLY_EXECUTION" in x["reasons"] for x in rows) else [])})
 symbols.sort(key=lambda x:(-x["score"],x["path"],x["lineno"],x["symbol"]));symbols=symbols[:max_symbols]
 result={"schema":SCHEMA,"status":"PASS__BOUNDED_DYNAMIC_FAULT_LOCALIZATION","pass":True,"failing_test_count":F,"passing_test_count":P,"test_traces":traces,"ranked_lines":ranked,"ranked_symbols":symbols,"localization_basis":"FAILING_VS_PASSING_DYNAMIC_LINE_SPECTRUM_PLUS_TRACEBACK_PLUS_AST_SYMBOL_OWNERSHIP_PLUS_BACKWARD_DEF_USE","model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_GENERAL_SEMANTIC_CAUSALITY_PROOF","NO_INTERPROCEDURAL_VALUE_PROVENANCE_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_PATCH_CORRECTNESS_OR_MERGEABILITY_CLAIM","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 out=(repo/str(args.get("output_path") or "")).resolve()
 if out==repo or repo not in out.parents:raise FaultLocalizerError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");result["output_path"]=_rel(repo,out);result["output_sha256"]=hashlib.sha256(out.read_bytes()).hexdigest();result["output_verified"]=True;return result
