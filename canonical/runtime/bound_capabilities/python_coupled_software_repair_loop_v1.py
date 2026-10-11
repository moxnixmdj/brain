#!/usr/bin/env python3
"""Bounded deterministic Python repair with evidence-guided localization and atomic coupled edits."""
from __future__ import annotations
import ast,difflib,hashlib,importlib.util,json,os,pathlib,re,subprocess,sys,time
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_PYTHON_COUPLED_SOFTWARE_REPAIR_LOOP_V1"
class CoupledRepairError(RuntimeError): pass

def _sha(b): return hashlib.sha256(b).hexdigest()
def _rel(repo,p): return str(p.relative_to(repo)).replace("\\","/")
def _safe_dir(repo,raw):
    p=(repo/str(raw or "")).resolve()
    if p!=repo and repo not in p.parents: raise CoupledRepairError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink(): raise CoupledRepairError("DIRECTORY_INVALID")
    return p
def _safe_file(repo,raw):
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py":
        raise CoupledRepairError("FILE_INVALID")
    return p
def _purge(p):
    try: c=pathlib.Path(importlib.util.cache_from_source(str(p)))
    except (NotImplementedError,ValueError): return
    try: c.unlink()
    except FileNotFoundError: pass
def _purge_many(paths):
    for p in paths: _purge(p)
def _run(repo,argv,timeout):
    if not argv or any(not isinstance(x,str) or not x for x in argv): raise CoupledRepairError("TEST_ARGV_INVALID")
    exe=pathlib.Path(argv[0]).name.lower()
    allowed={pathlib.Path(sys.executable).name.lower(),"python","python3","py"}
    if exe not in allowed: raise CoupledRepairError("TEST_EXECUTABLE_NOT_PYTHON")
    t=time.monotonic()
    try:
        q=subprocess.run(argv,cwd=repo,text=True,capture_output=True,timeout=timeout)
        return {"returncode":q.returncode,"stdout":q.stdout or "","stderr":q.stderr or "","timed_out":False,"elapsed_s":round(time.monotonic()-t,6)}
    except subprocess.TimeoutExpired as e:
        return {"returncode":None,"stdout":e.stdout or "","stderr":e.stderr or "","timed_out":True,"elapsed_s":round(time.monotonic()-t,6)}
def _text(r): return str(r.get("stdout") or "")+"\n"+str(r.get("stderr") or "")
def _score(r):
    if r.get("timed_out"): return None
    if r.get("returncode")==0: return 0
    t=_text(r)
    m=re.search(r"FAILED\s*\(([^)]*)\)",t)
    if m:
        n=sum(int(v) for _,v in re.findall(r"(failures|errors)=(\d+)",m.group(1)))
        if n:return n
    n=len(re.findall(r"(?m)^(?:FAIL|ERROR):\s",t))
    return n or None
def _tokens(s):
    return {x.lower() for x in re.findall(r"[A-Za-z_][A-Za-z0-9_]*",str(s or "")) if len(x)>1}
def _test_evidence(tests):
    imported=set();called=set();lits_num=set();lits_str=set()
    for p in tests:
        try: tree=ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except Exception: continue
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                for a in n.names: imported.add(a.name.split(".")[0])
            elif isinstance(n,ast.ImportFrom) and n.module:
                imported.add(n.module.split(".")[0])
                for a in n.names: called.add(a.asname or a.name)
            elif isinstance(n,ast.Call):
                if isinstance(n.func,ast.Name): called.add(n.func.id)
                elif isinstance(n.func,ast.Attribute): called.add(n.func.attr)
            elif isinstance(n,ast.Constant):
                v=n.value
                if isinstance(v,bool) or v is None: continue
                if isinstance(v,(int,float)) and not isinstance(v,bool): lits_num.add(v)
                elif isinstance(v,str) and 0<len(v)<=120: lits_str.add(v)
    return imported,called,sorted(lits_num,key=lambda x:(float(x),repr(x))),sorted(lits_str)
def _symbol_names(path):
    try: tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    except Exception:return set()
    out=set()
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): out.add(n.name)
    return out
def _localize(repo,root,tests,failure,max_files):
    imported,called,_,_=_test_evidence(tests)
    traceback=set()
    for raw in re.findall(r'File "([^"]+\.py)"',failure):
        p=pathlib.Path(raw)
        q=(p if p.is_absolute() else repo/p).resolve()
        if q.is_file(): traceback.add(q)
    fail_tokens=_tokens(failure)
    testset={p.resolve() for p in tests}; rows=[]
    for p in sorted(root.rglob("*.py")):
        q=p.resolve()
        if q in testset or p.name.startswith("test_") or not p.is_file() or p.is_symlink(): continue
        syms=_symbol_names(p); module=p.stem
        score=0; reasons=[]
        if q in traceback: score+=1000;reasons.append("TRACEBACK_PATH")
        if module in imported: score+=300;reasons.append("TEST_IMPORT")
        overlap=sorted(syms & called)
        if overlap: score+=50*len(overlap);reasons.append("CALLED_SYMBOL:"+",".join(overlap))
        mentioned=sorted(s for s in syms if s.lower() in fail_tokens)
        if mentioned: score+=20*len(mentioned);reasons.append("FAILURE_TEXT_SYMBOL:"+",".join(mentioned))
        if module.lower() in fail_tokens: score+=30;reasons.append("FAILURE_TEXT_MODULE")
        rows.append({"path":q,"score":score,"reasons":reasons,"symbols":sorted(syms)})
    rows.sort(key=lambda x:(-x["score"],_rel(repo,x["path"])))
    return rows[:max_files]

_COMPARE={ast.Eq:ast.NotEq,ast.NotEq:ast.Eq,ast.Lt:ast.LtE,ast.LtE:ast.Lt,ast.Gt:ast.GtE,ast.GtE:ast.Gt,ast.Is:ast.IsNot,ast.IsNot:ast.Is,ast.In:ast.NotIn,ast.NotIn:ast.In}
_BIN={ast.Add:[ast.Sub],ast.Sub:[ast.Add],ast.Mult:[ast.FloorDiv,ast.Div],ast.FloorDiv:[ast.Mult,ast.Div],ast.Div:[ast.Mult,ast.FloorDiv],ast.Mod:[ast.FloorDiv]}
_BOOL={ast.And:ast.Or,ast.Or:ast.And}
def _key(n): return (type(n).__name__,getattr(n,"lineno",None),getattr(n,"col_offset",None),getattr(n,"end_lineno",None),getattr(n,"end_col_offset",None))
def _desc(n,k,d): return {"kind":k,"detail":d,"lineno":getattr(n,"lineno",None),"col_offset":getattr(n,"col_offset",None),"end_lineno":getattr(n,"end_lineno",None),"end_col_offset":getattr(n,"end_col_offset",None)}
def _specs(tree,nums,strings):
    seen=set()
    nodes=[n for n in ast.walk(tree) if hasattr(n,"lineno")]
    nodes.sort(key=lambda n:(getattr(n,"lineno",10**9),getattr(n,"col_offset",10**9),type(n).__name__))
    for n in nodes:
        k=_key(n)
        if isinstance(n,ast.Compare) and len(n.ops)==1 and type(n.ops[0]) in _COMPARE:
            nt=_COMPARE[type(n.ops[0])]; sig=(k,"cmp",nt.__name__)
            if sig not in seen:
                seen.add(sig); yield k,_desc(n,"COMPARE_SWAP",type(n.ops[0]).__name__+"->"+nt.__name__),lambda x,nt=nt:ast.Compare(left=x.left,ops=[nt()],comparators=x.comparators)
        if isinstance(n,ast.BoolOp) and type(n.op) in _BOOL:
            nt=_BOOL[type(n.op)];sig=(k,"bool",nt.__name__)
            if sig not in seen:
                seen.add(sig);yield k,_desc(n,"BOOL_SWAP",type(n.op).__name__+"->"+nt.__name__),lambda x,nt=nt:ast.BoolOp(op=nt(),values=x.values)
        if isinstance(n,ast.BinOp):
            for nt in _BIN.get(type(n.op),[]):
                sig=(k,"bin",nt.__name__)
                if sig in seen:continue
                seen.add(sig);yield k,_desc(n,"BINOP_SWAP",type(n.op).__name__+"->"+nt.__name__),lambda x,nt=nt:ast.BinOp(left=x.left,op=nt(),right=x.right)
        if isinstance(n,ast.Constant):
            v=n.value; reps=[]
            if isinstance(v,bool): reps=[not v]
            elif isinstance(v,(int,float)) and not isinstance(v,bool):
                reps=[0,1,-1]+([v-1,v+1] if isinstance(v,int) else [])+list(nums)
            elif isinstance(v,str): reps=list(strings)
            uniq=[]
            for z in reps:
                if z==v:continue
                if isinstance(v,int) and isinstance(z,float):
                    if not z.is_integer():continue
                    z=int(z)
                if z not in uniq:uniq.append(z)
            for z in uniq[:64]:
                sig=(k,"const",repr(z))
                if sig in seen:continue
                seen.add(sig);yield k,_desc(n,"CONSTANT_REPLACE",repr(v)+"->"+repr(z)),lambda x,z=z:ast.Constant(value=z)
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Not):
            sig=(k,"dropnot")
            if sig not in seen:
                seen.add(sig);yield k,_desc(n,"DROP_NOT","not X -> X"),lambda x:x.operand
def _offset(lines,ln,col): return sum(len(x) for x in lines[:ln-1])+col
def _render(text,key,replacer):
    tree=ast.parse(text);target=None
    for n in ast.walk(tree):
        if _key(n)==key:target=n;break
    if target is None:return None
    vals=(getattr(target,"lineno",None),getattr(target,"col_offset",None),getattr(target,"end_lineno",None),getattr(target,"end_col_offset",None))
    if None in vals:return None
    rep=replacer(target);ast.fix_missing_locations(rep);s=ast.unparse(rep)
    raw=text.encode();lines=raw.splitlines(keepends=True)
    a=_offset(lines,target.lineno,target.col_offset);b=_offset(lines,target.end_lineno,target.end_col_offset)
    return (raw[:a]+s.encode()+raw[b:]).decode()
def _candidates(path,tests,limit):
    text=path.read_text(encoding="utf-8");tree=ast.parse(text,filename=str(path))
    _,_,nums,strings=_test_evidence(tests);out=[]
    for key,desc,replacer in _specs(tree,nums,strings):
        cand=_render(text,key,replacer)
        if not cand or cand==text:continue
        out.append({"path":path,"bytes":cand.encode(),"mutation":desc,"sha256":_sha(cand.encode())})
        if len(out)>=limit:break
    return out
def _apply_and_run(repo,edits,argv,timeout,baseline_bytes):
    paths=set()
    try:
        for e in edits:
            p=e["path"];paths.add(p);p.write_bytes(e["bytes"]);_purge(p)
        return _run(repo,argv,timeout)
    finally:
        for p in paths:
            p.write_bytes(baseline_bytes[p]);_purge(p)
def _diff(repo,p,a,b): return "".join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile="a/"+_rel(repo,p),tofile="b/"+_rel(repo,p)))

def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
    if not isinstance(args,Mapping):raise CoupledRepairError("ARGS_NOT_OBJECT")
    repo=pathlib.Path(root).resolve();src=_safe_dir(repo,args.get("source_root","."))
    tests=[_safe_file(repo,x) for x in (args.get("test_paths") or [])]
    if not tests:raise CoupledRepairError("TEST_PATHS_REQUIRED")
    argv=[str(x) for x in (args.get("test_argv") or [sys.executable]+[_rel(repo,p) for p in tests])]
    timeout=max(1,min(int(args.get("timeout_s",30)),300));roundmax=max(1,min(int(args.get("max_rounds",4)),12))
    maxfiles=max(2,min(int(args.get("max_files",8)),50));per=max(1,min(int(args.get("max_mutations_per_file",30)),500))
    pairmax=max(1,min(int(args.get("max_pairs",1000)),20000));totalmax=max(1,min(int(args.get("max_total_candidates",4000)),50000))
    out=(repo/str(args.get("output_path") or "")).resolve()
    if out==repo or repo not in out.parents:raise CoupledRepairError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    base=_run(repo,argv,timeout);score=_score(base)
    if base.get("timed_out"):raise CoupledRepairError("BASELINE_TIMEOUT")
    if base.get("returncode")==0:raise CoupledRepairError("BASELINE_ALREADY_PASSES")
    if score is None:raise CoupledRepairError("BASELINE_FAILURE_METRIC_UNPARSEABLE")
    originals={};current_bytes={};touched=set();accepted=[];rounds=[];tested=0;final_bytes={};vreplays=[];status="OPEN__NO_COMPLETE_REPAIR_IN_BOUNDED_SEARCH";current=base
    try:
        for ri in range(1,roundmax+1):
            loc=_localize(repo,src,tests,_text(current),maxfiles)
            files=[x["path"] for x in loc]
            for p in files:
                originals.setdefault(p,p.read_bytes());current_bytes[p]=p.read_bytes()
            cands=[]
            for row in loc:
                for c in _candidates(row["path"],tests,per):
                    c["localization_score"]=row["score"];c["localization_reasons"]=row["reasons"];cands.append(c)
            best=None;round_tested=0
            for c in cands:
                if tested>=totalmax:break
                tested+=1;round_tested+=1
                r=_apply_and_run(repo,[c],argv,timeout,current_bytes);s=_score(r)
                if s is not None and s<score:
                    best={"kind":"SINGLE","edits":[c],"score":s};break
            pair_tested=0
            if best is None and tested<totalmax:
                for i,a in enumerate(cands):
                    for b in cands[i+1:]:
                        if a["path"]==b["path"]:continue
                        if pair_tested>=pairmax or tested>=totalmax:break
                        pair_tested+=1;tested+=1;round_tested+=1
                        r=_apply_and_run(repo,[a,b],argv,timeout,current_bytes);s=_score(r)
                        if s is not None and s<score:
                            best={"kind":"ATOMIC_CROSS_FILE_PAIR","edits":[a,b],"score":s};break
                    if best is not None or pair_tested>=pairmax or tested>=totalmax:break
            rounds.append({"round":ri,"failure_score_before":score,"localized_files":[{"path":_rel(repo,x["path"]),"score":x["score"],"reasons":x["reasons"],"symbols":x["symbols"]} for x in loc],"single_candidate_count":len(cands),"pair_candidates_tested":pair_tested,"tested_candidate_count":round_tested,"accepted_kind":None if best is None else best["kind"],"failure_score_after":score if best is None else best["score"]})
            if best is None:
                status="OPEN__NO_IMPROVING_SINGLE_OR_ATOMIC_CROSS_FILE_PAIR";break
            group=[]
            for e in best["edits"]:
                p=e["path"];p.write_bytes(e["bytes"]);_purge(p);current_bytes[p]=e["bytes"];touched.add(p)
                group.append({"source_path":_rel(repo,p),"mutation":e["mutation"],"candidate_sha256":e["sha256"],"localization_score":e["localization_score"],"localization_reasons":e["localization_reasons"]})
            score=best["score"];accepted.append({"round":ri,"kind":best["kind"],"edits":group,"score_after":score})
            _purge_many(current_bytes);current=_run(repo,argv,timeout)
            replay_score=_score(current)
            if replay_score!=score:raise CoupledRepairError("ACCEPTED_GROUP_DID_NOT_REPLAY")
            if score==0:
                status="PASS__BOUNDED_COUPLED_REPAIR_FOUND";break
        if score==0:
            for _ in range(2):
                _purge_many(current_bytes);rr=_run(repo,argv,timeout);rs=_score(rr);vreplays.append({"returncode":rr.get("returncode"),"timed_out":rr.get("timed_out"),"failure_score":rs})
                if rr.get("returncode")!=0 or rs!=0:raise CoupledRepairError("FINAL_REPLAY_FAILED")
            final_bytes={p:p.read_bytes() for p in touched}
    finally:
        for p,b in originals.items():p.write_bytes(b)
        _purge_many(originals)
    patches=[{"source_path":_rel(repo,p),"original_sha256":_sha(originals[p]),"candidate_sha256":_sha(final_bytes[p]),"unified_diff":_diff(repo,p,originals[p],final_bytes[p])} for p in sorted(final_bytes,key=lambda q:_rel(repo,q))]
    result={"schema":SCHEMA,"status":status,"pass":status.startswith("PASS__"),"baseline_failure_score":_score(base),"rounds":rounds,"accepted_groups":accepted,"accepted_group_count":len(accepted),"tested_candidate_count":tested,"final_verification_replays":vreplays,"patches":patches,"source_restored":all(p.read_bytes()==b for p,b in originals.items()),"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_GENERAL_SEMANTIC_FAULT_LOCALIZATION","NO_SAME_FILE_COUPLED_EDIT_COMPLETENESS","NO_ARBITRARY_EDIT_BASIS_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_HIDDEN_REQUIREMENTS_OR_GENERAL_MERGEABILITY_PROOF","NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");result["output_path"]=_rel(repo,out);result["output_sha256"]=_sha(out.read_bytes());result["output_verified"]=True;return result
