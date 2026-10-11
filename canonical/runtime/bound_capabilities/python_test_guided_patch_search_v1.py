#!/usr/bin/env python3
"""Deterministic bounded test-guided Python patch search.

Candidate-only search over one repository-local Python source file. The runtime:
- requires an isolated writable workspace,
- records exact source/test bytes,
- requires the baseline test command to fail,
- enumerates one-node AST mutations plus literal substitutions mined from tests,
- executes the test command for each candidate,
- restores original source bytes after every trial,
- replays the winning candidate twice before emitting a unified diff,
- never leaves the source modified.

No model calls, network calls, package installation, or canonical source writes.
"""
from __future__ import annotations
import ast, difflib, hashlib, importlib.util, json, os, pathlib, subprocess, sys, time
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_TEST_GUIDED_PATCH_SEARCH_V1"

class PatchSearchError(RuntimeError): pass

def _safe_file(root: pathlib.Path, raw: Any, *, suffix: str|None=None) -> pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents or not p.is_file() or p.is_symlink():
        raise PatchSearchError("PATH_INVALID:"+str(raw))
    if suffix and p.suffix!=suffix:
        raise PatchSearchError("PATH_SUFFIX_INVALID:"+str(raw))
    return p

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _run_tests(root: pathlib.Path, argv: list[str], timeout_s: int) -> dict[str, Any]:
    if not argv or any(not isinstance(x,str) or not x for x in argv):
        raise PatchSearchError("TEST_ARGV_INVALID")
    exe=pathlib.Path(argv[0]).name.lower()
    allowed={pathlib.Path(sys.executable).name.lower(),"python","python3","py"}
    if exe not in allowed:
        raise PatchSearchError("TEST_EXECUTABLE_NOT_PYTHON")
    started=time.monotonic()
    try:
        proc=subprocess.run(argv,cwd=root,text=True,capture_output=True,timeout=timeout_s)
        return {
            "returncode":proc.returncode,
            "stdout":proc.stdout or "",
            "stderr":proc.stderr or "",
            "elapsed_s":round(time.monotonic()-started,6),
            "timed_out":False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode":None,
            "stdout":exc.stdout or "",
            "stderr":exc.stderr or "",
            "elapsed_s":round(time.monotonic()-started,6),
            "timed_out":True,
        }

def _test_literals(paths: Iterable[pathlib.Path]) -> tuple[list[Any], list[str]]:
    nums=set()
    strings=set()
    for path in paths:
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant):
                value=node.value
                if isinstance(value,bool) or value is None:
                    continue
                if isinstance(value,(int,float)) and not isinstance(value,bool):
                    if isinstance(value,float) and not (value==value and abs(value)!=float("inf")):
                        continue
                    nums.add(value)
                elif isinstance(value,str) and 0 < len(value) <= 120:
                    strings.add(value)
    return sorted(nums,key=lambda x:(float(x),repr(x))), sorted(strings)

_COMPARE_SWAPS={
    ast.Eq:ast.NotEq, ast.NotEq:ast.Eq,
    ast.Lt:ast.LtE, ast.LtE:ast.Lt,
    ast.Gt:ast.GtE, ast.GtE:ast.Gt,
    ast.Is:ast.IsNot, ast.IsNot:ast.Is,
    ast.In:ast.NotIn, ast.NotIn:ast.In,
}
_BINOP_SWAPS={
    ast.Add:[ast.Sub],
    ast.Sub:[ast.Add],
    ast.Mult:[ast.FloorDiv,ast.Div],
    ast.FloorDiv:[ast.Mult,ast.Div],
    ast.Div:[ast.Mult,ast.FloorDiv],
    ast.Mod:[ast.FloorDiv],
}
_BOOLOP_SWAPS={ast.And:ast.Or, ast.Or:ast.And}

def _descriptor(node: ast.AST, kind: str, detail: str) -> dict[str, Any]:
    return {
        "kind":kind,
        "detail":detail,
        "lineno":getattr(node,"lineno",None),
        "col_offset":getattr(node,"col_offset",None),
        "end_lineno":getattr(node,"end_lineno",None),
        "end_col_offset":getattr(node,"end_col_offset",None),
    }

def _locations(tree: ast.AST) -> list[ast.AST]:
    nodes=[n for n in ast.walk(tree) if hasattr(n,"lineno")]
    nodes.sort(key=lambda n:(getattr(n,"lineno",10**9),getattr(n,"col_offset",10**9),type(n).__name__))
    return nodes

def _node_key(node: ast.AST) -> tuple:
    return (
        type(node).__name__,
        getattr(node,"lineno",None),getattr(node,"col_offset",None),
        getattr(node,"end_lineno",None),getattr(node,"end_col_offset",None),
    )

def _candidate_specs(tree: ast.AST, numeric_literals: list[Any], string_literals: list[str]):
    seen=set()
    for node in _locations(tree):
        key=_node_key(node)
        if isinstance(node,ast.Compare) and len(node.ops)==1:
            typ=type(node.ops[0])
            newtyp=_COMPARE_SWAPS.get(typ)
            if newtyp:
                sig=(key,"compare",newtyp.__name__)
                if sig not in seen:
                    seen.add(sig)
                    yield key, _descriptor(node,"COMPARE_SWAP",typ.__name__+"->"+newtyp.__name__), (
                        lambda n,newtyp=newtyp: ast.Compare(left=n.left,ops=[newtyp()],comparators=n.comparators)
                    )
        if isinstance(node,ast.BoolOp):
            newtyp=_BOOLOP_SWAPS.get(type(node.op))
            if newtyp:
                sig=(key,"bool",newtyp.__name__)
                if sig not in seen:
                    seen.add(sig)
                    yield key,_descriptor(node,"BOOL_SWAP",type(node.op).__name__+"->"+newtyp.__name__),(
                        lambda n,newtyp=newtyp: ast.BoolOp(op=newtyp(),values=n.values)
                    )
        if isinstance(node,ast.BinOp):
            for newtyp in _BINOP_SWAPS.get(type(node.op),[]):
                sig=(key,"bin",newtyp.__name__)
                if sig in seen: continue
                seen.add(sig)
                yield key,_descriptor(node,"BINOP_SWAP",type(node.op).__name__+"->"+newtyp.__name__),(
                    lambda n,newtyp=newtyp: ast.BinOp(left=n.left,op=newtyp(),right=n.right)
                )
        if isinstance(node,ast.Constant):
            value=node.value
            replacements=[]
            if isinstance(value,bool):
                replacements=[not value]
            elif isinstance(value,(int,float)) and not isinstance(value,bool):
                base=[0,1,-1]
                if isinstance(value,int):
                    base += [value-1,value+1]
                replacements=base+numeric_literals
            elif isinstance(value,str):
                replacements=string_literals
            uniq=[]
            for rep in replacements:
                if rep==value or type(rep) is not type(value) and isinstance(value,bool):
                    continue
                if isinstance(value,int) and isinstance(rep,float) and not float(rep).is_integer():
                    continue
                if isinstance(value,int) and isinstance(rep,float):
                    rep=int(rep)
                if rep not in uniq:
                    uniq.append(rep)
            for rep in uniq[:64]:
                sig=(key,"const",repr(rep))
                if sig in seen: continue
                seen.add(sig)
                yield key,_descriptor(node,"CONSTANT_REPLACE",repr(value)+"->"+repr(rep)),(
                    lambda n,rep=rep: ast.Constant(value=rep)
                )
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.Not):
            sig=(key,"dropnot")
            if sig not in seen:
                seen.add(sig)
                yield key,_descriptor(node,"DROP_NOT","not X -> X"),(lambda n:n.operand)
        if isinstance(node,(ast.If,ast.While,ast.Assert)) and hasattr(node,"test"):
            test=node.test
            tkey=_node_key(test)
            sig=(tkey,"addnot")
            if sig not in seen and not isinstance(test,ast.UnaryOp):
                seen.add(sig)
                yield tkey,_descriptor(test,"ADD_NOT","condition -> not condition"),(
                    lambda n: ast.UnaryOp(op=ast.Not(),operand=n)
                )

def _byte_offset(lines: list[bytes], lineno: int, col: int) -> int:
    return sum(len(x) for x in lines[:lineno-1]) + col

def _render_candidate(source_text: str, key, replacer) -> str|None:
    tree=ast.parse(source_text)
    target=None
    for node in ast.walk(tree):
        if _node_key(node)==key:
            target=node
            break
    if target is None:
        return None
    if None in (
        getattr(target,"lineno",None),getattr(target,"col_offset",None),
        getattr(target,"end_lineno",None),getattr(target,"end_col_offset",None)
    ):
        return None
    replacement=replacer(target)
    ast.fix_missing_locations(replacement)
    replacement_text=ast.unparse(replacement)
    raw=source_text.encode("utf-8")
    lines=raw.splitlines(keepends=True)
    start=_byte_offset(lines,target.lineno,target.col_offset)
    end=_byte_offset(lines,target.end_lineno,target.end_col_offset)
    candidate=raw[:start]+replacement_text.encode("utf-8")+raw[end:]
    return candidate.decode("utf-8")

def _purge_source_bytecode(source: pathlib.Path) -> None:
    try:
        cache=pathlib.Path(importlib.util.cache_from_source(str(source)))
    except (NotImplementedError, ValueError):
        return
    try:
        cache.unlink()
    except FileNotFoundError:
        pass

def _diff(rel: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(True),after.splitlines(True),
        fromfile="a/"+rel,tofile="b/"+rel
    ))

def run(args: Mapping[str, Any], root: str|os.PathLike[str]) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping):
        raise PatchSearchError("ARGS_NOT_OBJECT")
    source=_safe_file(repo,args.get("source_path"),suffix=".py")
    tests_raw=args.get("test_paths") or []
    if not isinstance(tests_raw,list) or not tests_raw:
        raise PatchSearchError("TEST_PATHS_REQUIRED")
    tests=[_safe_file(repo,x,suffix=".py") for x in tests_raw]
    argv=args.get("test_argv")
    if argv is None:
        argv=[sys.executable]+[str(p.relative_to(repo)) for p in tests]
    if not isinstance(argv,list):
        raise PatchSearchError("TEST_ARGV_INVALID")
    argv=[str(x) for x in argv]
    timeout_s=max(1,min(int(args.get("timeout_s",60)),300))
    max_candidates=max(1,min(int(args.get("max_candidates",2000)),20000))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise PatchSearchError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    original_bytes=source.read_bytes()
    try:
        source_text=original_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchSearchError("SOURCE_NOT_UTF8") from exc
    baseline=_run_tests(repo,argv,timeout_s)
    if baseline["returncode"]==0:
        raise PatchSearchError("BASELINE_ALREADY_PASSES")
    if baseline["timed_out"]:
        raise PatchSearchError("BASELINE_TIMEOUT")
    nums,strings=_test_literals(tests)
    tree=ast.parse(source_text,filename=str(source))
    attempts=[]
    winner=None
    tested=0
    try:
        for key,desc,replacer in _candidate_specs(tree,nums,strings):
            if tested>=max_candidates:
                break
            candidate=_render_candidate(source_text,key,replacer)
            if candidate is None or candidate==source_text:
                continue
            tested+=1
            source.write_text(candidate,encoding="utf-8")
            _purge_source_bytecode(source)
            result=_run_tests(repo,argv,timeout_s)
            source.write_bytes(original_bytes)
            _purge_source_bytecode(source)
            attempts.append({
                "index":tested,
                "mutation":desc,
                "candidate_sha256":_sha(candidate.encode("utf-8")),
                "returncode":result["returncode"],
                "timed_out":result["timed_out"],
                "elapsed_s":result["elapsed_s"],
            })
            if result["returncode"]==0 and not result["timed_out"]:
                replay=[]
                ok=True
                for _ in range(2):
                    source.write_text(candidate,encoding="utf-8")
                    _purge_source_bytecode(source)
                    rr=_run_tests(repo,argv,timeout_s)
                    source.write_bytes(original_bytes)
                    _purge_source_bytecode(source)
                    replay.append({
                        "returncode":rr["returncode"],
                        "timed_out":rr["timed_out"],
                        "elapsed_s":rr["elapsed_s"],
                    })
                    ok=ok and rr["returncode"]==0 and not rr["timed_out"]
                if ok:
                    winner=(candidate,desc,replay)
                    break
    finally:
        source.write_bytes(original_bytes)
        _purge_source_bytecode(source)
    rel=str(source.relative_to(repo)).replace("\\","/")
    result={
        "schema":SCHEMA,
        "status":"PASS__VERIFIED_CANDIDATE_PATCH_FOUND" if winner else "OPEN__NO_VERIFIED_CANDIDATE_IN_BOUNDED_SEARCH",
        "pass":winner is not None,
        "source_path":rel,
        "source_sha256":_sha(original_bytes),
        "test_paths":[str(p.relative_to(repo)).replace("\\","/") for p in tests],
        "test_sha256":{str(p.relative_to(repo)).replace("\\","/"):_sha(p.read_bytes()) for p in tests},
        "baseline_returncode":baseline["returncode"],
        "tested_candidate_count":tested,
        "max_candidates":max_candidates,
        "candidate_generator":"DETERMINISTIC_SINGLE_AST_MUTATION_PLUS_TEST_LITERAL_SUBSTITUTION",
        "model_dependency_count":0,
        "external_capability_provider_count":0,
        "incremental_spend_usd":0,
        "source_restored":source.read_bytes()==original_bytes,
        "attempts":attempts,
        "hard_nonclaims":[
            "NO_UNIVERSAL_PATCH_SEARCH_COMPLETENESS",
            "NO_MULTI_EDIT_COMPLETENESS",
            "NO_NON_PYTHON_SUPPORT",
            "NO_SEMANTIC_CORRECTNESS_BEYOND_BOUND_TEST_ORACLE",
            "NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY",
            "NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"
        ],
    }
    if winner:
        candidate,desc,replay=winner
        patch=_diff(rel,source_text,candidate)
        result.update({
            "winning_mutation":desc,
            "candidate_source_sha256":_sha(candidate.encode("utf-8")),
            "verification_replays":replay,
            "unified_diff":patch,
        })
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(raw)
    result["output_verified"]=True
    return result
