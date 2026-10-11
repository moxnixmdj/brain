#!/usr/bin/env python3
"""Bounded neutral-plateau extension for Brain-owned Python repair.

Strictly improving single edits are preferred. When none exist, a bounded DFS
may cross score-neutral candidate states up to max_plateau_depth and accepts the
whole edit sequence atomically only if its final state strictly improves the
aggregate failing-test score. Trial states are always restored.
"""
from __future__ import annotations
import difflib,hashlib,importlib.util,json,os,pathlib,sys
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_NEUTRAL_PLATEAU_REPAIR_LOOP_V1"
class RepairLoopError(RuntimeError): pass

def _load(name,module):
 p=pathlib.Path(__file__).resolve().with_name(name)
 s=importlib.util.spec_from_file_location(module,p)
 if s is None or s.loader is None: raise RepairLoopError("DEPENDENCY_LOAD_FAILED:"+name)
 m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
_S=_load("python_iterative_software_repair_loop_v1.py","brain_strict_repair_v1")
_P=_S._PATCH

def _rel(repo,p): return str(p.relative_to(repo)).replace("\\","/")
def _sha(b): return hashlib.sha256(b).hexdigest()
def _diff(repo,p,a,b): return "".join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile="a/"+_rel(repo,p),tofile="b/"+_rel(repo,p)))

def _candidates(source,tests,limit):
 cur=source.read_bytes()
 try: text=cur.decode(); tree=_P.ast.parse(text)
 except Exception: return []
 nums,strings=_P._test_literals(tests); out=[]
 for key,desc,replacer in _P._candidate_specs(tree,nums,strings):
  if len(out)>=limit: break
  cand=_P._render_candidate(text,key,replacer)
  if not cand or cand==text: continue
  raw=cand.encode()
  out.append({"source":source,"bytes":raw,"mutation":desc,"sha256":_sha(raw)})
 return out

def _state_sig(files):
 h=hashlib.sha256()
 for p in files:
  h.update(str(p).encode()); h.update(b"\0"); h.update(p.read_bytes()); h.update(b"\0")
 return h.hexdigest()

def _plateau(repo,files,tests,argv,timeout,score,touched,max_depth,per_file,max_states,max_candidates):
 tested=0; states=0; visited={_state_sig(files)}
 def dfs(level,chain,modified):
  nonlocal tested,states
  if level>=max_depth: return None
  for source in files:
   previous=source.read_bytes()
   for cand in _candidates(source,tests,per_file):
    if tested>=max_candidates: return None
    tested+=1
    source.write_bytes(cand["bytes"]); _S._purge(set(touched)|set(modified)|{source})
    rr=_P._run_tests(repo,argv,timeout); sc=_S._score(rr)
    rec={"source":source,"mutation":cand["mutation"],"candidate_sha256":cand["sha256"],"observed_score":sc}
    if sc is not None and sc<score:
     paths=set(modified)|{source}
     final={p:p.read_bytes() for p in paths}
     source.write_bytes(previous); _S._purge(set(touched)|paths)
     return {"files":final,"edits":chain+[rec],"score":sc,"depth":level+1}
    if sc==score and level+1<max_depth and states<max_states:
     sig=_state_sig(files)
     if sig not in visited:
      visited.add(sig); states+=1
      found=dfs(level+1,chain+[rec],set(modified)|{source})
      if found is not None:
       source.write_bytes(previous); _S._purge(set(touched)|set(modified)|{source})
       return found
    source.write_bytes(previous); _S._purge(set(touched)|set(modified)|{source})
  return None
 result=dfs(0,[],set())
 return result,tested,states

def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 if not isinstance(args,Mapping): raise RepairLoopError("ARGS_NOT_OBJECT")
 repo=pathlib.Path(root).resolve(); src=_S._safe_dir(repo,args.get("source_root","."))
 tests=[_S._safe_file(repo,x) for x in (args.get("test_paths") or [])]
 if not tests: raise RepairLoopError("TEST_PATHS_REQUIRED")
 argv=[str(x) for x in (args.get("test_argv") or [sys.executable]+[_rel(repo,p) for p in tests])]
 timeout=max(1,min(int(args.get("timeout_s",30)),300))
 rounds_max=max(1,min(int(args.get("max_rounds",6)),20))
 files_max=max(1,min(int(args.get("max_files",12)),100))
 per=max(1,min(int(args.get("max_candidates_per_file",150)),3000))
 total_max=max(1,min(int(args.get("max_total_candidates",4000)),50000))
 plateau_depth=max(2,min(int(args.get("max_plateau_depth",3)),6))
 plateau_states=max(1,min(int(args.get("max_plateau_states",100)),5000))
 plateau_candidates=max(1,min(int(args.get("max_plateau_candidates",1600)),30000))
 out=(repo/str(args.get("output_path") or "")).resolve()
 if out==repo or repo not in out.parents: raise RepairLoopError("OUTPUT_PATH_OUTSIDE_REPOSITORY")

 base=_P._run_tests(repo,argv,timeout); score=_S._score(base)
 if base.get("timed_out"): raise RepairLoopError("BASELINE_TIMEOUT")
 if base.get("returncode")==0: raise RepairLoopError("BASELINE_ALREADY_PASSES")
 if score is None: raise RepairLoopError("BASELINE_FAILURE_METRIC_UNPARSEABLE")
 baseline_score=score
 originals={}; touched=set(); accepted=[]; rounds=[]; tested_total=0; final_bytes={}; vreplays=[]; status="OPEN__NO_COMPLETE_REPAIR_IN_BOUNDED_SEARCH"; current=base
 try:
  for ri in range(1,rounds_max+1):
   fs=_S._files(repo,src,tests,_S._text(current))[:files_max]
   single=None; round_tested=0
   for source in fs:
    rem=total_max-tested_total
    if rem<=0: break
    cand,n=_S._best(repo,source,tests,argv,timeout,score,min(per,rem),touched)
    tested_total+=n; round_tested+=n
    if cand is not None: single=cand; break
   if single is not None:
    p=single["source"]; originals.setdefault(p,p.read_bytes()); p.write_bytes(single["bytes"]); touched.add(p); _S._purge(touched)
    current=_P._run_tests(repo,argv,timeout); ns=_S._score(current)
    if ns is None or ns>=score: raise RepairLoopError("SINGLE_ACCEPTED_CANDIDATE_DID_NOT_REPLAY_IMPROVEMENT")
    accepted.append({"round":ri,"mode":"STRICT_SINGLE","source_path":_rel(repo,p),"mutation":single["mutation"],"candidate_sha256":single["sha256"],"score_before":score,"score_after":ns})
    rounds.append({"round":ri,"mode":"STRICT_SINGLE","localized_file_count":len(fs),"tested_candidate_count":round_tested,"score_before":score,"score_after":ns})
    score=ns
   else:
    remaining=max(0,min(plateau_candidates,total_max-tested_total))
    if remaining<=0: status="OPEN__CANDIDATE_BUDGET_EXHAUSTED"; break
    plateau,n,states=_plateau(repo,fs,tests,argv,timeout,score,touched,plateau_depth,per,plateau_states,remaining)
    tested_total+=n; round_tested+=n
    if plateau is None: status="OPEN__NO_STRICT_OR_BOUNDED_NEUTRAL_PLATEAU_IMPROVEMENT"; break
    before=score
    for p,b in plateau["files"].items():
     originals.setdefault(p,p.read_bytes()); p.write_bytes(b); touched.add(p)
    _S._purge(touched); current=_P._run_tests(repo,argv,timeout); ns=_S._score(current)
    if ns is None or ns>=score: raise RepairLoopError("PLATEAU_ACCEPTED_STATE_DID_NOT_REPLAY_IMPROVEMENT")
    depth=plateau["depth"]
    for i,e in enumerate(plateau["edits"],1):
     accepted.append({"round":ri,"mode":"NEUTRAL_PLATEAU","plateau_position":i,"plateau_depth":depth,"source_path":_rel(repo,e["source"]),"mutation":e["mutation"],"candidate_sha256":e["candidate_sha256"],"score_before":before,"observed_score":e["observed_score"],"score_after":ns if i==depth else before})
    rounds.append({"round":ri,"mode":"NEUTRAL_PLATEAU","plateau_depth":depth,"neutral_states_explored":states,"localized_file_count":len(fs),"tested_candidate_count":round_tested,"score_before":before,"score_after":ns})
    score=ns
   if score==0: status="PASS__BOUNDED_STRICT_OR_NEUTRAL_PLATEAU_REPAIR_FOUND"; break
  if score==0:
   for _ in range(2):
    _S._purge(touched); rr=_P._run_tests(repo,argv,timeout); rs=_S._score(rr)
    vreplays.append({"returncode":rr.get("returncode"),"timed_out":rr.get("timed_out"),"failure_score":rs})
    if rr.get("returncode")!=0 or rs!=0: raise RepairLoopError("FINAL_REPLAY_FAILED")
   final_bytes={p:p.read_bytes() for p in touched}
 finally:
  for p,b in originals.items(): p.write_bytes(b)
  _S._purge(originals)
 patches=[{"source_path":_rel(repo,p),"original_sha256":_sha(originals[p]),"candidate_sha256":_sha(final_bytes[p]),"unified_diff":_diff(repo,p,originals[p],final_bytes[p])} for p in sorted(final_bytes,key=lambda q:_rel(repo,q))]
 result={"schema":SCHEMA,"status":status,"pass":status.startswith("PASS__"),"baseline_failure_score":baseline_score,"rounds":rounds,"accepted_edit_count":len(accepted),"accepted_edits":accepted,"tested_candidate_count":tested_total,"max_plateau_depth":plateau_depth,"max_plateau_states":plateau_states,"final_verification_replays":vreplays,"patches":patches,"source_restored":all(p.read_bytes()==b for p,b in originals.items()),"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_UNBOUNDED_COUPLED_EDIT_COMPLETENESS","NO_NEUTRAL_PLATEAU_COMPLETENESS_BEYOND_CONFIGURED_DEPTH_AND_BUDGET","NO_TEMPORARILY_WORSE_INTERMEDIATE_SEARCH","NO_NON_PYTHON_SUPPORT","NO_GENERAL_SEMANTIC_FAULT_LOCALIZATION","NO_HIDDEN_REQUIREMENTS_OR_MERGEABILITY_PROOF","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); result["output_path"]=_rel(repo,out); result["output_sha256"]=_sha(out.read_bytes()); result["output_verified"]=True; return result
