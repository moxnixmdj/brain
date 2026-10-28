from __future__ import annotations
import ast,difflib,hashlib,importlib.util,json,os,pathlib,re,sys
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_PYTHON_COUPLED_SOFTWARE_REPAIR_LOOP_V1"
class RepairLoopError(RuntimeError): pass
def _load(name):
 p=pathlib.Path(__file__).with_name(name); s=importlib.util.spec_from_file_location("_x_"+name,p)
 m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
_PATCH=_load("python_test_guided_patch_search_v1.py")
_STRICT=_load("python_iterative_software_repair_loop_v1.py")
def _rel(repo,p): return str(p.relative_to(repo)).replace("\\","/")
def _sha(b): return hashlib.sha256(b).hexdigest()
def _safe_file(repo,raw):
 p=(repo/str(raw or "")).resolve()
 if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py": raise RepairLoopError("FILE_INVALID")
 return p
def _safe_dir(repo,raw):
 p=(repo/str(raw or ".")).resolve()
 if p!=repo and repo not in p.parents: raise RepairLoopError("PATH_OUTSIDE_REPOSITORY")
 if not p.is_dir() or p.is_symlink(): raise RepairLoopError("DIRECTORY_INVALID")
 return p
def _trace_frames(repo,text):
 out=[]
 pat=re.compile(r'File "([^"]+\.py)", line (\d+)(?:, in ([A-Za-z_][A-Za-z0-9_]*))?')
 for raw,line,func in pat.findall(text or ""):
  p=pathlib.Path(raw); p=p if p.is_absolute() else repo/p
  try:p=p.resolve()
  except OSError:continue
  if p.is_file() and repo in p.parents: out.append((p,int(line),func or ""))
 return out
def _test_imports(repo,tests):
 mods=[]; names=set()
 for t in tests:
  try:tree=ast.parse(t.read_text(encoding="utf-8"),filename=str(t))
  except Exception:continue
  for n in ast.walk(tree):
   if isinstance(n,ast.Import):
    for a in n.names: mods.append(a.name)
   elif isinstance(n,ast.ImportFrom) and n.module:
    mods.append(n.module)
    for a in n.names:
     if a.name!="*": names.add(a.asname or a.name)
 out=[]
 for mod in mods:
  q=pathlib.Path(*mod.split("."))
  for p in (repo/(str(q)+".py"),repo/q/"__init__.py"):
   try:p=p.resolve()
   except OSError:continue
   if p.is_file() and repo in p.parents and p not in out: out.append(p)
 return out,names
def _defs(path):
 try:tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
 except Exception:return []
 out=[]
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
   out.append({"name":n.name,"lineno":getattr(n,"lineno",0),"end_lineno":getattr(n,"end_lineno",getattr(n,"lineno",0))})
 return out
def _localize(repo,root,tests,failure,max_files,max_symbols):
 imported,imported_names=_test_imports(repo,tests); frames=_trace_frames(repo,failure)
 toks={x.lower() for x in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}",failure or "")}
 testset={p.resolve() for p in tests}; files=[]; seen=set()
 def add(p):
  try:q=p.resolve()
  except OSError:return
  if q in seen or q in testset or not q.is_file() or q.suffix!=".py" or q.name.startswith("test_"):return
  if q!=root and root not in q.parents:return
  seen.add(q); files.append(q)
 for p,_,_ in frames:add(p)
 for p in imported:add(p)
 for p in sorted(root.rglob("*.py")):add(p)
 ranked=[]
 for p in files:
  fscore=0; freasons=[]
  if any(x[0]==p for x in frames):fscore+=10000;freasons.append("TRACEBACK_FILE")
  if p in imported:fscore+=5000;freasons.append("TEST_IMPORT_FILE")
  symbols=[]
  for d in _defs(p):
   s=0; rs=[]
   if d["name"] in imported_names:s+=2000;rs.append("TEST_IMPORTED_SYMBOL")
   if d["name"].lower() in toks:s+=500;rs.append("FAILURE_TEXT_SYMBOL")
   for fp,line,func in frames:
    if fp==p and d["lineno"]<=line<=d["end_lineno"]:
     s+=4000;rs.append("TRACEBACK_LINE_CONTAINS_SYMBOL")
    if fp==p and func==d["name"]:
     s+=3000;rs.append("TRACEBACK_FUNCTION")
   symbols.append({**d,"score":s,"reasons":rs})
  symbols.sort(key=lambda x:(-x["score"],x["lineno"],x["name"]))
  if symbols:fscore+=symbols[0]["score"]
  ranked.append({"path":p,"rel":_rel(repo,p),"score":fscore,"reasons":freasons,"symbols":symbols[:max_symbols]})
 ranked.sort(key=lambda x:(-x["score"],x["rel"]))
 return ranked[:max_files]
def _edit(text,key,desc,replacer):
  # A file under source_root may be third-party and use syntax this interpreter cannot parse
  # (PEP 695 type aliases need 3.12). Such a file cannot be a repair candidate or a
  # localization target, so it contributes nothing - it must not abort the whole search,
  # which is the defect python_test_audit documents for timeouts one layer down.
 try:tree=ast.parse(text)
 except (SyntaxError,ValueError):return None
 target=None
 for n in ast.walk(tree):
  if _PATCH._node_key(n)==key:target=n;break
 if target is None:return None
 vals=(getattr(target,"lineno",None),getattr(target,"col_offset",None),getattr(target,"end_lineno",None),getattr(target,"end_col_offset",None))
 if any(v is None for v in vals):return None
 repl=replacer(target);ast.fix_missing_locations(repl);rb=ast.unparse(repl).encode()
 raw=text.encode();lines=raw.splitlines(keepends=True)
 start=_PATCH._byte_offset(lines,target.lineno,target.col_offset);end=_PATCH._byte_offset(lines,target.end_lineno,target.end_col_offset)
 if raw[start:end]==rb:return None
 return {"start":start,"end":end,"replacement":rb,"mutation":desc}
def _pool(row,tests,per_file):
 p=row["path"]
 try:
  text=p.read_bytes().decode("utf-8");tree=ast.parse(text,filename=str(p))
 except (SyntaxError,ValueError,UnicodeDecodeError):return []
 nums,strings=_PATCH._test_literals(tests)
 ranges=[(s["lineno"],s["end_lineno"],s["score"]) for s in row["symbols"] if s["score"]>0]
 out=[]
 for key,desc,replacer in _PATCH._candidate_specs(tree,nums,strings):
  line=desc.get("lineno") or 0
  priority=max([score for a,b,score in ranges if a<=line<=b] or [0])
  e=_edit(text,key,desc,replacer)
  if e is not None:out.append((priority,e))
 out.sort(key=lambda x:(-x[0],x[1]["start"],x[1]["end"],str(x[1]["mutation"])))
 return [e for _,e in out[:per_file]]
def _apply(text,edits):
 raw=text.encode(); es=sorted(edits,key=lambda e:(e["start"],e["end"]));last=-1
 for e in es:
  if e["start"]<last:return None
  last=e["end"]
 for e in sorted(es,key=lambda e:e["start"],reverse=True):
  raw=raw[:e["start"]]+e["replacement"]+raw[e["end"]:]
 try:out=raw.decode();ast.parse(out)
 except Exception:return None
 return out
def _candidate(originals,items):
 grouped={}
 for p,e in items:grouped.setdefault(p,[]).append(e)
 out={}
 for p,es in grouped.items():
  v=_apply(originals[p].decode(),es)
  if v is None or v.encode()==originals[p]:return None
  out[p]=v
 return out
def _run_candidate(repo,originals,cand,argv,timeout,env):
 try:
  for p,t in cand.items():p.write_text(t);_PATCH._purge_source_bytecode(p)
  return _PATCH._run_tests(repo,argv,timeout,env)
 finally:
  for p in cand:p.write_bytes(originals[p]);_PATCH._purge_source_bytecode(p)
def _diff(repo,p,a,b):
 return "".join(difflib.unified_diff(a.decode().splitlines(True),b.splitlines(True),fromfile="a/"+_rel(repo,p),tofile="b/"+_rel(repo,p)))
def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 if not isinstance(args,Mapping):raise RepairLoopError("ARGS_NOT_OBJECT")
 repo=pathlib.Path(root).resolve();src=_safe_dir(repo,args.get("source_root","."))
 env=_PATCH._source_env(src)
 _stated_tests=[x for x in (args.get("test_paths") or []) if str(x).strip()]
 if _stated_tests:
  tests=[_safe_file(repo,x) for x in _stated_tests];test_paths_source="stated"
 else:
  # "Repair the source root so the tests pass" names no file, and which files are
  # tests is a fact about the tree. The command on the next line was already
  # derived when unstated; only this list was missing, and its absence is what
  # kept the whole repair lane unreachable from the front door.
  from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_files
  try:tests=discover_test_files(src);test_paths_source="discovered_under_source_root"
  except FileNotFoundError:raise RepairLoopError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
 if not tests:raise RepairLoopError("TEST_PATHS_REQUIRED")
 argv=[str(x) for x in (args.get("test_argv") or _PATCH.suite_argv(sys.executable,*tests))]
 timeout=max(1,min(int(args.get("timeout_s",20)),120));max_files=max(1,min(int(args.get("max_files",8)),32));max_symbols=max(1,min(int(args.get("max_symbols_per_file",8)),64));per=max(1,min(int(args.get("mutations_per_file",24)),128));pair_max=max(1,min(int(args.get("max_pair_candidates",1200)),20000))
 out=(repo/str(args.get("output_path") or "")).resolve()
 if out==repo or repo not in out.parents:raise RepairLoopError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 strict_probe=out.parent/(".strict_"+out.name)
 strict_args={"source_root":_rel(repo,src) if src!=repo else ".","test_paths":[_rel(repo,p) for p in tests],"test_argv":argv,"output_path":_rel(repo,strict_probe),"timeout_s":timeout,"max_rounds":args.get("max_strict_rounds",6),"max_files":max_files,"max_candidates_per_file":args.get("max_strict_candidates_per_file",120),"max_total_candidates":args.get("max_strict_total_candidates",1000)}
 try:
  strict=_STRICT.run(strict_args,repo)
 except Exception as exc:
  strict={"pass":False,"status":"OPEN__STRICT_ROUTE_DECLINED","reason":type(exc).__name__+":"+str(exc)}
 finally:
  if strict_probe.exists():strict_probe.unlink()
 if strict.get("pass"):
  result={"schema":SCHEMA,"status":"PASS__STRICT_PROGRESS_ROUTE","pass":True,"route":"STRICT_PROGRESS","strict_result":strict,"localization_candidates":[],"crossed_nonmonotonic_valley":False,"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"source_restored":strict.get("source_restored") is True,"hard_nonclaims":["NO_UNIVERSAL_SOFTWARE_REPAIR_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_HIDDEN_REQUIREMENTS_OR_GENERAL_MERGEABILITY_PROOF","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 else:
  base=_PATCH._run_tests(repo,argv,timeout,env);score=_STRICT._score(base)
  if score is None and not base.get("timed_out"): score=1
  if base.get("timed_out"):raise RepairLoopError("BASELINE_TIMEOUT")
  if base.get("returncode")==0:raise RepairLoopError("BASELINE_ALREADY_PASSES")
  if score is None:raise RepairLoopError("BASELINE_FAILURE_METRIC_UNPARSEABLE")
  loc=_localize(repo,src,tests,_STRICT._text(base),max_files,max_symbols)
  originals={r["path"]:r["path"].read_bytes() for r in loc}
  pools={r["path"]:_pool(r,tests,per) for r in loc}
  items=[(r["path"],e) for r in loc for e in pools[r["path"]]]
  single_scores={};tested_single=0
  for p,e in items:
   cand=_candidate(originals,[(p,e)])
   if cand is None:continue
   rr=_run_candidate(repo,originals,cand,argv,timeout,env);ss=_STRICT._score(rr);single_scores[(p,e["start"],e["end"],e["replacement"])]=(1 if ss is None and rr.get("returncode")!=0 and not rr.get("timed_out") else ss);tested_single+=1
  winner=None;winner_items=None;pair_count=0;crossed=False
  for i in range(len(items)):
   if pair_count>=pair_max:break
   for j in range(i+1,len(items)):
    if pair_count>=pair_max:break
    pair_count+=1;a,b=items[i],items[j];cand=_candidate(originals,[a,b])
    if cand is None:continue
    rr=_run_candidate(repo,originals,cand,argv,timeout,env);ps=_STRICT._score(rr)
    if ps is None and rr.get("returncode")!=0 and not rr.get("timed_out"): ps=1
    if rr.get("returncode")==0 and ps==0:
     ka=(a[0],a[1]["start"],a[1]["end"],a[1]["replacement"]);kb=(b[0],b[1]["start"],b[1]["end"],b[1]["replacement"])
     sa=single_scores.get(ka);sb=single_scores.get(kb);crossed=(sa is None or sa>=score) and (sb is None or sb>=score)
     winner=cand;winner_items=[a,b];break
   if winner:break
  replay=[]
  if winner:
   ok=True
   for _ in range(2):
    rr=_run_candidate(repo,originals,winner,argv,timeout,env);rs=_STRICT._score(rr);rs=(0 if rr.get("returncode")==0 else (1 if rs is None and not rr.get("timed_out") else rs));replay.append({"returncode":rr.get("returncode"),"failure_score":rs,"timed_out":rr.get("timed_out")});ok=ok and rr.get("returncode")==0 and rs==0
   if not ok:winner=None;winner_items=None
  patches=[]
  if winner:
   for p,t in sorted(winner.items(),key=lambda x:_rel(repo,x[0])):patches.append({"source_path":_rel(repo,p),"original_sha256":_sha(originals[p]),"candidate_sha256":_sha(t.encode()),"unified_diff":_diff(repo,p,originals[p],t)})
  restored=all(p.read_bytes()==b for p,b in originals.items())
  result={"schema":SCHEMA,"status":"PASS__NONMONOTONIC_COUPLED_PAIR_REPAIR_FOUND" if winner else "OPEN__NO_VERIFIED_REPAIR_IN_STRICT_OR_COUPLED_BOUNDS","pass":winner is not None,"route":"COUPLED_PAIR" if winner else "NONE","baseline_failure_score":score,"strict_result_status":strict.get("status"),"localization_candidates":[{"path":r["rel"],"score":r["score"],"reasons":r["reasons"],"symbols":r["symbols"]} for r in loc],"single_candidates_tested":tested_single,"pair_candidates_tested":pair_count,"crossed_nonmonotonic_valley":crossed if winner else False,"verification_replays":replay,"patches":patches,"source_restored":restored,"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_UNIVERSAL_SOFTWARE_REPAIR_COMPLETENESS","NO_ARBITRARY_EDIT_BASIS_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_HIDDEN_REQUIREMENTS_OR_GENERAL_MERGEABILITY_PROOF","NO_CLAIM_LOCALIZATION_IS_COMPLETE_SEMANTIC_CAUSALITY","NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 if not result.get("source_restored"):raise RepairLoopError("SOURCE_RESTORATION_FAILED")
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");result["output_path"]=_rel(repo,out);result["output_sha256"]=_sha(out.read_bytes());result["output_verified"]=bool(result.get("pass"));return result
