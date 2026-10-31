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
import ast, copy, difflib, hashlib, importlib.util, json, os, pathlib, re, subprocess, sys, time
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
               extra_env: Mapping[str, str] | None = None,
               cwd: pathlib.Path | None = None) -> dict[str, Any]:
    # ``cwd`` overrides the subprocess working directory. WORLD-CWD LAW
    # (tqdm/9, measured): pytest-style argv paths are relative to the WORLD
    # root -- running them from the brain repository root exits rc=4
    # (file-or-directory-not-found) and every candidate reads as a PHANTOM
    # red. Suite runs for such suites must execute from the source root.

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
        proc=subprocess.run(argv,cwd=str(cwd) if cwd else root,text=True,capture_output=True,timeout=timeout_s,env=env)
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

def pytest_summary(text: str) -> dict[str, int] | None:
    """Read the final supported pytest summary; this is not attestation."""
    for line in reversed(text.splitlines()):
        summary = line.strip().strip("= ")
        if (re.match(r"^\d+ (?:passed|failed|skipped|xfailed|xpassed|errors?)\b", summary)
                and re.search(r"\bin \d+(?:\.\d+)?s\b", summary)):
            counts = {}
            for n, outcome in re.findall(
                    r"(\d+) (passed|failed|xfailed|xpassed|errors?)(?=,|\s+in\b|$)", summary):
                key = "errors" if outcome in ("error", "errors") else outcome
                counts[key] = counts.get(key, 0) + int(n)
            return counts
    return None


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
    # Add->Mult is load-bearing: the canonical injected-operator defect class
    # is "+ where * belongs" (unit_price(q) * k written as q + k). Without the
    # Add->Mult swap the bounded search never contains the repair, whatever
    # the budget (measured: L3 interprocedural tier 0% before, ladder receipt
    # REPAIR_DEPTH_LADDER_20261029). Pool growth is +1 candidate per Add site.
    ast.Add:[ast.Sub, ast.Mult],
    ast.Sub:[ast.Add],
    ast.Mult:[ast.FloorDiv,ast.Div],
    ast.FloorDiv:[ast.Mult,ast.Div],
    ast.Div:[ast.Mult,ast.FloorDiv],
    ast.Mod:[ast.FloorDiv],
}
_BOOLOP_SWAPS={ast.And:ast.Or, ast.Or:ast.And}

def _descriptor(node: ast.AST, kind: str, detail: str, family: str = "legacy", ratio: Any = None) -> dict[str, Any]:
    # FAMILY TAG (L5 dilution law): every candidate carries its family so
    # consumers can budget families SEPARATELY. Legacy families keep the
    # exact trial budget they always had; the decoded neighborhood family
    # draws from its own small reserve instead of eating legacy slots.
    # RATIO carries the multiplier that produced a neighborhood value so
    # consumers can apply the SAME multiplier across sites simultaneously
    # (the coordinated boundary-retune class: 1000->999.95, 100->99.95,
    # 10->9.995 is ONE logical edit spread over three constants).
    return {
        "kind":kind,
        "family":family,
        "ratio":ratio,
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
            # BOUNDARY NEIGHBORHOOD (L6-decoded spec, receipt REAL_CORPUS_L6
            # round4): a real numeric-boundary bug replaces a threshold by
            # one just BELOW it -- 1000.0->999.95, 100.0->99.95, 10.0->9.995
            # (tqdm format_sizeof). Family: n*0.9995, n*0.99995, n*0.999,
            # plus float-only eps moves. Bounded: <=9 extra candidates per
            # numeric site, only for abs(value)>=2 (0/1 boundaries are the
            # existing {0,1,-1} family's job).
            neighbors=[]
            neighbor_ratio={}
            if isinstance(value,(int,float)) and not isinstance(value,bool) \
                    and abs(value)>=2:
                v=float(value)
                for _m in (0.9995,0.99995,0.999):
                    _c=round(v*_m,6)
                    if _c!=v and _c not in neighbor_ratio:
                        neighbors.append(_c);neighbor_ratio[_c]=_m
                if isinstance(value,float):
                    for _e in (0.005,0.05):
                        for _c in (round(v-_e,6),round(v+_e,6)):
                            if _c!=v and _c not in neighbor_ratio:
                                neighbors.append(_c);neighbor_ratio[_c]=None
            if isinstance(value,bool):
                replacements=[not value]
            elif isinstance(value,(int,float)) and not isinstance(value,bool):
                base=[0,1,-1]
                if isinstance(value,int):
                    base += [value-1,value+1]
                replacements=base+numeric_literals+neighbors
            elif isinstance(value,str):
                replacements=string_literals
            # provenance-tagged: classification by ORIGIN, never by value
            # (999 == 999.0 is True in Python -- value-membership testing
            # against `neighbors` reclassified legacy coerced reps as
            # neighborhood and silently reordered the legacy stream; that
            # was the real L5 regression, caught by the ladder gate).
            uniq=[]
            tagged=[]
            for rep in replacements:
                is_neigh=rep in neighbors
                if rep==value or type(rep) is not type(value) and isinstance(value,bool):
                    continue
                if not is_neigh:
                    # LEGACY PATH -- byte-identical to the pre-neighborhood
                    # grammar so legacy candidates can never be displaced.
                    if isinstance(value,int) and isinstance(rep,float) \
                            and not float(rep).is_integer():
                        continue
                    if isinstance(value,int) and isinstance(rep,float) \
                            and float(rep).is_integer():
                        rep=int(rep)
                if rep not in uniq:
                    uniq.append(rep)
                    tagged.append(is_neigh)
            _legacy=[r for r,f in zip(uniq,tagged) if not f][:64]
            _neigh=[r for r,f in zip(uniq,tagged) if f][:3]
            uniq=_legacy+_neigh
            for rep in uniq:
                sig=(key,"const",repr(rep))
                if sig in seen: continue
                seen.add(sig)
                fam="neighborhood" if rep in neighbors else "legacy"
                yield key,_descriptor(node,"CONSTANT_REPLACE",repr(value)+"->"+repr(rep),fam,neighbor_ratio.get(rep)),(
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
        # GUARD / CLAUSE / BOUNDARY FAMILY (NOPOL / SPR / Plastic Surgery):
        # Kept strictly in `family="guard_clause"` so `legacy` and `neighborhood`
        # candidate budgets and pair-space indices remain 100% invariant.
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            _fn_swaps={"min":"max","max":"min","any":"all","all":"any"}
            _swap=_fn_swaps.get(node.func.id)
            if _swap:
                sig=(key,"guard_call",_swap)
                if sig not in seen:
                    seen.add(sig)
                    yield key,_descriptor(node,"CALL_FUNC_SWAP",f"{node.func.id}->{_swap}","guard_clause"),(
                        lambda n,_swap=_swap: ast.Call(func=ast.Name(id=_swap,ctx=ast.Load()),args=n.args,keywords=n.keywords)
                    )
            if node.func.id=="range" and len(node.args)==1:
                arg0=node.args[0]
                if isinstance(arg0,ast.BinOp) and isinstance(arg0.op,ast.Sub) and isinstance(arg0.right,ast.Constant) and arg0.right.value==1:
                    sig=(key,"guard_range","drop_minus1")
                    if sig not in seen:
                        seen.add(sig)
                        yield key,_descriptor(node,"RANGE_BOUND_ADJUST","range(n-1)->range(n)","guard_clause"),(
                            lambda n: ast.Call(func=n.func,args=[n.args[0].left],keywords=n.keywords)
                        )
                else:
                    sig=(key,"guard_range","add_plus1")
                    if sig not in seen:
                        seen.add(sig)
                        yield key,_descriptor(node,"RANGE_BOUND_ADJUST","range(n)->range(n+1)","guard_clause"),(
                            lambda n: ast.Call(func=n.func,args=[ast.BinOp(left=n.args[0],op=ast.Add(),right=ast.Constant(value=1))],keywords=n.keywords)
                        )
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            _params=[a.arg for a in (*node.args.posonlyargs,*node.args.args) if a.arg not in ("self","cls")]
            for sub in ast.walk(node):
                if isinstance(sub,ast.Return) and sub.value is not None and not isinstance(sub.value,ast.IfExp):
                    rval=sub.value
                    rkey=_node_key(rval)
                    # Division zero-denominator guard: `return a / b` -> `return (0 if b == 0 else a / b)`
                    if isinstance(rval,ast.BinOp) and isinstance(rval.op,(ast.Div,ast.FloorDiv,ast.Mod)) and isinstance(rval.right,ast.Name):
                        dname=rval.right.id
                        sig=(rkey,"guard_div0",dname)
                        if sig not in seen:
                            seen.add(sig)
                            yield rkey,_descriptor(rval,"GUARD_DIV_ZERO",f"0 if {dname}==0 else expr","guard_clause"),(
                                lambda n,dname=dname: ast.IfExp(
                                    test=ast.Compare(left=ast.Name(id=dname,ctx=ast.Load()),ops=[ast.Eq()],comparators=[ast.Constant(value=0)]),
                                    body=ast.Constant(value=0),
                                    orelse=n,
                                )
                            )
                    # Null / empty precondition guards on first parameter (NOPOL angelic precondition)
                    if _params:
                        p0=_params[0]
                        for tag,cond_fn,sent in (
                            ("none_none",lambda p=p0: ast.Compare(left=ast.Name(id=p,ctx=ast.Load()),ops=[ast.Is()],comparators=[ast.Constant(value=None)]),ast.Constant(value=None)),
                            ("none_zero",lambda p=p0: ast.Compare(left=ast.Name(id=p,ctx=ast.Load()),ops=[ast.Is()],comparators=[ast.Constant(value=None)]),ast.Constant(value=0)),
                            ("empty_zero",lambda p=p0: ast.UnaryOp(op=ast.Not(),operand=ast.Name(id=p,ctx=ast.Load())),ast.Constant(value=0)),
                            ("empty_str",lambda p=p0: ast.UnaryOp(op=ast.Not(),operand=ast.Name(id=p,ctx=ast.Load())),ast.Constant(value="")),
                        ):
                            sig=(rkey,"guard_ret",p0,tag)
                            if sig not in seen:
                                seen.add(sig)
                                yield rkey,_descriptor(rval,"GUARD_PRECONDITION",f"{p0}:{tag}","guard_clause"),(
                                    lambda n,cf=cond_fn,sv=sent: ast.IfExp(test=cf(),body=sv,orelse=n)
                                )

"""Child-side suite execution shared by repair, measurement and tracing.

Plain unittest suites keep their fast stdlib path. Pytest-style suites are run
by the real framework when available; fixtures, parametrization, configuration
and test classes are not reimplemented or silently skipped. When pytest is
needed but unavailable the run fails closed. Simple bare functions still work
without pytest. The first real failure retains its traceback for the localizer,
and the pytest reporter emits the same counted summary consumed by existing
repair and audit code. This is test execution, not an OS security sandbox.
"""
SUITE_RUNNER = r'''import ast,importlib.util,inspect,os,pathlib,runpy,sys,time,tokenize,unittest

def _brain_suite_shape(target):
 with tokenize.open(str(target)) as source:tree=ast.parse(source.read(),filename=str(target))
 prefer_pytest=False
 require_pytest=bool(os.environ.get("PYTEST_ADDOPTS") or os.environ.get("PYTEST_PLUGINS"))
 script=False
 for parent in (target.parent,*target.parent.parents):
  if (parent/"conftest.py").is_file() or (parent/"pytest.ini").is_file() or (parent/".pytest.ini").is_file():
   require_pytest=True
  for name,markers in (("pyproject.toml",("[tool.pytest",)),("setup.cfg",("[tool:pytest]",)),("tox.ini",("[pytest]",))):
   config=parent/name
   if config.is_file():
    try: content=config.read_text(encoding="utf-8")
    except (OSError,UnicodeError): require_pytest=True;continue
    if any(marker in content for marker in markers):require_pytest=True
 for node in ast.walk(tree):
  if isinstance(node,ast.Name) and node.id in ("pytest","pytestmark","pytest_plugins"):require_pytest=True
  if isinstance(node,ast.Import) and any(a.name.split(".")[0]=="pytest" for a in node.names):require_pytest=True
  if isinstance(node,ast.ImportFrom) and (node.module or "").split(".")[0]=="pytest":require_pytest=True
 unittest_modules=set();unittest_cases=set();case_names={"TestCase","IsolatedAsyncioTestCase"}
 for node in tree.body:
  if isinstance(node,ast.Import):
   unittest_modules.update(a.asname or a.name for a in node.names if a.name=="unittest")
  elif isinstance(node,ast.ImportFrom) and node.module in ("unittest","unittest.case","unittest.async_case"):
   for alias in node.names:
    if alias.name=="*":unittest_cases.update(case_names)
    elif alias.name in case_names:unittest_cases.add(alias.asname or alias.name)
 for node in tree.body:
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith("test_"):
   prefer_pytest=True
   args=node.args
   if (isinstance(node,ast.AsyncFunctionDef) or node.decorator_list or args.posonlyargs or args.args
       or args.kwonlyargs or args.vararg or args.kwarg or any(isinstance(x,(ast.Yield,ast.YieldFrom)) for x in ast.walk(node))):
    require_pytest=True
  elif isinstance(node,ast.ClassDef):
   unittest_base=any((isinstance(b,ast.Name) and b.id in unittest_cases) or
                     (isinstance(b,ast.Attribute) and b.attr in case_names and
                      isinstance(b.value,ast.Name) and b.value.id in unittest_modules) for b in node.bases)
   if unittest_base:unittest_cases.add(node.name)
   elif node.name.startswith("Test"):require_pytest=True
  elif isinstance(node,ast.Assert):script=True
  elif isinstance(node,ast.If):
   names={x.id for x in ast.walk(node.test) if isinstance(x,ast.Name)}
   values={x.value for x in ast.walk(node.test) if isinstance(x,ast.Constant) and isinstance(x.value,str)}
   if "__name__" in names and "__main__" in values:script=True
 return prefer_pytest,require_pytest,script

def _brain_project_file(frame,root,cache):
 if frame is None:return None
 filename=frame.f_code.co_filename
 if filename.startswith("<") and filename.endswith(">"):return None
 try:cwd=os.getcwd() if not os.path.isabs(filename) else None
 except OSError:return None
 key=(filename,cwd)
 if key not in cache:
  try:
   path=pathlib.Path(filename).resolve()
   cache[key]=path if path.is_file() and root in path.parents and path.suffix==".py" else None
  except (OSError,ValueError):cache[key]=None
 return cache[key]

def _brain_bare_functions(mod):
 out=[]
 for name in sorted(vars(mod)):
  if not name.startswith("test_"):continue
  fn=vars(mod)[name]
  if not callable(fn):continue
  try:params=list(inspect.signature(fn).parameters.values())
  except (TypeError,ValueError):raise RuntimeError("UNSUPPORTED_TEST_SIGNATURE:"+name)
  needs=[p for p in params if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD,p.KEYWORD_ONLY)]
  if needs:raise RuntimeError("PYTEST_REQUIRED:"+name)
  out.append((name,fn))
 return out

def _brain_reraise_failure(exc,tb):
 # Re-raising SystemExit(0) would turn a failed test or aborted collection
 # into a successful process while still printing a failure summary.
 if isinstance(exc,SystemExit) and exc.code in (None,0):
  raise AssertionError("TEST_RAISED_SYSTEM_EXIT_ZERO").with_traceback(tb) from exc
 raise exc.with_traceback(tb)

def _brain_run_stdlib(target,script):
 directory=str(target.resolve().parent)
 if directory not in sys.path:sys.path.insert(0,directory)
 spec=importlib.util.spec_from_file_location("__brain_suite__",str(target))
 mod=importlib.util.module_from_spec(spec);sys.modules["__brain_suite__"]=mod
 spec.loader.exec_module(mod)
 suite=unittest.TestLoader().loadTestsFromModule(mod)
 for _,fn in _brain_bare_functions(mod):suite.addTest(unittest.FunctionTestCase(fn))
 if suite.countTestCases()==0:
  if not script:raise RuntimeError("NO_TESTS_COLLECTED:"+str(target))
  try:runpy.run_path(str(target),run_name="__main__")
  except SystemExit as exc:
   if exc.code not in (None,0):raise
  return
 class _R(unittest.TestResult):
  def __init__(self,*a,**k):unittest.TestResult.__init__(self);self.err=None;self.no_passing=False
  def addFailure(self,test,err):unittest.TestResult.addFailure(self,test,err);self.err=err
  def addError(self,test,err):unittest.TestResult.addError(self,test,err);self.err=err
  def stopTestRun(self):
   unittest.TestResult.stopTestRun(self)
   # Existing consumers understand skipped, not unittest's expected-failure label.
   self.skipped.extend((test,"expected failure") for test,_ in self.expectedFailures)
   self.expectedFailures.clear()
   self.errors.extend((test,"unexpected success") for test in self.unexpectedSuccesses)
   self.unexpectedSuccesses.clear()
   if self.testsRun and self.testsRun==len(self.skipped):
    self.no_passing=True;self.testsRun+=1;self.errors.append((None,"no passing tests executed"))
 res=unittest.TextTestRunner(stream=sys.stderr,resultclass=_R).run(suite)
 if not res.wasSuccessful():
  if res.err:_brain_reraise_failure(res.err[1],res.err[2])
  if res.no_passing:raise RuntimeError("NO_PASSING_TESTS_EXECUTED")
  raise AssertionError("SUITE_FAILED_WITHOUT_EXCEPTION_INFO")

def _brain_run_pytest(targets,shapes):
 import pytest
 class _Report:
  def __init__(self):
   self.nodes=set();self.collected_files=set();self.selected_files=set()
   self.passed=0;self.failed=0;self.errors=0;self.skipped=0;self.exception=None
  def _file(self,item):
   path=getattr(item,"path",None) or getattr(item,"fspath",None)
   return pathlib.Path(str(path)).resolve() if path is not None else None
  def pytest_itemcollected(self,item):
   self.collected_files.add(self._file(item))
  def pytest_collection_finish(self,session):
   self.selected_files.update(self._file(item) for item in session.items)
  @pytest.hookimpl(hookwrapper=True)
  def pytest_runtest_makereport(self,item,call):
   outcome=yield
   report=outcome.get_result()
   if report.failed and call.excinfo and self.exception is None:
    self.exception=(call.excinfo.value,call.excinfo.tb)
  def pytest_runtest_logreport(self,report):
   if report.when=="call":
    self.nodes.add(report.nodeid)
    if report.failed:self.failed+=1
    elif report.skipped:self.skipped+=1
    elif report.passed:self.passed+=1
   elif report.when=="setup" and (report.failed or report.skipped):
    self.nodes.add(report.nodeid)
    if report.failed:self.errors+=1
    else:self.skipped+=1
   elif report.when=="teardown" and report.failed:self.errors+=1
  def pytest_collectreport(self,report):
   if report.failed:self.errors+=1
 report=_Report();started=time.monotonic()
 status=int(pytest.main(["-q","-p","no:cacheprovider"]+[str(t) for t in targets],plugins=[report]))
 if status in (0,5) and not report.errors:
  for target,shape in zip(targets,shapes):
   if target in report.selected_files:continue
   if shape[2] and target not in report.collected_files:
    # Pytest imports a script but does not execute its __main__ guard.
    try:runpy.run_path(str(target),run_name="__main__")
    except BaseException as exc:
     if isinstance(exc,SystemExit) and exc.code in (None,0):report.passed+=1;continue
     report.errors+=1;status=1
     if report.exception is None:report.exception=(exc,exc.__traceback__)
    else:report.passed+=1
   else:
    sys.stderr.write("NO_TESTS_COLLECTED_IN_TARGET:"+str(target)+"\n")
    report.errors+=1;status=1
  if status==5 and report.passed and not report.errors:status=0
 if status==0 and report.passed==0:
  sys.stderr.write("NO_PASSING_TESTS_EXECUTED\n")
  status=1;report.errors+=1
 if status and not (report.failed or report.errors):report.errors+=1
 # Collection, teardown and no-passing-oracle failures can add suite-level
 # errors beyond the number of collected test nodes.
 count=max(len(report.nodes),report.passed+report.failed+report.errors+report.skipped)
 sys.stderr.write("Ran %d test%s in %.3fs\n\n"%(count,"" if count==1 else "s",time.monotonic()-started))
 parts=[]
 if report.failed:parts.append("failures=%d"%report.failed)
 if report.errors:parts.append("errors=%d"%report.errors)
 if report.skipped:parts.append("skipped=%d"%report.skipped)
 sys.stderr.write(("FAILED" if status else "OK")+(" ("+", ".join(parts)+")" if parts else "")+"\n")
 if status:
  if report.exception:
   exc,tb=report.exception
   _brain_reraise_failure(exc,tb)
  raise RuntimeError("PYTEST_EXECUTION_FAILED:"+str(status))

def _brain_run_suites(targets):
 targets=[pathlib.Path(t).resolve() for t in targets]
 if not targets:raise RuntimeError("NO_TESTS_COLLECTED")
 shapes=[_brain_suite_shape(t) for t in targets]
 try:has_pytest=importlib.util.find_spec("pytest") is not None
 except (ImportError,ValueError):has_pytest=False
 if any(shape[1] for shape in shapes) and not has_pytest:
  raise RuntimeError("PYTEST_REQUIRED:"+", ".join(str(t) for t,s in zip(targets,shapes) if s[1]))
 if has_pytest and any(shape[0] or shape[1] for shape in shapes):
  _brain_run_pytest(targets,shapes);return
 errors=[]
 for target,shape in zip(targets,shapes):
  try:_brain_run_stdlib(target,shape[2])
  except BaseException as exc:errors.append(exc)
 if errors:_brain_reraise_failure(errors[0],errors[0].__traceback__)

def _brain_run_suite(target):
 _brain_run_suites([target])
'''


SUITE_ENTRY = (
    "import pathlib,sys\n"
    "_brain_run_suites([pathlib.Path(_t).resolve() for _t in sys.argv[1:]])\n"
)


def argv_names_a_target(argv: Any) -> bool:
    """True when a command line actually names a test suite to run.

    The runner ``suite_argv`` generates reads its targets from ``sys.argv[1:]``,
    so ``[executable, "-c", script]`` names no suite. An older runner returned
    zero for that command, causing a false BASELINE_ALREADY_PASSES result. The
    runner now fails closed, and this check also lets callers derive the actual
    discovered targets instead of retaining an empty command.

    Targets follow the ``-c`` script when there is one; otherwise any non-flag
    element after the executable is treated as a target.
    """
    items = [str(x) for x in (argv or [])]
    if not items:
        return False
    if "-c" in items:
        return len(items) > items.index("-c") + 2
    return any(not item.startswith("-") for item in items[1:])


def argv_or_derived(supplied: Any, executable: Any, *targets: Any) -> list[str]:
    """The caller's command line when it names a suite, otherwise the derived one.

    The derivation is not a fallback for a missing value only.  An argv that is
    present but empty of targets is worse than a missing one, because it looks
    bound: the missing value takes the derived path, while the empty one used to
    win and silently run nothing.  Both must derive.
    """
    if argv_names_a_target(supplied):
        return [str(x) for x in supplied]
    return suite_argv(executable, *targets)


def suite_argv(executable: Any, *targets: Any) -> list[str]:
    """Run named suites with the applicable framework and a counted result.

    Unittest suites and simple bare functions retain a stdlib-only path. When
    installed, pytest collects pytest-style suites together, including fixtures,
    parametrization and project configuration. Without pytest, suites requiring
    it fail explicitly instead of skipping cases and reporting success. A file
    without tests or an explicit script oracle and a command with no targets
    fail closed. Failures retain their tracebacks for localization.
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
        # NO package-dir walk here, reverted with evidence: intermediate
        # __init__.py parents on sys.path SHADOW STDLIB MODULES -- the
        # tornado package dir made `import locale` resolve to
        # tornado/locale.py inside gettext (measured: AttributeError
        # locale.normalize in-run, absent standalone). Package-rooted test
        # imports are satisfied by the WORLD ROOT, which callers already
        # pass as source_root; the rc=2/zero-failing-tests symptom this walk
        # once chased turned out to be the harness slicing -m off the argv.
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        dirs.append(existing)
    return {"PYTHONPATH": os.pathsep.join(dirs)}


def _byte_offset(lines: list[bytes], lineno: int, col: int) -> int:
    return sum(len(x) for x in lines[:lineno-1]) + col

def _replacement_span(raw, lines, target, replacer, offsets=None):
    """Shared byte-splice primitive, extracted from the coupled repair engine."""
    if target is None or any(getattr(target, name, None) is None for name in
                             ("lineno", "col_offset", "end_lineno", "end_col_offset")):
        return None
    # Replacers may mutate their argument. Never lend out the indexed subtree.
    replacement = replacer(copy.deepcopy(target))
    ast.fix_missing_locations(replacement)
    data = ast.unparse(replacement).encode("utf-8")
    start = (offsets[target.lineno - 1] + target.col_offset if offsets is not None
             else _byte_offset(lines, target.lineno, target.col_offset))
    end = (offsets[target.end_lineno - 1] + target.end_col_offset if offsets is not None
           else _byte_offset(lines, target.end_lineno, target.end_col_offset))
    return start, end, data


class _CandidateRenderer:
    """Request-local source index; caches syntax, never execution/acceptance."""
    def __init__(self, source_text, tree=None):
        self.raw = source_text.encode("utf-8")
        self.lines = self.raw.splitlines(keepends=True)
        self.offsets = [0]
        for line in self.lines:
            self.offsets.append(self.offsets[-1] + len(line))
        self.nodes = {}
        for node in ast.walk(ast.parse(source_text) if tree is None else tree):
            self.nodes.setdefault(_node_key(node), node)

    def span(self, key, replacer):
        return _replacement_span(self.raw, self.lines, self.nodes.get(key), replacer, self.offsets)

    def render(self, key, replacer):
        span = self.span(key, replacer)
        if span is None:
            return None
        start, end, data = span
        return (self.raw[:start] + data + self.raw[end:]).decode("utf-8")

    def edit(self, key, desc, replacer):
        span = self.span(key, replacer)
        if span is None:
            return None
        start, end, data = span
        if self.raw[start:end] == data:
            return None
        return {"start": start, "end": end, "replacement": data, "mutation": desc}


def _render_candidate(source_text: str, key, replacer) -> str|None:
    # One-off callers need no complete index. Search loops reuse a renderer.
    tree = ast.parse(source_text)
    target = next((node for node in ast.walk(tree) if _node_key(node) == key), None)
    raw = source_text.encode("utf-8")
    span = _replacement_span(raw, raw.splitlines(keepends=True), target, replacer)
    if span is None:
        return None
    start, end, data = span
    return (raw[:start] + data + raw[end:]).decode("utf-8")

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
    tests_raw=[x for x in (args.get("test_paths") or []) if str(x).strip()]
    if not isinstance(tests_raw,list):
        raise PatchSearchError("TEST_PATHS_REQUIRED")
    if not tests_raw:
        # This capability names a single SOURCE file, so the corpus is the tree
        # that file lives in -- the smallest scope in which its tests can be.
        from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_paths
        try: tests_raw=discover_test_paths(source.parent)
        except FileNotFoundError: raise PatchSearchError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
    if not tests_raw:
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
    from canonical.runtime.write_authority_v1 import check_report
    check_report(repo, output, [source, *tests])
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
    renderer=_CandidateRenderer(source_text, tree)
    attempts=[]
    winner=None
    tested=0
    legacy_tested=0
    neigh_tested=0
    NEIGH_RESERVE=6  # own budget; legacy slots untouched (zero dilution)
    try:
        for key,desc,replacer in _candidate_specs(tree,nums,strings):
            if desc.get("family")=="neighborhood":
                if neigh_tested>=NEIGH_RESERVE:
                    continue
                neigh_tested+=1
            elif legacy_tested>=max_candidates:
                continue  # keep scanning: neighborhood reserve must stay reachable
            candidate=renderer.render(key,replacer)
            if candidate is None or candidate==source_text:
                continue
            tested+=1
            if desc.get("family")!="neighborhood":
                legacy_tested+=1
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
        "patches":[],  # candidate patches: the machine-readable promised artifact
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
            "patches":[{
                "source_path":rel,
                "winning_mutation":desc,
                "candidate_source_sha256":_sha(candidate.encode("utf-8")),
                "verification_replays":replay,
                "unified_diff":patch,
            }],
        })
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(raw)
    result["output_verified"]=True
    return result
