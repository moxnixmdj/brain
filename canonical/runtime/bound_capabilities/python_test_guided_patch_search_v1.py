#!/usr/bin/env python3
"""Deterministic bounded test-guided Python patch search.

Candidate-only search over one repository-local Python source file. The runtime:
- requires an isolated writable workspace,
- records exact source/test bytes,
- requires the baseline test command to fail,
- enumerates one-node AST mutations plus literal substitutions mined from tests,
- executes the test command for each candidate within per-run and overall soft time budgets,
- restores original source bytes after every trial,
- replays the winning candidate twice before emitting a unified diff,
- never leaves the source modified.

No model calls, network calls, package installation, or canonical source writes.
The supplied workspace must be isolated: test subprocesses are not OS-sandboxed,
and custom test commands remain the caller's acceptance oracle.
"""
from __future__ import annotations
import ast, difflib, hashlib, importlib.util, json, math, os, pathlib, signal, subprocess, sys, time
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_TEST_GUIDED_PATCH_SEARCH_V1"

class PatchSearchError(RuntimeError): pass
class WallBudgetExhausted(PatchSearchError): pass

class WallBudget:
    """Shared soft wall budget; synchronous Python work and cleanup cannot be preempted."""
    def __init__(self, value: Any = None):
        try:self.limit=float(120 if value is None else value)
        except (TypeError,ValueError) as exc:raise PatchSearchError("INVALID_WALL_TIME_BUDGET") from exc
        if not math.isfinite(self.limit) or not 0 < self.limit <= 3600:
            raise PatchSearchError("INVALID_WALL_TIME_BUDGET")
        self.deadline=time.monotonic()+self.limit
    def remaining(self) -> float:
        return max(0.0,self.deadline-time.monotonic())
    def expired(self) -> bool:
        return self.remaining()<=0
    def timeout(self, maximum: float) -> float:
        remaining=self.remaining()
        if remaining<=0:raise WallBudgetExhausted("WALL_TIME_BUDGET_EXHAUSTED")
        return min(maximum,remaining)

def _safe_file(root: pathlib.Path, raw: Any, *, suffix: str|None=None) -> pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents or not p.is_file() or p.is_symlink():
        raise PatchSearchError("PATH_INVALID:"+str(raw))
    if suffix and p.suffix!=suffix:
        raise PatchSearchError("PATH_SUFFIX_INVALID:"+str(raw))
    return p

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _run_process(root: pathlib.Path, argv: list[str], timeout_s: float,
                 env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Run a process, confined by OS namespace when available, else ordinary
    process-group cleanup. Confinement is preferred; the unconfined path is
    only a fallback for hosts where user namespaces or chroot are denied.

    Preference order:
    1. sandboxkit (existing, tested library): user+mount+pid+net+ipc+uts
       namespaces, rlimits, optional Landlock, rootless by default.
    2. confine_v1 (Brain-owned): user+mount namespaces + chroot, /dev/null
       provisioned inside the chroot.
    3. Ordinary process-group bound execution (not an OS sandbox).
    """
    started = time.monotonic()
    # ---- 1. sandboxkit: PID namespace + rlimits + Landlock, rootless ----
    # sandboxkit does NOT chroot; the host filesystem is visible as-is.  Root
    # maps to "." (the sandbox cwd), other paths under root stay absolute since
    # they resolve on the host filesystem unchanged.
    try:
        from sandboxkit import Sandbox, RLimits
        root_resolved = root.resolve()
        sandbox_argv: list[str] = []
        for a in argv:
            a_str = str(a)
            try:
                a_path = pathlib.Path(a_str).resolve()
                if a_path == root_resolved:
                    sandbox_argv.append(".")
                elif root_resolved in a_path.parents:
                    sandbox_argv.append(str(a_path.relative_to(root_resolved)))
                else:
                    sandbox_argv.append(a_str)
            except (ValueError, OSError):
                sandbox_argv.append(a_str)
        sandbox_env = dict(env or {})
        sb = Sandbox(
            rlimits=RLimits(cpu_seconds=int(timeout_s),
                            memory_bytes=256 << 20),
            timeout=int(timeout_s),
            cwd=str(root),
            env=sandbox_env,
        )
        result = sb.run_argv(sandbox_argv)
        return {"returncode": result.returncode,
                "stdout": result.stdout.decode("utf-8", errors="replace")
                          if isinstance(result.stdout, bytes) else str(result.stdout or ""),
                "stderr": result.stderr.decode("utf-8", errors="replace")
                          if isinstance(result.stderr, bytes) else str(result.stderr or ""),
                "elapsed_s": round(time.monotonic() - started, 6),
                "timed_out": bool(result.timed_out)}
    except Exception:
        pass
    # ---- 2. confine_v1: user+mount namespaces + chroot ----
    try:
        from canonical.runtime.confine_v1 import run as _confined_run
        root_resolved = root.resolve()
        sandbox_argv: list[str] = []
        for a in argv:
            a_str = str(a)
            try:
                a_path = pathlib.Path(a_str).resolve()
                if root_resolved in a_path.parents:
                    sandbox_argv.append(str(a_path.relative_to(root_resolved)))
                elif a_path == root_resolved:
                    sandbox_argv.append("/project")
                else:
                    sandbox_argv.append(a_str)
            except (ValueError, OSError):
                sandbox_argv.append(a_str)
        sandbox_env: dict[str, str] | None = None
        if env is not None:
            sandbox_env = {}
            for k, v in env.items():
                vs = str(v)
                parts = vs.split(os.pathsep)
                new_parts = []
                for part in parts:
                    if not part:
                        new_parts.append(part)
                        continue
                    try:
                        p = pathlib.Path(part).resolve()
                        if root_resolved in p.parents:
                            new_parts.append(str(p.relative_to(root_resolved)))
                        elif p == root_resolved:
                            new_parts.append("/project")
                        else:
                            new_parts.append(part)
                    except (ValueError, OSError):
                        new_parts.append(part)
                sandbox_env[k] = os.pathsep.join(new_parts)
        confined = _confined_run(
            argv=sandbox_argv,
            root=str(root),
            timeout=int(timeout_s),
            env=sandbox_env,
            extra_bind_mounts=[("/dev/null", "/dev/null")],
        )
        if confined.get("confined") is True:
            rc = confined.get("exit_status")
            timed_out = confined.get("verdict") == "INDETERMINATE" and rc is None
            output = confined.get("output", "")
            return {"returncode": rc,
                    "stdout": output, "stderr": "",
                    "elapsed_s": round(time.monotonic() - started, 6),
                    "timed_out": bool(timed_out)}
    except Exception:
        pass
    # Fallback: ordinary process-group bound execution (not an OS sandbox).
    proc = subprocess.Popen(argv, cwd=root, text=True, encoding="utf-8",
                            errors="replace", stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                            env=env, start_new_session=(os.name == "posix"))
    timed_out = False
    def kill_group():
        if os.name == "posix":
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        elif proc.poll() is None:
            proc.kill()
    try:
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            kill_group()
            try:
                stdout, stderr = proc.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                for pipe in (proc.stdout, proc.stderr):
                    if pipe is not None: pipe.close()
                proc.wait(timeout=1)
                stdout, stderr = exc.stdout or b"", exc.stderr or b""
            if isinstance(stdout, bytes): stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes): stderr = stderr.decode("utf-8", errors="replace")
    finally:
        kill_group()
        if proc.poll() is None: proc.wait(timeout=1)
    return {"returncode": None if timed_out else proc.returncode, "stdout": stdout or "",
            "stderr": stderr or "", "elapsed_s": round(time.monotonic() - started, 6),
            "timed_out": timed_out}


def _run_tests(root: pathlib.Path, argv: list[str], timeout_s: float,
               extra_env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Run a Python test command and require the shared runner's completion marker.

    Extra environment entries extend the inherited environment so test imports
    resolve in the caller's source root. A custom argv is still the caller's
    oracle. Process-group cleanup is not sandboxing or containment of a child
    that deliberately creates a new session.
    """
    if not argv or any(not isinstance(x,str) or not x for x in argv):
        raise PatchSearchError("TEST_ARGV_INVALID")
    exe=pathlib.Path(argv[0]).name.lower()
    allowed={pathlib.Path(sys.executable).name.lower(),"python","python3","py"}
    if exe not in allowed:
        raise PatchSearchError("TEST_EXECUTABLE_NOT_PYTHON")
    env=None if not extra_env else {**os.environ,**{k:str(v) for k,v in extra_env.items()}}
    try:result=_run_process(root,argv,timeout_s,env)
    except OSError as exc:raise PatchSearchError("TEST_RUNNER_UNAVAILABLE:"+str(exc)) from exc
    if (result["returncode"] == 0 and len(argv) >= 3 and argv[1] == "-c"
            and argv[2] == SUITE_RUNNER + SUITE_ENTRY
            and SUITE_COMPLETION_MARKER not in result["stdout"].splitlines()):
        raise PatchSearchError("TEST_RUNNER_INFRASTRUCTURE:COMPLETION_MARKER_MISSING")
    if (result["returncode"] not in (None,0) and len(argv) >= 3 and argv[1] == "-c"
            and "_brain_run_suite" in argv[2] and "_BrainTestRunnerError:" in result["stderr"]):
        lines = result["stderr"].split("_BrainTestRunnerError:", 1)[1].strip().splitlines()
        raise PatchSearchError("TEST_RUNNER_INFRASTRUCTURE:" + (lines[0] if lines else "UNKNOWN"))
    return result


def _argv_python_files(repo: pathlib.Path, argv: Iterable[str], cwd: pathlib.Path | None = None) -> set[pathlib.Path]:
    """Protect explicit repository-local Python file arguments, not arbitrary command effects."""
    found=set()
    for token in list(argv)[1:]:
        token=token.split("::",1)[0]
        if not token or len(token)>4096 or "\n" in token or token.startswith("-") or not token.endswith(".py"):
            continue
        for base in (cwd or repo,repo):
            try:
                path=(base/token).resolve()
                if repo in path.parents and path.is_file():
                    found.add(path);break
            except (OSError,ValueError):
                continue
    return found


def _reject_output_overlap(output: pathlib.Path, source_root: pathlib.Path,
                           tests: Iterable[pathlib.Path]) -> None:
    """Never replace a declared test or an existing Python source with a receipt."""
    if output in set(tests) or (output.is_file() and output.suffix == ".py"
                                and source_root in output.parents):
        raise PatchSearchError("OUTPUT_OVERLAPS_INPUT")


def _check_protected_bytes(expected: Mapping[pathlib.Path, bytes]) -> None:
    """Detect and restore observed input changes; this is not OS isolation."""
    changed=[]
    for path,raw in expected.items():
        try:intact=not path.is_symlink() and path.is_file() and path.read_bytes()==raw
        except OSError:intact=False
        if not intact:changed.append(path)
    if not changed:return
    for path in changed:
        try:
            if path.is_symlink():path.unlink()
            if path.exists() and not path.is_file():raise OSError("INPUT_REPLACED_BY_NONFILE")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(expected[path])
            _purge_source_bytecode(path)
        except OSError as exc:
            raise PatchSearchError("INPUT_RESTORE_FAILED:"+str(path)) from exc
    raise PatchSearchError("TEST_OR_SOURCE_MODIFIED:"+str(changed[0]))


def _run_tests_guarded(root: pathlib.Path, argv: list[str], timeout_s: float,
                       env: Mapping[str, str] | None,
                       expected: Mapping[pathlib.Path, bytes]) -> dict[str, Any]:
    try:
        return _run_tests(root,argv,timeout_s,env)
    finally:
        _check_protected_bytes(expected)


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
    ast.Add:[ast.Sub, ast.Mult],
    ast.Sub:[ast.Add, ast.Mult],
    ast.Mult:[ast.Add, ast.Sub, ast.FloorDiv, ast.Div],
    ast.Div:[ast.Mult, ast.Sub, ast.FloorDiv],
    ast.Mod:[ast.FloorDiv, ast.Sub],
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

"""Child-side runner shared by patch search and tracing capabilities.

Plain unittest cases and simple parameterless functions retain a stdlib fast
path. Pytest-specific tests and configuration use real pytest, with fixture
injection and one session for multiple test files. A plugin records failures,
skips, deselections and a passing case per explicit file; infrastructure and
skipped-only results fail closed. The first failure keeps its traceback and a
unittest-style summary for existing repair scoring. Pytest must be installed
when required. Simple unconditional module-level assertion scripts run once;
branches and caught assertions are not treated as sufficient evidence. Mixed
interleaved script/pytest ordering is refused rather than silently reordered.
"""
SUITE_RUNNER = r'''import ast,importlib.util,inspect,os,pathlib,sys,unittest

class _BrainTestRunnerError(RuntimeError):
 pass

def _brain_pytest_context(target):
 if os.environ.get("PYTEST_PLUGINS"):
  return True
 names=("conftest.py","pytest.ini","pyproject.toml","tox.ini","setup.cfg")
 parent=target.resolve().parent
 cwd=pathlib.Path.cwd().resolve()
 while True:
  if any((parent/name).is_file() for name in names):return True
  if parent==cwd or parent.parent==parent:break
  parent=parent.parent
 return False

def _brain_requires_pytest(target):
 try:tree=ast.parse(target.read_bytes(),filename=str(target))
 except (OSError,SyntaxError,ValueError):return False
 unittest_names={"unittest"};case_names=set();uses_pytest=False;test_import=False
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):
   for a in n.names:
    if a.name.split(".")[0]=="pytest":uses_pytest=True
    if a.name=="unittest":unittest_names.add(a.asname or a.name)
  elif isinstance(n,ast.ImportFrom):
   if (n.module or "").split(".")[0]=="pytest":uses_pytest=True
   if n.module=="unittest":
    case_names.update(a.asname or a.name for a in n.names if a.name=="TestCase")
   if any((a.asname or a.name).startswith("test_") or a.name=="*" for a in n.names):test_import=True
  elif isinstance(n,(ast.Assign,ast.AnnAssign)):
   targets=n.targets if isinstance(n,ast.Assign) else [n.target]
   if any(isinstance(x,ast.Name) and x.id=="pytest_plugins" for x in targets):uses_pytest=True
 if uses_pytest or test_import:return True
 candidates=[]
 for node in tree.body:
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith("test_"):
   candidates.append(node)
   positional=node.args.posonlyargs+node.args.args
   if (isinstance(node,ast.AsyncFunctionDef) or len(positional)>len(node.args.defaults)
       or any(default is None for default in node.args.kw_defaults) or node.decorator_list
       or any(isinstance(x,(ast.Yield,ast.YieldFrom)) for x in ast.walk(node))):
    return True
  elif isinstance(node,ast.ClassDef):
   tests=[x for x in node.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name.startswith("test_")]
   if tests:
    candidates.append(node)
    is_unittest=any((isinstance(base,ast.Name) and base.id in case_names) or
                    (isinstance(base,ast.Attribute) and base.attr=="TestCase" and
                     isinstance(base.value,ast.Name) and base.value.id in unittest_names)
                    for base in node.bases)
    if node.name.startswith("Test") and not is_unittest:return True
 # A local pytest configuration or conftest can change collection and inject
 # autouse fixtures even into functions that take no explicit parameters.
 if _brain_pytest_context(target):
  if candidates or any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) for n in tree.body):
   return True
 return False

def _brain_bare_functions(mod):
 out=[]
 for name in sorted(vars(mod)):
  if not name.startswith("test_"):continue
  fn=vars(mod)[name]
  if not callable(fn):continue
  try:params=list(inspect.signature(fn).parameters.values())
  except (TypeError,ValueError):raise _BrainTestRunnerError("PYTEST_REQUIRED_FOR_TEST_SIGNATURE")
  needs=[p for p in params if p.default is p.empty and p.kind in
         (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD,p.KEYWORD_ONLY)]
  if (needs or inspect.iscoroutinefunction(fn) or inspect.isgeneratorfunction(fn)
      or inspect.isasyncgenfunction(fn) or getattr(fn,"pytestmark",None)):
   raise _BrainTestRunnerError("PYTEST_REQUIRED_FOR_TEST_COLLECTION")
  out.append((name,fn))
 return out

def _brain_run_pytest(target):
 try:import pytest
 except ImportError as exc:raise _BrainTestRunnerError("PYTEST_REQUIRED_FOR_TEST_COLLECTION") from exc
 targets=[target] if isinstance(target,pathlib.Path) else list(target)
 if not __debug__:
  for path in targets:
   try:tree=ast.parse(path.read_bytes(),filename=str(path))
   except (OSError,SyntaxError,ValueError):tree=None
   if tree is None or any(isinstance(n,ast.Assert) for n in ast.walk(tree)):
    raise _BrainTestRunnerError("PYTHON_ASSERTIONS_DISABLED")
 class _Recorder:
  def __init__(self):
   self.collected=0;self.passed=0;self.failed=0;self.errors=0;self.skipped=0;self.deselected=0;self.err=None
   self.owners={};self.file_passed={str(p.resolve()):0 for p in targets}
  def pytest_collection_finish(self,session):
   self.collected=len(session.items)
   for item in session.items:
    path=getattr(item,"path",getattr(item,"fspath",None))
    if path is not None:self.owners[item.nodeid]=str(pathlib.Path(str(path)).resolve())
  def pytest_deselected(self,items):self.deselected+=len(items)
  def pytest_runtest_makereport(self,item,call):
   if (call.excinfo is not None and self.err is None and not item.get_closest_marker("xfail")
       and not isinstance(call.excinfo.value,(pytest.skip.Exception,pytest.xfail.Exception))):
    self.err=(call.excinfo.value,call.excinfo.value.__traceback__)
  def pytest_runtest_logreport(self,report):
   if report.when=="call":
    if report.passed and not hasattr(report,"wasxfail"):
     self.passed+=1
     owner=self.owners.get(report.nodeid)
     if owner in self.file_passed:self.file_passed[owner]+=1
    elif report.skipped or hasattr(report,"wasxfail"):self.skipped+=1
    elif report.failed:self.failed+=1
   elif report.failed:self.errors+=1
   elif report.skipped and report.when=="setup":self.skipped+=1
 rec=_Recorder()
 code=pytest.main(["-q","-p","no:cacheprovider"]+[str(p) for p in targets],plugins=[rec])
 if rec.deselected:
  raise _BrainTestRunnerError("PYTEST_DESELECTED_TESTS:%d"%rec.deselected)
 print("Ran %d tests in 0.000s"%rec.collected,file=sys.stderr)
 if code==0 and rec.passed>0 and rec.failed==0 and rec.errors==0:
  missing=[p for p,n in rec.file_passed.items() if not n]
  if missing:raise _BrainTestRunnerError("PYTEST_FILE_WITHOUT_PASSING_CASE:"+missing[0])
  print("\nOK"+(" (skipped=%d)"%rec.skipped if rec.skipped else ""),file=sys.stderr)
  return
 if rec.failed or rec.errors:
  pieces=[]
  if rec.failed:pieces.append("failures=%d"%rec.failed)
  if rec.errors:pieces.append("errors=%d"%rec.errors)
  if rec.skipped:pieces.append("skipped=%d"%rec.skipped)
  print("\nFAILED ("+", ".join(pieces)+")",file=sys.stderr)
  if rec.err is not None:
   exc,tb=rec.err
   if isinstance(exc,SystemExit):raise AssertionError("TEST_RAISED_SYSTEM_EXIT") from exc
   raise exc.with_traceback(tb)
  raise AssertionError("PYTEST_SUITE_FAILED")
 raise _BrainTestRunnerError("PYTEST_NO_PASSING_TESTS_OR_COLLECTION_ERROR:%s"%code)

def _brain_run_suite(target,script=False):
 target=target.resolve()
 try:tree=ast.parse(target.read_bytes(),filename=str(target))
 except (OSError,SyntaxError,ValueError):tree=None
 if not __debug__ and (tree is None or any(isinstance(n,ast.Assert) for n in ast.walk(tree))):
  raise _BrainTestRunnerError("PYTHON_ASSERTIONS_DISABLED")
 if not script and _brain_requires_pytest(target):return _brain_run_pytest(target)
 _d=str(target.parent)
 if _d not in sys.path:sys.path.insert(0,_d)
 spec=importlib.util.spec_from_file_location("__brain_suite__",str(target))
 mod=importlib.util.module_from_spec(spec);sys.modules["__brain_suite__"]=mod
 try:spec.loader.exec_module(mod)
 except SystemExit as exc:raise _BrainTestRunnerError("TEST_MODULE_EXITED_BEFORE_COLLECTION") from exc
 suite=unittest.TestLoader().loadTestsFromModule(mod)
 bare=_brain_bare_functions(mod)
 for _,fn in bare:suite.addTest(unittest.FunctionTestCase(fn))
 if suite.countTestCases()==0:
  # An unconditional module-level assertion has already run once above.
  # An assert hidden in a branch, handler or uncalled function is not evidence.
  if tree is None or not any(isinstance(n,ast.Assert) for n in tree.body):
   raise _BrainTestRunnerError("NO_PASSING_TESTS_EXECUTED")
  return
 class _R(unittest.TestResult):
  def __init__(self,*a,**k):unittest.TestResult.__init__(self);self.err=None
  def addFailure(self,test,err):unittest.TestResult.addFailure(self,test,err);self.err=err
  def addError(self,test,err):unittest.TestResult.addError(self,test,err);self.err=err
 res=unittest.TextTestRunner(stream=sys.stderr,resultclass=_R).run(suite)
 if not res.wasSuccessful():
  if res.err:
   if isinstance(res.err[1],SystemExit):raise AssertionError("TEST_RAISED_SYSTEM_EXIT") from res.err[1]
   raise res.err[1].with_traceback(res.err[2])
  raise AssertionError("SUITE_FAILED_WITHOUT_EXCEPTION_INFO")
 if res.testsRun-len(res.skipped)-len(res.expectedFailures)<=0:
  raise _BrainTestRunnerError("NO_PASSING_TESTS_EXECUTED")

def _brain_simple_script(target):
 try:tree=ast.parse(target.read_bytes(),filename=str(target))
 except (OSError,SyntaxError,ValueError):return False
 if not any(isinstance(n,ast.Assert) for n in tree.body):return False
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_"):return False
  if isinstance(n,ast.ClassDef):return False
  if isinstance(n,ast.Import) and any(a.name.split(".")[0]=="pytest" for a in n.names):return False
  if isinstance(n,ast.ImportFrom) and (n.module or "").split(".")[0]=="pytest":return False
 return True

def _brain_run_all(targets):
 targets=[pathlib.Path(t).resolve() for t in targets]
 if not targets:raise _BrainTestRunnerError("NO_TEST_PATHS")
 scripts=[_brain_simple_script(t) for t in targets]
 test_indexes=[i for i,is_script in enumerate(scripts) if not is_script]
 use_pytest=any(_brain_requires_pytest(targets[i]) for i in test_indexes)
 errors=[]
 def one(target,is_script):
  try:_brain_run_suite(target,script=is_script)
  except BaseException as exc:errors.append(exc)
 if use_pytest:
  first,last=test_indexes[0],test_indexes[-1]
  if any(scripts[first:last+1]):
   raise _BrainTestRunnerError("INTERLEAVED_ASSERTION_SCRIPT_AND_PYTEST_FILES")
  for i in range(first):one(targets[i],True)
  try:_brain_run_pytest([targets[i] for i in test_indexes])
  except BaseException as exc:errors.append(exc)
  for i in range(last+1,len(targets)):one(targets[i],True)
 else:
  for target,is_script in zip(targets,scripts):one(target,is_script)
 if errors:raise errors[0]
'''


SUITE_COMPLETION_MARKER = "__BRAIN_SUITE_COMPLETED__"
SUITE_ENTRY = (
    "import sys\n"
    "_brain_run_all(sys.argv[1:])\n"
    f"print({SUITE_COMPLETION_MARKER!r})\n"
)


def suite_argv(executable: Any, *targets: Any) -> list[str]:
    """A command line that runs suites through the loader instead of executing the files.

    Running a test file as a script only starts the tests when the file carries a __main__ guard, and
    34% of the unittest files in this repository (695 of 2019, measured) do not, because they are
    written to be collected by a runner. Such a run executes nothing and exits 0, which a repair loop
    reads as BASELINE_ALREADY_PASSES - a false "already passes" for a program that fails its own test.
    SUITE_RUNNER collects simple unittest/function suites and invokes real pytest when fixtures or
    pytest context are needed. Recognized unconditional assertion scripts run once. A required but
    unavailable pytest, skipped-only file, or uncollected file fails closed.

    Pytest files share a session, and the first failure is re-raised so a baseline over several files
    cannot pass merely because each file was run in a separate session.
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
    started=time.monotonic()
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
    max_wall_time_s=float(120 if args.get("max_wall_time_s") is None else args["max_wall_time_s"])
    if not math.isfinite(max_wall_time_s) or not 0 < max_wall_time_s <= 3600:
        raise PatchSearchError("INVALID_WALL_TIME_BUDGET")
    deadline=started+max_wall_time_s
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise PatchSearchError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    oracle_files=(set(tests)|_argv_python_files(repo,argv))-{source}
    if source in tests or output==source or output in oracle_files:
        raise PatchSearchError("OUTPUT_OVERLAPS_INPUT")
    original_bytes=source.read_bytes()
    test_originals={p:p.read_bytes() for p in oracle_files}
    try:
        source_text=original_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchSearchError("SOURCE_NOT_UTF8") from exc
    env=_source_env(source,*tests)

    def guarded_run(expected_source: bytes, limit: float) -> dict[str, Any]:
        # Test commands may write to the workspace. Declared tests and the
        # candidate source must remain byte-identical throughout each trial.
        try:
            result=_run_tests(repo,argv,limit,env)
        finally:
            expected={source:expected_source, **test_originals}
            changed=[]
            for path,raw in expected.items():
                try:
                    intact=not path.is_symlink() and path.is_file() and path.read_bytes()==raw
                except OSError:
                    intact=False
                if not intact:changed.append(path)
            if changed:
                for path,raw in {source:original_bytes, **test_originals}.items():
                    try:
                        if path.is_symlink():path.unlink()
                        if path.exists() and not path.is_file():
                            raise OSError("INPUT_REPLACED_BY_NONFILE")
                        path.parent.mkdir(parents=True,exist_ok=True)
                        path.write_bytes(raw)
                        _purge_source_bytecode(path)
                    except OSError as exc:
                        raise PatchSearchError("INPUT_RESTORE_FAILED:"+str(path)) from exc
                raise PatchSearchError("TEST_OR_SOURCE_MODIFIED:"+str(changed[0]))
        return result

    remaining=deadline-time.monotonic()
    if remaining<=0:raise PatchSearchError("WALL_TIME_BUDGET_EXHAUSTED_BEFORE_BASELINE")
    baseline=guarded_run(original_bytes,min(timeout_s,remaining))
    if baseline["returncode"]==0:
        raise PatchSearchError("BASELINE_ALREADY_PASSES")
    if baseline["timed_out"]:
        raise PatchSearchError("BASELINE_TIMEOUT")
    nums,strings=_test_literals(tests)
    tree=ast.parse(source_text,filename=str(source))
    attempts=[]
    winner=None
    tested=0
    budget_exhausted=False
    try:
        for key,desc,replacer in _candidate_specs(tree,nums,strings):
            if tested>=max_candidates:
                break
            remaining=deadline-time.monotonic()
            if remaining<=0:
                budget_exhausted=True
                break
            candidate=_render_candidate(source_text,key,replacer)
            if candidate is None or candidate==source_text:
                continue
            tested+=1
            source.write_bytes(candidate.encode("utf-8"))
            _purge_source_bytecode(source)
            remaining=deadline-time.monotonic()
            if remaining<=0:
                budget_exhausted=True
                break
            result=guarded_run(candidate.encode("utf-8"),min(timeout_s,remaining))
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
            if result["timed_out"] and time.monotonic()>=deadline:
                budget_exhausted=True
                break
            if result["returncode"]==0 and not result["timed_out"]:
                replay=[]
                ok=True
                for _ in range(2):
                    remaining=deadline-time.monotonic()
                    if remaining<=0:
                        budget_exhausted=True
                        ok=False
                        break
                    source.write_bytes(candidate.encode("utf-8"))
                    _purge_source_bytecode(source)
                    remaining=deadline-time.monotonic()
                    if remaining<=0:
                        budget_exhausted=True
                        ok=False
                        break
                    rr=guarded_run(candidate.encode("utf-8"),min(timeout_s,remaining))
                    source.write_bytes(original_bytes)
                    _purge_source_bytecode(source)
                    replay.append({
                        "returncode":rr["returncode"],
                        "timed_out":rr["timed_out"],
                        "elapsed_s":rr["elapsed_s"],
                    })
                    ok=ok and rr["returncode"]==0 and not rr["timed_out"]
                    if rr["timed_out"] and time.monotonic()>=deadline:
                        budget_exhausted=True
                        break
                if ok:
                    winner=(candidate,desc,replay)
                    break
                if budget_exhausted:break
    finally:
        source.write_bytes(original_bytes)
        _purge_source_bytecode(source)
    rel=str(source.relative_to(repo)).replace("\\","/")
    result={
        "schema":SCHEMA,
        "status":("PASS__VERIFIED_CANDIDATE_PATCH_FOUND" if winner else
                  "OPEN__WALL_TIME_BUDGET_EXHAUSTED" if budget_exhausted else
                  "OPEN__NO_VERIFIED_CANDIDATE_IN_BOUNDED_SEARCH"),
        "pass":winner is not None,
        "max_wall_time_s":max_wall_time_s,
        "wall_time_budget_exhausted":budget_exhausted,
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
