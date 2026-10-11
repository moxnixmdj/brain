from __future__ import annotations
import ast,difflib,hashlib,importlib.util,json,os,pathlib,re,sys
from typing import Any,Mapping
SCHEMA='PROJECT_BRAIN_PYTHON_PAIR_LOOKAHEAD_REPAIR_V1'
class PairLookaheadError(RuntimeError):pass

def _load_patch():
 p=pathlib.Path(__file__).with_name('python_test_guided_patch_search_v1.py');s=importlib.util.spec_from_file_location('_p',p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
_PATCH=_load_patch()

def _safe_dir(repo,raw):
 p=(repo/str(raw or '')).resolve()
 if p!=repo and repo not in p.parents:raise PairLookaheadError('PATH_OUTSIDE_REPOSITORY')
 if not p.is_dir() or p.is_symlink():raise PairLookaheadError('DIRECTORY_INVALID')
 return p

def _safe_file(repo,raw):
 p=(repo/str(raw or '')).resolve()
 if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!='.py':raise PairLookaheadError('FILE_INVALID')
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

def _candidates(source,tests,limit):
 raw=source.read_bytes()
 try:text=raw.decode();tree=ast.parse(text)
 except Exception:return []
 nums,strings=_PATCH._test_literals(tests);out=[]
 for key,desc,replacer in _PATCH._candidate_specs(tree,nums,strings):
  if len(out)>=limit:break
  cand=_PATCH._render_candidate(text,key,replacer)
  if cand is None or cand==text:continue
  out.append((desc,cand.encode()))
 return out

def _diff(repo,p,a,b):
 return ''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='a/'+_rel(repo,p),tofile='b/'+_rel(repo,p)))

def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 if not isinstance(args,Mapping):raise PairLookaheadError('ARGS_NOT_OBJECT')
 repo=pathlib.Path(root).resolve();src=_safe_dir(repo,args.get('source_root','.'));tests=[_safe_file(repo,x) for x in (args.get('test_paths') or [])]
 if not tests:raise PairLookaheadError('TEST_PATHS_REQUIRED')
 argv=[str(x) for x in (args.get('test_argv') or [sys.executable]+[_rel(repo,p) for p in tests])]
 timeout=max(1,min(int(args.get('timeout_s',30)),300));files_max=max(2,min(int(args.get('max_files',8)),50));first_max=max(1,min(int(args.get('max_first_candidates',40)),1000));second_max=max(1,min(int(args.get('max_second_candidates',40)),1000));max_intermediate_increase=max(0,min(int(args.get('max_intermediate_failure_increase',0)),5));total_max=max(1,min(int(args.get('max_total_pairs',1000)),50000))
 out=(repo/str(args.get('output_path') or '')).resolve()
 if out==repo or repo not in out.parents:raise PairLookaheadError('OUTPUT_PATH_OUTSIDE_REPOSITORY')
 base=_PATCH._run_tests(repo,argv,timeout);base_score=_score(base)
 if base.get('timed_out'):raise PairLookaheadError('BASELINE_TIMEOUT')
 if base.get('returncode')==0:raise PairLookaheadError('BASELINE_ALREADY_PASSES')
 if base_score is None:raise PairLookaheadError('BASELINE_FAILURE_METRIC_UNPARSEABLE')
 files=_files(repo,src,tests,_text(base))[:files_max]
 if len(files)<2:raise PairLookaheadError('PAIR_SEARCH_REQUIRES_TWO_LOCALIZED_FILES')
 originals={p:p.read_bytes() for p in files};tested_first=0;tested_pairs=0;winner=None;replays=[];final_bytes={}
 try:
  for p1 in files:
   for d1,b1 in _candidates(p1,tests,first_max):
    tested_first+=1;p1.write_bytes(b1);_purge(files);r1=_PATCH._run_tests(repo,argv,timeout);s1=_score(r1)
    if s1 is not None and s1<=base_score+max_intermediate_increase:
     for p2 in files:
      if p2==p1:continue
      current2=p2.read_bytes()
      for d2,b2 in _candidates(p2,tests,second_max):
       if tested_pairs>=total_max:break
       tested_pairs+=1;p2.write_bytes(b2);_purge(files);r2=_PATCH._run_tests(repo,argv,timeout);s2=_score(r2);p2.write_bytes(current2);_purge(files)
       if s2==0:
        winner={'first_path':p1,'first_mutation':d1,'first_bytes':b1,'first_score':s1,'second_path':p2,'second_mutation':d2,'second_bytes':b2};break
      if winner or tested_pairs>=total_max:break
    if winner:break
    p1.write_bytes(originals[p1]);_purge(files)
    if tested_pairs>=total_max:break
   if winner or tested_pairs>=total_max:break
  if winner:
   p1=winner['first_path'];p2=winner['second_path'];p1.write_bytes(winner['first_bytes']);p2.write_bytes(winner['second_bytes']);_purge(files)
   for _ in range(2):
    rr=_PATCH._run_tests(repo,argv,timeout);rs=_score(rr);replays.append({'returncode':rr.get('returncode'),'timed_out':rr.get('timed_out'),'failure_score':rs})
    if rr.get('returncode')!=0 or rs!=0:raise PairLookaheadError('FINAL_REPLAY_FAILED')
   final_bytes={p:p.read_bytes() for p in (p1,p2)}
 finally:
  for p,b in originals.items():p.write_bytes(b)
  _purge(files)
 patches=[]
 if winner:
  for p in (winner['first_path'],winner['second_path']):patches.append({'source_path':_rel(repo,p),'original_sha256':_sha(originals[p]),'candidate_sha256':_sha(final_bytes[p]),'unified_diff':_diff(repo,p,originals[p],final_bytes[p])})
 result={'schema':SCHEMA,'status':'PASS__BOUNDED_TWO_EDIT_LOOKAHEAD_REPAIR_FOUND' if winner else 'OPEN__NO_VERIFIED_PAIR_IN_BOUNDED_SEARCH','pass':winner is not None,'baseline_failure_score':base_score,'tested_first_candidate_count':tested_first,'tested_pair_count':tested_pairs,'max_intermediate_failure_increase':max_intermediate_increase,'pair':None if not winner else {'first_source_path':_rel(repo,winner['first_path']),'first_mutation':winner['first_mutation'],'intermediate_failure_score':winner['first_score'],'second_source_path':_rel(repo,winner['second_path']),'second_mutation':winner['second_mutation']},'final_verification_replays':replays,'patches':patches,'source_restored':all(p.read_bytes()==b for p,b in originals.items()),'model_dependency_count':0,'external_capability_provider_count':0,'incremental_spend_usd':0,'hard_nonclaims':['NO_ARBITRARY_COUPLED_EDIT_COMPLETENESS','NO_MORE_THAN_TWO_EDIT_LOOKAHEAD','NO_SAME_FILE_PAIR_SEARCH','NO_GENERAL_SEMANTIC_LOCALIZATION','NO_NON_PYTHON_SUPPORT','NO_HIDDEN_REQUIREMENTS_OR_MERGEABILITY_PROOF','NO_FRONTIERCODE_SCORE_CREDIT']}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');result['output_path']=_rel(repo,out);result['output_sha256']=_sha(out.read_bytes());result['output_verified']=True;return result
