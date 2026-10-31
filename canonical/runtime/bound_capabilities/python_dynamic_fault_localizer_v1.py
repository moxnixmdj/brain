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
def _trace_file_cases(repo,test,timeout,max_events,env=None,trace_root=None):
 troot=pathlib.Path(trace_root).resolve() if trace_root else repo
 code=_PATCH.SUITE_RUNNER+r'''import importlib.util,inspect,json,pathlib,runpy,sys,traceback,unittest
repo=pathlib.Path(sys.argv[1]).resolve(); target=pathlib.Path(sys.argv[2]).resolve(); cap=int(sys.argv[3]); troot=pathlib.Path(sys.argv[4]).resolve(); path_cache={}
def _rel_if_in_scope(filename):
 if not filename or (filename.startswith("<") and filename.endswith(">")):return None
 if filename in path_cache:return path_cache[filename]
 try:
  p=pathlib.Path(filename).resolve()
  ok=p.is_file() and p.suffix==".py" and (p==troot or troot in p.parents) and (repo in p.parents)
  rel=str(p.relative_to(repo)).replace("\\","/") if ok else None
 except (OSError,ValueError):
  rel=None
 path_cache[filename]=rel
 return rel

class _FastLineRecorder:
 """PEP 669 sys.monitoring zero-overhead line recorder with sys.settrace fallback."""
 def __init__(self, seen, counter):
  self.seen=seen; self.counter=counter; self.mon_id=None
 def __enter__(self):
  mon=getattr(sys,"monitoring",None)
  if mon is not None:
   for tid in (3,4,2):
    try:
     if mon.get_tool(tid) is None:
      mon.use_tool_id(tid,"brain_fl_v1")
      self.mon_id=tid; break
    except ValueError:
     continue
  if self.mon_id is not None:
   DISABLE=mon.DISABLE
   seen=self.seen; counter=self.counter
   def _on_line(code_obj, line_no):
    if counter[0]>=cap:return DISABLE
    rel=_rel_if_in_scope(code_obj.co_filename)
    if rel is None:return DISABLE
    key=(rel,line_no,code_obj.co_name)
    seen[key]=seen.get(key,0)+1; counter[0]+=1
   mon.register_callback(self.mon_id, mon.events.LINE, _on_line)
   mon.set_events(self.mon_id, mon.events.LINE)
  else:
   seen=self.seen; counter=self.counter
   def _tr(frame,event,arg):
    if counter[0]>=cap:return None
    rel=_rel_if_in_scope(frame.f_code.co_filename)
    if rel is None:return None
    if event=="line":
     key=(rel,frame.f_lineno,frame.f_code.co_name)
     seen[key]=seen.get(key,0)+1;counter[0]+=1
    return _tr
   sys.settrace(_tr)
  return self
 def __exit__(self, exc_type, exc, tb):
  if self.mon_id is not None:
   mon=sys.monitoring
   try:
    mon.set_events(self.mon_id, 0)
    mon.register_callback(self.mon_id, mon.events.LINE, None)
    mon.free_tool_id(self.mon_id)
   except Exception:
    pass
  else:
   sys.settrace(None)
  return False

def _pack(ok, seen, counter, tb):
 return {"pass":ok,"events":[[a,b,c,n] for (a,b,c),n in sorted(seen.items())],"traceback":[[str(pathlib.Path(x.filename).resolve().relative_to(repo)).replace("\\","/"),x.lineno,x.name] for x in tb if pathlib.Path(x.filename).resolve().is_file() and repo in pathlib.Path(x.filename).resolve().parents],"event_count":counter[0]}

rows=[]
import ast as _ast
_src_txt=target.read_text(encoding="utf-8",errors="replace")
try:_ttree=_ast.parse(_src_txt,filename=str(target))
except SyntaxError:_ttree=None
_has_structured_cases=False
if _ttree is not None:
 for _n in _ttree.body:
  if isinstance(_n,_ast.ClassDef) and any(isinstance(_d,(_ast.FunctionDef,_ast.AsyncFunctionDef)) and _d.name.startswith("test") for _d in _n.body):
   _has_structured_cases=True;break
  if isinstance(_n,(_ast.FunctionDef,_ast.AsyncFunctionDef)) and _n.name.startswith("test_"):
   _has_structured_cases=True;break

loader=unittest.TestLoader()
mod_cases=[]
load_seen={};load_cnt=[0];load_tb=[];load_ok=True
if _has_structured_cases:
 with _FastLineRecorder(load_seen,load_cnt):
  try:
   spec=importlib.util.spec_from_file_location("_brain_tmod_"+target.stem,str(target))
   mod=importlib.util.module_from_spec(spec)
   sys.modules[spec.name]=mod
   spec.loader.exec_module(mod)
   suite=loader.loadTestsFromModule(mod)
   def _iter_cases(s):
    for item in s:
     if isinstance(item,unittest.TestSuite):yield from _iter_cases(item)
     else:yield item
   mod_cases=list(_iter_cases(suite))
   if not mod_cases:
    for name,obj in sorted(vars(mod).items()):
     if name.startswith("test_") and callable(obj) and not inspect.isclass(obj):
      mod_cases.append(("fn",name,obj))
  except SystemExit as e:
   load_ok=(e.code in (None,0,False))
   if not load_ok:load_tb=traceback.extract_tb(e.__traceback__)
  except BaseException as e:
   load_ok=False;load_tb=traceback.extract_tb(e.__traceback__)

if not load_ok:
 rows.append(_pack(False,load_seen,load_cnt,load_tb))
elif len(mod_cases)>=1:
 for item in mod_cases:
  seen={};cnt=[0];tb=[];ok=True
  with _FastLineRecorder(seen,cnt):
   try:
    if isinstance(item,tuple) and item[0]=="fn":
     item[2]()
    else:
     res=unittest.TestResult()
     item.run(res)
     if res.failures or res.errors:
      ok=False
      try:item.debug()
      except BaseException as de:tb=traceback.extract_tb(de.__traceback__)
   except SystemExit as e:
    ok=(e.code in (None,0,False))
    if not ok:tb=traceback.extract_tb(e.__traceback__)
   except BaseException as e:
    ok=False;tb=traceback.extract_tb(e.__traceback__)
  rows.append(_pack(ok,seen,cnt,tb))
else:
 seen={};cnt=[0];tb=[];ok=True
 with _FastLineRecorder(seen,cnt):
  try:
   _brain_run_suite(target)
  except SystemExit as e:
   ok=(e.code in (None,0,False))
   if not ok:tb=traceback.extract_tb(e.__traceback__)
  except BaseException as e:
   ok=False;tb=traceback.extract_tb(e.__traceback__)
 rows.append(_pack(ok,seen,cnt,tb))
print("__BRAIN_TRACE__"+json.dumps(rows,sort_keys=True))
'''
 try:r=subprocess.run([sys.executable,"-c",code,str(repo),str(test),str(max_events),str(troot)],cwd=repo,text=True,capture_output=True,timeout=timeout,env=env)
 except subprocess.TimeoutExpired:raise FaultLocalizerError("TEST_TIMEOUT")
 marker="__BRAIN_TRACE__"; lines=[x for x in r.stdout.splitlines() if x.startswith(marker)]
 if not lines: raise FaultLocalizerError("TRACE_OUTPUT_MISSING")
 parsed=json.loads(lines[-1][len(marker):])
 for row in parsed:row["returncode"]=0 if row["pass"] else (r.returncode or 1)
 return parsed
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
  except FileNotFoundError:
   if (src/"__init__.py").is_file() and (src.parent==repo or repo in src.parent.parents) and (src.parent/"tests").is_dir():
    try:tests=discover_test_files(src.parent/"tests")
    except FileNotFoundError:raise FaultLocalizerError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
   else:
    raise FaultLocalizerError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
 extra_roots=[src.parent] if (src/"__init__.py").is_file() and (src.parent==repo or repo in src.parent.parents) else []
 env=_source_env(src,*extra_roots,*tests)
 if not tests:raise FaultLocalizerError("TEST_PATHS_REQUIRED")
 timeout=max(1,min(int(args.get("timeout_s",20)),120));max_events=max(100,min(int(args.get("max_trace_events",200000)),1000000));max_lines=max(1,min(int(args.get("max_ranked_lines",100)),1000));max_symbols=max(1,min(int(args.get("max_ranked_symbols",50)),500))
 traces=[]
 for t in tests:
  for row in _trace_file_cases(repo,t,timeout,max_events,env,trace_root=src):
   traces.append({"test_path":_rel(repo,t),**row})
 F=sum(not x["pass"] for x in traces);P=sum(x["pass"] for x in traces)
 if F==0:raise FaultLocalizerError("NO_FAILING_TEST")
 fail_counts={}
 pass_counts={}
 func_by_loc={}
 tbset=set()
 for tr in traces:
  covered_locs=set()
  for rel,line,func,_ in tr["events"]:
   func_by_loc.setdefault((rel,line),set()).add(func)
   covered_locs.add((rel,line))
  target_counts=pass_counts if tr["pass"] else fail_counts
  for loc in covered_locs:
   target_counts[loc]=target_counts.get(loc,0)+1
  if not tr["pass"]:
   tbset.update(tuple(x) for x in tr.get("traceback",[]))

 # Precompute per-file line loads/stores and control-dependence spans for backward PDG boost
 file_pdg_cache={}
 def _pdg_info(rel_path):
  if rel_path not in file_pdg_cache:
   ap=(repo/rel_path).resolve()
   ln_names=_line_names(ap)
   defs_list=_defs_and_lines(ap)
   ctrl_spans=[]
   try:
    ptree=ast.parse(ap.read_text(encoding="utf-8"),filename=str(ap))
    for cn in ast.walk(ptree):
     if isinstance(cn,(ast.If,ast.While)) and hasattr(cn,"lineno"):
      ctrl_spans.append((cn.lineno,getattr(cn,"end_lineno",cn.lineno)))
   except (SyntaxError,ValueError,UnicodeDecodeError,OSError):
    pass
   file_pdg_cache[rel_path]=(ln_names,defs_list,ctrl_spans)
  return file_pdg_cache[rel_path]

 # Identify seed fault lines (traceback frames + fail-only lines + controlling ifs) and 2-hop backward def-use
 seed_vars_by_file_func={}
 all_locs=set(fail_counts)|set(pass_counts)
 for (rel,line) in sorted(all_locs):
  ef=fail_counts.get((rel,line),0)
  ep=pass_counts.get((rel,line),0)
  if not ef:continue
  funcs=func_by_loc.get((rel,line),{"<module>"})
  ln_names,_defs,ctrl_spans=_pdg_info(rel)
  controls_fail=any(cl==line and any((rel,sl) in fail_counts and pass_counts.get((rel,sl),0)==0 for sl in range(cl+1,ce+1)) for cl,ce in ctrl_spans)
  is_seed=(ep==0) or controls_fail or any((rel,line,fn) in tbset for fn in funcs)
  if is_seed:
   loaded=ln_names.get(line,{}).get("loads",[])
   for fn in funcs:
    seed_vars_by_file_func.setdefault((rel,fn),set()).update(loaded)
 # 2-hop transitive backward data-dependence closure within each (file, func)
 for _hop in range(2):
  for (rel,line) in sorted(all_locs):
   if not fail_counts.get((rel,line),0):continue
   ln_names,_defs,_ctrl=_pdg_info(rel)
   rec=ln_names.get(line,{})
   st=set(rec.get("stores",[]))
   if not st:continue
   for fn in func_by_loc.get((rel,line),{"<module>"}):
    sv=seed_vars_by_file_func.get((rel,fn))
    if sv and (st & sv):
     sv.update(rec.get("loads",[]))

 ranked=[]
 for (rel,line) in sorted(all_locs):
  p=(repo/rel).resolve()
  if p==repo or repo not in p.parents or not p.is_file() or p.suffix!=".py" or p.name.startswith("test_") or "/tests/" in ("/"+rel):continue
  f=fail_counts.get((rel,line),0)
  if not f:continue
  q=pass_counts.get((rel,line),0)
  ln_names,_defs,ctrl_spans=_pdg_info(rel)
  stores_here=set(ln_names.get(line,{}).get("stores",[]))
  for func in sorted(func_by_loc.get((rel,line),{"<module>"})):
   och=(f/math.sqrt(F*(f+q))) if f else 0.0
   score=och
   reasons=[]
   if f and not q:reasons.append("FAIL_ONLY_EXECUTION")
   if q:reasons.append("PASSING_TEST_OVERLAP")
   if (rel,line,func) in tbset:score+=1.0;reasons.append("FAILING_TRACEBACK_FRAME")
   if stores_here & seed_vars_by_file_func.get((rel,func),set()):
    score+=0.15;reasons.append("BACKWARD_PDG_DEF_USE")
   if any(cl==line and any((rel,sl) in fail_counts and pass_counts.get((rel,sl),0)==0 for sl in range(cl+1,ce+1)) for cl,ce in ctrl_spans):
    score+=0.1;reasons.append("CONTROL_DEPENDENCE_SLICE")
   ranked.append({"path":rel,"line":line,"function":func,"fail_coverage":f,"pass_coverage":q,"ochiai":round(och,12),"score":round(score,12),"reasons":reasons})
 ranked.sort(key=lambda x:(-x["score"],-x["fail_coverage"],x["pass_coverage"],x["path"],x["line"],x["function"]))
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
 top_answer=symbols[0]["symbol"] if symbols else ""
 result={"schema":SCHEMA,"status":"PASS__BOUNDED_DYNAMIC_FAULT_LOCALIZATION","pass":True,"answer":top_answer,"failing_test_count":F,"passing_test_count":P,"test_traces":traces,"ranked_lines":ranked,"ranked_symbols":symbols,"localization_basis":"FAILING_VS_PASSING_DYNAMIC_LINE_SPECTRUM_PLUS_TRACEBACK_PLUS_AST_SYMBOL_OWNERSHIP_PLUS_BACKWARD_DEF_USE","model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_GENERAL_SEMANTIC_CAUSALITY_PROOF","NO_INTERPROCEDURAL_VALUE_PROVENANCE_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_PATCH_CORRECTNESS_OR_MERGEABILITY_CLAIM","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 out=(repo/str(args.get("output_path") or "")).resolve()
 if out==repo or repo not in out.parents:raise FaultLocalizerError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");result["output_path"]=_rel(repo,out);result["output_sha256"]=hashlib.sha256(out.read_bytes()).hexdigest();result["output_verified"]=True;return result
