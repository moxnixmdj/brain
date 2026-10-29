from __future__ import annotations
import ast,difflib,hashlib,importlib.util,json,os,pathlib,re,sys
from typing import Any,Mapping
SCHEMA='PROJECT_BRAIN_PYTHON_ITERATIVE_SOFTWARE_REPAIR_LOOP_V1'
class RepairLoopError(RuntimeError):pass
def _load_patch():
 p=pathlib.Path(__file__).with_name('python_test_guided_patch_search_v1.py');s=importlib.util.spec_from_file_location('_p',p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
_PATCH=_load_patch()
def _safe_dir(repo,raw):
 p=(repo/str(raw or '')).resolve()
 if p!=repo and repo not in p.parents:raise RepairLoopError('PATH_OUTSIDE_REPOSITORY')
 if not p.is_dir() or p.is_symlink():raise RepairLoopError('DIRECTORY_INVALID')
 return p
def _safe_file(repo,raw):
 p=(repo/str(raw or '')).resolve()
 if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!='.py':raise RepairLoopError('FILE_INVALID')
 return p
def _rel(repo,p):return str(p.relative_to(repo)).replace('\\','/')
def _sha(b):return hashlib.sha256(b).hexdigest()
def _text(r):return str(r.get('stdout') or '')+'\n'+str(r.get('stderr') or '')
def _score(r):
 if r.get('timed_out'):return None
 if r.get('returncode')==0:return 0
 t=_text(r);m=re.search(r'FAILED\s*\(([^)]*)\)',t)
 if m:
  n=sum(int(v) for _,v in re.findall(r'(failures|errors)=(\d+)',m.group(1)))
  if n:return n
 n=len(re.findall(r'(?m)^(?:FAIL|ERROR):\s',t));return n or None
def _files(repo,root,tests,failure):
 ts={p.resolve() for p in tests};out=[];seen=set()
 def add(p):
  try:q=p.resolve()
  except OSError:return
  if q in seen or q in ts or not q.is_file() or q.suffix!='.py' or q.name.startswith('test_'):return
  if q!=root and root not in q.parents:return
  seen.add(q);out.append(q)
 for raw in re.findall(r'File "([^"]+\.py)"',failure):
  p=pathlib.Path(raw);add(p if p.is_absolute() else repo/p)
 for test in tests:
  try:tree=ast.parse(test.read_text())
  except Exception:continue
  mods=[]
  for n in ast.walk(tree):
   if isinstance(n,ast.Import):mods += [a.name for a in n.names]
   elif isinstance(n,ast.ImportFrom) and n.module:mods.append(n.module)
  for mod in mods:
   q=pathlib.Path(*mod.split('.'));add(root/(str(q)+'.py'));add(root/q/'__init__.py')
 for p in sorted(root.rglob('*.py')):add(p)
 return out
def _purge(paths):
 for p in paths:_PATCH._purge_source_bytecode(p)
def _diff(repo,p,a,b):return ''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='a/'+_rel(repo,p),tofile='b/'+_rel(repo,p)))
def _best(repo,source,tests,argv,timeout,score,limit,touched,env):
 cur=source.read_bytes()
 try:text=cur.decode();tree=ast.parse(text)
 except Exception:return None,0
 nums,strings=_PATCH._test_literals(tests);best=None;tested=0
 for key,desc,replacer in _PATCH._candidate_specs(tree,nums,strings):
  if tested>=limit:break
  cand=_PATCH._render_candidate(text,key,replacer)
  if not cand or cand==text:continue
  tested+=1;source.write_text(cand);_purge(set(touched)|{source});r=_PATCH._run_tests(repo,argv,timeout,env);source.write_bytes(cur);_purge(set(touched)|{source});s=_score(r)
  if s is None or s>=score:continue
  rec={'source':source,'bytes':cand.encode(),'score':s,'mutation':desc,'sha256':_sha(cand.encode())}
  return rec,tested
 return best,tested
def _source_env(src):
    """Delegate to the shared helper in the patch-search module; one implementation."""
    return _PATCH._source_env(src)


def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 if not isinstance(args,Mapping):raise RepairLoopError('ARGS_NOT_OBJECT')
 repo=pathlib.Path(root).resolve();src=_safe_dir(repo,args.get('source_root','.'));tests=[_safe_file(repo,x) for x in (args.get('test_paths') or [])]
 if not tests:raise RepairLoopError('TEST_PATHS_REQUIRED')
 argv=[str(x) for x in (args.get('test_argv') or _PATCH.suite_argv(sys.executable,*tests))]
 timeout=max(1,min(int(args.get('timeout_s',30)),300));rounds_max=max(1,min(int(args.get('max_rounds',6)),20));files_max=max(1,min(int(args.get('max_files',12)),100));per=max(1,min(int(args.get('max_candidates_per_file',250)),5000));total_max=max(1,min(int(args.get('max_total_candidates',2000)),50000))
 out=(repo/str(args.get('output_path') or '')).resolve()
 if out==repo or repo not in out.parents:raise RepairLoopError('OUTPUT_PATH_OUTSIDE_REPOSITORY')
 env=_source_env(src)
 base=_PATCH._run_tests(repo,argv,timeout,env);score=_score(base)
 # Mutant-wall law (L6, faulthandler-proven): candidates probe with a wall
 # derived from the MEASURED baseline suite time (8x + 3s), not the caller
 # timeout -- on real pytest nodes (1-3s collection each) hundreds of
 # candidates at caller timeout is the whole wall gone (measured tqdm/9).
 cand_timeout=max(6,min(timeout,int(8*float(base.get('elapsed_s') or 1)+3)))
 # Anytime law (L6): count caps are meaningless when one candidate costs a
 # pytest collection -- the deadline stops the search mid-pass, gracefully.
 import time as _t
 _deadline=args.get('wall_deadline')
 def _wall_left():
  return _deadline is None or _t.monotonic()<_deadline
 if base.get('timed_out'):raise RepairLoopError('BASELINE_TIMEOUT')
 if base.get('returncode')==0:raise RepairLoopError('BASELINE_ALREADY_PASSES')
 if score is None:raise RepairLoopError('BASELINE_FAILURE_METRIC_UNPARSEABLE')
 originals={};touched=set();accepted=[];rrecs=[];tested_total=0;final_bytes={};vreplays=[];status='OPEN__NO_COMPLETE_REPAIR_IN_BOUNDED_SEARCH';current=base
 try:
  for ri in range(1,rounds_max+1):
   if not _wall_left():status='OPEN__WALL_DEADLINE_EXHAUSTED';break
   fs=_files(repo,src,tests,_text(current))[:files_max];best=None;round_tested=0
   for source in fs:
    if not _wall_left():status='OPEN__WALL_DEADLINE_EXHAUSTED';break
    rem=total_max-tested_total
    if rem<=0:break
    cand,n=_best(repo,source,tests,argv,cand_timeout,score,min(per,rem),touched,env);tested_total+=n;round_tested+=n
    if cand is not None:
     best=cand
     break
   if best is None:status='OPEN__NO_STRICTLY_IMPROVING_CANDIDATE';break
   p=best['source'];originals.setdefault(p,p.read_bytes());p.write_bytes(best['bytes']);touched.add(p);_purge(touched);current=_PATCH._run_tests(repo,argv,timeout,env);ns=_score(current)
   if ns is None or ns>=score:raise RepairLoopError('ACCEPTED_CANDIDATE_DID_NOT_REPLAY_IMPROVEMENT')
   accepted.append({'round':ri,'source_path':_rel(repo,p),'mutation':best['mutation'],'candidate_sha256':best['sha256'],'score_before':score,'score_after':ns});rrecs.append({'round':ri,'localized_file_count':len(fs),'tested_candidate_count':round_tested,'score_before':score,'score_after':ns});score=ns
   if score==0:status='PASS__BOUNDED_MULTI_ROUND_REPAIR_FOUND';break
  if score==0:
   for _ in range(2):
    _purge(touched);rr=_PATCH._run_tests(repo,argv,timeout,env);rs=_score(rr);vreplays.append({'returncode':rr.get('returncode'),'timed_out':rr.get('timed_out'),'failure_score':rs})
    if rr.get('returncode')!=0 or rs!=0:raise RepairLoopError('FINAL_REPLAY_FAILED')
   final_bytes={p:p.read_bytes() for p in touched}
 finally:
  for p,b in originals.items():p.write_bytes(b)
  _purge(originals)
 patches=[{'source_path':_rel(repo,p),'original_sha256':_sha(originals[p]),'candidate_sha256':_sha(final_bytes[p]),'unified_diff':_diff(repo,p,originals[p],final_bytes[p])} for p in sorted(final_bytes,key=lambda q:_rel(repo,q))]
 result={'schema':SCHEMA,'status':status,'pass':status.startswith('PASS__'),'baseline_failure_score':_score(base),'rounds':rrecs,'accepted_edit_count':len(accepted),'accepted_edits':accepted,'tested_candidate_count':tested_total,'final_verification_replays':vreplays,'patches':patches,'source_restored':all(p.read_bytes()==b for p,b in originals.items()),'model_dependency_count':0,'external_capability_provider_count':0,'incremental_spend_usd':0,'hard_nonclaims':['NO_UNIVERSAL_SOFTWARE_REPAIR_COMPLETENESS','NO_SYNTACTICALLY_UNIVERSAL_EDIT_BASIS','NO_NON_PYTHON_SUPPORT','NO_HIDDEN_REQUIREMENTS_OR_MERGEABILITY_PROOF','NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY','NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT']}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');result['output_path']=_rel(repo,out);result['output_sha256']=_sha(out.read_bytes());result['output_verified']=True;return result
