from __future__ import annotations
import hashlib,importlib.util,json,math,os,pathlib,sys
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_PYTHON_PROVENANCE_GUIDED_COUPLED_REPAIR_V1"
class GuidedRepairError(RuntimeError): pass

def _load(name):
 p=pathlib.Path(__file__).with_name(name);s=importlib.util.spec_from_file_location("_brain_"+name,p)
 if s is None or s.loader is None:raise GuidedRepairError("MODULE_LOAD_FAILED:"+name)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

_PATCH=_load("python_test_guided_patch_search_v1.py")
_COUPLED=_load("python_coupled_software_repair_loop_v1.py")
_LOC=_load("python_dynamic_fault_localizer_v1.py")
_PROV=_load("python_interprocedural_value_provenance_v1.py")
_STRICT=_COUPLED._STRICT

def _rel(repo,p):return str(p.relative_to(repo)).replace("\\","/")
def _sha(b):return hashlib.sha256(b).hexdigest()
def _safe_file(repo,raw):
 p=(repo/str(raw or "")).resolve()
 if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py":raise GuidedRepairError("FILE_INVALID")
 return p
def _safe_dir(repo,raw):
 p=(repo/str(raw or ".")).resolve()
 if p!=repo and repo not in p.parents:raise GuidedRepairError("PATH_OUTSIDE_REPOSITORY")
 if not p.is_dir() or p.is_symlink():raise GuidedRepairError("DIRECTORY_INVALID")
 return p

def _guided_rows(repo,loc,prov,max_files,max_symbols):
 boosts={}
 for h in prov.get("interprocedural_hypotheses",[]):
  score=float(h.get("dynamic_score",0) or 0)
  for path,sym in ((h.get("caller_path"),h.get("caller_symbol")),(h.get("callee_path"),h.get("callee_symbol"))):
   if path and sym:boosts[(path,sym)]=max(boosts.get((path,sym),0.0),score)
 by={}
 for s in loc.get("ranked_symbols",[]):
  path=str(s.get("path") or "");sym=str(s.get("symbol") or "")
  if not path or not sym:continue
  p=(repo/path).resolve()
  if not p.is_file() or repo not in p.parents:continue
  base=float(s.get("score",0) or 0);boost=boosts.get((path,sym),0.0)
  row=by.setdefault(path,{"path":p,"rel":path,"score":0.0,"reasons":[],"symbols":[]})
  total=base+(2.0*boost)
  row["score"]=max(row["score"],total)
  reasons=["DYNAMIC_SPECTRUM_SYMBOL"]
  if boost>0:reasons.append("INTERPROCEDURAL_PROVENANCE_BOOST")
  row["symbols"].append({"name":sym,"lineno":int(s.get("lineno",0) or 0),"end_lineno":int(s.get("end_lineno",s.get("lineno",0)) or 0),"score":total,"reasons":reasons})
 for path,row in by.items():
  row["symbols"].sort(key=lambda x:(-x["score"],x["lineno"],x["name"]))
  row["symbols"]=row["symbols"][:max_symbols]
  rs=set()
  for x in row["symbols"]:rs.update(x["reasons"])
  row["reasons"]=sorted(rs)
 rows=list(by.values());rows.sort(key=lambda x:(-x["score"],x["rel"]))
 return rows[:max_files]

def _items(rows,tests,per):
 pools={r["path"]:_COUPLED._pool(r,tests,per) for r in rows}
 return [(r["path"],e) for r in rows for e in pools[r["path"]]]

def _pair_space(n):return n*(n-1)//2

def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 if not isinstance(args,Mapping):raise GuidedRepairError("ARGS_NOT_OBJECT")
 repo=pathlib.Path(root).resolve();src=_safe_dir(repo,args.get("source_root","."))
 env=_PATCH._source_env(src)
 tests=[_safe_file(repo,x) for x in (args.get("test_paths") or []) if str(x).strip()]
 if not tests:
  from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_files
  try:tests=discover_test_files(src)
  except FileNotFoundError:raise GuidedRepairError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
 if not tests:raise GuidedRepairError("TEST_PATHS_REQUIRED")
 argv=[str(x) for x in (args.get("test_argv") or _PATCH.suite_argv(sys.executable,*tests))]
 timeout=max(1,min(int(args.get("timeout_s",20)),120))
 max_files=max(1,min(int(args.get("max_guided_files",4)),16))
 max_symbols=max(1,min(int(args.get("max_guided_symbols_per_file",6)),32))
 per=max(1,min(int(args.get("mutations_per_file",24)),128))
 pair_max=max(1,min(int(args.get("max_pair_candidates",1000)),20000))
 control_files=max(max_files,min(int(args.get("max_control_files",12)),32))
 control_symbols=max(max_symbols,min(int(args.get("max_control_symbols_per_file",12)),64))
 out=(repo/str(args.get("output_path") or "")).resolve()
 if out==repo or repo not in out.parents:raise GuidedRepairError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 base=_PATCH._run_tests(repo,argv,timeout,env)
 if base.get("timed_out"):raise GuidedRepairError("BASELINE_TIMEOUT")
 if base.get("returncode")==0:raise GuidedRepairError("BASELINE_ALREADY_PASSES")
 base_score=_STRICT._score(base)
 if base_score is None:base_score=1
 temp_loc=out.parent/(".loc_"+out.name);temp_prov=out.parent/(".prov_"+out.name)
 loc_args={"source_root":_rel(repo,src) if src!=repo else ".","test_paths":[_rel(repo,p) for p in tests],"output_path":_rel(repo,temp_loc),"timeout_s":timeout,"max_trace_events":args.get("max_trace_events",100000),"max_ranked_lines":args.get("max_ranked_lines",100),"max_ranked_symbols":args.get("max_ranked_symbols",100)}
 prov_args={"source_root":_rel(repo,src) if src!=repo else ".","test_paths":[_rel(repo,p) for p in tests],"output_path":_rel(repo,temp_prov),"timeout_s":timeout,"max_trace_events":args.get("max_trace_events",100000),"max_value_chars":args.get("max_value_chars",120)}
 try:
  loc=_LOC.run(loc_args,repo);prov=_PROV.run(prov_args,repo)
 finally:
  if temp_loc.exists():temp_loc.unlink()
  if temp_prov.exists():temp_prov.unlink()
 rows=_guided_rows(repo,loc,prov,max_files,max_symbols)
 if not rows:raise GuidedRepairError("GUIDANCE_EMPTY")
 guided_items=_items(rows,tests,per)
 failure_text=_STRICT._text(base)
 control_rows=_COUPLED._localize(repo,src,tests,failure_text,control_files,control_symbols)
 control_items=_items(control_rows,tests,per)
 guidance={
  "guided_file_count":len(rows),
  "guided_candidate_item_count":len(guided_items),
  "guided_pair_space":_pair_space(len(guided_items)),
  "control_file_count":len(control_rows),
  "control_candidate_item_count":len(control_items),
  "control_pair_space":_pair_space(len(control_items)),
  "candidate_item_reduction":len(control_items)-len(guided_items),
  "pair_space_reduction":_pair_space(len(control_items))-_pair_space(len(guided_items)),
 }
 guidance["guidance_reduced_candidate_items"]=guidance["candidate_item_reduction"]>0
 guidance["guidance_reduced_pair_space"]=guidance["pair_space_reduction"]>0
 originals={r["path"]:r["path"].read_bytes() for r in rows}
 single_scores={};tested_single=0
 for p,e in guided_items:
  cand=_COUPLED._candidate(originals,[(p,e)])
  if cand is None:continue
  rr=_COUPLED._run_candidate(repo,originals,cand,argv,timeout,env);ss=_STRICT._score(rr)
  if ss is None and rr.get("returncode")!=0 and not rr.get("timed_out"):ss=1
  single_scores[(p,e["start"],e["end"],e["replacement"])]=ss;tested_single+=1
 winner=None;winner_mode=None;pair_count=0;crossed=False
 for p,e in guided_items:
  cand=_COUPLED._candidate(originals,[(p,e)])
  if cand is None:continue
  rr=_COUPLED._run_candidate(repo,originals,cand,argv,timeout,env);ss=_STRICT._score(rr)
  if rr.get("returncode")==0 and (ss==0 or ss is None):
   winner=cand;winner_mode="SINGLE_GUIDED";break
 if winner is None:
  for i in range(len(guided_items)):
   if pair_count>=pair_max:break
   for j in range(i+1,len(guided_items)):
    if pair_count>=pair_max:break
    pair_count+=1;a,b=guided_items[i],guided_items[j]
    cand=_COUPLED._candidate(originals,[a,b])
    if cand is None:continue
    rr=_COUPLED._run_candidate(repo,originals,cand,argv,timeout,env);ps=_STRICT._score(rr)
    if ps is None and rr.get("returncode")!=0 and not rr.get("timed_out"):ps=1
    if rr.get("returncode")==0 and (ps==0 or ps is None):
     ka=(a[0],a[1]["start"],a[1]["end"],a[1]["replacement"]);kb=(b[0],b[1]["start"],b[1]["end"],b[1]["replacement"])
     sa=single_scores.get(ka);sb=single_scores.get(kb);crossed=(sa is None or sa>=base_score) and (sb is None or sb>=base_score)
     winner=cand;winner_mode="COUPLED_PAIR_GUIDED";break
   if winner:break
 replay=[]
 if winner:
  ok=True
  for _ in range(2):
   rr=_COUPLED._run_candidate(repo,originals,winner,argv,timeout,env);rs=_STRICT._score(rr)
   if rr.get("returncode")==0:rs=0
   elif rs is None and not rr.get("timed_out"):rs=1
   replay.append({"returncode":rr.get("returncode"),"failure_score":rs,"timed_out":rr.get("timed_out")})
   ok=ok and rr.get("returncode")==0 and rs==0
  if not ok:winner=None
 patches=[]
 if winner:
  for p,t in sorted(winner.items(),key=lambda x:_rel(repo,x[0])):
   patches.append({"source_path":_rel(repo,p),"original_sha256":_sha(originals[p]),"candidate_sha256":_sha(t.encode()),"unified_diff":_COUPLED._diff(repo,p,originals[p],t)})
 restored=all(p.read_bytes()==b for p,b in originals.items())
 if not restored:raise GuidedRepairError("SOURCE_RESTORATION_FAILED")
 result={"schema":SCHEMA,"status":"PASS__PROVENANCE_GUIDED_COUPLED_REPAIR" if winner else "OPEN__NO_VERIFIED_REPAIR_IN_GUIDED_BOUNDS","pass":winner is not None,"baseline_failure_score":base_score,"guidance":guidance,"guided_localization":[{"path":r["rel"],"score":r["score"],"reasons":r["reasons"],"symbols":r["symbols"]} for r in rows],"provenance_hypothesis_count":len(prov.get("interprocedural_hypotheses",[])),"single_candidates_tested":tested_single,"pair_candidates_tested":pair_count,"winner_mode":winner_mode,"crossed_nonmonotonic_valley":crossed if winner else False,"verification_replays":replay,"patches":patches,"source_restored":restored,"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_UNIVERSAL_SOFTWARE_REPAIR_COMPLETENESS","NO_GENERAL_SEMANTIC_CAUSALITY_PROOF","NO_CLAIM_GUIDANCE_ALWAYS_REDUCES_SEARCH","NO_ARBITRARY_EDIT_BASIS_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_HIDDEN_REQUIREMENTS_OR_GENERAL_MERGEABILITY_PROOF","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");result["output_path"]=_rel(repo,out);result["output_sha256"]=_sha(out.read_bytes());result["output_verified"]=bool(result.get("pass"));return result
