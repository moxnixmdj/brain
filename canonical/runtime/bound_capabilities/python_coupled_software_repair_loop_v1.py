from __future__ import annotations
import ast, difflib, hashlib, json, os, pathlib, re, subprocess, sys
from typing import Any, Mapping, NamedTuple

SCHEMA = "PROJECT_BRAIN_PYTHON_COUPLED_SOFTWARE_REPAIR_LOOP_V1"

class RepairLoopError(RuntimeError):
    pass

_COMPARE_SWAPS = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
}
_BINOP_SWAPS = {ast.Add: [ast.Sub, ast.Mult], ast.Sub: [ast.Add], ast.Mult: [ast.Add]}
_BOOLOP_SWAPS = {ast.And: ast.Or, ast.Or: ast.And}

class Variant(NamedTuple):
    source: pathlib.Path
    text: str
    mutation: str

def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _rel(repo: pathlib.Path, p: pathlib.Path) -> str:
    return str(p.relative_to(repo)).replace("\\", "/")

def _safe_dir(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RepairLoopError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink():
        raise RepairLoopError("DIRECTORY_INVALID")
    return p

def _safe_file(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p == repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix != ".py":
        raise RepairLoopError("FILE_INVALID")
    return p

def _run_tests(repo: pathlib.Path, argv: list[str], timeout: int) -> dict[str, Any]:
    try:
        cp=subprocess.run(argv,cwd=repo,text=True,capture_output=True,timeout=timeout)
        return {"returncode":cp.returncode,"stdout":cp.stdout,"stderr":cp.stderr,"timed_out":False}
    except subprocess.TimeoutExpired as exc:
        return {"returncode":None,"stdout":exc.stdout or "","stderr":exc.stderr or "","timed_out":True}

def _text(r: Mapping[str, Any]) -> str:
    return str(r.get("stdout") or "")+"\n"+str(r.get("stderr") or "")

def _failure_score(r: Mapping[str, Any]) -> int | None:
    if r.get("timed_out"):
        return None
    if r.get("returncode") == 0:
        return 0
    t=_text(r)
    m=re.search(r"FAILED\s*\(([^)]*)\)",t)
    if m:
        n=sum(int(v) for _,v in re.findall(r"(failures|errors)=(\d+)",m.group(1)))
        if n:
            return n
    n=len(re.findall(r"(?m)^(?:FAIL|ERROR):\s",t))
    return n or None

def _purge(paths) -> None:
    import importlib.util
    for p in paths:
        try:
            pathlib.Path(importlib.util.cache_from_source(str(p))).unlink(missing_ok=True)
        except Exception:
            pass

def _test_literals(tests: list[pathlib.Path]) -> tuple[list[Any], list[str]]:
    nums=[]; strings=[]
    for test in tests:
        try:
            tree=ast.parse(test.read_text(encoding="utf-8"))
        except Exception:
            continue
        for n in ast.walk(tree):
            if not isinstance(n,ast.Constant):
                continue
            v=n.value
            if isinstance(v,(int,float)) and not isinstance(v,bool) and v not in nums:
                nums.append(v)
            elif isinstance(v,str) and v not in strings:
                strings.append(v)
    return nums,strings

def _mutation_specs(text: str, nums: list[Any], strings: list[str]):
    tree=ast.parse(text)
    nodes=list(ast.walk(tree))
    for idx,node in enumerate(nodes):
        if isinstance(node,ast.Compare) and len(node.ops)==1 and type(node.ops[0]) in _COMPARE_SWAPS:
            nt=_COMPARE_SWAPS[type(node.ops[0])]
            yield idx, f"COMPARE_SWAP:{type(node.ops[0]).__name__}->{nt.__name__}", ("compare",nt)
        if isinstance(node,ast.BoolOp) and type(node.op) in _BOOLOP_SWAPS:
            nt=_BOOLOP_SWAPS[type(node.op)]
            yield idx, f"BOOL_SWAP:{type(node.op).__name__}->{nt.__name__}", ("bool",nt)
        if isinstance(node,ast.BinOp) and type(node.op) in _BINOP_SWAPS:
            for nt in _BINOP_SWAPS[type(node.op)]:
                yield idx, f"BINOP_SWAP:{type(node.op).__name__}->{nt.__name__}", ("bin",nt)
        if isinstance(node,ast.Constant):
            value=node.value
            reps=[]
            if isinstance(value,bool):
                reps=[not value]
            elif isinstance(value,(int,float)) and not isinstance(value,bool):
                reps=[]
                if isinstance(value,int): reps += [value+1,value-1]
                reps += nums
                reps += [0,1,-1]
            elif isinstance(value,str):
                reps += strings
            seen=[]
            for rep in reps:
                if rep == value or rep in seen: continue
                if isinstance(value,int) and isinstance(rep,float):
                    if not rep.is_integer(): continue
                    rep=int(rep)
                if isinstance(value,bool) and not isinstance(rep,bool): continue
                seen.append(rep)
                yield idx, f"CONSTANT_REPLACE:{value!r}->{rep!r}", ("const",rep)
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.Not):
            yield idx, "DROP_NOT", ("dropnot",None)
        if isinstance(node,(ast.If,ast.While,ast.Assert)) and not isinstance(node.test,ast.UnaryOp):
            try: tidx=nodes.index(node.test)
            except ValueError: tidx=-1
            if tidx >= 0:
                yield tidx, "ADD_NOT", ("addnot",None)

def _replace_node(tree: ast.AST, target: ast.AST, replacement: ast.AST) -> bool:
    for parent in ast.walk(tree):
        for field,val in ast.iter_fields(parent):
            if val is target:
                setattr(parent,field,replacement); return True
            if isinstance(val,list):
                for i,x in enumerate(val):
                    if x is target:
                        val[i]=replacement; return True
    return False

def _render(text: str, index: int, spec) -> str | None:
    tree=ast.parse(text)
    nodes=list(ast.walk(tree))
    if index < 0 or index >= len(nodes): return None
    target=nodes[index]; kind,arg=spec
    if kind=="compare" and isinstance(target,ast.Compare) and len(target.ops)==1:
        target.ops=[arg()]
    elif kind=="bool" and isinstance(target,ast.BoolOp): target.op=arg()
    elif kind=="bin" and isinstance(target,ast.BinOp): target.op=arg()
    elif kind=="const" and isinstance(target,ast.Constant): target.value=arg
    elif kind=="dropnot" and isinstance(target,ast.UnaryOp) and isinstance(target.op,ast.Not):
        if not _replace_node(tree,target,target.operand): return None
    elif kind=="addnot":
        if not _replace_node(tree,target,ast.UnaryOp(op=ast.Not(),operand=target)): return None
    else: return None
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+"\n"

def _variants(source: pathlib.Path, tests: list[pathlib.Path], limit: int) -> list[Variant]:
    text=source.read_text(encoding="utf-8")
    nums,strings=_test_literals(tests)
    out=[]; seen=set()
    for idx,desc,spec in _mutation_specs(text,nums,strings):
        cand=_render(text,idx,spec)
        if not cand or cand==text or cand in seen: continue
        seen.add(cand); out.append(Variant(source=source,text=cand,mutation=desc))
        if len(out)>=limit: break
    return out

def _module_file(root: pathlib.Path, module: str) -> pathlib.Path | None:
    rel=pathlib.Path(*module.split("."))
    for p in (root/rel.with_suffix(".py"),root/rel/"__init__.py"):
        if p.is_file(): return p.resolve()
    return None

def _rank_sources(repo: pathlib.Path, source_root: pathlib.Path, tests: list[pathlib.Path], failure: str):
    testset={p.resolve() for p in tests}; scores={}; reasons={}; symbols={}
    def add(p,score,reason,symbol=None):
        try:q=p.resolve()
        except Exception:return
        if q in testset or not q.is_file() or q.suffix!=".py" or q.name.startswith("test_"): return
        if q!=source_root and source_root not in q.parents: return
        scores[q]=scores.get(q,0)+score; reasons.setdefault(q,set()).add(reason)
        if symbol: symbols.setdefault(q,set()).add(symbol)
    for raw in re.findall(r'File "([^"]+\.py)"',failure):
        p=pathlib.Path(raw); add(p if p.is_absolute() else repo/p,1000,"TRACEBACK_FRAME")
    referenced=set()
    for test in tests:
        try: tree=ast.parse(test.read_text(encoding="utf-8"))
        except Exception: continue
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                for a in n.names:
                    p=_module_file(source_root,a.name)
                    if p: add(p,300,"TEST_IMPORT_MODULE")
            elif isinstance(n,ast.ImportFrom) and n.module:
                p=_module_file(source_root,n.module)
                if p:
                    add(p,400,"TEST_IMPORT_FROM")
                    for a in n.names:
                        if a.name!="*": referenced.add(a.name); add(p,80,"TEST_REFERENCED_SYMBOL",a.name)
    for p in sorted(source_root.rglob("*.py")):
        if p.resolve() in testset or p.name.startswith("test_"): continue
        try: tree=ast.parse(p.read_text(encoding="utf-8"))
        except Exception: continue
        defs={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
        overlap=defs & referenced
        if overlap:
            add(p,120*len(overlap),"SYMBOL_DEFINITION_OVERLAP")
            for s in overlap: symbols.setdefault(p,set()).add(s)
        add(p,1,"BOUNDED_FALLBACK")
    rows=[]
    for p in scores:
        rows.append({"source_path":_rel(repo,p),"score":scores[p],"reasons":sorted(reasons.get(p,set())),"symbols":sorted(symbols.get(p,set())),"_path":p})
    rows.sort(key=lambda r:(-r["score"],r["source_path"])); return rows

def _diff(repo,p,a,b):
    return "".join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile="a/"+_rel(repo,p),tofile="b/"+_rel(repo,p)))

def run(args: Mapping[str,Any], root: str|os.PathLike[str]) -> dict[str,Any]:
    if not isinstance(args,Mapping): raise RepairLoopError("ARGS_NOT_OBJECT")
    repo=pathlib.Path(root).resolve(); source_root=_safe_dir(repo,args.get("source_root","."))
    tests=[_safe_file(repo,x) for x in (args.get("test_paths") or [])]
    if not tests: raise RepairLoopError("TEST_PATHS_REQUIRED")
    argv=[str(x) for x in (args.get("test_argv") or [sys.executable]+[_rel(repo,p) for p in tests])]
    timeout=max(1,min(int(args.get("timeout_s",30)),300)); max_rounds=max(1,min(int(args.get("max_rounds",6)),20)); max_files=max(1,min(int(args.get("max_files",10)),50)); variants_per_file=max(1,min(int(args.get("max_variants_per_file",24)),200)); max_single=max(1,min(int(args.get("max_single_candidates",400)),5000)); max_pairs=max(1,min(int(args.get("max_pair_candidates",1200)),20000))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents: raise RepairLoopError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    baseline=_run_tests(repo,argv,timeout); score=_failure_score(baseline)
    if baseline.get("timed_out"): raise RepairLoopError("BASELINE_TIMEOUT")
    if baseline.get("returncode")==0: raise RepairLoopError("BASELINE_ALREADY_PASSES")
    if score is None: raise RepairLoopError("BASELINE_FAILURE_METRIC_UNPARSEABLE")
    ranked=_rank_sources(repo,source_root,tests,_text(baseline))[:max_files]; sources=[r["_path"] for r in ranked]
    if not sources: raise RepairLoopError("NO_LOCALIZED_SOURCE_FILES")
    originals={p:p.read_bytes() for p in sources}; touched=set(); accepted=[]; pair_events=[]; single_tested=0; pair_tested=0; current=baseline; status="OPEN__NO_COMPLETE_REPAIR_IN_BOUNDED_SEARCH"; final_bytes={}; replays=[]
    try:
        for round_id in range(1,max_rounds+1):
            current_score=score; all_variants={p:_variants(p,tests,variants_per_file) for p in sources}; chosen=None
            for p in sources:
                cur=p.read_bytes()
                for v in all_variants[p]:
                    if single_tested>=max_single: break
                    single_tested+=1; p.write_text(v.text,encoding="utf-8"); _purge(touched|{p}); rr=_run_tests(repo,argv,timeout); p.write_bytes(cur); _purge(touched|{p}); ns=_failure_score(rr)
                    if ns is not None and ns < current_score:
                        chosen=("single",[(p,v)],ns); break
                if chosen or single_tested>=max_single: break
            if chosen is None:
                stop=False
                for i,p1 in enumerate(sources):
                    for p2 in sources[i+1:]:
                        cur1=p1.read_bytes(); cur2=p2.read_bytes()
                        for v1 in all_variants[p1]:
                            for v2 in all_variants[p2]:
                                if pair_tested>=max_pairs: stop=True; break
                                pair_tested+=1; p1.write_text(v1.text,encoding="utf-8"); p2.write_text(v2.text,encoding="utf-8"); _purge(touched|{p1,p2}); rr=_run_tests(repo,argv,timeout); p1.write_bytes(cur1); p2.write_bytes(cur2); _purge(touched|{p1,p2}); ns=_failure_score(rr)
                                if ns is not None and ns < current_score:
                                    chosen=("pair",[(p1,v1),(p2,v2)],ns); stop=True; break
                            if stop: break
                        if stop: break
                    if stop: break
            if chosen is None:
                status="OPEN__NO_STRICT_OR_COUPLED_IMPROVING_CANDIDATE"; break
            kind,edits,ns=chosen; edit_records=[]
            for p,v in edits:
                before=p.read_bytes(); p.write_text(v.text,encoding="utf-8"); touched.add(p); edit_records.append({"source_path":_rel(repo,p),"mutation":v.mutation,"before_sha256":_sha(before),"after_sha256":_sha(p.read_bytes())})
            _purge(touched); current=_run_tests(repo,argv,timeout); replay_score=_failure_score(current)
            if replay_score is None or replay_score != ns or replay_score >= current_score: raise RepairLoopError("ACCEPTED_EDIT_SET_DID_NOT_REPLAY_IMPROVEMENT")
            accepted.append({"round":round_id,"edit_kind":kind,"edit_count":len(edits),"score_before":current_score,"score_after":replay_score,"edits":edit_records})
            if kind=="pair": pair_events.append({"round":round_id,"atomic_pair":True,"score_before":current_score,"score_after":replay_score,"intermediate_single_improvement_required":False})
            score=replay_score
            if score==0: status="PASS__BOUNDED_COUPLED_REPAIR_FOUND"; break
        if score==0:
            for _ in range(2):
                _purge(touched); rr=_run_tests(repo,argv,timeout); rs=_failure_score(rr); replays.append({"returncode":rr.get("returncode"),"timed_out":rr.get("timed_out"),"failure_score":rs})
                if rr.get("returncode")!=0 or rs!=0: raise RepairLoopError("FINAL_REPLAY_FAILED")
            final_bytes={p:p.read_bytes() for p in touched}
    finally:
        for p,b in originals.items(): p.write_bytes(b)
        _purge(originals)
    patches=[{"source_path":_rel(repo,p),"original_sha256":_sha(originals[p]),"candidate_sha256":_sha(final_bytes[p]),"unified_diff":_diff(repo,p,originals[p],final_bytes[p])} for p in sorted(final_bytes,key=lambda q:_rel(repo,q))]
    result={"schema":SCHEMA,"status":status,"pass":status.startswith("PASS__"),"baseline_failure_score":_failure_score(baseline),"localization":[{k:v for k,v in row.items() if k!="_path"} for row in ranked],"accepted_edit_sets":accepted,"accepted_edit_set_count":len(accepted),"coupled_pair_event_count":len(pair_events),"coupled_pair_events":pair_events,"tested_single_candidate_count":single_tested,"tested_pair_candidate_count":pair_tested,"final_verification_replays":replays,"patches":patches,"source_restored":all(p.read_bytes()==b for p,b in originals.items()),"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_GENERAL_SEMANTIC_FAULT_LOCALIZATION_COMPLETENESS","NO_ARBITRARY_SOFTWARE_REPAIR_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_HIDDEN_REQUIREMENTS_OR_MERGEABILITY_PROOF","NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); result["output_path"]=_rel(repo,output); result["output_sha256"]=_sha(output.read_bytes()); result["output_verified"]=True; return result
