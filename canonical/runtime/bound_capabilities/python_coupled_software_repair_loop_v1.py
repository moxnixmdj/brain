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
_LOC=_load("python_dynamic_fault_localizer_v1.py")
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
 return _edit_node(text.encode(),text.encode().splitlines(keepends=True),target,desc,replacer)
def _edit_node(raw,lines,target,desc,replacer):
 # Compatibility entry; all engines now share the same replacement primitive.
 span=_PATCH._replacement_span(raw,lines,target,replacer)
 if span is None:return None
 start,end,rb=span
 if raw[start:end]==rb:return None
 return {"start":start,"end":end,"replacement":rb,"mutation":desc}
FOCUS_BONUS_MAX=10000
FOCUS_DECAY_PER_LINE=100
FOCUS_WINDOW_LINES=100

def _focus_bonus(line,focus):
 """How much a candidate site is favoured by the stack that failed.

 Measured 2026-11-01 on pluggy at 3fc9e561 (injected `and`->`or` at src/pluggy/_manager.py:247,
 7 of 226 tests failing). The failing run's traceback names `_manager.py:251`, which is INSIDE the
 branch the faulty predicate chose: `elif not verified or hook.has_spec():` raised from
 `self._verify_hook(...)` four lines below it. The old rule was a binary +/-2-line window, so the
 one site that mattered scored exactly zero while 64 slots went to line-142 constant flips. The
 guided search reported OPEN__NO_VERIFIED_REPAIR_IN_GUIDED_BOUNDS while the single-file search over
 the same file found the repair -- a localized search is only as good as this function.

 A raise site and the condition that sent control there are the same fact a few lines apart, so
 proximity is graded instead of thresholded: the stack's own line is strongest, its neighbourhood
 decays linearly, and nothing in the file is ever discarded (a distant site still outranks an
 unranked sibling by its symbol score). Distance is clamped, so the bonus can never go negative and
 reorder two equally-ranked sites behind a third.
 """
 if not focus:return 0
 d=min(abs(line-f) for f in focus)
 if d>FOCUS_WINDOW_LINES:return 0
 return max(0,FOCUS_BONUS_MAX-FOCUS_DECAY_PER_LINE*d)


FOCUS_CONDITION_BONUS=20000

def _branch_condition_lines(tree,focus):
 """The `if`/`elif` conditions guarding the lines the failing stack names.

 Measured 2026-11-01 on pluggy 3fc9e561 with `and`->`or` injected at src/pluggy/_manager.py:247.
 The stack names 251, which is INSIDE the branch that the faulty condition sent control into:

     247:  elif not verified or hook.has_spec():      <- the fault
     251:      self._verify_hook(hook, hookimpl)       <- the raise the stack names

 A raise site and its guarding condition are the same fact one branch apart, and proximity alone
 cannot express that: with graded distance the true site scored 9600 while eight unrelated constant
 guesses three lines from another frame scored 9700 and crowded it out of the pool. Control entered
 that branch BECAUSE its test evaluated true, so the test line is the prime suspect whenever the
 stack lands in a branch body. This is read from the AST, not guessed from indentation.
 """
 out=set()
 if not focus:return out
 for node in ast.walk(tree):
  if not isinstance(node,ast.If) or not node.body:
   continue
  body=node.body
  start=min(getattr(x,"lineno",10**9) for x in body)
  end=max(getattr(x,"end_lineno",getattr(x,"lineno",0)) or 0 for x in body)
  if any(start<=f<=end for f in focus):
   out.add(int(getattr(node,"lineno",0) or 0))
 return out


def _pool(row,tests,per_file):
 p=row["path"]
 try:
  text=p.read_bytes().decode("utf-8");tree=ast.parse(text,filename=str(p))
 except (SyntaxError,ValueError,UnicodeDecodeError):return []
 nums,strings=_PATCH._test_literals(tests)
 ranges=[(s["lineno"],s["end_lineno"],s["score"]) for s in row["symbols"] if s["score"]>0]
 focus=set(row.get("focus") or ())
 cond_lines=_branch_condition_lines(tree,focus)
 out=[]
 renderer=_PATCH._CandidateRenderer(text,tree)
 for key,desc,replacer in _PATCH._candidate_specs(tree,nums,strings,p):
  line=desc.get("lineno") or 0
  sym_score=max([score for a,b,score in ranges if a<=line<=b] or [0])
  focus_near=_focus_bonus(line,focus)
  if line in cond_lines:focus_near+=FOCUS_CONDITION_BONUS
  _ef=row.get("_ev_freq") or {}
  if _ef:
   # EXECUTION-EVIDENCE RANKING LAW: inside an evidence span the trace IS
   # the ranker -- static symbol scores are IGNORED there (measured: the
   # scored format_meter symbol let its equally-hot trivia sites consume
   # the whole neighborhood reserve ahead of the faulty format_sizeof
   # zone). Hot-loop lines first, then plain executed, then the rest.
   _hot=min(1.0,_ef.get(line,0)/8.0)
   if any(a<=line<=b for a,b in (row.get("_ev_spans") or ())):
    priority=20000*_hot+focus_near
   else:
    priority=sym_score+focus_near+(2000*_hot if _hot>0 else 0)
  else:
   # traceback-frame proximity dominates: a site ON/next-to a line the
   # stack names is the evidence-first candidate, not early-line trivia
   priority=sym_score+focus_near
  e=renderer.edit(key,desc,replacer)
  if e is not None:
   e["family"]=desc.get("family") or "legacy"
   if desc.get("ratio"):e["ratio"]=desc["ratio"]
   e["lineno"]=line
   out.append((priority,e))
 out.sort(key=lambda x:(-x[0],x[1]["start"],x[1]["end"],str(x[1]["mutation"])))
 # FAMILY-RESERVE LAW (L5 dilution, ladder-measured): legacy families keep
 # the FULL per_file budget they always had; neighborhood entries are an
 # appended reserve, never slot competitors. Pair space is legacy-only:
 # the pair loop enumerates the index product of the flattened pool under
 # pair_max -- extra entries there push the winning pair past the cap
 # (the L5 (Add->+,Add->+) repair fell outside 1000).
 legacy=[e for _,e in out if e.get("family") not in ("neighborhood","guard_clause","dropped_operand")][:per_file]
 neigh=[e for _,e in out if e.get("family")=="neighborhood"][:9]
 guards=[e for _,e in out if e.get("family")=="guard_clause"][:12]
 # DROPPED-OPERAND RESERVE: a *removed* operand (`price` for `price * qty`) has
 # no node to swap, so it is reachable only through this family.  Its own slots,
 # appended -- legacy indices, pair-space membership and every existing budget
 # stay byte-identical to what the ladder receipts measured.
 dropped=[e for _,e in out if e.get("family")=="dropped_operand"][:8]
 return legacy+neigh+guards+dropped
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
def _run_candidate(repo,originals,cand,argv,timeout,env,cwd=None):
 try:
  for p,t in cand.items():p.write_text(t);_PATCH._purge_source_bytecode(p)
  return _PATCH._run_tests(repo,argv,timeout,env,cwd=cwd)
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
 argv=_PATCH.argv_or_derived(args.get("test_argv"),sys.executable,*tests)
 timeout=max(1,min(int(args.get("timeout_s",20)),120));max_files=max(1,min(int(args.get("max_files",8)),32));max_symbols=max(1,min(int(args.get("max_symbols_per_file",8)),64));per=max(1,min(int(args.get("mutations_per_file",24)),128));pair_max=max(1,min(int(args.get("max_pair_candidates",1200)),20000))
 # WALL GOVERNOR (tqdm/9 measured): every phase is individually bounded but
 # the phases in SUM exceeded the engine's share -- the strict probe burned
 # the budget before the coordinated/singles/pair phases could run. One
 # deadline at entry; every phase checks it; suite timeouts shrink to the
 # remaining wall.
 import time as _wt
 _cwb=args.get("wall_budget_s")
 _cdead=(_wt.monotonic()+float(_cwb)) if _cwb else None
 def _cleft():return _cdead is None or _wt.monotonic()<_cdead
 def _ctimeout():
  return min(timeout,max(5.0,round(_cdead-_wt.monotonic(),1))) if _cdead else timeout
 out=(repo/str(args.get("output_path") or "")).resolve()
 if out==repo or repo not in out.parents:raise RepairLoopError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 strict_probe=out.parent/(".strict_"+out.name)
 strict_args={"source_root":_rel(repo,src) if src!=repo else ".","test_paths":[_rel(repo,p) for p in tests],"test_argv":argv,"output_path":_rel(repo,strict_probe),"timeout_s":timeout,"max_rounds":args.get("max_strict_rounds",6),"max_files":max_files,"max_candidates_per_file":args.get("max_strict_candidates_per_file",120),"max_total_candidates":args.get("max_strict_total_candidates",1000)}
 if args.get("exec_evidence"):
  # evidence mode exists to focus the coordinated/singles/pair phases; the
  # strict probe is a full extra search and would eat exactly the share the
  # evidence was bought for (measured: 120s share, strict consumed it all)
  strict={"pass":False,"status":"SKIPPED_EXEC_EVIDENCE_MODE"}
 elif _cdead is not None and (_cdead-_wt.monotonic())<45:
  # a low-share invocation goes straight to the evidence phases: the strict
  # probe is a full extra search and would starve the coordinated phase
  strict={"pass":False,"status":"SKIPPED_WALL_BUDGET_STRICT"}
 else:
  try:
   strict=_STRICT.run(strict_args,repo)
  except Exception as exc:
   strict={"pass":False,"status":"OPEN__STRICT_ROUTE_DECLINED","reason":type(exc).__name__+":"+str(exc)}
 if strict_probe.exists():strict_probe.unlink()
 if strict.get("pass"):
  result={"schema":SCHEMA,"status":"PASS__STRICT_PROGRESS_ROUTE","pass":True,"route":"STRICT_PROGRESS","strict_result":strict,"patches":strict.get("patches") or [],"localization_candidates":[],"crossed_nonmonotonic_valley":False,"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"source_restored":strict.get("source_restored") is True,"hard_nonclaims":["NO_UNIVERSAL_SOFTWARE_REPAIR_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_HIDDEN_REQUIREMENTS_OR_GENERAL_MERGEABILITY_PROOF","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 else:
  _runcwd=src if (src!=repo and src.is_dir()) else None
  base=_PATCH._run_tests(repo,argv,timeout,env,cwd=_runcwd);score=_STRICT._score(base)
  if score is None and not base.get("timed_out"): score=1
  if base.get("timed_out"):raise RepairLoopError("BASELINE_TIMEOUT")
  if base.get("returncode")==0:raise RepairLoopError("BASELINE_ALREADY_PASSES")
  if score is None:raise RepairLoopError("BASELINE_FAILURE_METRIC_UNPARSEABLE")
  loc=_localize(repo,src,tests,_STRICT._text(base),max_files,max_symbols)
  # EXECUTION-EVIDENCE FOCUS (the tqdm/9 seam): pytest tracebacks name only
  # the TEST file, so traceback-frame focus is empty for pytest suites and
  # line-order trivia fills the pools. The existing dynamic fault localizer
  # traces the failing suite ONCE and ranks executed source lines
  # (fail-vs-pass spectrum + traceback + AST ownership). Merging its ranked
  # lines into focus puts the real threshold sites at the pool front, where
  # the coordinated-neighborhood phase fires first (~1 run per ratio).
  exec_evidence_row=None
  if args.get("exec_evidence"):
   try:
    _ev=_LOC.run({"source_root":_rel(repo,src) if src!=repo else ".",
      "test_paths":[_rel(repo,q) for q in tests],"test_argv":argv,
      "timeout_s":timeout,
      "output_path":_rel(repo,out.parent/("._ev_"+out.name)),
      # NOT the PGC tracer's 30000 economics: pytest collection alone burns
      # that before the test body runs (measured: format_sizeof lines absent
      # at 30k, present at 400k)
      "max_trace_events":int(args.get("exec_evidence_trace_events",1000000)),
      "max_ranked_lines":200,"max_ranked_symbols":60},repo)
    _fl={}
    for _r in _ev.get("ranked_lines") or []:
     if (_r.get("score") or 0)<=0:continue
     _p=(repo/str(_r.get("path"))).resolve()
     _fl.setdefault(_p,set()).add(int(_r.get("line") or 0))
    for row in loc:
     row["focus"]=sorted(set(row.get("focus") or ())|_fl.get(row["path"],set()))
    # evidence function spans: the localizer's (path,line,function) rows
    # define symbol scopes the static symbol ranking may miss
    _spans={}
    for _r in _ev.get("ranked_lines") or []:
     if not _r.get("function") or _r.get("function")=="<module>":continue
     _p=(repo/str(_r.get("path"))).resolve()
     _spans.setdefault(_p,{}).setdefault(_r["function"],[]).append(int(_r.get("line") or 0))
    _ev_spans={}
    for _p,fs in _spans.items():
     _ev_spans[_p]=[(min(v),max(v)) for f,v in fs.items()]
    # execution frequency: the tracer already records per-line hit counts;
    # loop-body lines (hot code) must outrank incidentally-executed setup
    # lines in pool priority (measured: format_sizeof's lines run 8x+ per
    # call, module/init lines run once -- static symbol scores invert this)
    _ev_freq={}
    for _t in _ev.get("test_traces") or []:
     for _a,_b,_c,_n in _t.get("events") or []:
      _p=(repo/str(_a)).resolve()
      _m=_ev_freq.setdefault(_p,{})
      _m[int(_b)]=_m.get(int(_b),0)+int(_n or 0)
    for row in loc:
     row["_ev_freq"]=_ev_freq.get(row["path"],{})
     row["_ev_spans"]=_ev_spans.get(row["path"],[])
    exec_evidence_row={"status":_ev.get("status"),"ranked_lines":len(_fl),"spans":len(_ev_spans)}
   except Exception as _exc:
    exec_evidence_row={"status":"EXEC_EVIDENCE_DECLINED:"+type(_exc).__name__+":"+str(_exc)[:80]}
  originals={r["path"]:r["path"].read_bytes() for r in loc}
  pools={r["path"]:_pool(r,tests,per) for r in loc}
  items=[(r["path"],e) for r in loc for e in pools[r["path"]]]
  # pair space stays legacy+guard exactly as measured: a new family may add
  # single-site candidates, never re-index the product the pair loop walks.
  items_pairs=[it for it in items if it[1].get("family") not in ("neighborhood","dropped_operand")]
  winner=None;winner_items=None;pair_count=0;crossed=False
  # COORDINATED-NEIGHBORHOOD PHASE FIRST (decoded tqdm/9 class): a real
  # boundary fix retunes a FAMILY of thresholds with the SAME multiplier
  # (1000->999.95, 100->99.95, 10->9.995 = one logical edit over three
  # constants). One candidate per ratio, all same-ratio edits applied
  # simultaneously -- ~1 suite run per ratio, cheaper than any sweep.
  _ratios={}
  for _p,_e in items:
   if _e.get("family")=="neighborhood" and _e.get("ratio"):
    _ratios.setdefault(_e["ratio"],[]).append((_p,_e))
  # candidate groups per ratio: FULL SET first, then per-symbol scopes
  # (measured: the full set mixed spurious same-ratio edits from other
  # executed sites and stayed red; the decoded real fix is bounded to ONE
  # function's thresholds)
  _symran={r["path"]:[(x["lineno"],x["end_lineno"]) for x in r["symbols"]] for r in loc}
  for _p,_ss in (_ev_spans if args.get("exec_evidence") else {}).items():
   _symran.setdefault(_p,[]).extend(_ss)
  def _groups(ees):
   # MINIMAL-FIRST: symbol-scoped candidates before the full set -- a
   # green full-set that carries extra files' edits is a worse repair than
   # a green single-function retune (the measured tqdm/9 winner is exactly
   # the one-function trio)
   by={}
   for _p,_e in ees:
    _s=None
    for _a,_b in _symran.get(_p,()):
     if _a<=(_e.get("lineno") or 0)<=_b:_s=(_p,_a,_b);break
    by.setdefault(_s or (_p,"file"),[]).append((_p,_e))
   return [v for _,v in sorted(by.items(),key=lambda kv:str(kv[0]))]+[ees]
  for _ratio in sorted(_ratios):
   if not _cleft():break
   for _gi,_ees in enumerate(_groups(_ratios[_ratio])):
    if not _cleft():break
    _cand=_candidate(originals,_ees)
    if _cand is None:continue
    _rr=_run_candidate(repo,originals,_cand,argv,_ctimeout(),env,_runcwd)
    pair_count+=1
    if _rr.get("returncode")==0 and not _rr.get("timed_out"):
     winner=_cand;winner_items=_ees;crossed=True;break
   if winner:break
  single_scores={};tested_single=0
  if winner is None:
   for p,e in items:
    if not _cleft():break
    cand=_candidate(originals,[(p,e)])
    if cand is None:continue
    rr=_run_candidate(repo,originals,cand,argv,_ctimeout(),env,_runcwd);ss=_STRICT._score(rr);single_scores[(p,e["start"],e["end"],e["replacement"])]=(1 if ss is None and rr.get("returncode")!=0 and not rr.get("timed_out") else ss);tested_single+=1
  for i in range(len(items_pairs)) if not winner else range(0):
   if pair_count>=pair_max or not _cleft():break
   for j in range(i+1,len(items_pairs)):
    if pair_count>=pair_max or not _cleft():break
    pair_count+=1;a,b=items_pairs[i],items_pairs[j];cand=_candidate(originals,[a,b])
    if cand is None:continue
    rr=_run_candidate(repo,originals,cand,argv,_ctimeout(),env,_runcwd);ps=_STRICT._score(rr)
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
    rr=_run_candidate(repo,originals,winner,argv,_ctimeout(),env,_runcwd);rs=_STRICT._score(rr);rs=(0 if rr.get("returncode")==0 else (1 if rs is None and not rr.get("timed_out") else rs));replay.append({"returncode":rr.get("returncode"),"failure_score":rs,"timed_out":rr.get("timed_out")});ok=ok and rr.get("returncode")==0 and rs==0
   if not ok:winner=None;winner_items=None
  patches=[]
  if winner:
   for p,t in sorted(winner.items(),key=lambda x:_rel(repo,x[0])):patches.append({"source_path":_rel(repo,p),"original_sha256":_sha(originals[p]),"candidate_sha256":_sha(t.encode()),"unified_diff":_diff(repo,p,originals[p],t)})
  restored=all(p.read_bytes()==b for p,b in originals.items())
  result={"schema":SCHEMA,"status":"PASS__NONMONOTONIC_COUPLED_PAIR_REPAIR_FOUND" if winner else "OPEN__NO_VERIFIED_REPAIR_IN_STRICT_OR_COUPLED_BOUNDS","pass":winner is not None,"route":"COUPLED_PAIR" if winner else "NONE","baseline_failure_score":score,"strict_result_status":strict.get("status"),"localization_candidates":[{"path":r["rel"],"score":r["score"],"reasons":r["reasons"],"symbols":r["symbols"]} for r in loc],"single_candidates_tested":tested_single,"pair_candidates_tested":pair_count,"exec_evidence":exec_evidence_row,"crossed_nonmonotonic_valley":crossed if winner else False,"verification_replays":replay,"patches":patches,"source_restored":restored,"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_UNIVERSAL_SOFTWARE_REPAIR_COMPLETENESS","NO_ARBITRARY_EDIT_BASIS_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_HIDDEN_REQUIREMENTS_OR_GENERAL_MERGEABILITY_PROOF","NO_CLAIM_LOCALIZATION_IS_COMPLETE_SEMANTIC_CAUSALITY","NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
 if not result.get("source_restored"):raise RepairLoopError("SOURCE_RESTORATION_FAILED")
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");result["output_path"]=_rel(repo,out);result["output_sha256"]=_sha(out.read_bytes());result["output_verified"]=True;return result
