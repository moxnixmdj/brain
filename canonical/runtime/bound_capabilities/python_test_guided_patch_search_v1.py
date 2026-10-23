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

def _run_tests(root: pathlib.Path, argv: list[str], timeout_s: int,
               extra_env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Run the test argv and report the outcome.

    ``extra_env`` is merged over the inherited environment. It exists because the bound executor
    calls every adapter with the REPOSITORY ROOT as ``root``, and the subprocess inherits that as
    its working directory. A test that imports the module under repair - which is how ordinary
    Python test suites are written - then dies with ModuleNotFoundError instead of reaching its
    assertion. Measured: for ``def add(a, b): return a - b`` with ``assertEqual(add(2, 3), 5)``,
    cwd at the repository root gives ``errors=1`` (No module named 'calc') and cwd at the source
    directory gives ``failures=1`` (-1 != 5). Both score 1, so no edit to the source can ever
    strictly improve the metric and the repair loop reports OPEN__NO_STRICTLY_IMPROVING_CANDIDATE
    for every bug. The fix is to put the source directory on PYTHONPATH, which makes the module
    importable without changing the working directory the caller chose.
    """
    if not argv or any(not isinstance(x,str) or not x for x in argv):
        raise PatchSearchError("TEST_ARGV_INVALID")
    exe=pathlib.Path(argv[0]).name.lower()
    allowed={pathlib.Path(sys.executable).name.lower(),"python","python3","py"}
    if exe not in allowed:
        raise PatchSearchError("TEST_EXECUTABLE_NOT_PYTHON")
    started=time.monotonic()
    try:
        env=None if not extra_env else {**os.environ,**{k:str(v) for k,v in extra_env.items()}}
        proc=subprocess.run(argv,cwd=root,text=True,capture_output=True,timeout=timeout_s,env=env)
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

"""Child-side source injected into every traced suite execution.

runpy.run_path(..., run_name="__main__") only executes the tests when the file carries that guard.
34% of the unittest files in this repository (695 of 2019, measured) do not, because they are meant
to be collected by a runner. For those the traced child produced no failures at all, so the caller
raised NO_FAILING_TEST and the whole localization-and-repair chain was dead on a third of the corpus.

Loading the module and running the collected suite works for both shapes, and the first failure is
re-raised with its original traceback so the caller can still rank the lines that actually executed.
The suite is run through unittest.TextTestRunner so the child still prints the standard summary and
FAIL:/ERROR: lines, which is what the repair loops parse to score a baseline; the first failure is
then re-raised so a tracing caller can still rank the lines that executed. Files that are not
unittest suites fall back to runpy, so nothing that worked before changes.
"""
SUITE_RUNNER = """import importlib.util,unittest
def _brain_run_suite(target):
 import runpy,sys
 spec=importlib.util.spec_from_file_location("__brain_suite__",str(target))
 mod=importlib.util.module_from_spec(spec);sys.modules["__brain_suite__"]=mod
 spec.loader.exec_module(mod)
 suite=unittest.TestLoader().loadTestsFromModule(mod)
 if suite.countTestCases()==0:
  runpy.run_path(str(target),run_name="__main__");return
 class _R(unittest.TestResult):
  def __init__(self,*a,**k):unittest.TestResult.__init__(self);self.err=None
  def addFailure(self,test,err):unittest.TestResult.addFailure(self,test,err);self.err=err
  def addError(self,test,err):unittest.TestResult.addError(self,test,err);self.err=err
 res=unittest.TextTestRunner(stream=sys.stderr,resultclass=_R).run(suite)
 if not res.wasSuccessful():
  if res.err:raise res.err[1].with_traceback(res.err[2])
  raise AssertionError("SUITE_FAILED_WITHOUT_EXCEPTION_INFO")
"""



SUITE_ENTRY = (
    "import pathlib,sys\n"
    "_errs=[]\n"
    "for _t in sys.argv[1:]:\n"
    " try:_brain_run_suite(pathlib.Path(_t).resolve())\n"
    " except BaseException as _e:_errs.append(_e)\n"
    "if _errs:raise _errs[0]\n"
)


def suite_argv(executable: Any, *targets: Any) -> list[str]:
    """A command line that runs suites through the loader instead of executing the files.

    Running a test file as a script only starts the tests when the file carries a __main__ guard, and
    34% of the unittest files in this repository (695 of 2019, measured) do not, because they are
    written to be collected by a runner. Such a run executes nothing and exits 0, which a repair loop
    reads as BASELINE_ALREADY_PASSES - a false "already passes" for a program that fails its own test.
    Delegating to SUITE_RUNNER collects the tests the way a real runner does and falls back to runpy
    for files that are not unittest suites, so the shape of the file stops deciding whether a
    capability can see its failures.

    Every suite named is run and the first failure is re-raised, so a baseline over several files
    fails if any one of them fails, which is what a repair loop needs.
    """
    return [str(executable), "-c", SUITE_RUNNER + SUITE_ENTRY] + [str(x) for x in targets]


def _source_env(*paths: Any) -> dict[str, str]:
    """PYTHONPATH extended with the directories holding the code under repair.

    A test suite normally imports the module it tests. The bound executor calls every adapter
    with the REPOSITORY ROOT as ``root`` and the subprocess inherits that as its working
    directory, so a sibling ``import calc`` dies with ModuleNotFoundError before any assertion
    runs - and then the baseline and every candidate score identically, so a search that only
    accepts a STRICT improvement reports no candidate for any bug. Adding the source directory to
    PYTHONPATH makes the module importable without changing the working directory the caller
    chose, so no other caller's relative paths change meaning.
    """
    dirs: list[str] = []
    for raw in paths:
        q = pathlib.Path(str(raw))
        d = q if q.is_dir() else q.parent
        if str(d) not in dirs:
            dirs.append(str(d))
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        dirs.append(existing)
    return {"PYTHONPATH": os.pathsep.join(dirs)}


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
        argv=suite_argv(sys.executable,*tests)
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
    env=_source_env(source,*tests)
    baseline=_run_tests(repo,argv,timeout_s,env)
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
            result=_run_tests(repo,argv,timeout_s,env)
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
                    rr=_run_tests(repo,argv,timeout_s,env)
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
